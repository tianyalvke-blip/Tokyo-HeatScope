# Policy ingestion report

- Document: 東京都環境局《夏の暑さ対策の手引》 (`tokyo_summer_heat_guideline_2019`)
- Pages processed: 50
- Chunks generated: 44
- Interventions extracted: 19
- Scenarios detected: 9
- Low-confidence records: 5
- Missing pages: None
- Validation errors: 0

## Parsing warnings

- Embedded text quality was 0.87; used rendered-page Japanese OCR.
- Rendered-page OCR was required by the document metadata to prevent embedded-text cross-page bleed.
- Page 31: fewer than three table-row anchors recognized.
- Page 31: fewer than three table-row anchors recognized.
- Page 31: fewer than three table-row anchors recognized.

## Low-confidence records

- chunk: tokyo_summer_heat_guideline_2019-p023-building_insulation
- chunk: tokyo_summer_heat_guideline_2019-p024-dry_mist
- intervention: energy_efficiency
- intervention: waste_heat_mitigation
- intervention: exhaust_location

## Validation

- All schema and cross-reference checks passed.

## Requested QA samples

### 街区

```json
{
  "scenario_id": "urban_block",
  "name_ja": "街区",
  "name_en": "urban block",
  "characteristics": [
    "building_hvac_waste_heat"
  ],
  "problems": [
    "surface_heat_storage",
    "anthropogenic_waste_heat",
    "pedestrian_heat_exposure"
  ],
  "recommended_interventions": [
    "building_configuration",
    "building_insulation",
    "green_roof",
    "green_wall",
    "ground_greening",
    "heat_reflective_surface",
    "retroreflective_surface",
    "roof_heat_shielding",
    "uchimizu",
    "water_retentive_surface",
    "water_surface"
  ],
  "characteristics_and_guidance_ja": "⑤ 街区 【 特徴 】 街区内の建物からの排熱があり 、 また 、 熱をためやすい 。 【 対策 】 ・建物の屋上などに緑化・遮熱化などを行うことで 、 建物表面への蓄熱を抑制 ( 熱をためない ) ・建物の断熱の強化や省エネルギ - 機器の導入により排熱を減少 ( 熱をださない ) ・街区 - 帯で緑化や保水化の整備を行うことで 、 快適性を向上 ( 熱をもらわない ) ・建物建設の際には 、 風通しを確保するため建物の形状や配置を工夫 ( 熱をためない ) ・まちなかで打ち水を行うなど 、 来街者を含めてまち全体で - 体となった暑さ対策を実施第 — 部基礎編一 ~ ・屋根面での対策・風通し対策建物形状 / 配置の工夫 300 屋上緑化屋上の遮熱化・建物外構での対策水面 / 水辺の確保ためもらわ第第を第朝第第ト・壁面等での対策壁面緑化再帰反射化・建物外構での対策緑化・保水化 ( 地表面 ) ・その他の対策打ち水遮熱化 30 各対策の説明 ( 第 4 章参照 ) 水面 / 水辺の確保 → o. 35 建物形状の工夫 → 0.31 屋上緑化 → P23 壁面緑化 → P26 打ら水 → o. 39 再帰反射化 → 028 建物外構での対策 ( 緑化・遮熱化・保水化なと ) → 032 ~ 34 なと 14",
  "evidence_type": "policy",
  "extraction_confidence": "high",
  "source_evidence": [
    {
      "document_id": "tokyo_summer_heat_guideline_2019",
      "source_file": "F:\\GLEN_LST_AGENT\\heat_island$regulation.files$atsusa_tebiki_h30kaitei.pdf",
      "page": 16,
      "chapter": "第I部 基礎編",
      "section": "第3章 夏の暑さ対策の用途別メニュー",
      "chunk_id": "tokyo_summer_heat_guideline_2019-p016-urban_block",
      "printed_page": 14
    }
  ]
}
```

### 道路

```json
{
  "scenario_id": "road",
  "name_ja": "道路",
  "name_en": "road",
  "characteristics": [
    "large_asphalt_surface",
    "vehicle_waste_heat"
  ],
  "problems": [
    "surface_heat_storage",
    "anthropogenic_waste_heat",
    "pedestrian_heat_exposure"
  ],
  "recommended_interventions": [
    "dry_mist",
    "ground_greening",
    "heat_reflective_surface",
    "shade",
    "water_retentive_surface"
  ],
  "characteristics_and_guidance_ja": "③ 道路車道・歩道にアスファルト面が多く熱をためやすいほか 、 自動車等による排熱もある 。 【 特徴 】 【 対策 】 ・車道の遮熱化・保水化 、 歩道の緑化・保水化により地表面への蓄熱を抑制 ( 熱をためない ) ・街路樹により緑陰をつくり 、 バス停には日除けやドライ型 ( 微細 ) ミストを設置することで快適性を向上 ( 熱をもらわない ) ・クールスポットづくり日除けドライ型 ( 微細 ) ミスト第 - 部基礎編 ~ よためもらわ 6 らわ・道での対策保水化 O O ためもらわ緑化一ミ・車道での対策遮熱化保水化 0 にめもらわ各対策の説明 ( 第 4 章参照 ) 日除け → o. 36 ドライ型 ( 微細 ) ミスト → o. 38 緑化 → o. 32 保水化 → o. 34 遮熱化 → o. 33 などよ 17",
  "evidence_type": "policy",
  "extraction_confidence": "high",
  "source_evidence": [
    {
      "document_id": "tokyo_summer_heat_guideline_2019",
      "source_file": "F:\\GLEN_LST_AGENT\\heat_island$regulation.files$atsusa_tebiki_h30kaitei.pdf",
      "page": 19,
      "chapter": "第I部 基礎編",
      "section": "第3章 夏の暑さ対策の用途別メニュー",
      "chunk_id": "tokyo_summer_heat_guideline_2019-p019-road",
      "printed_page": 17
    }
  ]
}
```

