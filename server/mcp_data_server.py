"""
mcp_data_server.py — Local MCP data server for the GLEN LST Agent.

Serves the same two tools the remote mcp-data-server would: `query` (read-only
DuckDB SQL over the Tokyo LST parquet) and `get_stac_details` (schema info).
This is the local compatibility layer that lets the existing GeoAgent frontend
(MCPClient → ToolRegistry → Agent) run against local files instead of S3.

Run from the project root with:
    python server/mcp_data_server.py
"""

import json
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = PROJECT_ROOT / "app"
PARQUET_PATH = WEB_ROOT / "data" / "tokyo_lst_grid.parquet"
CATALOG_PATH = WEB_ROOT / "data" / "catalog.json"
COLLECTION_PATH = WEB_ROOT / "data" / "tokyo-lst" / "collection.json"

# Canonical table name the agent is told to use.
TABLE_NAME = "tokyo_lst_grid"

# Max result rows / chars returned from `query` so the LLM doesn't drown.
MAX_ROWS = 200
MAX_CHARS = 80000

from fastmcp import FastMCP  # noqa: E402
try:  # works both as `python server/mcp_data_server.py` and package import
    from .policy_retrieval import PolicyKnowledgeStore  # type: ignore  # noqa: E402
except ImportError:
    from policy_retrieval import PolicyKnowledgeStore  # noqa: E402

import duckdb  # noqa: E402

# ── Experimental Spatial Tools (optional modules) ──────────────────────────
# If these fail to import (e.g. missing deps), the two extra tools simply do
# not register / report UNAVAILABLE — the core `query` / `get_stac_details`
# tools and the whole server keep working.
try:
    import spatial_analysis
    import python_runner
    import result_store
    import rf_model
except Exception as _se:
    spatial_analysis = None
    python_runner = None
    result_store = None
    rf_model = None
    print(f"[mcp] WARNING: spatial tool modules unavailable: {_se}")

# Cached RF pipelines (loaded on first use; ~17 MB each).
_rf_cache = {}


def _rf_model(name):
    if name not in _rf_cache:
        _rf_cache[name] = rf_model.load(name)
    return _rf_cache[name]

mcp = FastMCP("glen-lst-data-server")

try:
    POLICY_STORE = PolicyKnowledgeStore(PROJECT_ROOT)
    _POLICY_ERROR = None
except Exception as _pe:
    POLICY_STORE = None
    _POLICY_ERROR = str(_pe)
    print(f"[mcp] WARNING: policy knowledge unavailable: {_pe}")


def _connect():
    con = duckdb.connect()  # in-memory
    # Make read_parquet('data/...') resolve relative to the web root.
    con.execute(f"SET file_search_path = '{str(WEB_ROOT).replace(chr(39), chr(39)+chr(39))}'")
    return con


def _fmt(value, width):
    if value is None:
        s = "NULL"
    elif isinstance(value, float):
        s = f"{value:.4g}"
    else:
        s = str(value)
    return s[:width]


def _render_table(cols, rows):
    """Render a plain text table from column names + rows (no pandas needed)."""
    if not cols:
        return "(no columns)"
    widths = [len(c) for c in cols]
    for r in rows:
        for i, v in enumerate(r):
            if i < len(widths):
                widths[i] = max(widths[i], len(_fmt(v, 60)))
    widths = [min(w, 60) for w in widths]

    def line(sep="-", fill="-"):
        return sep.join(fill * (w + 2) for w in widths)

    out = []
    out.append(line("+", "-"))
    out.append("| " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(cols)) + " |")
    out.append(line("+", "-"))
    for r in rows:
        out.append("| " + " | ".join(_fmt(v, widths[i]).ljust(widths[i]) for i, v in enumerate(r)) + " |")
    out.append(line("+", "-"))
    return "\n".join(out)


def _preload(con):
    con.execute(
        f"CREATE OR REPLACE VIEW {TABLE_NAME} AS "
        f"SELECT * FROM read_parquet('data/tokyo_lst_grid.parquet')"
    )


