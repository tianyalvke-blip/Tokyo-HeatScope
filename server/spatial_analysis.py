"""
spatial_analysis.py — Local Moran's I for the Tokyo LST grid.

Optional, self-contained module for the GLEN LST Agent experimental branch.

Key properties:
  * `is_available()` is False if geopandas / libpysal / esda cannot be loaded;
    the MCP server then exposes `local_moran()` as UNAVAILABLE instead of
    failing to boot.
  * Source data is READ ONLY. Intermediate artifacts (Queen weights, results)
    live under server/cache/local_moran/ and are always regenerable — delete
    them and the next call recomputes from source.
  * `query()` / `get_stac_details()` / map tools are NOT touched by this module.
"""

import json
import logging
from pathlib import Path

log = logging.getLogger("spatial_analysis")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = PROJECT_ROOT / "app"
PARQUET = WEB_ROOT / "data" / "tokyo_lst_grid.parquet"
CACHE_DIR = PROJECT_ROOT / "server" / "cache" / "local_moran"

QUADRANT_LABELS = {1: "HH", 2: "LH", 3: "LL", 4: "HL"}

_available = None


def is_available() -> bool:
    """True when the spatial-analysis stack is importable (checked once)."""
    global _available
    if _available is None:
        try:
            import geopandas  # noqa: F401
            import libpysal  # noqa: F401
            import esda  # noqa: F401
            _available = True
        except Exception as exc:  # pragma: no cover - env-dependent
            log.warning("spatial stack unavailable: %s", exc)
            _available = False
    return _available


def _load_gdf():
    """Load the LST grid with polygon geometries (source data, read-only)."""
    import pandas as pd
    import geopandas as gpd
    from shapely import wkt

    df = pd.read_parquet(PARQUET)
    df["geometry"] = df["geometry_wkt"].map(wkt.loads)
    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
    gdf = gdf.dropna(subset=["geometry"])
    return gdf


def _queen_weights(gdf):
    """Queen contiguity weights, cached on disk (regenerable).

    libpysal 4.x dropped W.to_json(), so the neighbor/weight dicts are cached
    as plain JSON and rebuilt via W(neighbors, id_order=...). JSON keys are
    always strings, so ids are normalized to strings on both save and load.
    """
    import libpysal

    def _str_dict(neighbors):
        return {str(k): [str(n) for n in v] for k, v in neighbors.items()}

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / "queen_weights.json"
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            return libpysal.weights.W(data["neighbors"], id_order=data["id_order"])
        except Exception as exc:
            log.warning("weights cache unreadable (%s); recomputing", exc)
    w = libpysal.weights.Queen.from_dataframe(gdf, use_index=True, silence_warnings=True)
    payload = {"neighbors": _str_dict(w.neighbors), "id_order": [str(i) for i in w.id_order]}
    cache_file.write_text(json.dumps(payload), encoding="utf-8")
    return w


def compute_local_moran(column: str = "day_lst", permutations: int = 999, seed: int = 0):
    """Compute Local Moran's I for one grid column.

    Returns `(summary, results_df)` where `results_df` has columns
    grid_id / lisa / p_sim / cluster ('HH','LH','LL','HL') / significant.
    Persistence into the Analysis Result Store is the caller's job (the MCP
    `local_moran` tool registers it and returns a compact `analysis_id`).

    Computation is cached per (column, permutations) under
    server/cache/local_moran/ and can be deleted at any time — it is rebuilt
    from the source parquet.
    """
    if not is_available():
        raise RuntimeError("spatial analysis dependencies are not available")

    import numpy as np
    import pandas as pd
    import esda

    perms = int(permutations)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    # Cache keyed by (column, permutations) so different significance settings
    # never share results. Regenerable: delete the files to recompute.
    parquet_path = CACHE_DIR / f"moran_{column}_p{perms}.parquet"
    summary_path = CACHE_DIR / f"moran_{column}_p{perms}.json"

    # Cache hit → reuse (regenerable: delete files to recompute).
    if parquet_path.exists() and summary_path.exists():
        results = pd.read_parquet(parquet_path)
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        return summary, results

    gdf = _load_gdf()
    if column not in gdf.columns:
        raise ValueError(
            f"column '{column}' not in grid. Available: {[c for c in gdf.columns if c in ('day_lst','night_lst','day_night_gap','ndvi','bldg_coverage_ratio','elevation_mean','water_ratio')]}"
        )
    y = gdf[column].to_numpy(dtype=float)
    w = _queen_weights(gdf)

    local = esda.Moran_Local(y, w, transformation="R", permutations=perms, seed=seed)
    global_moran = esda.Moran(y, w, permutations=min(perms, 999))

    results = pd.DataFrame({
        "grid_id": gdf["grid_id"].to_numpy(),
        "lisa": local.Is,
        "p_sim": local.p_sim,
        "cluster": [QUADRANT_LABELS.get(int(q), "") for q in local.q],
    })
    results["significant"] = results["p_sim"].notna() & (results["p_sim"] <= 0.05)

    sig = results[results["significant"]]
    cluster_counts = results["cluster"].value_counts().to_dict()
    sig_counts = sig["cluster"].value_counts().to_dict()

    # Representative examples for the LLM summary (top |lisa| significant).
    ex = sig.reindex(sig["lisa"].abs().sort_values(ascending=False).index).head(5)
    example_rows = [
        {"grid_id": int(r.grid_id), "cluster": r.cluster, "lisa": round(float(r.lisa), 3),
         "p_sim": round(float(r.p_sim), 4)}
        for r in ex.itertuples()
    ]

    summary = {
        "column": column,
        "n": int(len(results)),
        "n_significant": int(len(sig)),
        "global_moran_i": round(float(global_moran.I), 4),
        "global_p_value": round(float(global_moran.p_sim), 4),
        "cluster_counts": {k: int(cluster_counts.get(k, 0)) for k in ("HH", "LH", "LL", "HL")},
        "significant_cluster_counts": {k: int(sig_counts.get(k, 0)) for k in ("HH", "LH", "LL", "HL")},
        "example_rows": example_rows,
    }
    results.to_parquet(parquet_path, index=False)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
    return summary, results
