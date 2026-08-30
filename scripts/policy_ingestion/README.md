# Tokyo policy ingestion

This isolated phase-1 pipeline builds two linked knowledge layers:

- Layer A: provenance-rich semantic chunks in JSONL and a page-marked Japanese
  Markdown transcription.
- Layer B: versioned document, scenario, and intervention records for precise
  filtering before retrieval.

Run from the repository root:

```powershell
C:\Users\lyuke\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe `
  -m scripts.policy_ingestion.ingest `
  --input "path\to\policy.pdf" `
  --metadata "path\to\policy.metadata.json"
```

If `--input` is omitted, the benchmark is discovered or expected at
`data/policy_sources/tokyo_summer_heat_guideline.pdf`. Future documents should
receive their own sidecar; absent status is always exported as `unknown`.

The loader checks the embedded text layer. Low-quality Japanese text falls back
to Poppler page rendering plus Windows Japanese OCR. The original PDF is never
modified. OCR coordinates are used for labeled technical-table rows, and
ambiguous relationships generate warnings/low confidence instead of guesses.

No embeddings are built in phase 1. `knowledge/indexes/policy_manifest.json`
is the stable handoff point for a later retrieval adapter.

Run content-level benchmark assertions after ingestion:

```powershell
C:\Users\lyuke\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe `
  -m scripts.policy_ingestion.qa
```
