# Tokyo HeatScope v1.0

**Tokyo HeatScope** — a geospatial AI agent for exploring day/night **land surface
temperature (LST)** across Tokyo's 23 wards on a **200 m grid**. Talk to the map
in natural language: visualize LST, run spatial statistics, predict urban-form
"what-if" scenarios, and retrieve citation-ready Tokyo heat-policy guidance.

Standalone v1.0 snapshot of the GLEN LST Agent project.

## Quick start

Requires Python 3.13.

```powershell
# 1. Launch — creates .venv, installs deps, builds data, starts both servers
.\start.ps1
```

Or manually:

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements-spatial.txt -r requirements-ingest.txt tqdm
.venv\Scripts\python scripts\prepare_data.py      # CSV -> GeoJSON + Parquet
.venv\Scripts\python scripts\start_servers.py      # static web + MCP data server
```

Open <http://localhost:8100/>.

| Service | URL |
|---|---|
| Web app | http://localhost:8100/ |
| MCP data server | http://127.0.0.1:8765/mcp |

> Only one instance should run at a time (ports 8100 / 8765). Stop with
> `.venv\Scripts\python scripts\stop_servers.py`.

> **Basemap:** the Tokyo OSM PMTiles (~197 MB) is served from
> `F:\TokyoLSTAgent\geo-app\basemap\tokyo-osm-20260824-z15.pmtiles` (serve.py's
> default external basemap path). To make it fully self-contained, copy that
> file to `app\data\basemap\` — the server checks local copies first.

## Features

- **Map + Agent (MapLibre GL JS + DeepSeek):** `query` (DuckDB SQL), `local_moran`,
  `rf_predict` (urban-form what-if), `run_python`, policy RAG tools.
- **Analysis Result Layers:** derived outputs (clusters, thresholds, custom
  indices, predictions) become independent map layers — source data layers are
  never polluted. Types: categorical / continuous / binary / diverging.
- **Policy Knowledge Base (RAG):** a generalizable ingestion pipeline
  (`scripts/policy_ingestion/`) turns Japanese policy PDFs into provenance-rich
  chunks + structured interventions/scenarios, with `search_policy_knowledge`,
  `filter_policy_interventions`, `get_policy_evidence` retrieval tools.
- **RF LST models:** day (`rf_day.joblib`, R² 0.93) and night (`rf_night.joblib`,
  R² 0.87) trained from `Indicators_nofar.csv`; `rf_predict` supports changing
  urban-form parameters (building coverage, NDVI, height, ...).
- **Multi-language UI:** EN / 日本語 / 中文 chrome switching (preset welcome +
  branding; agent replies follow the LLM).

## Architecture

```
Browser (app/, vanilla ES modules, no build step)
  ├─ MapLibre GL JS  ─────────► Tokyo OSM PMTiles (Protomaps theme)
  ├─ Agent (agentic tool-use) ─► DeepSeek API (OpenAI-compatible)
  ├─ Local map tools ─────────► show/hide/filter/style/fly/create_result_layer
  └─ MCP client ──────────────► FastMCP (Python) ─► DuckDB / spatial / RF / policy
```

- `app/` — frontend (map-manager, map-tools, tool-registry, agent, chat-ui,
  result-layer-manager, i18n, ...). No framework, no build.
- `server/` — FastMCP data server (`mcp_data_server.py`), static server with
  Range/CORS (`serve.py`), spatial analysis, python runner, result store,
  policy retrieval, RF model loader.
- `scripts/` — data preparation (`prepare_data.py`), population resampling,
  RF training, policy ingestion, server launchers.
- `knowledge/` — policy KB (sources, chunks, interventions, scenarios,
  documents, ontology, manifest).
- `models/rf/` — trained day/night RF regressors (regenerable via
  `scripts/train_rf_models.py`).
- `data/policy_sources/` — policy PDF + document metadata sidecar.

## Data adaptation

`tokyo_lst_grid_flat.csv` (14 896 grids; source of truth) →
`app/data/tokyo_lst_grid.geojson` (map) + `app/data/tokyo_lst_grid.parquet`
(SQL). Optional CSIS population (2020) is area-weighted onto the grid via
`scripts/resample_csis_population.py` / `prepare_tokyo_lst.py`.

- **LST is land surface temperature, not air temperature.** The agent is
  prompted to never call it air temperature and to avoid causal claims.

## LLM configuration

`app/config.json` (git-ignored) carries the model + API key. `app/layers-input.json`
also declares `llm.user_provided: true`: delete `config.json` and use the ⚙ button
to enter your own key. No API key is hardcoded in committed code.

## Tests

- Policy ingestion: `python -m scripts.policy_ingestion.ingest --metadata data/policy_sources/tokyo_summer_heat_guideline.metadata.json`
- Content QA: `python scripts/policy_ingestion/qa.py` (11 assertions)
- Retrieval unit: `PYTHONPATH=. python test/test_policy_retrieval.py`
- MCP tools: `python server/test_mcp.py`
