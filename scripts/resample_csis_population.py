"""Resample the CSIS "Simple 100m Mesh Population 2020" data onto the GLEN 200m grid.

Reads:
  - CSIS 100m mesh population CSVs (one per Tokyo 23 ward: 13101-13123),
    downloaded from the gtfs-gis.jp mirror of the University of Tokyo CSIS
    "Kokusei Chosa ni Motozuku Kani 100m Mesh Jinko Data (2020)".
      F:\TokyoCSIS_Population_100m\100m_mesh_pop2020_13xxx.zip
  - The GLEN 200m grid (grid_id + geometry_wkt) from tokyo_lst_grid_flat.csv.

Writes:
  - data/processed/grid_pop2020.csv  -> join table: grid_id, pop_2020_total,
    pop_2020_density_km2, pop_0_14, pop_15_64, pop_65_over.
  - data/metadata/csis_pop2020_metadata.json  -> provenance + coverage report.

Method:
  1. Parse each 10-digit 100m mesh code (JIS X 0410 4th-level mesh) into a
     cell polygon (top-left corner + 3" lat x 4.5" lon extent).
  2. Concatenate all ward CSVs, keep Meshcode, Shicode, PopT, Pop0_14,
     Pop15_64, Pop65over.
  3. Area-weighted resampling: for each 200m grid, population equals the sum
     over intersecting 100m cells of (cell_population * intersection_area /
     cell_area). Both geometries are projected to EPSG:32654 (UTM 54N) for
     accurate area math, matching the study grid's native CRS.

The script is idempotent: it can be re-run after the CSIS folder is updated.

The population source is a static 2020 census distribution, NOT a time-series.
"""

from __future__ import annotations

import json
import os
import sys
import zipfile
from pathlib import Path

import pandas as pd
from shapely.geometry import Polygon

# ---- paths (all derived, overridable via env) -------------------------------
REPO = Path(__file__).resolve().parents[1]
CSIS_DATA_DIR = Path(os.environ.get("CSIS_DATA_DIR", r"F:\TokyoCSIS_Population_100m"))
GRID_FLAT_CSV = Path(os.environ.get("GRID_FLAT_CSV", REPO / "tokyo_lst_grid_flat.csv"))
OUT_DIR = REPO / "data" / "processed"
META_DIR = REPO / "data" / "metadata"

TOKYO23_WARDS = list(range(13101, 13124))  # Chiyoda-ku .. Edogawa-ku


def decode_100m_mesh(code) -> Polygon:
    """Convert a 10-digit JIS X 0410 4th-level (100m) mesh code to a lat/lon polygon.

    Code layout (e.g. 5339450937):
      digits 0-1 : 1st-level lat band (value = d0*10+d1, top lat = value * 2/3 deg)
      digits 2-3 : 1st-level lon band (value = d2*10+d3, left lon = 100 + value)
      digits 4,5 : 2nd-level lat, lon (5' lat, 7.5' lon offsets)
      digits 6,7 : 3rd-level lat, lon (30" lat, 45" lon offsets)
      digits 8,9 : 4th-level lat, lon (3" lat, 4.5" lon offsets)
    Cell extent: 3 arcsec lat x 4.5 arcsec lon.
    """
    s = str(int(code)).zfill(10)
    la1, la2 = int(s[0]), int(s[1])
    lo1, lo2 = int(s[2]), int(s[3])
    a2, b2 = int(s[4]), int(s[5])
    a3, b3 = int(s[6]), int(s[7])
    a4, b4 = int(s[8]), int(s[9])

    lat_top = (la1 * 10 + la2) * (2 / 3) + a2 * (5 / 60) + a3 * (30 / 3600) + a4 * (3 / 3600)
    lon_left = 100 + (lo1 * 10 + lo2) + b2 * (7.5 / 60) + b3 * (45 / 3600) + b4 * (4.5 / 3600)

    d_lat = 3 / 3600
    d_lon = 4.5 / 3600
    return Polygon([
        (lon_left, lat_top),
        (lon_left + d_lon, lat_top),
        (lon_left + d_lon, lat_top - d_lat),
        (lon_left, lat_top - d_lat),
        (lon_left, lat_top),
    ])


def read_csis_csv(zip_path: Path, csv_name: str) -> pd.DataFrame:
    """Read one ward CSV (cp932 encoded) from inside its zip."""
    with zipfile.ZipFile(zip_path) as z:
        raw = z.read(csv_name)
    for enc in ("cp932", "utf-8-sig", "shift_jis"):
        try:
            return pd.read_csv(pd.io.common.BytesIO(raw), encoding=enc,
                               dtype={"Meshcode": str, "Shicode": str})
        except (UnicodeDecodeError, Exception):
            continue
    raise ValueError(f"could not decode {csv_name}")


def load_csis_cells() -> pd.DataFrame:
    """Load + parse every Tokyo 23-ward 100m population cell."""
    frames = []
    for ward in TOKYO23_WARDS:
        zips = sorted(CSIS_DATA_DIR.glob(f"100m_mesh_pop2020_{ward}.zip"))
        if not zips:
            print(f"[csis] missing zip for ward {ward}, skipping")
            continue
        with zipfile.ZipFile(zips[0]) as z:
            csv_names = [n for n in z.namelist() if n.lower().endswith(".csv")]
            if not csv_names:
                print(f"[csis] no csv in {zips[0].name}")
                continue
            df = read_csis_csv(zips[0], csv_names[0])
            df["ward"] = ward
            frames.append(df)
    if not frames:
        raise FileNotFoundError(
            f"no CSIS 100m population zips found under {CSIS_DATA_DIR}; "
            "download the Tokyo 23 ward files first."
        )
    cells = pd.concat(frames, ignore_index=True)
    cells["geometry"] = cells["Meshcode"].map(decode_100m_mesh)
    print(f"[csis] loaded {len(cells)} 100m cells from {len(frames)} wards")
    return cells


