"""structure.py — generic, text-driven document structure detection for policy PDFs.

Lets the ingestion pipeline process future documents without a benchmark page
map. The benchmark document keeps its verified page map in section_splitter;
this module is the generic path for any other Japanese planning / heat-policy
document (Chapter/Section headings, 【特徴】/【対策】 scenario blocks, numbered
technical entries 【概要】, case-study and reference pages).

All hints are derived purely from the page text — nothing is hardcoded to a
specific document's page numbers.
"""

from __future__ import annotations

import re
from typing import Any

from .catalog import INTERVENTION_CATALOG, SCENARIO_CATALOG

_VIEWPOINTS = (
    ("dasanai", "熱を「ださない」"),
    ("tamenai", "熱を「ためない」"),
    ("morawanai", "熱をもらわない"),
)


def _compact(text: str | None) -> str:
    return re.sub(r"\s+", "", text or "")


def _heading_parts(text: str) -> tuple[str, str, str]:
    """Best-effort chapter / section / subsection from explicit heading text."""
    chapter = section = subsection = ""
    m = re.search(r"(第\s*[一二三四五六]\s*部\s*[^\n]{0,20})", text or "")
    if m:
        chapter = m.group(1).strip()
    m = re.search(r"(第\s*[0-9一二三四五六七八九十]+\s*章\s*[^\n]{0,30})", text or "")
    if m:
        section = m.group(1).strip()
    m = re.search(r"(第\s*[0-9一二三四五六七八九十]+\s*[-－—]\s*[0-9一二三四五六七八九十]+\s*[^\n]{0,30})", text or "")
    if m:
        subsection = m.group(1).strip()
    return chapter, section, subsection


def _viewpoint_in(text: str) -> str:
    compact = _compact(text)
    for key, label in _VIEWPOINTS:
        if label in compact:
            return key
    return ""


def detect_structure(text: str) -> dict[str, Any]:
    """Return {chapter, section, subsection, knowledge_type, scenarios} hints
    derived purely from the page text (generic across Japanese policy PDFs)."""
    compact = _compact(text)
    chapter, section, subsection = _heading_parts(text)
    scenarios: list[str] = []
    knowledge_type = "background"

    if "【特徴】" in compact and "【対策】" in compact:
        knowledge_type = "scenario_guidance"
        # A numbered scenario heading such as "③ 道路" / "④ 屋外イベント会場".
        for sid, (name_ja, _) in SCENARIO_CATALOG.items():
            norm = _compact(name_ja)
            if norm in compact and re.search(rf"[①②③④⑤⑥⑦⑧⑨⑩]\s*{re.escape(norm)}", compact):
                scenarios.append(sid)
                break
    elif "【概要】" in compact or (
        "概要" in compact
        and any(alias in compact for spec in INTERVENTION_CATALOG.values() for alias in spec["aliases"])
    ):
        knowledge_type = "intervention"
    elif "事例" in compact and len(compact) > 120 and "参考" not in compact:
        knowledge_type = "case_study"
    elif "出所" in compact or "参考文献" in compact or "参考資料" in compact:
        knowledge_type = "definition"
    else:
        viewpoint = _viewpoint_in(text)
        if viewpoint:
            knowledge_type = "policy_principle"
            subsection = next(label for key, label in _VIEWPOINTS if key == viewpoint)

    return {
        "chapter": chapter,
        "section": section,
        "subsection": subsection,
        "knowledge_type": knowledge_type,
        "scenarios": scenarios,
    }
