# Graphify-Inspired Knowledge Graph

This skill ships a local, dependency-light graph layer inspired by Graphify and paired with a Beads-inspired review queue. It does not require the external `graphify` package, does not install Beads, and does not run an MCP server.

Obsidian Markdown remains the source of truth. Generated graph outputs are derived reports that can be deleted and rebuilt.

## What This Skill Ships

Copy `assets/graph/` into the graph folder in your vault:

- Single-agent vault: `memory/graph/`
- Multi-agent vault: `12-shared/graph/`

Bundled files:

- `_graph_utils.py` - small dependency-free graph helper used by the scripts.
- `extract_vault.py` - builds `graphify-out/graph.json`, `GRAPH_REPORT.md`, and missing target suggestions.
- `suggest_wikilinks.py` - builds `graphify-out/missing-links.md` and `GRAPH_READY.md`.
- `hybrid_retrieval.py` - builds `graphify-out/retrieval_candidates.jsonl` for a query.
- `review-state.jsonl` - append-only review state.
- `requirements.txt` - optional packages for external graph inspection; not required for the bundled fixture test.
- `tests/test_graphify_beads.py` - fixture test for stable IDs, review-state behavior, and raw-source safety.

## Review Queue

The graph layer borrows operational patterns from Beads without adding a `.beads/` runtime.

Generated actions use stable IDs like `gq-a1b2c3d4e5` and can include:

- `create_missing_page`
- `add_wikilink`
- `review_inferred_edge`
- `attach_orphan`
- `create_moc_candidate`
- `add_source_evidence`
- `review_temporal_conflict`

Graph suggestions are review candidates. They do not become canonical wiki edits until a human/operator accepts them and edits the wiki intentionally.

## Review State

`review-state.jsonl` is append-only. One JSON object per line. The newest record for an ID wins.

```json
{"id":"gq-a1b2c3d4e5","status":"skipped","reason":"not a useful link","source":"manual","date":"YYYY-MM-DD"}
```

Allowed statuses:

- `open`
- `accepted`
- `skipped`
- `obsolete`

## Regenerate

```bash
cd {VAULT}/memory/graph
python3 extract_vault.py
python3 suggest_wikilinks.py
python3 hybrid_retrieval.py "current project priorities"
```

For multi-agent vaults:

```bash
cd {VAULT}/12-shared/graph
python3 extract_vault.py
python3 suggest_wikilinks.py
```

Generated outputs:

- `graphify-out/graph.json`
- `graphify-out/GRAPH_REPORT.md`
- `graphify-out/GRAPH_READY.md`
- `graphify-out/missing-links.md`
- `graphify-out/wikilink-suggestions.md`
- `graphify-out/retrieval_candidates.jsonl`

## Human Review Rules

- Scripts never edit `wiki/` or `raw-sources/`.
- Treat `GRAPH_READY.md` as a review queue, not as source of truth.
- Add wikilinks only after human review.
- Mark rejected suggestions in `review-state.jsonl`; do not delete them from generated reports by hand.
- Cycles in a knowledge graph are not automatically errors.
- RAW cache files should be routed through converted markdown, summaries, or provenance before becoming wiki links.

## Validate

```bash
cd {VAULT}/memory/graph
python3 -m py_compile *.py tests/test_graphify_beads.py
python3 tests/test_graphify_beads.py
```

The fixture test checks:

- stable node, edge, and action IDs between runs;
- `GRAPH_READY.md` sections;
- `review-state.jsonl` filtering;
- provenance and temporal review actions;
- hybrid retrieval candidate ranking;
- no writes to `raw-sources/`.

## Optional External Consumers

The public skill does not ship an MCP runtime. If another local tool wants to consume the derived graph, point that tool at the generated JSON:

```text
{VAULT}/memory/graph/graphify-out/graph.json
```

For multi-agent vaults, use:

```text
{VAULT}/12-shared/graph/graphify-out/graph.json
```