def main() -> int:
    import geopandas as gpd

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    META_DIR.mkdir(parents=True, exist_ok=True)

    # 1) 100m population cells (EPSG:4326).
    cells = load_csis_cells()
    gdf_100 = gpd.GeoDataFrame(
        cells[["Meshcode", "Shicode", "ward", "PopT", "Pop0_14", "Pop15_64", "Pop65over"]],
        geometry=cells["geometry"], crs="EPSG:4326",
    )
    # Mesh cells carry no CRS area meaning in degrees -> project to UTM 54N.
    gdf_100 = gdf_100.to_crs("EPSG:32654")
    gdf_100["cell_area"] = gdf_100.geometry.area

    # 2) GLEN 200m grid (geometry_wkt is EPSG:4326 in the flat CSV).
    if not GRID_FLAT_CSV.exists():
        raise FileNotFoundError(f"grid flat csv not found: {GRID_FLAT_CSV}")
    grid = pd.read_csv(GRID_FLAT_CSV, usecols=["grid_id", "geometry_wkt"])
    gdf_grid = gpd.GeoDataFrame(
        grid[["grid_id"]],
        geometry=gpd.GeoSeries.from_wkt(grid["geometry_wkt"]),
        crs="EPSG:4326",
    ).to_crs("EPSG:32654")

    # 3) Area-weighted resampling: join 100m cells to 200m grids.
    joined = gpd.sjoin(gdf_grid, gdf_100, predicate="intersects", how="inner")
    grid_geom = gpd.GeoSeries(joined.geometry, index=joined.index)
    cell_geom = gpd.GeoSeries(gdf_100.loc[joined.index_right, "geometry"].values,
                              index=joined.index)
    joined["inter_area"] = grid_geom.intersection(cell_geom).area
    joined["cell_area"] = cell_geom.area
    joined["frac"] = joined["inter_area"] / joined["cell_area"]
    joined["pop_w"] = joined["PopT"] * joined["frac"]
    joined["p0_w"] = joined["Pop0_14"] * joined["frac"]
    joined["p15_w"] = joined["Pop15_64"] * joined["frac"]
    joined["p65_w"] = joined["Pop65over"] * joined["frac"]

    agg = joined.groupby("grid_id").agg(
        pop_2020_total=("pop_w", "sum"),
        pop_0_14=("p0_w", "sum"),
        pop_15_64=("p15_w", "sum"),
        pop_65_over=("p65_w", "sum"),
    ).reset_index()
    agg["pop_2020_total"] = agg["pop_2020_total"].round(3)
    agg["pop_0_14"] = agg["pop_0_14"].round(3)
    agg["pop_15_64"] = agg["pop_15_64"].round(3)
    agg["pop_65_over"] = agg["pop_65_over"].round(3)
    # 200m grid = 0.04 km2.
    agg["pop_2020_density_km2"] = (agg["pop_2020_total"] / 0.04).round(1)

    # Fill grids with no intersecting cell with 0 population.
    out = grid[["grid_id"]].merge(agg, on="grid_id", how="left")
    for col in ["pop_2020_total", "pop_0_14", "pop_15_64", "pop_65_over", "pop_2020_density_km2"]:
        out[col] = out[col].fillna(0.0)

    out_path = OUT_DIR / "grid_pop2020.csv"
    out.to_csv(out_path, index=False, encoding="utf-8")

    # 4) Provenance + coverage report.
    total_pop = float(out["pop_2020_total"].sum())
    wards_covered = int(cells["ward"].nunique())
    report = {
        "source": "CSIS Kokusei Chosa ni Motozuku Kani 100m Mesh Jinko Data 2020 "
                  "(mirror: gtfs-gis.jp)",
        "source_crs": "EPSG:4612 (JGD2000 geographic)",
        "source_url": "https://gtfs-gis.jp/teikyo/kani_100m_download2020.html",
        "wards_downloaded": wards_covered,
        "cell_count_100m": int(len(cells)),
        "grid_count_200m": int(len(out)),
        "resample_method": "area-weighted (intersection_area / cell_area), EPSG:32654",
        "total_population": round(total_pop, 1),
        "official_census_total_2020": 9668047,
        "population_caveat": (
            "CSIS 'Kani' (simple) mesh population is allocated proportionally; "
            "summing cells runs ~6% above the official 2020 census ward totals "
            "(per-ward +2%..+14%). Use for RELATIVE density comparisons, not as "
            "an exact headcount."
        ),
        "pop_field": "pop_2020_total",
        "density_field": "pop_2020_density_km2 (persons per km2, grid=0.04 km2)",
        "note": "static 2020 census population; not a time series.",
    }
    meta_path = META_DIR / "csis_pop2020_metadata.json"
    meta_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[csis] wrote {out_path} ({len(out)} grids)")
    print(f"[csis] total population (23 wards): {total_pop:,.1f}")
    print(f"[csis] metadata -> {meta_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