### 保水化

```json
{
  "intervention_id": "water_retentive_surface",
  "name_ja": "保水化",
  "name_en": "water-retentive surface treatment",
  "category": "surface_material",
  "target": [
    "road",
    "sidewalk",
    "open_space"
  ],
  "applicable_scenarios": [
    "apartment",
    "detached_house",
    "office_commercial_building",
    "park",
    "plaza",
    "road",
    "urban_block",
    "warehouse_factory"
  ],
  "policy_logic": {
    "dasanai": false,
    "tamenai": true,
    "morawanai": true
  },
  "mechanisms": [
    "evaporative_cooling"
  ],
  "expected_effects": [
    "路面等を濡れた状態に保つことで 、 気化熱を利用した表面温度の上昇抑制や冷却の効果があり 、 緩和策として有効です 。 また 、 路面温度の上昇が抑制されることにより赤外放射が低減されるため 、 適応策としても有効です 。",
    "・路面等の保水性効果は 、 通常のアスファルトとして比較して次のことが確認されています 。 ① 路面の表面温度は 、 最大 1 0 ℃ 程度低下し 、 日陰で散水すると気温以下にまで低下することが確認されています 2 5 。 ② 体感温度として 、 体感温度指標 SET* は 、 通常のアスファルトと比べて 、 高さ 0.6m 地点では 2 ℃ 程度低いことが確認されていいます 2 第 Ⅱ 部技術編 , 当 ~ 保水性舗装密粒度黼装降水量を : ( しし目ツ .4 ( 0 0 グラフ 4 ー 2 密粒度舗装との温度差 ( 平成 15 年八重洲 )"
  ],
  "co_benefits": [],
  "constraints": [
    "路面温度の上昇を抑制する効果は 、 路面の湿潤程度により影響を受けるため 、 舗装面を湿潤な状態に保てるよう 、 給水システムの併用や定期的な散水が必要です 。"
  ],
  "maintenance": [
    "舗装面の定期的な清掃 、 灌水設備の定期的な清掃",
    "・点検が必要です 。"
  ],
  "cost_level": null,
  "cost_evidence_ja": "保水性舗装の場合 、 数千 ~ 1 万円 / 前後 ( 材料 + 施工費 ) 2 8 ′ 2 9 ・保水性プロックの場合 、 1 万円 / 前後 ( 材料 + 施工費 )",
  "implementation_notes": [
    "建物外構や道路の路面等において 、 保水性の高い舗装やプロック等 ( 舗装表面に吸水",
    "・保水性能を持つ保水材を充填 ) を敷設する対策です 。 図 4 ー 8 保水性路面の概要 2 5 写真 4 ー 8 丸の内バークビルディング中庭 ( 東京都千代田区 )"
  ],
  "case_studies_ja": [
    "丸の内ノ ← クビルディング中庭の給水型保水性舗装 ( 東京都千代田区 )"
  ],
  "evidence_type": "policy",
  "extraction_confidence": "high",
  "source_evidence": [
    {
      "document_id": "tokyo_summer_heat_guideline_2019",
      "source_file": "F:\\GLEN_LST_AGENT\\heat_island$regulation.files$atsusa_tebiki_h30kaitei.pdf",
      "page": 36,
      "page_end": 36,
      "printed_page": 34,
      "printed_page_end": 34,
      "chapter": "第II部 技術編",
      "section": "第4章 4-1 各技術の紹介",
      "chunk_id": "tokyo_summer_heat_guideline_2019-p036-water_retentive_surface"
    }
  ],
  "gis_interface": {
    "planning_problem_tags": [],
    "candidate_variable_names": [],
    "causal_claim": null,
    "note": "Reserved for future model-to-policy filtering; no threshold or causal rule is asserted."
  }
}
```

### 屋上緑化

