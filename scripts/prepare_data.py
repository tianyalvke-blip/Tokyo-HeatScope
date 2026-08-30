"""
prepare_data.py — Build GLEN LST Agent data artifacts from the source CSV.

Reads:
    tokyo_lst_grid_flat.csv        (source of truth, never modified)
    tokyo_lst_grid_metadata.json

Writes (into app/data/, the web root):
    app/data/tokyo_lst_grid.parquet   — flat table for DuckDB / MCP SQL analytics
    app/data/tokyo_lst_grid.geojson   — 200 m grid polygons for MapLibre
    app/data/catalog.json             — minimal local STAC-like catalog
    app/data/tokyo-lst/collection.json— STAC-like collection for the LST grid

The CSV and metadata JSON are left untouched.
"""

import csv
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "tokyo_lst_grid_flat.csv"
META_PATH = ROOT / "tokyo_lst_grid_metadata.json"
OUT = ROOT / "app" / "data"

# Analytical columns exposed to the agent and the map. Names match the CSV
# exactly so set_filter / filter_by_query / get_schema stay consistent.
NUMERIC_FIELDS = [
    "day_lst", "night_lst", "day_night_gap",
    "dist_to_coast", "elevation_mean", "water_ratio", "dist_to_major_river",
    "avg_height", "road_length", "bldg_coverage_ratio", "svf_mean",
    "height_variance", "ndvi",
]
# geometry_wkt is carried into the parquet as text (spatial joins later);
# it is not exposed as a GeoJSON property (geometry is parsed instead).
PARQUET_EXTRA_FIELDS = ["geometry_wkt"]

# CSIS census population (2020), area-weighted from the 100m mesh to this grid.
# Read from the resample output; missing file simply yields zero population.
POP_CSV = ROOT / "data" / "processed" / "grid_pop2020.csv"
POP_FIELDS = ["pop_2020_total", "pop_0_14", "pop_15_64", "pop_65_over", "pop_2020_density_km2"]


def parse_wkt_polygon(wkt):
    """Parse 'POLYGON ((x y, x y, ...))' -> list of [lon, lat] rings.

    Robust to optional Z and optional inner-ring parentheses. Axis-aligned
    200 m squares have a single exterior ring.
    """
    if not wkt:
        return None
    m = re.search(r"POLYGON\s*\((.*)\)\s*$", wkt, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    inner = m.group(1).strip()
    rings = []
    # Split ring groups (handles '(...),(...)' and bare 'x y, x y').
    groups = re.findall(r"\((.*?)\)", inner)
    if not groups:
        groups = [inner]
    for g in groups:
        ring = []
        for token in g.split(","):
            parts = token.split()
            if len(parts) < 2:
                continue
            lon, lat = float(parts[0]), float(parts[1])
            ring.append([lon, lat])
        if len(ring) >= 4:
            rings.append(ring)
    if not rings:
        return None
    return rings


def to_number(v):
    if v is None or (isinstance(v, str) and v.strip() in ("", "nan", "None", "null")):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def to_int(v):
    n = to_number(v)
    return int(n) if n is not None else None


def build_features(rows, pop_lookup=None):
    features = []
    for r in rows:
        wkt = r.get("geometry_wkt", "")
        rings = parse_wkt_polygon(wkt)
        if rings is None:
            continue
        props = {"grid_id": to_int(r.get("grid_id"))}
        props["centroid_lon"] = to_number(r.get("centroid_lon"))
        props["centroid_lat"] = to_number(r.get("centroid_lat"))
        for f in NUMERIC_FIELDS:
            props[f] = to_number(r.get(f))
        pop = (pop_lookup or {}).get(to_int(r.get("grid_id")))
        if pop:
            for f in POP_FIELDS:
                props[f] = to_number(pop.get(f))
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": {"type": "Polygon", "coordinates": rings},
        })
    return features