def _load_known_columns():
    if COLLECTION_PATH.exists():
        try:
            coll = json.loads(COLLECTION_PATH.read_text(encoding="utf-8"))
            return coll.get("table:columns", [])
        except Exception:
            pass
    return []


def _collection_for(dataset_id):
    if COLLECTION_PATH.exists():
        try:
            coll = json.loads(COLLECTION_PATH.read_text(encoding="utf-8"))
            if coll.get("id") == dataset_id:
                return coll
        except Exception:
            pass
    return None


@mcp.tool()
def query(sql_query: str) -> str:
    """Execute a read-only SQL query against the pre-loaded Tokyo LST dataset.

    A DuckDB database is pre-loaded with a view named `tokyo_lst_grid` created
    from `data/tokyo_lst_grid.parquet`. You may query that view directly, or
    call `read_parquet('data/tokyo_lst_grid.parquet')` (the path is relative to
    the web root). Only read-only SELECT statements are allowed.
    """
    sql = (sql_query or "").strip()
    if not sql:
        return "Error: empty SQL query"
    if not re.match(r"^\s*(SELECT|WITH)\b", sql, re.IGNORECASE):
        return "Error: only read-only SELECT (or WITH) statements are allowed."

    con = _connect()
    try:
        _preload(con)
        cur = con.execute(sql)
        cols = [d[0] for d in (cur.description or [])]
        all_rows = cur.fetchall()
    except Exception as e:
        try:
            con.close()
        except Exception:
            pass
        return f"SQL error: {e}"

    if len(all_rows) == 0:
        con.close()
        return "Query executed successfully but returned no rows."

    # Single-column results (e.g. the filter_by_query ID lists or scalar
    # aggregates) are rendered raw, one value per line — no width truncation,
    # so JSON arrays like [9463,10791,...] survive intact for the client's
    # extractJsonArray parser.
    if len(cols) == 1:
        text = "\n".join(_fmt(r[0], 1_000_000) for r in all_rows[:MAX_ROWS])
    else:
        shown = all_rows[:MAX_ROWS]
        text = _render_table(cols, shown)
        if len(all_rows) > MAX_ROWS:
            text += f"\n... ({len(all_rows) - MAX_ROWS} more rows not shown)"
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n... (truncated)"
    con.close()
    return text


@mcp.tool()
def get_stac_details(dataset_id: str = "tokyo-lst", collection: dict = None) -> str:
    """Return the schema (column names, types, sample values) and parquet path
    for the Tokyo LST dataset. Call before writing SQL."""
    coll = collection if isinstance(collection, dict) else _collection_for(dataset_id)
    columns = coll.get("table:columns", []) if coll else _load_known_columns()

    lines = []
    lines.append(f"Dataset: {dataset_id}")
    if coll:
        lines.append(f"Title: {coll.get('title', '')}")
        lines.append(f"Description: {coll.get('description', '')}")
    lines.append(f"read_parquet path: read_parquet('data/tokyo_lst_grid.parquet')")
    lines.append(f"Pre-loaded table/view: {TABLE_NAME}")
    lines.append("")

    con = _connect()
    try:
        _preload(con)
        cur = con.execute(f"SELECT * FROM {TABLE_NAME} LIMIT 1")
        cols_desc = [d[0] for d in (cur.description or [])]
        one_row = cur.fetchone()
        describe = con.execute(f"DESCRIBE {TABLE_NAME}").fetchall()
    except Exception as e:
        one_row = None
        cols_desc = []
        describe = []
        lines.append(f"(schema introspection failed: {e})")

    lines.append("Columns (name | type | sample | description):")
    for col in columns:
        name = col.get("name", "?")
        ctype = col.get("type", "?")
        desc = col.get("description", "")
        sample_val = ""
        if one_row is not None and name in cols_desc:
            v = one_row[cols_desc.index(name)]
            sample_val = "NULL" if v is None else str(v)
        lines.append(f"  {name} | {ctype} | {sample_val} | {desc}")

    if describe and not columns:
        lines.append("\n(no table:columns metadata; DESCRIBE output follows)")
        for row in describe:
            lines.append("  " + " | ".join(str(x) for x in row))

    if con:
        try:
            con.close()
        except Exception:
            pass
    return "\n".join(lines)