```json
{
  "intervention_id": "green_roof",
  "name_ja": "屋上緑化",
  "name_en": "green roof",
  "category": "vegetation",
  "target": [
    "building_roof"
  ],
  "applicable_scenarios": [
    "apartment",
    "office_commercial_building",
    "urban_block"
  ],
  "policy_logic": {
    "dasanai": true,
    "tamenai": true,
    "morawanai": true
  },
  "mechanisms": [
    "evaporative_cooling",
    "reduce_heat_transfer"
  ],
  "expected_effects": [
    "屋上 ( 屋根 ) 緑化の土壌などによる断熱効果 ( 省エネルギ - 効果 ) や 、 植物の蒸散による建物の蓄熱イ氏減は 、 緩和策として有効です 。 また 、 屋上庭園やガーデニングとして活用した場合は 、 屋上利用者のための適応策としても有効です 。 第 Ⅱ 部技術編 - 4 写真 4-1 郁文館夢学園屋上庭園平成 22 年度屋上緑化部門「環境大臣賞」屋上",
    "・技術特殊緑化技術コンクール ( 財団法人都市緑化機構 )"
  ],
  "co_benefits": [],
  "constraints": [
    "屋上面の耐荷重及び防水 、 耐根対策の考慮が必要です 。",
    "・植物は散水など - 定の管理をすることで 、 蒸散による効果が得られます 。"
  ],
  "maintenance": [
    "散水 、 施肥 、 落ち葉等清掃 、 除草 、 病害虫駆除 、 せん定 、 点検等が必要です 。"
  ],
  "cost_level": null,
  "cost_evidence_ja": "芝類やセダム類による屋上緑化の設置に要する費用は 、 数万円 / m ( 材料 + 施工費 )",
  "implementation_notes": [
    "屋上 ( 屋根 ) に人工軽量土壌などの植栽基盤を敷き 、 その上を芝生や樹木などで緑化する対策です 。"
  ],
  "case_studies_ja": [
    "東京スクエアガ - デン ( 東京都中央区 )",
    "・豊島区役所 ( 東京都豊島区 )"
  ],
  "evidence_type": "policy",
  "extraction_confidence": "high",
  "source_evidence": [
    {
      "document_id": "tokyo_summer_heat_guideline_2019",
      "source_file": "F:\\GLEN_LST_AGENT\\heat_island$regulation.files$atsusa_tebiki_h30kaitei.pdf",
      "page": 25,
      "page_end": 25,
      "printed_page": 23,
      "printed_page_end": 23,
      "chapter": "第II部 技術編",
      "section": "第4章 4-1 各技術の紹介",
      "chunk_id": "tokyo_summer_heat_guideline_2019-p025-green_roof"
    }
  ],
  "gis_interface": {
    "planning_problem_tags": [],
    "candidate_variable_names": [],
    "causal_claim": null,
    "note": "Reserved for future model-to-policy filtering; no threshold or causal rule is asserted."
  }
}
```

### 建物形状の工夫

```json
{
  "intervention_id": "building_configuration",
  "name_ja": "建物形状の工夫",
  "name_en": "building form and configuration",
  "category": "building_form",
  "target": [
    "building",
    "urban_block"
  ],
  "applicable_scenarios": [
    "apartment",
    "office_commercial_building",
    "urban_block"
  ],
  "policy_logic": {
    "dasanai": false,
    "tamenai": true,
    "morawanai": false
  },
  "mechanisms": [
    "reduce_surface_heat_storage",
    "improve_ventilation"
  ],
  "expected_effects": [
    "風の通りがよくなることで建物等の蓄熱を抑制するため 、 緩和策として有効です 。"
  ],
  "co_benefits": [],
  "constraints": [
    "大規模開発などの場合は 、 建物が周辺において 、 歩行者に悪影響 ( 強風 ) を及ぼさないよう配慮が必要です 。 第 Ⅱ"
  ],
  "maintenance": [],
  "cost_level": null,
  "cost_evidence_ja": "規模等により 、 導入コストには幅があります 。",
  "implementation_notes": [
    "建物の建設時には 、 建築物の配置や形状が夏の主風向の通風を妨けない等 、 風向や風の通り道に配慮して建物配置や形状を工夫するなどの対策です 。",
    "・連続したオープンスへ - ス ( 開放的な空間 ) の創出により風を都市空間に流入させることが重要となります 。 ※ 見付幅比 = bc / ad 夏の主風ロ ad. 最大敷地幅 bc",
    "・見付幅図 4-6 風に対する見付け幅の考え方"
  ],
  "case_studies_ja": [
    "大手町",
    "・丸の内",
    "・有楽町地区「風の道」 1 6",
    "・東京都環境局東京都建築物環境計画書制度ホ - ムへ - ジ公表建物参照技 (http://www7.kankyo.metro.tokyo.jp/building/area_select.html)"
  ],
  "evidence_type": "policy",
  "extraction_confidence": "high",
  "source_evidence": [
    {
      "document_id": "tokyo_summer_heat_guideline_2019",
      "source_file": "F:\\GLEN_LST_AGENT\\heat_island$regulation.files$atsusa_tebiki_h30kaitei.pdf",
      "page": 33,
      "page_end": 33,
      "printed_page": 31,
      "printed_page_end": 31,
      "chapter": "第II部 技術編",
      "section": "第4章 4-1 各技術の紹介",
      "chunk_id": "tokyo_summer_heat_guideline_2019-p033-building_configuration"
    }
  ],
  "gis_interface": {
    "planning_problem_tags": [],
    "candidate_variable_names": [],
    "causal_claim": null,
    "note": "Reserved for future model-to-policy filtering; no threshold or causal rule is asserted."
  }
}
```
