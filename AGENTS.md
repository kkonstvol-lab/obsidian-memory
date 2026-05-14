# AGENTS.md

Instructions for AI agents maintaining this public skill repository.

---

## Repository Purpose

This repository stores the public standalone `obsidian-memory` skill. Treat it as portable skill source, not as a runtime vault or private workspace.

Primary release target:

- `kkonstvol-lab/obsidian-memory` on `master`.

Secondary sync target after standalone is correct:

- `kkonstvol-lab/agents/agent-skills/obsidian-memory` on `main`.

---

## Public-Only Rule

Do not commit:

- private `12-codex`, `12-claude`, or other runtime memory content;
- `session-drafts`, `hook-runs`, local reports, caches, sqlite files, or logs;
- RAW PDF/DOCX/ZIP files;
- credentials, API keys, tokens, cookies, auth files, or local configs;
- machine-specific absolute paths;
- generated graph/retrieval reports that contain private vault content.

Use generic examples such as `{YOUR_VAULT_PATH}`, `/path/to/vault`, `12-{agent}`, and `~/.agents/skills`.

---

## Maintenance Rules

- Update the standalone repo first.
- Sync the monorepo copy only after standalone docs, scripts, and tests are correct.
- Treat the README as the public showcase surface: major shipped capabilities must appear in the first-level narrative, not only in `references/`.
- Keep brand assets final-only: commit the finished image, not prompts, caches, alternate drafts, or generated intermediate files.
- Keep `SKILL.md` concise; move long guidance to `references/`.
- Keep scripts deterministic and dry-run/advisory by default.
- Any hook, graph, or operator script should have a syntax check, smoke test, or fixture test.
- Do not add DB, vector, MCP, or job-runtime behavior without a separate approved plan.
- ClaudSoul-style content here means practical bridges only, not full ontology/persona architecture.
- GBrain-inspired content here means runtime discipline only, not migration to GBrain.

---

## Required Checks Before Commit

Run the relevant subset:

```bash
git diff --check
node --check assets/codex/hooks/codex-session-start.js
node --check assets/codex/hooks/codex-post-tool-use.js
node --check assets/codex/hooks/precompact-autosave.js
node assets/codex/hooks/tests/test_precompact_autosave.js
python3 -m py_compile assets/operator/*.py
python3 assets/operator/tests/test_bridge_health.py
python3 assets/operator/tests/test_operation_registry.py
python3 assets/operator/tests/test_retrieval_eval.py
python3 assets/operator/tests/test_skill_repo_audit.py
python3 -m py_compile assets/graph/*.py assets/graph/tests/test_graphify_beads.py
python3 assets/graph/tests/test_graphify_beads.py
find . \( -name '.DS_Store' -o -name '__pycache__' -o -name '*.pyc' -o -name '*.sqlite' -o -name '*.log' -o -name '.env' -o -name 'node_modules' -o -name 'graphify-out' -o -name '.git' \) -print
rg -n "(AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]+|sk-[A-Za-z0-9]{20,}|BEGIN (RSA|OPENSSH|EC|PRIVATE) KEY|password\s*=|api[_-]?key\s*=|secret\s*=|token\s*=)" .
```

The artifact scan may show the repository root `.git`; it should not show nested/runtime artifacts inside the skill.