@mcp.tool()
def search_policy_knowledge(
    query: str,
    scenario: str = None,
    intervention_ids: list = None,
    knowledge_types: list = None,
    document_status: list = None,
    min_confidence: str = "low",
    top_k: int = 5,
    include_text: bool = True,
) -> str:
    """Search Japanese/English policy chunks after optional structured filters.

    Returns policy evidence with PDF/printed pages and chunk provenance. Ranking
    does not establish model or scientific causality.
    """
    if POLICY_STORE is None:
        return json.dumps({"success": False, "error": _POLICY_ERROR, "evidence_type": "policy"}, ensure_ascii=False)
    try:
        result = POLICY_STORE.search(
            query, scenario=scenario, intervention_ids=intervention_ids,
            knowledge_types=knowledge_types, document_status=document_status,
            min_confidence=min_confidence, top_k=top_k, include_text=include_text,
        )
    except ValueError as exc:
        result = {"success": False, "error": str(exc), "evidence_type": "policy"}
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def filter_policy_interventions(
    scenario: str = None,
    categories: list = None,
    policy_logic: list = None,
    document_status: list = None,
    min_confidence: str = "low",
    intervention_ids: list = None,
    limit: int = 50,
    include_details: bool = False,
) -> str:
    """Filter structured policy interventions without applying GIS causal rules."""
    if POLICY_STORE is None:
        return json.dumps({"success": False, "error": _POLICY_ERROR, "evidence_type": "policy"}, ensure_ascii=False)
    try:
        result = POLICY_STORE.filter_interventions(
            scenario=scenario, categories=categories, policy_logic=policy_logic,
            document_status=document_status, min_confidence=min_confidence,
            intervention_ids=intervention_ids, limit=limit, include_details=include_details,
        )
    except ValueError as exc:
        result = {"success": False, "error": str(exc), "evidence_type": "policy"}
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def get_policy_evidence(chunk_id: str) -> str:
    """Return one complete policy chunk and citation-ready provenance."""
    if POLICY_STORE is None:
        return json.dumps({"success": False, "error": _POLICY_ERROR, "evidence_type": "policy"}, ensure_ascii=False)
    try:
        result = POLICY_STORE.get_evidence(chunk_id)
    except ValueError as exc:
        result = {"success": False, "error": str(exc), "evidence_type": "policy"}
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def local_moran(column: str = "day_lst", permutations: int = 999) -> str:
    """Calculate Local Moran's I (spatial autocorrelation) for a column of the
    Tokyo 200 m LST grid.

    Uses Queen contiguity weights over the grid polygons and permutation-based
    significance (esda / libpysal). Choose `column` from: day_lst, night_lst,
    day_night_gap, ndvi, bldg_coverage_ratio, elevation_mean, water_ratio.

    The per-grid result is registered in the Analysis Result Store and returned
    compactly: an `analysis_id` + summary. Display it with the map tool
    `create_result_layer(analysis_id='<analysis_id>')`, then use
    `set_filter(layer_id, [["==",["get","cluster"],"HH"]])` to isolate a
    cluster. Results are cached and regenerable."""
    if spatial_analysis is None or not spatial_analysis.is_available():
        return json.dumps({
            "success": False,
            "error": "Local Moran tool is currently unavailable because required spatial-analysis dependencies could not be loaded.",
        }, ensure_ascii=False)
    try:
        summary, results_df = spatial_analysis.compute_local_moran(column=column, permutations=permutations)
    except Exception as exc:
        return json.dumps({"success": False, "error": f"Local Moran computation failed: {exc}"}, ensure_ascii=False)

    analysis_id = result_store.new_analysis_id(f"local_moran_{column}")
    viz = {
        "type": "categorical",
        "field": "cluster",
        "categories": {"HH": "#d73027", "LL": "#4575b4", "HL": "#fdae61", "LH": "#91bfdb"},
    }
    meta = result_store.register_result(
        analysis_id=analysis_id,
        analysis_type="local_moran",
        display_name=f"Local Moran · {column}",
        source_dataset="tokyo-lst",
        source_field=column,
        visualization=viz,
        tooltip_fields=["grid_id", "cluster", "lisa", "p_sim", "significant", column],
        df=results_df,
    )
    return json.dumps({
        "success": True,
        "analysis_id": analysis_id,
        "display_name": meta["display_name"],
        "analysis_type": "local_moran",
        "summary": {
            "global_moran_i": summary["global_moran_i"],
            "global_p_value": summary["global_p_value"],
            "n_significant": summary["n_significant"],
            "significant_cluster_counts": summary["significant_cluster_counts"],
        },
        "next": f"Call the map tool create_result_layer(analysis_id='{analysis_id}') to display it.",
    }, ensure_ascii=False)


