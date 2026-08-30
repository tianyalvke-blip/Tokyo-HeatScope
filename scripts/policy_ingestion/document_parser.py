from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .intervention_extractor import extract_interventions
from .metadata_extractor import build_document_metadata
from .pdf_loader import LoadedDocument, load_pdf, sha256_file
from .scenario_extractor import extract_scenarios
from .section_splitter import build_chunks


@dataclass
class ParsedPolicy:
    loaded: LoadedDocument
    document: dict[str, Any]
    chunks: list[dict[str, Any]]
    interventions: list[dict[str, Any]]
    scenarios: list[dict[str, Any]]
    warnings: list[str]


def parse_policy(
    repo_root: Path, source_pdf: Path, metadata_sidecar: Path | None,
    force_ocr: bool = False,
) -> ParsedPolicy:
    if metadata_sidecar and metadata_sidecar.exists():
        supplied = json.loads(metadata_sidecar.read_text(encoding="utf-8"))
        if supplied.get("extraction_options", {}).get("force_ocr"):
            force_ocr = True
    source_hash = sha256_file(source_pdf)[:16]
    work_dir = repo_root / "tmp" / "pdfs" / "policy_ingestion" / source_hash
    loaded = load_pdf(
        source_pdf, work_dir,
        repo_root / "scripts" / "policy_ingestion" / "windows_ocr.ps1",
        force_ocr=force_ocr,
    )
    if force_ocr:
        loaded.warnings.append("Rendered-page OCR was required by the document metadata to prevent embedded-text cross-page bleed.")
    document = build_document_metadata(loaded, metadata_sidecar)
    chunks = build_chunks(document, loaded.pages)
    scenarios = extract_scenarios(chunks)
    interventions, extraction_warnings = extract_interventions(
        document, chunks, loaded.pages, scenarios
    )
    return ParsedPolicy(
        loaded=loaded, document=document, chunks=chunks,
        interventions=interventions, scenarios=scenarios,
        warnings=loaded.warnings + extraction_warnings,
    )
