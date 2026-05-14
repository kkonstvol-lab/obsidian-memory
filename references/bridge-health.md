# Bridge Health — Practical Memory Bridges

This reference describes the ClaudSoul-style part that is intentionally adopted in this skill: practical bridges between memory layers.

It does **not** adopt full ontology, persona architecture, autonomous promotion, or automatic canonical writes.

---

## Goal

Bridge health answers one operational question:

> Which memory artifacts should connect to each other, and what is the next script-checkable step when the connection is missing?

The bridge report is advisory by default. It may produce `blocker`, `warn`, `known_backlog`, or `info` findings, but it must not edit `wiki/`, `raw-sources/`, graph state, lessons, or memory files automatically.

---

## Practical Bridges

Recommended bridge set:

| Bridge | Meaning | Typical next step |
|---|---|---|
| `raw -> converted` | RAW source should have converted markdown or be intentionally parked | convert, replace bad source, or leave as backlog |
| `converted -> summary` | converted source should have a wiki summary or explicit parking decision | create/link summary or mark intentionally parked |
| `summary -> domain` | summary should be visible from index or a domain MOC | link from relevant domain or index |
| `wiki -> graph` | derived graph reports should reflect current wiki state | regenerate graph reports |
| `graph action -> review-state` | graph suggestions require explicit accept/skip/obsolete/defer state | review action batch before editing wiki |
| `correction -> lesson` | repeated/high-impact corrections may become draft lessons | create reviewed draft lesson candidates |
| `lesson -> gate` | lesson schema/lint should be visible in release gates | wire lint/checks into local release process |
| `session draft -> memory_active` | non-canonical session drafts may contain closeout facts | review manually; copy only durable facts |

---

## Finding Buckets

- `blocker`: release or trust issue that should stop publication.
- `warn`: real issue requiring attention, but not always a release blocker.
- `known_backlog`: visible backlog that is intentionally not blocking.
- `info`: useful signal or deferred housekeeping.

Known backlog is useful because it prevents debt from being hidden while avoiding noisy release failures.

---

## Portable Script

Run the public bridge report against a vault:

```bash
python3 assets/operator/bridge_health.py --vault /path/to/obsidian-vault
python3 assets/operator/bridge_health.py --vault /path/to/obsidian-vault --status
python3 assets/operator/bridge_health.py --vault /path/to/obsidian-vault --status --json
```

Agent-private paths default to `12-codex/`. Override them when needed:

```bash
OBSIDIAN_AGENT_ID=claude python3 assets/operator/bridge_health.py --vault /path/to/vault
OBSIDIAN_PRIVATE_ROOT=12-my-agent python3 assets/operator/bridge_health.py --vault /path/to/vault
```

---

## Safety Rules

- Do not auto-edit wiki pages from bridge findings.
- Do not auto-promote graph actions into wikilinks.
- Do not auto-activate lessons from corrections.
- Do not copy session drafts into canonical memory without review.
- Treat graph/retrieval reports as derived and rebuildable.
- Keep Markdown/Git/Obsidian as source of truth.
