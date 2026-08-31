"""build_400m.py — Build a standard 400 m grid over Tokyo and aggregate.

Robust to the slightly-irregular 200 m source cells:

  1. Define a canonical 400 m x 400 m grid aligned to the dataset origin.
  2. For every 200 m cell compute its overlap (polygon intersection) with each
     400 m cell.
  3. Aggregate each numeric field as an AREA-WEIGHTED mean:
         value = sum(overlap_area_i * field_i) / sum(overlap_area_i)
     A 200 m cell straddling a 400 m edge contributes proportionally to each
     intersecting 400 m cell, so nothing is double counted or dropped.
  4. Only 400 m cells with any overlap are emitted.

Reads app/data/tokyo_lst_grid.geojson, writes
app/data/tokyo_lst_grid_400m.geojson.
"""

import json
import math
from collections import defaultdict
from pathlib import Path

from shapely.geometry import box

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "app" / "data" / "tokyo_lst_grid.geojson"
DST = ROOT / "app" / "data" / "tokyo_lst_grid_400m.geojson"

AVG_FIELDS = ["day_lst", "night_lst", "day_night_gap", "ndvi",
              "pop_2020_total", "pop_2020_density_km2", "pop_65_over"]

# 400 m cell size in degrees at Tokyo (lat ~35.7)
LAT0 = 35.7
D_LAT = 400 / 111132.95
D_LON = 400 / (111319.49 * math.cos(math.radians(LAT0)))


def main():
    fc = json.loads(SRC.read_text(encoding="utf-8"))
    feats = fc["features"]

    w0 = min(min(c[0] for c in f["geometry"]["coordinates"][0]) for f in feats)
    s0 = min(min(c[1] for c in f["geometry"]["coordinates"][0]) for f in feats)

    # Accumulators per 400m cell: sum(area*value) and total area
    acc = {}  # (col,row) -> {field: weighted_sum}, plus 'area'

    for f in feats:
        ring = f["geometry"]["coordinates"][0]
        poly = box(min(c[0] for c in ring), min(c[1] for c in ring),
                   max(c[0] for c in ring), max(c[1] for c in ring))
        # Determine the 400m cells this polygon may touch
        min_col = math.floor((poly.bounds[0] - w0) / D_LON)
        max_col = math.floor((poly.bounds[2] - w0) / D_LON)
        min_row = math.floor((poly.bounds[1] - s0) / D_LAT)
        max_row = math.floor((poly.bounds[3] - s0) / D_LAT)

        for col in range(min_col, max_col + 1):
            for row in range(min_row, max_row + 1):
                cell_w = w0 + col * D_LON
                cell_s = s0 + row * D_LAT
                cell = box(cell_w, cell_s, cell_w + D_LON, cell_s + D_LAT)
                inter = poly.intersection(cell)
                if inter.is_empty:
                    continue
                area = inter.area
                key = (col, row)
                if key not in acc:
                    acc[key] = {fld: 0.0 for fld in AVG_FIELDS}
                    acc[key]["_area"] = 0.0
                acc[key]["_area"] += area
                for fld in AVG_FIELDS:
                    v = f["properties"].get(fld)
                    if v is not None:
                        acc[key][fld] += area * v

    out_features = []
    gid = 1
    for (col, row), data in acc.items():
        total_area = data["_area"]
        if total_area <= 0:
            continue
        w = w0 + col * D_LON
        e = w + D_LON
        s = s0 + row * D_LAT
        n = s + D_LAT
        ring = [[w, s], [w, n], [e, n], [e, s], [w, s]]
        props = {}
        for fld in AVG_FIELDS:
            props[fld] = round(data[fld] / total_area, 6)
        # Stable-ish id: unique per 400m cell (independent of the 200m ids).
        props["grid_id"] = gid
        gid += 1
        props["centroid_lon"] = round((w + e) / 2, 6)
        props["centroid_lat"] = round((s + n) / 2, 6)
        out_features.append({
            "type": "Feature",
            "properties": props,
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        })

    result = {"type": "FeatureCollection", "features": out_features}
    DST.write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")
    print(f"200m cells: {len(feats)}")
    print(f"400m cells: {len(out_features)}")
    print(f"400m cell size: {D_LON:.6f} lon x {D_LAT:.6f} lat")
    print(f"wrote {DST} ({DST.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
