from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pdfplumber


@dataclass
class LoadedDocument:
    source_file: Path
    source_sha256: str
    pages: list[dict[str, Any]]
    parser: str
    warnings: list[str]
    missing_pages: list[int]


def discover_pdf(repo_root: Path, requested: Path | None = None) -> Path:
    if requested and requested.exists():
        return requested.resolve()
    conventional = repo_root / "data" / "policy_sources" / "tokyo_summer_heat_guideline.pdf"
    if conventional.exists():
        return conventional.resolve()
    candidates = sorted(repo_root.glob("**/*atsusa_tebiki*.pdf"))
    if len(candidates) == 1:
        return candidates[0].resolve()
    if not candidates:
        raise FileNotFoundError(
            f"No source PDF found. Place it at {conventional} or pass --input."
        )
    raise RuntimeError("Multiple matching PDFs found; pass --input explicitly: " + ", ".join(map(str, candidates)))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _text_quality(text: str) -> float:
    compact = re.sub(r"\s+", "", text)
    if not compact:
        return 0.0
    valid = sum(
        ch.isascii() or "\u3040" <= ch <= "\u30ff" or "\u3400" <= ch <= "\u9fff"
        for ch in compact
    )
    replacement = compact.count("�")
    kana = sum("\u3040" <= ch <= "\u30ff" for ch in compact)
    # Japanese prose with almost no kana is commonly a broken font encoding
    # that happens to map bytes into unrelated CJK code points.
    kana_penalty = 0.35 if len(compact) > 200 and kana / len(compact) < 0.015 else 0.0
    replacement_penalty = min(0.8, replacement / len(compact) * 20)
    return max(0.0, valid / len(compact) - replacement_penalty - kana_penalty)


def _extract_embedded_text(pdf_path: Path) -> tuple[list[dict[str, Any]], float]:
    pages: list[dict[str, Any]] = []
    scores: list[float] = []
    with pdfplumber.open(pdf_path) as pdf:
        for number, page in enumerate(pdf.pages, 1):
            text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
            words = page.extract_words(x_tolerance=2, y_tolerance=3, keep_blank_chars=False)
            groups: list[list[dict[str, Any]]] = []
            for word in sorted(words, key=lambda item: (float(item["top"]), float(item["x0"]))):
                if not groups or abs(float(word["top"]) - float(groups[-1][0]["top"])) > 3:
                    groups.append([word])
                else:
                    groups[-1].append(word)
            lines = []
            for group in groups:
                group.sort(key=lambda item: float(item["x0"]))
                lines.append({
                    "text": " ".join(item["text"] for item in group),
                    "words": [{
                        "text": item["text"], "x": float(item["x0"]), "y": float(item["top"]),
                        "width": float(item["x1"]) - float(item["x0"]),
                        "height": float(item["bottom"]) - float(item["top"]),
                    } for item in group],
                })
            score = _text_quality(text)
            scores.append(score)
            pages.append({"page": number, "text": text, "lines": lines, "text_quality": score})
    return pages, (sum(scores) / len(scores) if scores else 0.0)


def _find_poppler() -> Path:
    configured = os.environ.get("POPPLER_BIN")
    candidates = [
        Path(configured) if configured else None,
        Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin",
    ]
    for candidate in candidates:
        if candidate and (candidate / "pdftoppm.exe").exists():
            return candidate
    executable = shutil.which("pdftoppm") or shutil.which("pdftoppm.exe")
    if executable:
        return Path(executable).parent
    raise FileNotFoundError("pdftoppm was not found. Set POPPLER_BIN or install Poppler.")


def _render_pages(pdf_path: Path, render_dir: Path, dpi: int = 150) -> None:
    render_dir.mkdir(parents=True, exist_ok=True)
    executable = _find_poppler() / ("pdftoppm.exe" if os.name == "nt" else "pdftoppm")
    prefix = render_dir / "page"
    subprocess.run(
        [str(executable), "-r", str(dpi), "-png", str(pdf_path), str(prefix)],
        check=True,
        capture_output=True,
        text=True,
    )


def _windows_ocr(script: Path, render_dir: Path, output_json: Path) -> list[dict[str, Any]]:
    powershell = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    subprocess.run(
        [str(powershell), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
         "-InputDirectory", str(render_dir.resolve()), "-OutputJson", str(output_json.resolve()), "-Language", "ja"],
        check=True,
        capture_output=True,
        text=True,
    )
    records = json.loads(output_json.read_text(encoding="utf-8"))
    if isinstance(records, dict):
        records = [records]
    for index, record in enumerate(records, 1):
        # Poppler names pages as page-01/page-001; filename parsing is authoritative.
        match = re.search(r"(\d+)$", Path(record.get("image", "")).stem)
        record["page"] = int(match.group(1)) if match else index
        record["text_quality"] = _text_quality(record.get("text", ""))
    return records


def load_pdf(pdf_path: Path, work_dir: Path, ocr_script: Path, force_ocr: bool = False) -> LoadedDocument:
    warnings: list[str] = []
    embedded_pages, quality = _extract_embedded_text(pdf_path)
    if quality >= 0.82 and not force_ocr:
        pages = embedded_pages
        parser = "pdfplumber_text"
    else:
        warnings.append(f"Embedded text quality was {quality:.2f}; used rendered-page Japanese OCR.")
        render_dir = work_dir / "rendered_pages"
        ocr_json = work_dir / "ocr_pages.json"
        if ocr_json.exists():
            pages = json.loads(ocr_json.read_text(encoding="utf-8"))
            if isinstance(pages, dict):
                pages = [pages]
            warnings.append("Reused cached page OCR from the source-hash work directory.")
        else:
            _render_pages(pdf_path, render_dir)
            pages = _windows_ocr(ocr_script, render_dir, ocr_json)
        parser = "poppler_windows_ocr_ja"
    expected = set(range(1, len(embedded_pages) + 1))
    found = {int(page["page"]) for page in pages}
    missing = sorted(expected - found)
    if missing:
        warnings.append(f"Missing extracted pages: {missing}")
    return LoadedDocument(
        source_file=pdf_path.resolve(),
        source_sha256=sha256_file(pdf_path),
        pages=sorted(pages, key=lambda item: item["page"]),
        parser=parser,
        warnings=warnings,
        missing_pages=missing,
    )
