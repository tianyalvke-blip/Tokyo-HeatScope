from __future__ import annotations

import re
from typing import Any

from .catalog import SCENARIO_CATALOG


CHARACTERISTIC_PATTERNS = {
    "large_asphalt_surface": [r"アスファルト.*熱をため", r"アスファルト面が多く"],
    "concrete_surface_heat_storage": [r"コンクリート.*熱をため"],
    "vehicle_waste_heat": [r"自動車.*排熱"],
    "building_hvac_waste_heat": [r"空調.*排熱", r"建物からの排熱"],
    "limited_shade": [r"日射を遮るものが少"],
    "metal_roof_heat_storage": [r"金属製の屋根.*熱をため"],
    "prolonged_outdoor_crowding": [r"たくさんの人が集まり.*行列", r"長時間の行列"],
}

PROBLEM_PATTERNS = {
    "surface_heat_storage": [r"熱をため", r"蓄熱"],
    "anthropogenic_waste_heat": [r"排熱"],
    "pedestrian_heat_exposure": [r"歩行.*暑", r"人が熱をもら", r"快適性"],
    "solar_heat_exposure": [r"日射を遮るものが少", r"炎天下"],
}


def _tags(text: str, patterns: dict[str, list[str]]) -> list[str]:
    return [tag for tag, variants in patterns.items() if any(re.search(pattern, text) for pattern in variants)]


def extract_scenarios(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for chunk in chunks:
        for scenario_id in chunk.get("scenario", []):
            name_ja, name_en = SCENARIO_CATALOG[scenario_id]
            text = chunk["text_ja"]
            evidence = {
                "document_id": chunk["document_id"], "source_file": chunk["source_file"],
                "page": chunk["page_start"], "chapter": chunk["chapter"],
                "section": chunk["section"], "chunk_id": chunk["chunk_id"],
                "printed_page": chunk.get("printed_page_start"),
            }
            records.append({
                "scenario_id": scenario_id, "name_ja": name_ja, "name_en": name_en,
                "characteristics": _tags(text, CHARACTERISTIC_PATTERNS),
                "problems": _tags(text, PROBLEM_PATTERNS),
                "recommended_interventions": chunk.get("interventions", []),
                "characteristics_and_guidance_ja": text,
                "evidence_type": "policy", "extraction_confidence": chunk["extraction_confidence"],
                "source_evidence": [evidence],
            })
    return records
