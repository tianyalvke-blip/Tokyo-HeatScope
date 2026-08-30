from __future__ import annotations


SCENARIO_CATALOG = {
    "office_commercial_building": ("ビル", "office/commercial/public building"),
    "apartment": ("集合住宅", "apartment building"),
    "detached_house": ("戸建住宅", "detached house"),
    "warehouse_factory": ("倉庫・工場", "warehouse/factory"),
    "urban_block": ("街区", "urban block"),
    "park": ("公園", "park"),
    "plaza": ("広場", "plaza"),
    "road": ("道路", "road"),
    "outdoor_event": ("屋外イベント会場", "outdoor event venue"),
}


# English labels and ontology fields are a retrieval crosswalk. Japanese names
# remain authoritative and are never replaced by this catalog.
INTERVENTION_CATALOG = {
    "green_roof": {
        "name_ja": "屋上緑化", "name_en": "green roof", "category": "vegetation",
        "aliases": ["屋上緑化"], "target": ["building_roof"], "page_start": 25, "page_end": 25,
        "logic": ["dasanai", "tamenai", "morawanai"],
    },
    "building_insulation": {
        "name_ja": "断熱化", "name_en": "building insulation", "category": "building_envelope",
        "aliases": ["断熱化", "断熱"], "target": ["building_roof", "building_wall", "window"], "page_start": 26, "page_end": 26,
        "logic": ["dasanai"],
    },
    "roof_heat_shielding": {
        "name_ja": "遮熱化（建物屋根面）", "name_en": "solar-reflective roof treatment", "category": "building_envelope",
        "aliases": ["屋根の遮熱化", "屋上の遮熱化"], "target": ["building_roof"], "page_start": 27, "page_end": 27,
        "logic": ["dasanai", "tamenai"],
    },
    "green_wall": {
        "name_ja": "壁面緑化", "name_en": "green wall", "category": "vegetation",
        "aliases": ["壁面緑化", "緑のカーテン"], "target": ["building_wall", "window"], "page_start": 28, "page_end": 28,
        "logic": ["dasanai", "tamenai", "morawanai"],
    },
    "window_heat_shielding": {
        "name_ja": "遮熱化（建物窓面）", "name_en": "solar-control window treatment", "category": "building_envelope",
        "aliases": ["窓面の遮熱化", "遮熱フィルム"], "target": ["window"], "page_start": 29, "page_end": 29,
        "logic": ["dasanai"],
    },
    "retroreflective_surface": {
        "name_ja": "再帰反射化", "name_en": "retroreflective surface treatment", "category": "surface_material",
        "aliases": ["再帰反射化", "再帰反射"], "target": ["building_wall", "window"], "page_start": 30, "page_end": 30,
        "logic": ["dasanai", "tamenai", "morawanai"],
    },
    "energy_efficiency": {
        "name_ja": "省エネルギー化", "name_en": "energy efficiency", "category": "energy",
        "aliases": ["省エネルギー化", "省エネルギー機器"], "target": ["building_equipment"], "page_start": 31, "page_end": 32,
        "logic": ["dasanai"],
    },
    "waste_heat_mitigation": {
        "name_ja": "排熱の緩和", "name_en": "waste-heat mitigation", "category": "anthropogenic_heat",
        "aliases": ["排熱の緩和", "排熱の潜熱化"], "target": ["building_equipment"], "page_start": 31, "page_end": 32,
        "logic": ["dasanai"],
    },
    "exhaust_location": {
        "name_ja": "排熱位置の工夫", "name_en": "exhaust location design", "category": "anthropogenic_heat",
        "aliases": ["排熱位置の工夫", "排熱の位置"], "target": ["building_equipment", "pedestrian_space"], "page_start": 31, "page_end": 32,
        "logic": ["morawanai"],
    },
    "building_configuration": {
        "name_ja": "建物形状の工夫", "name_en": "building form and configuration", "category": "building_form",
        "aliases": ["建物形状の工夫", "建物形状 / 配置の工夫", "建物形状・配置の工夫"], "target": ["building", "urban_block"], "page_start": 33, "page_end": 33,
        "logic": ["tamenai"],
    },
    "ground_greening": {
        "name_ja": "緑化", "name_en": "ground and streetscape greening", "category": "vegetation",
        "aliases": ["街路樹", "地表面緑化", "敷地内の緑化", "緑化"], "target": ["open_space", "road", "sidewalk"], "page_start": 34, "page_end": 34,
        "logic": ["tamenai", "morawanai"],
    },
    "heat_reflective_surface": {
        "name_ja": "遮熱化", "name_en": "heat-reflective surface treatment", "category": "surface_material",
        "aliases": ["車道の遮熱化", "路面等の遮熱化", "遮熱化"], "target": ["road", "sidewalk", "open_space"], "page_start": 35, "page_end": 35,
        "logic": ["tamenai", "morawanai"],
    },
    "water_retentive_surface": {
        "name_ja": "保水化", "name_en": "water-retentive surface treatment", "category": "surface_material",
        "aliases": ["保水化", "保水性舗装", "保水性ブロック"], "target": ["road", "sidewalk", "open_space"], "page_start": 36, "page_end": 36,
        "logic": ["tamenai", "morawanai"],
    },
    "water_surface": {
        "name_ja": "水面・水辺の確保", "name_en": "provision of water surfaces and waterside spaces", "category": "water",
        "aliases": ["水面・水辺の確保", "水面 / 水辺の確保", "水景施設"], "target": ["park", "plaza", "building_site"], "page_start": 37, "page_end": 37,
        "logic": ["tamenai", "morawanai"],
    },
    "shade": {
        "name_ja": "日除け", "name_en": "shade", "category": "shading",
        "aliases": ["日除け", "すだれ", "テント", "パラソル"], "target": ["pedestrian_space", "window", "open_space"], "page_start": 38, "page_end": 38,
        "logic": ["dasanai", "tamenai", "morawanai"],
    },
    "side_surface_cooling": {
        "name_ja": "側面等の冷却", "name_en": "side-surface evaporative cooling", "category": "cooling_device",
        "aliases": ["側面等の冷却", "側面冷却", "冷却ルーバー"], "target": ["pedestrian_space", "building_wall"], "page_start": 39, "page_end": 39,
        "logic": ["tamenai", "morawanai"],
    },
    "dry_mist": {
        "name_ja": "ドライ型（微細）ミスト", "name_en": "dry fine mist", "category": "cooling_device",
        "aliases": ["ドライ型 ( 微細 ) ミスト", "ドライ型（微細）ミスト", "微細ミスト"], "target": ["pedestrian_space", "event_venue"], "page_start": 40, "page_end": 40,
        "logic": ["morawanai"],
    },
    "uchimizu": {
        "name_ja": "打ち水", "name_en": "uchimizu (water sprinkling)", "category": "water",
        "aliases": ["打ち水", "散水"], "target": ["road", "open_space", "building_site"], "page_start": 41, "page_end": 41,
        "logic": ["tamenai", "morawanai"],
    },
    "heatstroke_prevention_support": {
        "name_ja": "熱中症対策（日傘・飲料水等）", "name_en": "heatstroke prevention support (parasols and drinking water)", "category": "public_health",
        "aliases": ["日傘の貸し出し", "飲料水の提供", "熱中症対策"], "target": ["event_venue"], "page_start": 20, "page_end": 20,
        "logic": ["morawanai"],
    },
}


MECHANISM_PATTERNS = {
    "evaporative_cooling": ["気化熱", "蒸散"],
    "reduce_surface_heat_storage": ["蓄熱を抑", "表面温度の上昇を抑"],
    "reflect_solar_radiation": ["日射を反射", "日射反射"],
    "redirect_reflected_solar_radiation": ["上空に返す", "再帰反射"],
    "reduce_heat_transfer": ["熱の移動を抑", "断熱"],
    "improve_ventilation": ["風通し", "通風"],
    "reduce_anthropogenic_waste_heat": ["排熱を減", "排熱の潜熱化"],
    "redirect_waste_heat": ["排熱位置", "排熱の位置"],
    "block_solar_radiation": ["日射を遮", "日射の侵入を防"],
}
