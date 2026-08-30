# Policy source inputs

Place source PDFs here without modifying them. The default benchmark path is:

`data/policy_sources/tokyo_summer_heat_guideline.pdf`

The ingestion CLI also accepts `--input` and can discover a uniquely matching
PDF elsewhere in the repository. Per-document facts that cannot be safely
inferred from a PDF belong in a sibling `*.metadata.json` sidecar.

