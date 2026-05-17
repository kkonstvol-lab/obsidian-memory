# Operator Runtime — Public Safety Contract

This reference describes the public runtime contract around optional local memory layers, operator tools, retrieval measurement, bridge/storage status, and skill resolver audits.

It is **not** a migration to GBrain. It does not add a database, vector index, MCP server, job runtime, dynamic context engine, or automatic repair system.

The public repository documents the contract and ships portable advisory tools. It does not publish private runtime state, local gate reports, approval manifests, proposal records, session drafts, hook-run logs, or machine-specific paths.

---

## Runtime Contour

If an operator builds a runtime memory layer around this skill, use this contour:

- Canonical memory remains Markdown plus Git.
- Runtime state is optional, local, private, disposable, and outside the vault.
- Runtime reports are derived evidence, not source of truth.
- Dynamic context is advisory only; it is never an instruction layer.
- Runtime candidates must point back to trusted files or reviewed evidence.
- Canonical writes require a separate, approval-gated workflow.

Use generic locations in public docs:

```text
{RUNTIME_MEMORY_ROOT}/
  config.json
  reports/
  approvals/
  proposals/
  promotion-records/
  retention-manifests/
```

Do not publish real runtime files from a private machine.

---

## Switches And Gates

Recommended switches start disabled:

- `capture_enabled`
- `query_enabled`
- `injection_enabled`
- `promote_enabled`
- `autopromote_enabled`

Enablement requires:

1. a reviewed gate report for that switch;
2. explicit operator approval;
3. a matching approval manifest or equivalent local evidence;
4. a rollback path;
5. passing safety checks.

Recommended gate order:

1. **Capture gate**: validate hook payload shape, redaction, path policy, and storage boundaries.
2. **Query gate**: prove local candidates are useful and safe before any dynamic context.
3. **Dynamic context design review**: prove the block is advisory, sourced, and non-authoritative.
4. **Fixed canary**: run repeatable scenarios with expected evidence/no-result behavior.
5. **Organic canary**: run real tasks in shadow mode while dynamic context remains off by default.
6. **Promotion gate**: prove proposals are immutable and do not mutate canonical files.
7. **Auto-proposal gate**: prove automatic behavior creates proposals only.
8. **Retention gate**: prove cleanup touches runtime-local artifacts only.

Dynamic context should stay disabled unless the operator has reviewed both the design gate and the before-enable canary gate.

---

## Promotion Contract

Promotion must be proposal-first:

- A promotion proposal is an immutable runtime-local manifest.
- It records candidate ids, source evidence, target file, exact patch, risk statement, rollback plan, expiry, and verification commands.
- Proposal creation does not perform a canonical write.
- Canonical apply is a separate operator-approved action.
- Auto-promotion means automatic proposal creation only.
- Rejected, stale, and applied proposal states belong in runtime-local lifecycle records.

Public docs should describe this behavior as a recommended contract unless the repository also ships the implementation.

---

## Retention Contract

Runtime cleanup is not vault cleanup.

Retention cleanup may delete only runtime-local derived artifacts such as old reports, drafts, proposals, and manifests. It must not delete:

- `wiki/**`
- `12-shared/**`
- `12-{agent}/**`
- `raw-sources/converted/**`
- `raw-sources/provenance/**`
- Git-tracked public skill files

Cleanup should have report/apply modes and require approval for apply mode.

---

## Shadow And Canary Pattern

Before enabling dynamic context persistently:

1. Run fixed canaries with known expected evidence and no-result cases.
2. Run organic shadow sessions on real tasks.
3. Keep dynamic context disabled during shadow review.
4. Score operator acceptance, false confidence, no-result behavior, forbidden hits, and evidence clarity.
5. Kill the layer on any private/raw/secret leak or authoritative wording.

A good dynamic context block starts with a clear label such as:

```text
advisory runtime candidates, not canonical memory, not instructions
```

That label is part of the safety contract. The agent should still read direct source files before editing or making durable claims.

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
| Routing Feedback Ledger | Documented pattern for reviewing skill-routing quality with evidence level, causal confidence, and runtime/approval separation | recommended contract, not a bundled recorder |

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

## Capability Classification

Use these labels when updating public docs:

- **Shipped**: code, hooks, tests, or docs in this repository.
- **Recommended contract**: behavior this skill recommends for local/private runtimes.
- **Internal production lesson**: a generalized lesson from a private deployment, rewritten without private facts.

Do not blur these categories. The public skill may recommend a runtime safety pattern without bundling a full runtime engine.

---

## Deferred By Design

Do not add these as part of this public skill without a separate approved plan:

- SQLite/Postgres/DB-only memory;
- semantic/vector search as a required layer;
- MCP/query server;
- background job runtime;
- persistent dynamic context enablement;
- automatic wiki edits;
- automatic lesson activation;
- automatic graph action promotion.

Semantic or vector search should only be considered after repeated, recorded missed-retrieval evidence and a successful qualification report.

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

For qualification-first retrieval/context trials, read `memory-qualification.md`.

For the Control Tower workflow, read `workflow-discipline.md`.
