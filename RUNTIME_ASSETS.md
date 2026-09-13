# HeatScope runtime assets

This repository tracks the source code and the two compact administrative
boundary overlays below so a fresh checkout can render ward and town boundaries.

| Tracked asset | Purpose |
|---|---|
| `app/data/boundaries/tokyo_23_wards_estat_2020.geojson` | Tokyo 23-ward boundaries |
| `app/data/boundaries/tokyo_23_wards_town_level_estat_2020.geojson` | Tokyo town-level boundaries |

The following are intentionally deployment assets, not ordinary Git objects:

| Runtime asset | Expected location | Reason |
|---|---|---|
| 200 m / 400 m LST grid GeoJSON and Parquet | `app/data/` | Large derived analytical data |
| RF day/night models and feature metadata | `app/data/models/rf/` | Model artifacts |
| PMTiles basemap | `app/data/basemap/` | Large binary tile archive |

Before a local or server deployment, copy these assets from the approved data
bundle into the paths above, then verify the MCP `get_schema` and an RF feature
curve. Do not add the PMTiles archive or model binaries to normal Git history.

The deployment record must identify the code commit, the asset-bundle date or
checksum, and the Agent/App/UI tags used together.