def load_pop_lookup():
    """grid_id -> row dict from the population join table (empty if absent)."""
    lookup = {}
    if not POP_CSV.exists():
        return lookup
    with open(POP_CSV, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                lookup[int(row["grid_id"])] = row
            except (KeyError, ValueError):
                continue
    print(f"population join: {len(lookup)} grids (from {POP_CSV.name})")
    return lookup


def main():
    if not CSV_PATH.exists():
        print(f"ERROR: missing {CSV_PATH}")
        sys.exit(1)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "tokyo-lst").mkdir(parents=True, exist_ok=True)

    meta = json.loads(META_PATH.read_text(encoding="utf-8")) if META_PATH.exists() else {}

    with open(CSV_PATH, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    print(f"CSV rows: {len(rows)}")

    # ---- GeoJSON -------------------------------------------------------
    pop_lookup = load_pop_lookup()
    features = build_features(rows, pop_lookup)
    geojson = {"type": "FeatureCollection", "features": features}
    lons = [f["geometry"]["coordinates"][0][i][0] for f in features for i in (0, 1, 2, 3)]
    lats = [f["geometry"]["coordinates"][0][i][1] for f in features for i in (0, 1, 2, 3)]
    bbox = [min(lons), min(lats), max(lons), max(lats)]
    print(f"GeoJSON features: {len(features)}")
    print(f"bbox: {bbox}")

    gj_path = OUT / "tokyo_lst_grid.geojson"
    with open(gj_path, "w", encoding="utf-8") as fh:
        json.dump(geojson, fh, separators=(",", ":"))
    print(f"wrote {gj_path} ({gj_path.stat().st_size / 1e6:.1f} MB)")

    # ---- Parquet -------------------------------------------------------
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        print("pyarrow not available; skipping parquet")
        return

    cols = []
    cols.append(("grid_id", pa.int32()))
    cols.append(("centroid_lon", pa.float64()))
    cols.append(("centroid_lat", pa.float64()))
    for f in NUMERIC_FIELDS:
        cols.append((f, pa.float64()))
    for f in POP_FIELDS:
        cols.append((f, pa.float64()))
    cols.append(("geometry_wkt", pa.string()))
    for f in PARQUET_EXTRA_FIELDS:
        if f == "geometry_wkt":
            continue
        cols.append((f, pa.float64()))

    arrays = {}
    arrays["grid_id"] = pa.array([to_int(r.get("grid_id")) for r in rows], type=pa.int32())
    arrays["centroid_lon"] = pa.array([to_number(r.get("centroid_lon")) for r in rows], type=pa.float64())
    arrays["centroid_lat"] = pa.array([to_number(r.get("centroid_lat")) for r in rows], type=pa.float64())
    for f in NUMERIC_FIELDS:
        arrays[f] = pa.array([to_number(r.get(f)) for r in rows], type=pa.float64())
    for f in POP_FIELDS:
        arrays[f] = pa.array(
            [to_number((pop_lookup or {}).get(to_int(r.get("grid_id")), {}).get(f))
             if (pop_lookup or {}).get(to_int(r.get("grid_id"))) else None
             for r in rows],
            type=pa.float64(),
        )
    arrays["geometry_wkt"] = pa.array([(r.get("geometry_wkt") or "").strip() for r in rows], type=pa.string())

    table = pa.table(arrays, schema=pa.schema([pa.field(n, t) for n, t in cols]))
    pq_path = OUT / "tokyo_lst_grid.parquet"
    pq.write_table(table, pq_path)
    print(f"wrote {pq_path} ({pq_path.stat().st_size / 1e6:.1f} MB)")

    # ---- Catalog (local STAC-like) ------------------------------------
    catalog = {
        "type": "Catalog",
        "id": "glen-tokyo-lst-catalog",
        "title": "GLEN Tokyo LST",
        "description": "Tokyo 200 m day/night LST grid catalog (local).",
        "links": [{"rel": "self", "href": "data/catalog.json"}],
    }
    (OUT / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")

    column_defs = [
        {"name": "grid_id", "type": "integer", "description": "Unique spatial unit ID of the 200 m grid cell"},
        {"name": "day_lst", "type": "number", "description": "Daytime Land Surface Temperature (degrees Celsius)"},
        {"name": "night_lst", "type": "number", "description": "Nighttime Land Surface Temperature (degrees Celsius)"},
        {"name": "day_night_gap", "type": "number", "description": "Daytime minus nighttime LST (degrees Celsius)"},
        {"name": "centroid_lon", "type": "number", "description": "Grid cell centroid longitude (EPSG:4326)"},
        {"name": "centroid_lat", "type": "number", "description": "Grid cell centroid latitude (EPSG:4326)"},
        {"name": "dist_to_coast", "type": "number", "description": "Distance to coastline (meters)"},
        {"name": "elevation_mean", "type": "number", "description": "Mean elevation (meters)"},
        {"name": "water_ratio", "type": "number", "description": "Fraction of the cell covered by water (0-1)"},
        {"name": "dist_to_major_river", "type": "number", "description": "Distance to nearest major river (meters)"},
        {"name": "avg_height", "type": "number", "description": "Mean building height (meters); null where no buildings"},
        {"name": "road_length", "type": "number", "description": "Total road length within the cell (meters)"},
        {"name": "bldg_coverage_ratio", "type": "number", "description": "Building footprint coverage ratio (0-1)"},
        {"name": "svf_mean", "type": "number", "description": "Mean sky view factor (0-1)"},
        {"name": "height_variance", "type": "number", "description": "Variance of building heights; null where no buildings"},
        {"name": "ndvi", "type": "number", "description": "Normalized Difference Vegetation Index"},
        {"name": "pop_2020_total", "type": "number", "description": "Census population (2020) area-weighted to the 200 m grid (CSIS simple 100 m mesh)"},
        {"name": "pop_2020_density_km2", "type": "number", "description": "pop_2020_total / 0.04 km2 (persons per square kilometre)"},
        {"name": "pop_0_14", "type": "number", "description": "Population aged 0-14 (2020, area-weighted)"},
        {"name": "pop_15_64", "type": "number", "description": "Population aged 15-64 (2020, area-weighted)"},
        {"name": "pop_65_over", "type": "number", "description": "Population aged 65+ (2020, area-weighted)"},
    ]

    collection = {
        "type": "Collection",
        "id": "tokyo-lst",
        "title": "Tokyo Day-Night LST Grid (200 m)",
        "description": (
            "Daytime and nighttime land surface temperature (LST) for a 200 m x 200 m grid "
            "over Tokyo 23 Wards, with urban covariates. LST is the temperature of the land "
            "surface, NOT air temperature. Units: degrees Celsius."
        ),
        "license": "proprietary",
        "keywords": ["LST", "land surface temperature", "Tokyo", "urban heat", "200m grid"],
        "providers": [{"name": "GLEN LST Project", "roles": ["producer", "licensor"]}],
        "extent": {"spatial": {"bbox": [bbox]}, "temporal": {"interval": [[None, None]]}},
        "table:columns": column_defs,
        "assets": {
            "grid-geojson": {
                "title": "Tokyo LST grid (GeoJSON)",
                "type": "application/geo+json",
                "href": "data/tokyo_lst_grid.geojson",
                "description": "200 m grid polygons with day_lst / night_lst and urban covariates (map display).",
            },
            "grid-parquet": {
                "title": "Tokyo LST grid (Parquet)",
                "type": "application/vnd.apache.parquet",
                "href": "data/tokyo_lst_grid.parquet",
                "description": "Flat tabular form of the grid for SQL analytics.",
            },
        },
    }
    (OUT / "tokyo-lst" / "collection.json").write_text(
        json.dumps(collection, indent=2), encoding="utf-8"
    )
    print("wrote catalog.json + tokyo-lst/collection.json")

    # ---- Summary -------------------------------------------------------
    def mm(f):
        vals = [to_number(r.get(f)) for r in rows]
        vals = [v for v in vals if v is not None]
        return (round(min(vals), 2), round(max(vals), 2))

    print("\nColumn ranges:")
    for f in ["day_lst", "night_lst", "day_night_gap", "ndvi", "water_ratio",
              "avg_height", "road_length", "bldg_coverage_ratio", "svf_mean",
              "height_variance", "elevation_mean", "dist_to_coast", "dist_to_major_river"]:
        print(f"  {f}: {mm(f)}")
    if pop_lookup:
        for f in POP_FIELDS:
            vals = [to_number(v.get(f)) for v in pop_lookup.values()]
            vals = [v for v in vals if v is not None]
            if vals:
                print(f"  {f}: {round(min(vals), 2)}..{round(max(vals), 2)}")
    print(f"\nmetadata row_count: {meta.get('row_count')}")


if __name__ == "__main__":
    main()
