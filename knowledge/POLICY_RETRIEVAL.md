# Tokyo policy retrieval

Phase 2 exposes the phase-1 artifacts as a read-only, provenance-first retrieval
surface. It does not create recommendation rules from GIS variables.

## Tools

### `filter_policy_interventions`

Layer B structured filtering supports scenario, category, the Tokyo three-viewpoint
logic, document status, extraction confidence, and exact intervention IDs. The
default result is compact. Set `include_details=true` only when all structured
fields are needed.

### `search_policy_knowledge`

Layer A retrieval uses `retrieval_text`. Japanese is indexed with character
bigrams/trigrams and whole runs; English words and normalized IDs are indexed
as terms. BM25 is built in memory at server startup, so no generated binary
index or new package is required.

Filters are applied before ranking. Results include stable chunk IDs, document
status, PDF and printed pages, section, evidence type, and confidence. Use
`include_text=false` for discovery and fetch selected passages with
`get_policy_evidence`.

### `get_policy_evidence`

Returns one complete semantic chunk, document metadata, linked intervention
records, and a citation object. Use the exact chunk ID returned by search.

## Safe orchestration

```text
GIS / RF / LISA observation (model or derived_analysis evidence)
    -> explicit planning problem/scenario selected by the caller
    -> Layer B filter (policy candidates, not recommendations)
    -> Layer A search (policy passages)
    -> full evidence fetch (Japanese source + citation)
    -> synthesis that labels each evidence role separately
```

Do not infer rules such as `Road_Length high -> street trees required`. The
policy service neither accepts numeric GIS thresholds nor emits causal claims.

The current corpus has 44 chunks, so dependency-free runtime BM25 is sufficient
and inspectable. The manifest reserves an embedding adapter; future embeddings
should add recall, not replace filters, Japanese text, stable IDs, or provenance.

