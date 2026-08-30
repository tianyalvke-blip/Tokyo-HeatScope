from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


TYPE_MAP = {
    "object": dict, "array": list, "string": str, "integer": int,
    "number": (int, float), "boolean": bool, "null": type(None),
}


def _validate_node(value: Any, schema: dict[str, Any], path: str, errors: list[str]) -> None:
    allowed_types = schema.get("type")
    if allowed_types:
        names = [allowed_types] if isinstance(allowed_types, str) else allowed_types
        if not any(isinstance(value, TYPE_MAP[name]) and not (name == "integer" and isinstance(value, bool)) for name in names):
            errors.append(f"{path}: expected type {names}, got {type(value).__name__}")
            return
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} is not in enum {schema['enum']}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: string is shorter than minLength")
        if schema.get("pattern") and not re.search(schema["pattern"], value):
            errors.append(f"{path}: string does not match {schema['pattern']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: array is shorter than minItems")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                _validate_node(item, item_schema, f"{path}[{index}]", errors)
    if isinstance(value, dict):
        for required in schema.get("required", []):
            if required not in value:
                errors.append(f"{path}: missing required field {required}")
        for key, child_schema in schema.get("properties", {}).items():
            if key in value:
                _validate_node(value[key], child_schema, f"{path}.{key}", errors)


def validate_records(records: list[dict[str, Any]], schema_path: Path, label: str) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    for index, record in enumerate(records):
        _validate_node(record, schema, f"{label}[{index}]", errors)
    return errors


def validate_cross_references(
    documents: list[dict[str, Any]], chunks: list[dict[str, Any]],
    interventions: list[dict[str, Any]], scenarios: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    document_ids = {item["document_id"] for item in documents}
    chunk_ids = {item["chunk_id"] for item in chunks}
    intervention_ids = {item["intervention_id"] for item in interventions}
    for chunk in chunks:
        if chunk["document_id"] not in document_ids:
            errors.append(f"Chunk {chunk['chunk_id']} references unknown document.")
        if chunk["page_start"] > chunk["page_end"]:
            errors.append(f"Chunk {chunk['chunk_id']} has inverted page range.")
        for item in chunk["interventions"]:
            if item not in intervention_ids:
                errors.append(f"Chunk {chunk['chunk_id']} references unknown intervention {item}.")
    for collection_name, records in [("intervention", interventions), ("scenario", scenarios)]:
        for record in records:
            for evidence in record["source_evidence"]:
                if evidence["document_id"] not in document_ids:
                    errors.append(f"{collection_name} {record.get(collection_name + '_id')} has unknown document evidence.")
                if evidence["chunk_id"] not in chunk_ids:
                    errors.append(f"{collection_name} {record.get(collection_name + '_id')} has unknown chunk evidence.")
    for scenario in scenarios:
        for item in scenario["recommended_interventions"]:
            if item not in intervention_ids:
                errors.append(f"Scenario {scenario['scenario_id']} references unknown intervention {item}.")
    return errors

