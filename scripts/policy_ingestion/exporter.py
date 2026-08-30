from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import SCHEMA_VERSION


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def export_source_markdown(path: Path, document: dict[str, Any], pages: list[dict[str, Any]]) -> None:
    lines = [
        f"# {document['title_ja']}", "",
        f"- Document ID: `{document['document_id']}`",
        f"- Authority: {document['authority']}",
        f"- Source: `{document['source_file']}`",
        f"- SHA-256: `{document['source_sha256']}`",
        f"- Extraction: {document['extraction']['parser']}", "",
        "> OCR-derived transcription for retrieval and QA. The original PDF is authoritative.", "",
    ]
    for page in pages:
        lines += [f"## PDF page {page['page']}", "", page.get("text", "").strip(), ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def export_all(
    repo_root: Path, document: dict[str, Any], pages: list[dict[str, Any]],
    chunks: list[dict[str, Any]], interventions: list[dict[str, Any]],
    scenarios: list[dict[str, Any]], errors: list[str], warnings: list[str],
) -> dict[str, Path]:
    knowledge = repo_root / "knowledge"
    is_benchmark = document["document_id"] == "tokyo_summer_heat_guideline_2019"
    base_name = "tokyo_summer_heat_guideline" if is_benchmark else document["document_id"]
    intervention_name = "tokyo_heat_interventions" if is_benchmark else f"{document['document_id']}_interventions"
    scenario_name = "tokyo_heat_scenarios" if is_benchmark else f"{document['document_id']}_scenarios"
    outputs = {
        "source_markdown": knowledge / f"sources/{base_name}.md",
        "chunks": knowledge / f"chunks/{base_name}.jsonl",
        "interventions": knowledge / f"interventions/{intervention_name}.json",
        "scenarios": knowledge / f"interventions/{scenario_name}.json",
        "documents": knowledge / "documents/policy_documents.json",
        "manifest": knowledge / "indexes/policy_manifest.json",
        "report": knowledge / "policy_ingestion_report.md",
        "errors": knowledge / "documents/policy_extraction_errors.json",
    }
    export_source_markdown(outputs["source_markdown"], document, pages)
    outputs["chunks"].parent.mkdir(parents=True, exist_ok=True)
    outputs["chunks"].write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in chunks), encoding="utf-8"
    )
    _write_json(outputs["interventions"], {"schema_version": SCHEMA_VERSION, "interventions": interventions})
    _write_json(outputs["scenarios"], {"schema_version": SCHEMA_VERSION, "scenarios": scenarios})
    documents = []
    if outputs["documents"].exists():
        try:
            documents = json.loads(outputs["documents"].read_text(encoding="utf-8")).get("documents", [])
        except (json.JSONDecodeError, OSError):
            documents = []
    documents = [item for item in documents if item.get("document_id") != document["document_id"]] + [document]
    _write_json(outputs["documents"], {"schema_version": SCHEMA_VERSION, "documents": documents})
    chunk_files = sorted(
        str(path.relative_to(repo_root)).replace("\\", "/")
        for path in (knowledge / "chunks").glob("*.jsonl")
    )
    _write_json(outputs["manifest"], {
        "schema_version": SCHEMA_VERSION,
        "documents": [document["document_id"]],
        "chunk_files": chunk_files,
        "retrieval": {
            "lexical": {"type": "bm25_japanese_character_ngram_and_word", "status": "runtime_built"},
            "embedding": {"index": None, "status": "not_built", "adapter": None}
        },
        "note": "Layer B filters first; Layer A chunks are then ranked. Embeddings remain an optional future adapter.",
    })
    _write_json(outputs["errors"], {"validation_errors": errors, "parsing_warnings": warnings})
    return outputs


def write_report(
    path: Path, document: dict[str, Any], chunks: list[dict[str, Any]],
    interventions: list[dict[str, Any]], scenarios: list[dict[str, Any]],
    missing_pages: list[int], warnings: list[str], errors: list[str],
) -> None:
    low = []
    for kind, records in [("chunk", chunks), ("intervention", interventions), ("scenario", scenarios)]:
        low += [f"{kind}: {item.get(kind + '_id', item.get('chunk_id'))}" for item in records if item["extraction_confidence"] == "low"]
    by_intervention = {item["intervention_id"]: item for item in interventions}
    by_scenario = {item["scenario_id"]: item for item in scenarios}
    samples = [
        ("街区", by_scenario.get("urban_block")),
        ("道路", by_scenario.get("road")),
        ("保水化", by_intervention.get("water_retentive_surface")),
        ("屋上緑化", by_intervention.get("green_roof")),
        ("建物形状の工夫", by_intervention.get("building_configuration")),
    ]
    lines = [
        "# Policy ingestion report", "",
        f"- Document: {document['authority']}《{document['title_ja']}》 (`{document['document_id']}`)",
        f"- Pages processed: {document['pages']}",
        f"- Chunks generated: {len(chunks)}",
        f"- Interventions extracted: {len(interventions)}",
        f"- Scenarios detected: {len(scenarios)}",
        f"- Low-confidence records: {len(low)}",
        f"- Missing pages: {missing_pages or 'None'}",
        f"- Validation errors: {len(errors)}", "",
        "## Parsing warnings", "",
    ]
    lines += [f"- {warning}" for warning in warnings] or ["- None"]
    lines += ["", "## Low-confidence records", ""]
    lines += [f"- {item}" for item in low] or ["- None"]
    lines += ["", "## Validation", ""]
    lines += [f"- {error}" for error in errors] or ["- All schema and cross-reference checks passed."]
    lines += ["", "## Requested QA samples", ""]
    for label, record in samples:
        lines += [f"### {label}", ""]
        if record is None:
            lines += ["Record not generated.", ""]
        else:
            lines += ["```json", json.dumps(record, ensure_ascii=False, indent=2), "```", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
