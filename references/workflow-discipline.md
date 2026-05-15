# Workflow Discipline And Operator Control Tower

This layer makes release, branch-close, decision-capture, and lesson-review work visible without turning the skill into a private vault clone.

It is portable and advisory. Markdown/Git remain the source of truth; private runtime state stays private.

---

## What This Adds

The Control Tower layer contains five read-only boards plus one approval-gated lifecycle write:

| Tool | Purpose | Writes by default |
|---|---|---|
| `release_status.py` | Release/push preflight: repo identity, branch, upstream, push boundary, staged files, RAW binary risk, recommended checks | no |
| `branch_close_pack.py` | Branch closeout handoff: working tree, recent commits, done/remaining candidates, backlog, risks, verification | no |
| `release_surface_check.py` | Public surface guard: README narrative, hooks, graph/bridge, Control Tower visibility, license, attribution | no |
| `decision_review_board.py` | Durable-memory candidate board: shared decisions, wiki synthesis, runbooks, private lessons, public surface notes | no |
| `lesson_lint.py` / `lesson_review_board.py` | Private lesson schema and promotion review | no |
| `decision_review_board.py --mark` | Append a reviewed candidate lifecycle record | yes, only with approval |

The intent is simple: make the next responsible action obvious before an agent says "done", pushes, closes a branch, or forgets a process correction.

---

## Release Status

Use `release-status` before commit, push, or final release claims.

```bash
python3 assets/operator/release_status.py --repo . --intent public-obsidian-memory
python3 assets/operator/release_status.py --repo . --intent vault-memory --expected-branch main --strict
```

It checks:

- repo root, branch, upstream, ahead/behind;
- expected branch/remote when provided;
- staged, unstaged, and untracked files;
- staged RAW binary risk under `raw-sources/`;
- detected release surface;
- recommended verification commands;
- post-push obligations.

It does not stage, commit, push, or write memory.

---

## Branch Close Pack

Use `branch-close` before closing long branches, after large memory work, or before a handoff.

```bash
python3 assets/operator/branch_close_pack.py --root /path/to/vault --agent codex --md
python3 assets/operator/branch_close_pack.py --root /path/to/vault --agent codex --json
```

The report gathers:

- repo state and working tree cleanliness;
- recent commits;
- compact done/remaining candidates from `12-{agent}/memory_*`;
- lesson, graph, and bridge backlog summaries;
- blocker/warn findings;
- a handoff skeleton and verification list.

Branch archives should be executive artifacts, not compressed chat logs. A good archive captures status, decisions, backlog, next steps, verification, and evidence references. If it grows beyond roughly 150-220 lines, split evidence into linked sources rather than expanding the archive.

---

## Release Surface Check

Use `release-surface-check` before public skill releases.

```bash
python3 assets/operator/release_surface_check.py --profile public-skill --standalone /path/to/obsidian-memory
python3 assets/operator/release_surface_check.py --profile vault --root /path/to/vault
```

For public skill repos, the check expects visible public value:

- README first screen explains Obsidian Memory;
- hooks are visible;
- graph/bridge are visible;
- Control Tower / workflow discipline is visible;
- quick start exists;
- `LICENSE` exists;
- `AGENTS.md` exists;
- recent commits include Codex co-author attribution when Codex did public release work.

This is a local guardrail. It does not call GitHub.

---

## Decision Review

Use `decision-review` after long branches, public releases, or large operator changes.

```bash
python3 assets/operator/decision_review_board.py --root /path/to/vault --agent codex --md
python3 assets/operator/decision_review_board.py --root /path/to/vault --agent codex --json
```

The board scans:

- `12-{agent}/memory_in_progress.md`;
- `12-{agent}/memory_corrections.md`;
- `wiki/log.md`;
- recent Git commits;
- recent `12-{agent}/session-drafts/`.

It routes candidates to one of:

- `memory_decision`;
- `agent_lesson`;
- `wiki_synthesis`;
- `runbook_update`;
- `public_surface_note`;
- `no_durable_write`.

Candidates are not automatic writes. The board only says what may deserve durable capture.

To mark a reviewed candidate:

```bash
MEMORY_OPERATOR_APPROVED=1 python3 assets/operator/decision_review_board.py \
  --root /path/to/vault \
  --agent codex \
  --mark <candidate-id> \
  --status skipped \
  --note "covered by existing decision"
```

The mark command appends a JSONL lifecycle record under `12-{agent}/decision-review/review-state.jsonl`. Do not publish real review-state from a private vault.

---

## Lesson Review

Operational lessons are private process memory. They are not wiki knowledge and not public release content.

```bash
python3 assets/operator/lesson_lint.py --vault /path/to/vault --agent codex --json
python3 assets/operator/lesson_review_board.py --root /path/to/vault --agent codex --md
```

The lesson schema supports three levels:

- `case` — one concrete incident;
- `pattern` — two or more reviewed cases with shared anchors;
- `principle` — broader rule backed by patterns or multiple domains.

Rules:

- draft cases can stay draft forever;
- active patterns/principles require explicit human review;
- promotion is never automatic;
- contradictions must be recorded, not hidden;
- private lesson files are not public examples unless rewritten as synthetic fixtures.

---

## Public-Skill Boundary

For this repository, publish:

- generic scripts;
- synthetic tests;
- docs explaining the workflow;
- generic `12-{agent}` examples.

Do not publish:

- real `12-codex/lessons/*.md`;
- real `12-codex/decision-review/review-state.jsonl`;
- `session-drafts`;
- `hook-runs`;
- local reports;
- private corrections;
- local absolute paths.

This keeps the public skill useful without leaking the operator's private working memory.