@mcp.tool()
def create_sql_result(sql_query: str, display_name: str, visualization: dict = None) -> str:
    """Run a read-only SQL query whose result is a set of grid cells with
    derived attributes, and register it as an Analysis Result (so it can be
    shown as an independent Result Layer, without touching the raw Day/Night
    LST layers).

    The query must SELECT `grid_id` (optionally with extra derived columns),
    e.g.:
        SELECT grid_id, day_lst FROM tokyo_lst_grid WHERE day_lst > 38
    Optionally pass `visualization`: {type, field, min, max, center, categories,
    color} — otherwise it is inferred (binary for pure grid_id selections,
    continuous on the first numeric column otherwise).

    Returns a compact analysis_id; display with
    create_result_layer(analysis_id='<analysis_id>')."""
    sql = (sql_query or "").strip()
    if not sql:
        return json.dumps({"success": False, "error": "empty SQL query"}, ensure_ascii=False)
    if not re.match(r"^\s*(SELECT|WITH)\b", sql, re.IGNORECASE):
        return json.dumps({"success": False, "error": "only read-only SELECT (or WITH) statements are allowed."}, ensure_ascii=False)

    con = _connect()
    try:
        _preload(con)
        cur = con.execute(sql)
        cols = [d[0] for d in (cur.description or [])]
        rows = cur.fetchall()
    except Exception as exc:
        return json.dumps({"success": False, "error": f"SQL error: {exc}"}, ensure_ascii=False)
    finally:
        try:
            con.close()
        except Exception:
            pass

    if "grid_id" not in cols:
        return json.dumps({
            "success": False,
            "error": "create_sql_result requires the query to return a `grid_id` column (SELECT grid_id, ...).",
        }, ensure_ascii=False)

    import pandas as pd
    df = pd.DataFrame(rows, columns=cols)
    if len(df) == 0:
        return json.dumps({"success": False, "error": "query returned no rows."}, ensure_ascii=False)

    viz = visualization or result_store.inference_visualization(df)
    analysis_id = result_store.new_analysis_id("query")
    meta = result_store.register_result(
        analysis_id=analysis_id,
        analysis_type="sql_query",
        display_name=display_name,
        source_dataset="tokyo-lst",
        source_field=None,
        visualization=viz,
        tooltip_fields=["grid_id"] + [c for c in cols if c != "grid_id"],
        df=df,
    )
    return json.dumps({
        "success": True,
        "analysis_id": analysis_id,
        "display_name": meta["display_name"],
        "analysis_type": "sql_query",
        "n": int(len(df)),
        "visualization": viz,
        "next": f"Call the map tool create_result_layer(analysis_id='{analysis_id}') to display it.",
    }, ensure_ascii=False)


