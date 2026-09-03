# Environment management

v2.0 uses `uv` for reproducible Python environments. Install `uv` once, then run from the project root:

```powershell
uv sync
uv sync --extra spatial --extra ingest --extra eval
```

`uv.lock` should be generated and committed after the first successful `uv sync`. Do not commit `.venv`, `server/cache`, evaluation reports, logs, or API keys.

The local services can then be started with:

```powershell
uv run python scripts/start_servers.py
uv run python evals/dashboard.py
```

The evaluation dashboard is at `http://127.0.0.1:8170/`.
