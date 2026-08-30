from __future__ import annotations

import re
from typing import Any

from .catalog import INTERVENTION_CATALOG, MECHANISM_PATTERNS
from .text_utils import normalize_ocr_text


ROW_LABELS = ["概要", "効果", "導入コスト", "維持管理", "留意点", "事例", "参考"]


def _line_geometry(line: dict[str, Any]) -> tuple[float, float, str]:
    words = line.get("words") or []
    if not words:
        return (0.0, 0.0, normalize_ocr_text(line.get("text", "")))
    return (
        min(float(word.get("x", 0)) for word in words),
        min(float(word.get("y", 0)) for word in words),
        normalize_ocr_text(line.get("text", "")),
    )


def extract_labeled_rows(page: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    """Extract table rows using OCR coordinates, never visual reading order alone."""
    geometries = [_line_geometry(line) for line in page.get("lines", [])]
    anchors: list[tuple[float, str, float]] = []
    for x, y, text in geometries:
        compact = re.sub(r"\s+", "", text)
        for label in ROW_LABELS:
            if compact == label or compact.startswith(label):
                anchors.append((y, label, x))
                break
    anchors.sort()
    warnings: list[str] = []
    rows: dict[str, str] = {}
    if len(anchors) < 3:
        warnings.append(f"Page {page['page']}: fewer than three table-row anchors recognized.")
        return rows, warnings
    for pos, (start_y, label, anchor_x) in enumerate(anchors):
        end_y = anchors[pos + 1][0] if pos + 1 < len(anchors) else float("inf")
        selected = []
        for x, y, text in geometries:
            if start_y - 4 <= y < end_y - 4 and text:
                compact = re.sub(r"\s+", "", text)
                if compact.startswith(label) and abs(x - anchor_x) < 80:
                    compact = compact[len(label):].strip()
                    if compact:
                        selected.append((y, x, compact))
                elif x > anchor_x + 60 or y > start_y + 12:
                    selected.append((y, x, text))
        selected.sort()
        value = normalize_ocr_text(" ".join(item[2] for item in selected))
        value = re.sub(r"\s+", " ", value).strip(" ・")
        if value and value not in {"-", "―", "ー"}:
            rows[label] = value
    return rows, warnings


def _mechanisms(text: str) -> list[str]:
    return [key for key, patterns in MECHANISM_PATTERNS.items() if any(pattern in text for pattern in patterns)]


def _as_list(value: str | None) -> list[str]:
    if not value:
        return []
    parts = [part.strip() for part in re.split(r"(?=・)", value) if part.strip(" ・")]
    return parts or [value]


# Effect sentences are only taken from the source text. A sentence counts as an
# effect only when it carries a benefit verb AND a benefit connective, so
# constraints/notes are never promoted into effects.
_EFFECT_VERBS = [
    "抑制", "低減", "減らし", "少なく", "向上", "防ぐ", "潜熱化", "冷却",
    "低下", "下げる", "改善", "予防",
]
_EFFECT_LINKERS = ["ことにより", "により", "ことで", "ため、", "として有効", "効果が", "策として", "によって"]


def _inline_effects(text: str | None, limit: int = 3) -> list[str]:
    """Fallback: extract source-stated effect sentences when the structured
    table's 効果 row is unavailable (e.g. OCR table anchors failed on a page).
    Fires only on text the source actually contains — never general knowledge."""
    if not text:
        return []
    compact = re.sub(r"\s+", "", text)
    sentences = re.split(r"(?<=。)", compact)
    out: list[str] = []
    for sentence in sentences:
        stripped = sentence.strip("。 ・")
        if not stripped:
            continue
        if any(v in stripped for v in _EFFECT_VERBS) and any(l in stripped for l in _EFFECT_LINKERS):
            cleaned = re.sub(r"^(?:・|(?:①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩|⑪|⑫))", "", stripped)
            if cleaned and cleaned not in out:
                out.append(cleaned)
        if len(out) >= limit:
            break
    return out


def extract_interventions(
    document: dict[str, Any],
    chunks: list[dict[str, Any]],
    pages: list[dict[str, Any]],
    scenarios: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    page_map = {int(page["page"]): page for page in pages}
    warnings: list[str] = []
    records: list[dict[str, Any]] = []
    for intervention_id, spec in INTERVENTION_CATALOG.items():
        chunk = next(
            (item for item in chunks if intervention_id in item.get("interventions", []) and item["page_start"] <= spec["page_start"] <= item["page_end"]),
            None,
        )
        if not chunk:
            warnings.append(f"No semantic chunk found for intervention {intervention_id}.")
            continue
        rows: dict[str, str] = {}
        row_warnings: list[str] = []
        if spec["page_start"] >= 25:
            for page_number in range(spec["page_start"], spec["page_end"] + 1):
                extracted, page_warnings = extract_labeled_rows(page_map[page_number])
                row_warnings.extend(page_warnings)
                for label, value in extracted.items():
                    rows[label] = (rows.get(label, "") + " " + value).strip()
        else:
            # Public-health item is stated in a scenario, not the technical table.
            rows["概要"] = chunk["text_ja"]
        warnings.extend(row_warnings)
        applicable = sorted(
            scenario["scenario_id"] for scenario in scenarios
            if intervention_id in scenario.get("recommended_interventions", [])
        )
        logic = {key: key in spec["logic"] for key in ["dasanai", "tamenai", "morawanai"]}
        evidence = {
            "document_id": document["document_id"], "source_file": document["source_file"],
            "page": spec["page_start"], "page_end": spec["page_end"],
            "printed_page": chunk.get("printed_page_start"),
            "printed_page_end": chunk.get("printed_page_end"),
            "chapter": chunk["chapter"], "section": chunk["section"], "chunk_id": chunk["chunk_id"],
        }
        technical_text = " ".join(rows.values()) or chunk["text_ja"]
        confidence = "high" if rows.get("概要") and spec["page_start"] != 31 else "medium"
        if row_warnings:
            confidence = "low"
        # Effect fallback: if the structured 効果 row was not recovered (e.g.
        # OCR table anchors failed), pull source-stated effect sentences from
        # the chunk text. Confidence stays low — these are inline, not table.
        effects = _as_list(rows.get("効果"))
        if not effects and not spec.get("effects_inline_manual"):
            effects = _inline_effects(chunk["text_ja"])
        records.append({
            "intervention_id": intervention_id, "name_ja": spec["name_ja"], "name_en": spec["name_en"],
            "category": spec["category"], "target": spec["target"], "applicable_scenarios": applicable,
            "policy_logic": logic, "mechanisms": _mechanisms(technical_text),
            "expected_effects": effects, "co_benefits": [],
            "constraints": _as_list(rows.get("留意点")), "maintenance": _as_list(rows.get("維持管理")),
            # The source gives ranges/bars, not a stable low/medium/high category.
            "cost_level": None, "cost_evidence_ja": rows.get("導入コスト"),
            "implementation_notes": _as_list(rows.get("概要")),
            "case_studies_ja": _as_list(rows.get("事例")),
            "evidence_type": "policy", "extraction_confidence": confidence,
            "source_evidence": [evidence],
            "gis_interface": {
                "planning_problem_tags": [],
                "candidate_variable_names": [],
                "causal_claim": None,
                "note": "Reserved for future model-to-policy filtering; no threshold or causal rule is asserted.",
            },
        })
    return records, warnings
