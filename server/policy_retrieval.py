"""Read-only retrieval over the phase-1 Tokyo policy knowledge base.

Layer B filters structured interventions. Layer A ranks semantic chunks. The
two layers join only through stable intervention/chunk/document identifiers;
model evidence is deliberately out of scope here.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}


def _tokens(value: str) -> list[str]:
    text = unicodedata.normalize("NFKC", value or "").lower()
    words = re.findall(r"[a-z0-9_]+", text)
    japanese_runs = re.findall(r"[\u3040-\u30ff\u3400-\u9fffー]+", text)
    result = list(words)
    for run in japanese_runs:
        result.append(run)
        for size in (2, 3):
            result.extend(run[i:i + size] for i in range(max(0, len(run) - size + 1)))
    return result


def _as_set(value: str | Iterable[str] | None) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {value}
    return {str(item) for item in value}


@dataclass
class _BM25Document:
    chunk: dict[str, Any]
    counts: Counter[str]
    length: int


class PolicyKnowledgeStore:
    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = (repo_root or Path(__file__).resolve().parent.parent).resolve()
        knowledge = self.repo_root / "knowledge"
        self.documents = self._load_envelope(knowledge / "documents/policy_documents.json", "documents")
        self.interventions = self._load_all_envelopes(knowledge / "interventions", "interventions")
        self.scenarios = self._load_all_envelopes(knowledge / "interventions", "scenarios")
        self.chunks = self._load_all_jsonl(knowledge / "chunks")
        self.document_by_id = {item["document_id"]: item for item in self.documents}
        self.intervention_by_id = {item["intervention_id"]: item for item in self.interventions}
        self.interventions_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in self.interventions:
            self.interventions_by_id[item["intervention_id"]].append(item)
        self.scenario_by_id = {item["scenario_id"]: item for item in self.scenarios}
        self.chunk_by_id = {item["chunk_id"]: item for item in self.chunks}
        self._build_index()

    @staticmethod
    def _load_envelope(path: Path, key: str) -> list[dict[str, Any]]:
        if not path.exists():
            raise FileNotFoundError(f"Policy knowledge artifact not found: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = payload.get(key)
        if not isinstance(records, list):
            raise ValueError(f"Expected list '{key}' in {path}")
        return records

    @staticmethod
    def _load_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            raise FileNotFoundError(f"Policy chunk artifact not found: {path}")
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    @classmethod
    def _load_all_envelopes(cls, directory: Path, key: str) -> list[dict[str, Any]]:
        files = sorted(directory.glob("*.json"))
        records: list[dict[str, Any]] = []
        for path in files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if key in payload:
                if not isinstance(payload[key], list):
                    raise ValueError(f"Expected list '{key}' in {path}")
                records.extend(payload[key])
        if not records:
            raise FileNotFoundError(f"No policy {key} envelopes found under {directory}")
        return records

    @classmethod
    def _load_all_jsonl(cls, directory: Path) -> list[dict[str, Any]]:
        files = sorted(directory.glob("*.jsonl"))
        if not files:
            raise FileNotFoundError(f"No policy chunk JSONL files found under {directory}")
        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        for path in files:
            for record in cls._load_jsonl(path):
                chunk_id = record["chunk_id"]
                if chunk_id in seen:
                    raise ValueError(f"Duplicate chunk_id {chunk_id} found while loading {path}")
                seen.add(chunk_id)
                records.append(record)
        return records

    def _build_index(self) -> None:
        self._index: list[_BM25Document] = []
        document_frequency: Counter[str] = Counter()
        for chunk in self.chunks:
            terms = _tokens(chunk.get("retrieval_text", ""))
            counts = Counter(terms)
            self._index.append(_BM25Document(chunk, counts, len(terms)))
            document_frequency.update(counts.keys())
        self._avg_length = sum(item.length for item in self._index) / max(1, len(self._index))
        count = max(1, len(self._index))
        self._idf = {
            term: math.log(1.0 + (count - freq + 0.5) / (freq + 0.5))
            for term, freq in document_frequency.items()
        }

    def metadata(self) -> dict[str, Any]:
        return {
            "success": True,
            "evidence_type": "policy",
            "documents": len(self.documents),
            "chunks": len(self.chunks),
            "interventions": len(self.interventions),
            "scenarios": len(self.scenarios),
            "retrieval": "runtime_bm25_japanese_character_ngram_and_word",
            "embedding_status": "not_built",
        }

    def filter_interventions(
        self,
        scenario: str | None = None,
        categories: str | Iterable[str] | None = None,
        policy_logic: str | Iterable[str] | None = None,
        document_status: str | Iterable[str] | None = None,
        min_confidence: str = "low",
        intervention_ids: Iterable[str] | None = None,
        limit: int = 50,
        include_details: bool = False,
    ) -> dict[str, Any]:
        if min_confidence not in CONFIDENCE_RANK:
            raise ValueError("min_confidence must be high, medium, or low")
        category_set = _as_set(categories)
        logic_set = _as_set(policy_logic)
        status_set = _as_set(document_status)
        id_set = _as_set(intervention_ids)
        if scenario and scenario not in self.scenario_by_id:
            raise ValueError(f"unknown scenario: {scenario}")
        known_logic = {"dasanai", "tamenai", "morawanai"}
        if logic_set - known_logic:
            raise ValueError(f"unknown policy_logic: {sorted(logic_set - known_logic)}")
        rows = []
        for item in self.interventions:
            if id_set and item["intervention_id"] not in id_set:
                continue
            if scenario and scenario not in item.get("applicable_scenarios", []):
                continue
            if category_set and item.get("category") not in category_set:
                continue
            if logic_set and not all(item.get("policy_logic", {}).get(key) for key in logic_set):
                continue
            if CONFIDENCE_RANK[item.get("extraction_confidence", "low")] < CONFIDENCE_RANK[min_confidence]:
                continue
            evidence = item.get("source_evidence", [])
            statuses = {
                self.document_by_id.get(source.get("document_id"), {}).get("status", "unknown")
                for source in evidence
            }
            if status_set and not statuses.intersection(status_set):
                continue
            rows.append(item)
        rows.sort(key=lambda item: (-CONFIDENCE_RANK[item["extraction_confidence"]], item["intervention_id"]))
        selected = rows[:max(1, min(int(limit), 100))]
        if not include_details:
            selected = [{
                key: item[key] for key in [
                    "intervention_id", "name_ja", "name_en", "category", "target",
                    "applicable_scenarios", "policy_logic", "mechanisms",
                    "evidence_type", "extraction_confidence", "source_evidence",
                ]
            } for item in selected]
        return {
            "success": True,
            "evidence_type": "policy",
            "filters": {
                "scenario": scenario, "categories": sorted(category_set),
                "policy_logic": sorted(logic_set), "document_status": sorted(status_set),
                "min_confidence": min_confidence,
            },
            "match_count": len(rows),
            "returned_count": len(selected),
            "include_details": include_details,
            "interventions": selected,
            "note": "Policy guidance only; this result does not establish model or scientific causality.",
        }

    def _eligible_chunks(
        self,
        scenario: str | None,
        intervention_ids: set[str],
        knowledge_types: set[str],
        document_status: set[str],
        min_confidence: str,
    ) -> list[_BM25Document]:
        eligible = []
        for indexed in self._index:
            chunk = indexed.chunk
            if scenario and scenario not in chunk.get("scenario", []):
                continue
            if intervention_ids and not intervention_ids.intersection(chunk.get("interventions", [])):
                continue
            if knowledge_types and chunk.get("knowledge_type") not in knowledge_types:
                continue
            if CONFIDENCE_RANK[chunk.get("extraction_confidence", "low")] < CONFIDENCE_RANK[min_confidence]:
                continue
            document = self.document_by_id.get(chunk["document_id"], {})
            if document_status and document.get("status", "unknown") not in document_status:
                continue
            eligible.append(indexed)
        return eligible

    def search(
        self,
        query: str,
        scenario: str | None = None,
        intervention_ids: Iterable[str] | None = None,
        knowledge_types: Iterable[str] | None = None,
        document_status: str | Iterable[str] | None = None,
        min_confidence: str = "low",
        top_k: int = 5,
        include_text: bool = True,
    ) -> dict[str, Any]:
        query_terms = _tokens(query)
        if not query_terms:
            raise ValueError("query must contain searchable Japanese or English text")
        if min_confidence not in CONFIDENCE_RANK:
            raise ValueError("min_confidence must be high, medium, or low")
        intervention_set = _as_set(intervention_ids)
        unknown = intervention_set - self.intervention_by_id.keys()
        if unknown:
            raise ValueError(f"unknown intervention_ids: {sorted(unknown)}")
        if scenario and scenario not in self.scenario_by_id:
            raise ValueError(f"unknown scenario: {scenario}")
        eligible = self._eligible_chunks(
            scenario, intervention_set, _as_set(knowledge_types),
            _as_set(document_status), min_confidence,
        )
        query_counts = Counter(query_terms)
        k1, b = 1.5, 0.75
        scored = []
        for indexed in eligible:
            score = 0.0
            for term, query_weight in query_counts.items():
                frequency = indexed.counts.get(term, 0)
                if not frequency:
                    continue
                norm = k1 * (1.0 - b + b * indexed.length / max(1.0, self._avg_length))
                score += query_weight * self._idf.get(term, 0.0) * frequency * (k1 + 1.0) / (frequency + norm)
            if score > 0:
                scored.append((score, indexed.chunk))
        scored.sort(key=lambda pair: (-pair[0], pair[1]["chunk_id"]))
        results = []
        for score, chunk in scored[:max(1, min(int(top_k), 20))]:
            document = self.document_by_id[chunk["document_id"]]
            result = {
                "score": round(score, 6),
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk["document_id"],
                "document_title_ja": document["title_ja"],
                "authority": document["authority"],
                "document_status": document["status"],
                "chapter": chunk["chapter"], "section": chunk["section"],
                "subsection": chunk["subsection"], "knowledge_type": chunk["knowledge_type"],
                "scenario": chunk["scenario"], "interventions": chunk["interventions"],
                "policy_logic": chunk["policy_logic"],
                "page_start": chunk["page_start"], "page_end": chunk["page_end"],
                "printed_page_start": chunk.get("printed_page_start"),
                "printed_page_end": chunk.get("printed_page_end"),
                "source_file": chunk["source_file"],
                "evidence_type": "policy",
                "extraction_confidence": chunk["extraction_confidence"],
                "text_en_summary": chunk["text_en_summary"],
            }
            if include_text:
                result["text_ja"] = chunk["text_ja"]
            results.append(result)
        return {
            "success": True, "query": query, "evidence_type": "policy",
            "retrieval_method": "bm25_japanese_character_ngram_and_word",
            "candidate_count": len(eligible), "result_count": len(results),
            "results": results,
            "note": "Retrieval ranking finds policy passages; it does not prove causal effectiveness.",
        }

    def get_evidence(self, chunk_id: str) -> dict[str, Any]:
        chunk = self.chunk_by_id.get(chunk_id)
        if not chunk:
            raise ValueError(f"unknown chunk_id: {chunk_id}")
        document = self.document_by_id[chunk["document_id"]]
        linked = []
        for intervention_id in chunk.get("interventions", []):
            candidates = self.interventions_by_id.get(intervention_id, [])
            exact = [item for item in candidates if any(
                evidence.get("chunk_id") == chunk_id for evidence in item.get("source_evidence", [])
            )]
            linked.extend(exact or candidates[:1])
        return {
            "success": True, "evidence_type": "policy",
            "document": document, "chunk": chunk,
            "linked_interventions": linked,
            "citation": {
                "authority": document["authority"], "title_ja": document["title_ja"],
                "chapter": chunk["chapter"], "section": chunk["section"],
                "pdf_pages": [chunk["page_start"], chunk["page_end"]],
                "printed_pages": [chunk.get("printed_page_start"), chunk.get("printed_page_end")],
                "source_file": chunk["source_file"], "chunk_id": chunk["chunk_id"],
            },
        }
