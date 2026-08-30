from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .pdf_loader import LoadedDocument


def build_document_metadata(loaded: LoadedDocument, sidecar: Path | None) -> dict[str, Any]:
    supplied: dict[str, Any] = {}
    if sidecar and sidecar.exists():
        supplied = json.loads(sidecar.read_text(encoding="utf-8"))
    stem = loaded.source_file.stem.lower().replace("-", "_")
    document = {
        "document_id": supplied.get("document_id", stem),
        "title_ja": supplied.get("title_ja", loaded.source_file.stem),
        "title_en": supplied.get("title_en", ""),
        "authority": supplied.get("authority", ""),
        "government_level": supplied.get("government_level", "unknown"),
        "document_type": supplied.get("document_type", "unknown"),
        "publication_year": supplied.get("publication_year"),
        # Never infer current legal/policy validity.
        "status": supplied.get("status", "unknown"),
        "geography": supplied.get("geography", []),
        "topics": supplied.get("topics", []),
        "language": supplied.get("language", "ja"),
        "source_file": str(loaded.source_file),
        "source_sha256": loaded.source_sha256,
        "source_url": supplied.get("source_url"),
        "pages": len(loaded.pages),
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "notes": supplied.get("notes", ""),
        "extraction": {
            "parser": loaded.parser,
            "embedded_text_preserved": True,
            "ocr_language": "ja" if "ocr" in loaded.parser else None,
            "warnings": loaded.warnings,
            "source_options": supplied.get("extraction_options", {}),
        },
    }
    return document
