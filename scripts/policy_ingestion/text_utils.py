from __future__ import annotations

import re

JP = r"\u3040-\u30ff\u3400-\u9fff"


def normalize_ocr_text(text: str) -> str:
    """Normalize OCR spacing without translating or rewriting source terms."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(fr"(?<=[{JP}])\s+(?=[{JP}])", "", text)
    text = re.sub(fr"(?<=[{JP}])\s+(?=[ー・「」（）])", "", text)
    text = re.sub(fr"(?<=[ー・「」（）])\s+(?=[{JP}])", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def clean_lines(text: str) -> list[str]:
    return [line.strip() for line in normalize_ocr_text(text).splitlines() if line.strip()]


def slugify_ascii(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return value or "record"

