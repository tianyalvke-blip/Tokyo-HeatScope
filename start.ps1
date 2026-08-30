# Tokyo HeatScope v1.0 — Start launcher

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    Write-Host "No .venv found — creating one and installing dependencies..."
    python -m venv "$root\.venv"
    if (-not (Test-Path $py)) { Write-Error "Failed to create venv. Install Python 3.13 first."; exit 1 }
    & $py -m pip install --upgrade pip -q
    & $py -m pip install -r "$root\requirements-spatial.txt" -q
    & $py -m pip install -r "$root\requirements-ingest.txt" -q
    & $py -m pip install tqdm -q
}

if (-not (Test-Path (Join-Path $root "app\data\tokyo_lst_grid.parquet"))) {
    Write-Host "Data artifacts missing — building from CSV..."
    & $py (Join-Path $root "scripts\prepare_data.py")
}

& $py (Join-Path $root "scripts\start_servers.py")
Write-Host ""
Write-Host "Tokyo HeatScope v1.0 is running:"
Write-Host "  App:  http://localhost:8100/"
Write-Host "  MCP:  http://127.0.0.1:8765/mcp"
Write-Host "Stop with: .venv\Scripts\python.exe scripts\stop_servers.py"
