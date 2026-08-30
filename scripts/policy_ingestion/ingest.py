from __future__ import annotations

import argparse
from pathlib import Path

from .document_parser import parse_policy
from .exporter import export_all, write_report
from .pdf_loader import discover_pdf
from .schema_validator import validate_cross_references, validate_records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest a traceable Tokyo policy PDF.")
    parser.add_argument("--input", type=Path, help="Source PDF; auto-discovered when omitted.")
    parser.add_argument("--metadata", type=Path, help="Document metadata JSON sidecar.")
    parser.add_argument("--force-ocr", action="store_true", help="Ignore a healthy embedded text layer.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    source = discover_pdf(repo_root, args.input)
    metadata = args.metadata or repo_root / "data/policy_sources/tokyo_summer_heat_guideline.metadata.json"
    parsed = parse_policy(repo_root, source, metadata if metadata.exists() else None, args.force_ocr)
    schemas = repo_root / "scripts/policy_ingestion/schemas"
    errors = []
    errors += validate_records([parsed.document], schemas / "document.schema.json", "documents")
    errors += validate_records(parsed.chunks, schemas / "chunk.schema.json", "chunks")
    errors += validate_records(parsed.interventions, schemas / "intervention.schema.json", "interventions")
    errors += validate_records(parsed.scenarios, schemas / "scenario.schema.json", "scenarios")
    errors += validate_cross_references(
        [parsed.document], parsed.chunks, parsed.interventions, parsed.scenarios
    )
    outputs = export_all(
        repo_root, parsed.document, parsed.loaded.pages, parsed.chunks,
        parsed.interventions, parsed.scenarios, errors, parsed.warnings,
    )
    write_report(
        outputs["report"], parsed.document, parsed.chunks, parsed.interventions,
        parsed.scenarios, parsed.loaded.missing_pages, parsed.warnings, errors,
    )
    print(f"Document: {parsed.document['document_id']}")
    print(f"Pages: {parsed.document['pages']}; chunks: {len(parsed.chunks)}; interventions: {len(parsed.interventions)}; scenarios: {len(parsed.scenarios)}")
    print(f"Validation errors: {len(errors)}")
    for name, path in outputs.items():
        print(f"{name}: {path}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

