# Operator Runtime — Advisory Tools

This reference describes the GBrain-inspired part that is intentionally adopted in this skill: runtime discipline around operations, retrieval measurement, bridge/storage status, and skill resolver audits.

It is **not** a migration to GBrain. It does not add a database, vector index, MCP server, job runtime, or automatic repair system.

---

## Adopted Ideas

| Tool | Purpose | Default posture |
|---|---|---|
| `operation_registry.py` | Describe operator commands, touched areas, approval needs, and verification | descriptive, not source of truth |
| `retrieval_eval.py` | Measure keyword retrieval, missed retrievals, skipped candidates, and baseline replay | read-only/dry-run unless explicitly approved |
| `bridge_health.py` | Show practical bridge and storage status | advisory report |
| `skill_repo_audit.py` | Compare public skill repos and installed skill folders; audit routing/trigger noise | advisory, no auto-fix |
| `release_status.py` | Build a release/push preflight packet: repo, branch, upstream, push boundary, staged files, RAW risk, and obligations | read-only preflight |
| `branch_close_pack.py` | Gather compact branch closeout context: commits, working tree, memory context, backlog, risks, and verification | read-only handoff |
| `release_surface_check.py` | Check public-facing repo markers: README core narrative, hooks, graph/bridge, Control Tower visibility, license, attribution | read-only surface guard |
| `decision_review_board.py` | Surface candidates for durable routing into decisions, wiki synthesis, runbooks, lessons, or public surface notes | read-only by default; mark is approval-gated |
| `lesson_lint.py` / `lesson_review_board.py` | Validate and review private operational lessons before promotion | read-only; no activation |

---

## Source Of Truth

The source of truth remains:

- `wiki/`
- `12-shared/`
- `12-{agent}/`
- `raw-sources/converted/`
- `raw-sources/provenance/`
- Git history and explicit release checks

Derived outputs may be deleted and rebuilt.

---

## Deferred By Design

Do not add these as part of this public skill without a separate approved plan:

- SQLite/Postgres/DB-only memory;
- semantic/vector search as a required layer;
- MCP/query server;
- background job runtime;
- automatic wiki edits;
- automatic lesson activation;
- automatic graph action promotion.

Semantic or vector search should only be considered after repeated, recorded missed-retrieval evidence.

---

## Example Commands

```bash
python3 assets/operator/operation_registry.py
python3 assets/operator/retrieval_eval.py query --query "raw provenance summary bridge"
python3 assets/operator/retrieval_eval.py report
python3 assets/operator/bridge_health.py --vault /path/to/vault --status
python3 assets/operator/skill_repo_audit.py --repo-path /path/to/agents --skills-dir agent-skills --installed ~/.agents/skills
python3 assets/operator/release_status.py --repo . --intent public-obsidian-memory
python3 assets/operator/branch_close_pack.py --root /path/to/vault --agent codex --md
python3 assets/operator/release_surface_check.py --profile public-skill --standalone /path/to/obsidian-memory
python3 assets/operator/decision_review_board.py --root /path/to/vault --agent codex --md
python3 assets/operator/lesson_review_board.py --root /path/to/vault --agent codex --json
```

Write modes, where present, must remain explicit and approval-gated.

For the Control Tower workflow, read `workflow-discipline.md`.
