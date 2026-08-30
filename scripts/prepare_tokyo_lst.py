"""Prepare the GLEN Tokyo LST analysis assets.

Pipeline (idempotent, re-runnable):

  tokyo_lst_grid_flat.csv  (joined + field-standardized flat table, 14896 rows)
        +
  data/processed/grid_pop2020.csv  (CSIS 100m population resampled to 200m grid)
        |
        v
  data/processed/tokyo_lst_grid.parquet   (analysis layer -> DuckDB)
  public/data/tokyo_lst_grid.geojson      (map layer -> MapLibre, EPSG:4326)
  data/metadata/tokyo_lst_grid_metadata.json

Derived fields added without touching the source table:
  avg_height_filled       = avg_height       where bldg_coverage_ratio > 0 else 0
  height_variance_filled  = height_variance  where bldg_coverage_ratio > 0 else 0
  (no-building grids keep their original NULLs in the raw columns)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
from shapely import wkt

REPO = Path(__file__).resolve().parents[1]
FLAT_CSV = Path(os.environ.get("GRID_FLAT_CSV", REPO / "tokyo_lst_grid_flat.csv"))
POP_CSV = REPO / "data" / "processed" / "grid_pop2020.csv"
PARQUET_OUT = REPO / "data" / "processed" / "tokyo_lst_grid.parquet"
GEOJSON_OUT = REPO / "public" / "data" / "tokyo_lst_grid.geojson"
META_OUT = REPO / "data" / "metadata" / "tokyo_lst_grid_metadata.json"

# Analysis columns carried into parquet + geojson (map display + popup).
ANALYSIS_COLS = [
    "grid_id", "day_lst", "night_lst", "day_night_gap",
    "dist_to_coast", "elevation_mean", "water_ratio", "dist_to_major_river",
    "avg_height", "road_length", "bldg_coverage_ratio", "svf_mean",
    "height_variance", "ndvi",
    "avg_height_filled", "height_variance_filled",
    "pop_2020_total", "pop_2020_density_km2",
    "centroid_lon", "centroid_lat",
]


def load_base() -> pd.DataFrame:
    df = pd.read_csv(FLAT_CSV, low_memory=False)
    df["grid_id"] = df["grid_id"].astype(int)
    dup = df["grid_id"].duplicated().sum()
    if dup:
        raise ValueError(f"duplicate grid_id in flat csv: {dup}")
    return df


def add_population(df: pd.DataFrame) -> pd.DataFrame:
    if not POP_CSV.exists():
        print("[prepare] population join table missing; adding zero population")
        for col in ["pop_2020_total", "pop_2020_density_km2", "pop_0_14", "pop_15_64", "pop_65_over"]:
            df[col] = 0.0
        return df
    pop = pd.read_csv(POP_CSV)
    pop["grid_id"] = pop["grid_id"].astype(int)
    merged = df.merge(pop, on="grid_id", how="left")
    for col in ["pop_2020_total", "pop_2020_density_km2", "pop_0_14", "pop_15_64", "pop_65_over"]:
        merged[col] = merged[col].fillna(0.0)
    return merged


def add_derived(df: pd.DataFrame) -> pd.DataFrame:
    # No-building grids (bldg_coverage_ratio == 0) have no meaningful building
    # height stats. Semantic fill keeps raw columns intact.
    no_bldg = df["bldg_coverage_ratio"].fillna(0) == 0
    df["avg_height_filled"] = df["avg_height"].where(~no_bldg, 0.0)
    df["height_variance_filled"] = df["height_variance"].where(~no_bldg, 0.0)
    return df


def build_parquet(df: pd.DataFrame) -> None:
    out = df[ANALYSIS_COLS].copy()
    PARQUET_OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(PARQUET_OUT, index=False, engine="pyarrow")
    print(f"[prepare] parquet -> {PARQUET_OUT} ({len(out)} rows, {out.shape[1]} cols)")


def build_geojson(df: pd.DataFrame) -> dict:
    geoms = [wkt.loads(g) for g in df["geometry_wkt"]]
    features = []
    for row, geom in zip(df.to_dict(orient="records"), geoms):
        props = {c: (None if pd.isna(row[c]) else row[c]) for c in ANALYSIS_COLS}
        features.append({"type": "Feature", "properties": props, "geometry": __import__("shapely.geometry", fromlist=["mapping"]).mapping(geom)})
    return {"type": "FeatureCollection", "features": features}


def main() -> int:
    import shapely.geometry

    df = load_base()
    df = add_population(df)
    df = add_derived(df)

    # ---- GeoJSON ----
    collection = build_geojson(df)
    GEOJSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(GEOJSON_OUT, "w", encoding="utf-8") as fh:
        json.dump(collection, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"[prepare] geojson -> {GEOJSON_OUT} ({len(collection['features'])} features)")

    # ---- Parquet ----
    build_parquet(df)

    # ---- Metadata ----
    null_report = {c: int(df[c].isna().sum()) for c in
                   ["avg_height", "height_variance", "svf_mean", "day_lst", "night_lst"]}
    no_bldg = int((df["bldg_coverage_ratio"].fillna(0) == 0).sum())
    stats = {}
    for c in ["day_lst", "night_lst", "day_night_gap", "ndvi", "pop_2020_total"]:
        s = df[c].dropna()
        stats[c] = {"min": round(float(s.min()), 3), "max": round(float(s.max()), 3),
                    "mean": round(float(s.mean()), 3), "count": int(s.notna().sum())}

    xs = df["centroid_lon"]
    ys = df["centroid_lat"]
    meta = {
        "dataset_name": "Tokyo 200m Day-Night LST Grid",
        "row_count": int(len(df)),
        "study_area": "Tokyo 23 Wards",
        "spatial_unit": "200m x 200m grid",
        "grid_id_range": [int(df["grid_id"].min()), int(df["grid_id"].max())],
        "map_crs": "EPSG:4326",
        "analysis_crs": "EPSG:32654",
        "bbox": {
            "west": round(float(xs.min()), 6), "south": round(float(ys.min()), 6),
            "east": round(float(xs.max()), 6), "north": round(float(ys.max()), 6),
            "center": [round(float(xs.mean()), 6), round(float(ys.mean()), 6)],
        },
        "temperature_fields": {
            "day_lst": "Daytime Land Surface Temperature (deg C)",
            "night_lst": "Nighttime Land Surface Temperature (deg C)",
            "day_night_gap": "day_lst - night_lst (deg C)",
            "warning": "LST is land surface temperature, NOT air temperature.",
        },
        "null_counts": null_report,
        "no_building_grids": no_bldg,
        "derived_fields": {
            "avg_height_filled": "avg_height where bldg_coverage_ratio>0 else 0",
            "height_variance_filled": "height_variance where bldg_coverage_ratio>0 else 0",
            "pop_2020_total": "CSIS simple 100m census population (2020), area-weighted to grid",
            "pop_2020_density_km2": "pop_2020_total / 0.04",
        },
        "value_stats": stats,
        "population_metadata": "data/metadata/csis_pop2020_metadata.json",
    }
    META_OUT.parent.mkdir(parents=True, exist_ok=True)
    META_OUT.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[prepare] metadata -> {META_OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
