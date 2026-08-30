"""test_mcp.py — quick end-to-end check of the local MCP data server."""

import asyncio
import json
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/mcp"


async def main():
    async with streamablehttp_client(URL) as (read, write, _get_sid):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("TOOLS:", [t.name for t in tools.tools])

            cases = [
                ("avg day/night", "SELECT AVG(day_lst) AS avg_day, AVG(night_lst) AS avg_night, MIN(day_lst) AS min_day, MAX(day_lst) AS max_day FROM tokyo_lst_grid"),
                ("hot grids", "SELECT grid_id, day_lst FROM tokyo_lst_grid WHERE day_lst > 38 ORDER BY day_lst DESC LIMIT 5"),
                ("avg via parquet", "SELECT AVG(day_lst) AS avg_day FROM read_parquet('data/tokyo_lst_grid.parquet')"),
            ]
            for label, sql in cases:
                print(f"\n=== {label} ===")
                res = await session.call_tool("query", {"sql_query": sql})
                for c in res.content:
                    print(getattr(c, "text", c))

            print("\n=== get_stac_details ===")
            res = await session.call_tool("get_stac_details", {"dataset_id": "tokyo-lst"})
            for c in res.content:
                print(getattr(c, "text", c))

            print("\n=== policy structured filter (road) ===")
            res = await session.call_tool("filter_policy_interventions", {
                "scenario": "road", "min_confidence": "high", "limit": 10,
            })
            for c in res.content:
                print(getattr(c, "text", c)[:2000])

            print("\n=== policy search (道路 保水化) ===")
            res = await session.call_tool("search_policy_knowledge", {
                "query": "道路 保水化", "top_k": 2, "include_text": False,
            })
            for c in res.content:
                print(getattr(c, "text", c)[:2000])

            print("\n=== policy evidence (保水化) ===")
            res = await session.call_tool("get_policy_evidence", {
                "chunk_id": "tokyo_summer_heat_guideline_2019-p036-water_retentive_surface",
            })
            for c in res.content:
                print(getattr(c, "text", c)[:2000])

            print("\n=== local_moran (day_lst, quick perms) ===")
            res = await session.call_tool("local_moran", {"column": "day_lst", "permutations": 99})
            for c in res.content:
                print(getattr(c, "text", c))

            print("\n=== create_sql_result (grids > 38) ===")
            res = await session.call_tool("create_sql_result", {
                "sql_query": "SELECT grid_id, day_lst FROM tokyo_lst_grid WHERE day_lst > 38",
                "display_name": "Daytime LST > 38\u00b0C",
            })
            for c in res.content:
                print(getattr(c, "text", c))

            print("\n=== run_python (grid_id + custom index) ===")
            code = (
                "import numpy as np\n"
                "day_p = df['day_lst'].rank(pct=True)\n"
                "ndvi_p = df['ndvi'].rank(pct=True)\n"
                "__result__ = {'grid_id': df['grid_id'].tolist(), 'custom_index': (day_p - ndvi_p).tolist()}"
            )
            res = await session.call_tool("run_python", {"code": code, "timeout": 30})
            for c in res.content:
                print(getattr(c, "text", c))

            print("\n=== list_analysis_results ===")
            res = await session.call_tool("list_analysis_results", {})
            for c in res.content:
                print(getattr(c, "text", c)[:400])

            print("\n=== get_analysis_result (first id) ===")
            res = await session.call_tool("list_analysis_results", {})
            txt = getattr(res.content[0], "text", "{}")
            import json
            ids = [r["analysis_id"] for r in json.loads(txt).get("results", [])]
            if ids:
                res = await session.call_tool("get_analysis_result", {"analysis_id": ids[0]})
                for c in res.content:
                    print(getattr(c, "text", c)[:400])

            print("\n=== run_python (runtime error isolation) ===")
            res = await session.call_tool("run_python", {"code": "x = 1/0", "timeout": 10})
            for c in res.content:
                print(getattr(c, "text", c))


asyncio.run(main())