@mcp.tool()
def list_analysis_results() -> str:
    """List all registered analysis results (metadata only: analysis_id,
    display_name, analysis_type, visualization, n). Use to discover results the
    agent may display with create_result_layer()."""
    if result_store is None:
        return json.dumps({"success": False, "error": "result store unavailable"}, ensure_ascii=False)
    return json.dumps({"success": True, "results": result_store.list_results()}, ensure_ascii=False, default=str)


@mcp.tool()
def get_analysis_result(analysis_id: str) -> str:
    """Return metadata for one analysis result (visualization, tooltip fields,
    data URL) so create_result_layer() can render it."""
    if result_store is None:
        return json.dumps({"success": False, "error": "result store unavailable"}, ensure_ascii=False)
    meta = result_store.get_result(analysis_id)
    if not meta:
        return json.dumps({"success": False, "error": f"unknown analysis_id: {analysis_id}"}, ensure_ascii=False)
    return json.dumps({"success": True, "result": meta}, ensure_ascii=False, default=str)


@mcp.tool()
def run_python(code: str, timeout: int = 30) -> str:
    """Execute a short Python snippet for ad-hoc analysis on the Tokyo LST grid
    (e.g. a quick temporary regression).

    Pre-loaded in the snippet namespace: `df` = pandas DataFrame of the grid
    (columns grid_id, day_lst, night_lst, ndvi, bldg_coverage_ratio, ...),
    plus numpy (np), pandas (pd), scipy, sklearn.

    Set the variable `__result__` to return a JSON-serializable value; print()
    output is captured too. Execution runs in an isolated subprocess with a
    timeout; failures (syntax / runtime / timeout) affect only this one call.

    Example (linear regression of day_lst on ndvi + building coverage):
        import numpy as np
        X = df[['ndvi', 'bldg_coverage_ratio']].fillna(0)
        y = df['day_lst']
        beta, res, rank, sv = np.linalg.lstsq(
            np.column_stack([np.ones(len(X)), X]), y, rcond=None)
        r2 = 1 - res[0] / ((y - y.mean()) ** 2).sum()
        __result__ = {'intercept': float(beta[0]),
                      'coefs': {'ndvi': float(beta[1]),
                                'bldg_coverage_ratio': float(beta[2])},
                      'r2': float(r2)}"""
    if python_runner is None:
        return json.dumps({"success": False, "error": "run_python is unavailable on this server."}, ensure_ascii=False)
    try:
        result = python_runner.run_python(code, timeout=timeout)
    except Exception as exc:
        result = {"success": False, "error": f"run_python failed: {exc}"}

    # If the snippet returned a grid_id-keyed table (list of records or a
    # columnar dict), register it as an Analysis Result and return a compact
    # analysis_id — the LLM never sees thousands of rows.
    if result.get("success") and result_store is not None:
        df = _coerce_grid_df(result.get("result"))
        if df is not None and "grid_id" in df.columns and len(df) > 0:
            viz = result_store.inference_visualization(df)
            field = viz.get("field")
            analysis_id = result_store.new_analysis_id("python")
            meta = result_store.register_result(
                analysis_id=analysis_id,
                analysis_type="python",
                display_name=f"Python Result · {field}" if field else "Python Result",
                source_dataset="tokyo-lst",
                visualization=viz,
                tooltip_fields=["grid_id"] + [c for c in df.columns if c != "grid_id"],
                df=df,
            )
            summary = {}
            import numpy as np
            for c in df.columns:
                if c == "grid_id":
                    continue
                try:
                    v = df[c].dropna()
                    summary[c] = {"min": float(np.min(v)), "max": float(np.max(v)),
                                  "mean": float(np.mean(v))}
                except Exception:
                    continue
            result = {
                "success": True,
                "analysis_id": analysis_id,
                "display_name": meta["display_name"],
                "analysis_type": "python",
                "n": int(len(df)),
                "visualization": viz,
                "summary": summary,
                "next": f"Call the map tool create_result_layer(analysis_id='{analysis_id}') to display it.",
            }
    return json.dumps(result, ensure_ascii=False)


