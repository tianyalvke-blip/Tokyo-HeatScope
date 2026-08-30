"""
result_store.py — Analysis Result Store / Registry for the GLEN LST Agent.

All derived spatial analysis outputs (Local Moran, SQL grid selections, custom
Python results, and future RF / SHAP / scenario outputs) are persisted here as:

    server/cache/analysis-results/<analysis_id>.parquet    canonical data (grid_id + derived fields)
    server/cache/analysis-results/<analysis_id>.json       records served to the browser
    server/cache/analysis-results/<analysis_id>.meta.json  metadata (visualization, tooltip, ...)

Geometry is NOT stored — the frontend joins `grid_id` onto the shared Tokyo
200 m grid geometry at display time, so no tool ever regenerates polygons.

Everything in this store is a cache: delete the files and re-run the analysis
to regenerate. Source data (CSV / parquet / GeoJSON / PMTiles) is never touched.
"""

import itertools
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULT_DIR = PROJECT_ROOT / "server" / "cache" / "analysis-results"

_counter = itertools.count(1)

# Visualization types supported by the frontend Result Layer Manager.
VIZ_TYPES = ("categorical", "continuous", "binary", "diverging")


def new_analysis_id(kind: str) -> str:
    """Generate a unique analysis id like `local_moran_day_lst_1700000000_1`."""
    return f"{kind}_{int(time.time())}_{next(_counter)}"


def _url(name: str) -> str:
    # Served by serve.py's /results/ external root.
    return f"/results/{name}"


def register_result(*, analysis_id, analysis_type, display_name,
                    source_dataset="tokyo-lst", source_field=None,
                    visualization=None, tooltip_fields=None, df):
    """Persist a grid_id-keyed result DataFrame + metadata.

    `df` must contain a `grid_id` column; all other columns become derived
    result fields. Returns the metadata dict.
    """
    import pandas as pd  # noqa: F401  (imported lazily for safe degradation)

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    if "grid_id" not in df.columns:
        raise ValueError("result data must contain a 'grid_id' column")
    cols = ["grid_id"] + [c for c in df.columns
                          if c != "grid_id" and str(c).lower() not in ("geometry", "geom")]
    df = df[cols]

    df.to_parquet(RESULT_DIR / f"{analysis_id}.parquet", index=False)
    records = df.to_dict("records")
    (RESULT_DIR / f"{analysis_id}.json").write_text(
        json.dumps(records, default=str), encoding="utf-8"
    )

    meta = {
        "analysis_id": analysis_id,
        "analysis_type": analysis_type,
        "source_dataset": source_dataset,
        "source_field": source_field,
        "display_name": display_name,
        "visualization": visualization,
        "tooltip_fields": tooltip_fields or [],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "n": int(len(df)),
        "columns": list(df.columns),
        "data_url": _url(f"{analysis_id}.json"),
        "parquet_url": _url(f"{analysis_id}.parquet"),
    }
    (RESULT_DIR / f"{analysis_id}.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8"
    )
    return meta


def list_results():
    """All registered result metadata (most recent first)."""
    if not RESULT_DIR.exists():
        return []
    out = []
    for mf in sorted(RESULT_DIR.glob("*.meta.json"), reverse=True):
        try:
            out.append(json.loads(mf.read_text(encoding="utf-8")))
        except Exception:
            continue
    return out


def get_result(analysis_id: str):
    """Metadata for one analysis_id, or None."""
    mf = RESULT_DIR / f"{analysis_id}.meta.json"
    if not mf.exists():
        return None
    try:
        return json.loads(mf.read_text(encoding="utf-8"))
    except Exception:
        return None


def delete_result(analysis_id: str):
    """Remove a result's files. Returns list of removed filenames."""
    removed = []
    for suffix in (".parquet", ".json", ".meta.json"):
        p = RESULT_DIR / f"{analysis_id}{suffix}"
        if p.exists():
            p.unlink()
            removed.append(p.name)
    return removed


def inference_visualization(df):
    """Default visualization for a result DataFrame.

    * only grid_id              -> binary ("selected" solid highlight)
    * grid_id + one numeric col  -> continuous on that column
    * anything else              -> categorical on the first non-grid_id column
    """
    import pandas as pd
    num_cols = [c for c in df.columns
                if c != "grid_id" and pd.api.types.is_numeric_dtype(df[c])]
    if not num_cols:
        return {"type": "binary", "field": "selected", "color": "#E65100"}
    field = num_cols[0]
    vals = df[field].dropna()
    if len(vals) == 0:
        return {"type": "binary", "field": "selected", "color": "#E65100"}
    return {
        "type": "continuous",
        "field": field,
        "min": float(vals.min()),
        "max": float(vals.max()),
    }
