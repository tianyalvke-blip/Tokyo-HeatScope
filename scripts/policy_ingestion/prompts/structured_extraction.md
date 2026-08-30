# Structured policy extraction prompt (optional LLM adapter)

This prompt is intentionally centralized. The default pipeline is deterministic
and does not require an LLM. Any future adapter must return JSON conforming to
the repository schemas.

Rules:

1. Extract only statements supported by the supplied Japanese source passage.
2. Preserve Japanese policy terms verbatim in all `*_ja` and `text_ja` fields.
3. Use empty arrays or null when the passage does not state a fact.
4. Never infer legal status, current validity, cost, maintenance, constraints,
   effects, or causal relationships from general knowledge.
5. Every record must cite document_id, source_file, page, structural heading,
   and chunk_id where applicable.
6. Set evidence_type to `policy`; do not call guidance scientific evidence.
7. Mark extraction_confidence low when a table, diagram, or spatial alignment
   makes relationships ambiguous.
8. Output JSON only. On validation failure, retry with the validation errors and
   the same source passage; do not add unsupported information.

