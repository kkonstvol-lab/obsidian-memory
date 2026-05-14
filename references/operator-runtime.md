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
```

Write modes, where present, must remain explicit and approval-gated.