def _coerce_grid_df(value):
    """Coerce a runner result to a pandas DataFrame if it looks grid_id-keyed."""
    import pandas as pd
    if isinstance(value, list):
        if len(value) and all(isinstance(r, dict) for r in value):
            return pd.DataFrame(value)
        return None
    if isinstance(value, dict):
        # columnar: {'grid_id': [...], 'col': [...]}
        lists = {k: v for k, v in value.items() if isinstance(v, (list, tuple))}
        if lists and "grid_id" in lists:
            return pd.DataFrame(lists)
    return None


# ── RF urban-form What-If prediction ─────────────────────────────────────────

def _norm_col(name):
    """Accept GLEN lowercase or model feature names -> model feature name."""
    if isinstance(name, str):
        if name in rf_model.FEATURES:
            return name
        if name in rf_model.GLEN_TO_MODEL:
            return rf_model.GLEN_TO_MODEL[name]
    return None


def _grid_lookup():
    import pandas as pd
    df = pd.read_parquet(PARQUET_PATH)
    df["grid_id"] = df["grid_id"].astype(int)
    return df.set_index("grid_id")


_GRID = None


def _grid_df():
    global _GRID
    if _GRID is None:
        _GRID = _grid_lookup()
    return _GRID


@mcp.tool()
def rf_predict(grid_id: int = None, overrides: dict = None, parameters: dict = None,
               grid_ids: list = None, model: str = "both") -> str:
    """Predict daytime/nighttime LST (land surface temperature, °C) for grid
    parameters using the trained Random Forest models.

    INPUT is grid parameters (urban-form indicators), which may be ADJUSTED to
    simulate changed urban form:

    - `grid_id`       : base the prediction on an existing grid's parameters.
    - `overrides`     : dict of parameters to CHANGE for that grid (urban-form
                        what-if), e.g. {'bldg_coverage_ratio': 0.6, 'ndvi': 0.2,
                        'avg_height': 25}. Accepts GLEN lowercase or model names.
    - `parameters`    : alternative to overrides — explicit full/partial parameter
                        set. Without grid_id, missing values use grid medians
                        (a hypothetical grid).
    - `grid_ids`      : list of grids to predict with the same overrides; registers
                        an Analysis Result (analysis_id) so you can display the
                        scenario with create_result_layer().
    - `model`         : 'day' | 'night' | 'both' (default both).

    Predictable features: dist_to_coast, elevation_mean, water_ratio,
    dist_to_major_river, avg_height, road_length, bldg_coverage_ratio, svf_mean,
    height_variance, ndvi.

    Returns the effective input parameters, predicted LST, and (for a single
    existing grid) the observed LST and the urban-form-change delta."""
    import pandas as pd

    if rf_model is None:
        return json.dumps({"success": False,
                           "error": "rf_predict unavailable: Random Forest models not loaded."},
                          ensure_ascii=False)
    models = []
    if model in ("day", "both"):
        models.append("day")
    if model in ("night", "both"):
        models.append("night")
    if not models:
        return json.dumps({"success": False, "error": "model must be 'day', 'night', or 'both'."},
                          ensure_ascii=False)

    overrides = {k: v for k, v in (overrides or {}).items() if v is not None}
    parameters = {k: v for k, v in (parameters or {}).items() if v is not None}
    # Normalize names; unknown columns are reported.
    unknown = [c for c in {**overrides, **parameters} if _norm_col(c) is None]
    if unknown:
        return json.dumps({"success": False,
                           "error": f"unknown parameter(s): {unknown}. Available: {rf_model.FEATURES}"},
                          ensure_ascii=False)

    grid = _grid_df()
    targets = []
    if grid_ids:
        targets = [int(g) for g in grid_ids]
    elif grid_id is not None:
        targets = [int(grid_id)]

    # Determine the target grids / hypothetical rows.
    # effective_rows: list of (row_id, params_dict, observed_lst_dict)
    import numpy as np
    medians = {rf_model.GLEN_TO_MODEL[c]: float(grid[c].median())
               for c in rf_model.GLEN_TO_MODEL}
    medians["Water_Ratio"] = 0.0  # avoid ratio-0 pitfall for hypothetical grids

    def params_for(gid):
        row = grid.loc[gid]
        p = {m: float(row[glen]) for glen, m in rf_model.GLEN_TO_MODEL.items()}
        for k, v in {**overrides, **parameters}.items():
            p[_norm_col(k)] = float(v)
        return p

    def observed_for(gid):
        row = grid.loc[gid]
        return {"day_lst": float(row["day_lst"]), "night_lst": float(row["night_lst"])}

    rows = []
    if targets:
        missing_ids = [g for g in targets if g not in grid.index]
        if missing_ids:
            return json.dumps({"success": False, "error": f"unknown grid_id(s): {missing_ids}"},
                              ensure_ascii=False)
        for g in targets:
            rows.append({"id": g, "params": params_for(g), "observed": observed_for(g)})
    else:
        base = dict(medians)
        for k, v in {**overrides, **parameters}.items():
            base[_norm_col(k)] = float(v)
        rows.append({"id": None, "params": base, "observed": None})

    # Predict.
    out = []
    for r in rows:
        X = pd.DataFrame([r["params"]])[rf_model.FEATURES]
        pred = {m: float(_rf_model(m).predict(X)[0]) for m in models}
        item = {
            "grid_id": r["id"],
            "input_parameters": {k: round(v, 3) for k, v in r["params"].items()},
            "predicted": {k: round(v, 3) for k, v in pred.items()},
        }
        if r["observed"]:
            item["observed"] = {k: round(v, 3) for k, v in r["observed"].items()}
            # delta = predicted(with adjusted params) - observed (current form)
            item["delta_vs_current"] = {
                "day_lst": round(pred.get("day", r["observed"]["day_lst"]) - r["observed"]["day_lst"], 3),
                "night_lst": round(pred.get("night", r["observed"]["night_lst"]) - r["observed"]["night_lst"], 3),
            }
        out.append(item)

    payload = {"success": True, "results": out, "n": len(out)}
    # Multi-grid scenario -> register as an Analysis Result for map display.
    if targets and len(targets) > 1 and result_store is not None:
        recs = []
        for r in out:
            rec = {"grid_id": r["grid_id"]}
            if "day" in models:
                rec["predicted_day_lst"] = r["predicted"]["day"]
            if "night" in models:
                rec["predicted_night_lst"] = r["predicted"]["night"]
            recs.append(rec)
        analysis_id = result_store.new_analysis_id("rf_scenario")
        meta = result_store.register_result(
            analysis_id=analysis_id,
            analysis_type="rf_scenario",
            display_name="RF Scenario · predicted LST",
            source_dataset="tokyo-lst",
            source_field=None,
            visualization=result_store.inference_visualization(pd.DataFrame(recs)),
            tooltip_fields=["grid_id"] + [c for c in recs[0] if c != "grid_id"],
            df=pd.DataFrame(recs),
        )
        payload["analysis_id"] = analysis_id
        payload["display_name"] = meta["display_name"]
        payload["next"] = f"create_result_layer(analysis_id='{analysis_id}') to display the scenario."

    return json.dumps(payload, ensure_ascii=False)


def main():
    port = int(os.environ.get("GLEN_MCP_PORT", "8765"))
    host = os.environ.get("GLEN_MCP_HOST", "127.0.0.1")

    if not PARQUET_PATH.exists():
        print(f"ERROR: missing {PARQUET_PATH} — run scripts/prepare_data.py first.")
        sys.exit(1)

    from starlette.middleware import Middleware
    from starlette.middleware.cors import CORSMiddleware

    cors_mw = Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Mcp-Session-Id"],
    )

    print(f"[mcp] Tokyo LST data server on http://{host}:{port}/mcp")
    print(f"[mcp] parquet: {PARQUET_PATH}")

    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
        path="/mcp",
        show_banner=False,
        middleware=[cors_mw],
    )


if __name__ == "__main__":
    main()
