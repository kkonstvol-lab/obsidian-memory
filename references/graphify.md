# Graphify Knowledge Graph

Graphify is an optional derived layer over `wiki/` and `raw-sources/`. Obsidian remains the canonical source of truth; generated graph files can be deleted and rebuilt.

## What This Skill Ships

Copy `assets/graph/` into the graph folder in your vault:

- Single-agent vault: `memory/graph/`
- Multi-agent vault: `12-shared/graph/`

The bundled graph layer includes:

- `extract_vault.py` — builds `graphify-out/graph.json`, `GRAPH_REPORT.md`, and missing target suggestions.
- `suggest_wikilinks.py` — builds `graphify-out/missing-links.md` and `GRAPH_READY.md`.
- `review-state.jsonl` — append-only human review state.
- `tests/test_graphify_beads.py` — fixture test for stable IDs, review-state behavior, and raw-source safety.

## Beads-Style Review Queue

The graph layer borrows operational patterns from Beads without installing Beads, Dolt, or `.beads/`.

Nodes include typed metadata:

- `node_type`: `wiki`, `raw_source`, `missing`, `domain`, `summary`, `entity`, `concept`, or `document`
- `source_path`
- `stable_id`

Edges include typed metadata:

- `edge_id`
- `relation`
- `confidence`
- `source_file`
- `review_status`

Generated actions use stable IDs like `gq-a1b2c3d4e5`.

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
python extract_vault.py
python suggest_wikilinks.py
```

For multi-agent vaults:

```bash
cd {VAULT}/12-shared/graph
python extract_vault.py
python suggest_wikilinks.py
```

Generated outputs:

- `graphify-out/graph.json`
- `graphify-out/GRAPH_REPORT.md`
- `graphify-out/GRAPH_READY.md`
- `graphify-out/missing-links.md`
- `graphify-out/wikilink-suggestions.md`

## Human Review Rules

- Scripts never edit `wiki/` or `raw-sources/`.
- Treat `GRAPH_READY.md` as a review queue, not as source of truth.
- Add wikilinks only after human review.
- Mark rejected suggestions in `review-state.jsonl`; do not delete them from generated reports by hand.
- Cycles in a knowledge graph are not automatically errors.

## Validate

```bash
cd {VAULT}/memory/graph
python -m py_compile extract_vault.py suggest_wikilinks.py tests/test_graphify_beads.py
python tests/test_graphify_beads.py
```

The fixture test checks:

- stable node, edge, and action IDs between runs
- `GRAPH_READY.md` sections
- `review-state.jsonl` filtering
- no writes to `raw-sources/`

## MCP

If using graphify MCP, point it to the generated `graph.json`:

```json
{
  "mcpServers": {
    "graphify": {
      "command": "python",
      "args": ["-m", "graphify.serve", "memory/graph/graphify-out/graph.json"],
      "type": "stdio"
    }
  }
}
```

For multi-agent vaults, use `12-shared/graph/graphify-out/graph.json`.
