# Obsidian Memory - LLM Wiki + Agent Memory for Obsidian

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Turn an Obsidian vault into a Markdown/Git-based memory system for AI agents: a source-backed LLM wiki, operational agent memory, lifecycle hooks, graph review tools, runtime safety contracts, memory qualification gates, and release safety checks.

![Obsidian Memory architecture: wiki graph, agent memory, hooks, and provenance](assets/brand/obsidian-memory-hero.png)

**The agent is the operator. Obsidian is the IDE. The wiki is the codebase.**

This repository is the public, portable skill source. It reflects production lessons from an internal Obsidian Memory system without publishing private vault state, local RAW caches, session drafts, or machine-specific paths.

## Why This Exists

Obsidian Memory is built on the LLM Wiki pattern: direct file reading, deliberate page structure, and Git history can beat premature RAG for small-to-medium knowledge bases. The agent manages Markdown like code: it ingests sources, creates linked pages, keeps provenance, and turns recurring questions into reviewed synthesis pages.

The system extends that base with agent-memory ideas from ALIVE-style memory, gstack-style runtime discipline, MemPalace-style wings/drawers, Graphify-inspired extraction, and a Beads-inspired review queue. These are practical layers, not a private-vault dump or a database migration.

## What You Get

**LLM Wiki** (`wiki/`)

Books, articles, PDFs, conversations, and notes become source-backed summaries, entities, concepts, domain maps, and synthesis pages.

**Agent Memory** (`12-shared/` + `12-{agent}/`)

Shared decisions, project/tool context, active focus, corrections, and handoff state stay separate from durable wiki knowledge.

**Self-Improvement Loop** (`memory_corrections.md` + backlog/metrics/lessons)

Agents record process mistakes, extract repeated patterns into reviewed lessons, and load recent corrections before non-trivial work.

**Codex Lifecycle Hooks** (`assets/codex/hooks/`)

`SessionStart`, `PostToolUse`, and `PreCompact` connect runtime events to bounded memory loading, push reminders, and safe pre-compaction drafts.

**Runtime Safety Contract**

Runtime memory, when an operator builds it locally, stays optional, private, disposable, and outside the vault. Capture, query, dynamic context, promotion, and auto-proposal switches should start disabled and become usable only after reviewed gate evidence plus explicit operator approval.

**Memory Qualification**

New retrieval or context patterns must earn their way in: golden set, baseline contest, gap report, then the smallest read-only trial that addresses an observed failure mode. OpenViking-style ideas are treated as reference patterns, not as a dependency.

**Operator Control Tower / Workflow Discipline** (`assets/operator/`)

Read-only release status, branch-close handoff, decision review, lesson review, and public release-surface checks help agents close work without losing decisions or over-promoting drafts.

**Graph / Bridge / Operator Tools** (`assets/graph/` + `assets/operator/`)

Derived graph reports, bridge health checks, retrieval replay, operation registry, and skill resolver audits make memory drift visible without auto-mutating the vault.

## 5-Minute Smoke Start

1. Install the skill:

   ```bash
   git clone https://github.com/kkonstvol-lab/obsidian-memory ~/.agents/skills/obsidian-memory
   ```

2. Create an empty Obsidian vault and copy:
   - `assets/vault-CLAUDE.md` -> `wiki/CLAUDE.md` or adapt into `AGENTS.md`;
   - `assets/vault-index.md` -> `wiki/index.md`;
   - `assets/vault-log.md` -> `wiki/log.md`;
   - `assets/templates/` -> `templates/`.

3. Create `12-shared/` and one private `12-{agent}/` folder.

4. Add the RAW-safe `.gitignore` policy from `references/setup.md`.

5. If using Codex hooks, configure `assets/codex/env.example` and `assets/codex/hooks/hooks.json.template`, then run the smoke checks in `references/codex-hooks.md`.

6. Run one small INGEST, QUERY, LINT, or hook smoke test before bulk importing sources.

Detailed setup lives in `references/setup.md`.

## Core Architecture

```text
vault/
  wiki/                         source-backed knowledge base
    summaries/                  one digest per source
    entities/                   people, companies, tools, products
    concepts/                   frameworks, methods, ideas
    synthesis/                  cross-source answers and analysis
    domains/                    Maps of Content
  12-shared/                    shared decisions, routing, scripts
  12-{agent}/                   private operational memory per agent
  raw-sources/
    converted/                  Git-tracked converted markdown
    provenance/                 Git-tracked source identity
    pdfs/                       local RAW cache, usually ignored
    00 RAW INBOX/               local intake, usually ignored
  templates/                    wiki, wing, and drawer templates
```

Repository layout:

```text
obsidian-memory/
  README.md
  SKILL.md
  AGENTS.md
  LICENSE
  references/                   deep guides and safety contracts
  assets/
    brand/                      README visual assets
    codex/hooks/                SessionStart, PostToolUse, PreCompact
    graph/                      dependency-light derived graph tools
    operator/                   bridge/retrieval/audit/control tower tools
    templates/                  drop-in Obsidian templates
```

## Runtime Hooks

The Codex hook bundle is a first-class part of the system:

- `SessionStart` reads bounded active/shared/correction context at startup.
- `PostToolUse` notices important tool events, including `git push`, and reminds the agent to update memory.
- `PreCompact` writes a non-canonical session draft before context compaction.
- `hooks.json.template` provides a starting point for wiring the bundle into Codex.

Hooks are conservative by design. They do not mutate `wiki/`, `raw-sources/`, shared memory, or canonical memory automatically. Treat hooks as live only after local runtime configuration and `hooks-status` or equivalent smoke checks confirm that they run.

See `references/codex-hooks.md`.

## Runtime Safety And Qualification

This skill documents a public contract for optional runtime memory layers without publishing a private runtime engine:

- Markdown and Git remain the source of truth.
- Runtime state stays local, private, disposable, and outside the vault.
- Dynamic context is advisory only; it is not an instruction layer.
- Promotion starts as an immutable proposal. Canonical apply requires explicit approval.
- Auto-promotion means proposal creation only, never direct canonical mutation.
- Retention cleanup may touch runtime-local artifacts only.
- New retrieval/context layers require qualification evidence before adoption.

Read `references/operator-runtime.md` for the runtime safety contract and `references/memory-qualification.md` for qualification-first retrieval trials.

## Graph, Bridges, And Operator Tools

- `assets/graph/` is a local Graphify-inspired derived layer. It builds `graph.json`, `GRAPH_REPORT.md`, review queues, and retrieval candidates without requiring the external `graphify` package.
- `review-state.jsonl` is append-only. Suggestions become canonical wiki links only after review.
- `assets/operator/bridge_health.py` reports practical bridge gaps such as `raw -> converted`, `converted -> summary`, `summary -> domain`, and `graph action -> review-state`.
- `assets/operator/retrieval_eval.py`, `operation_registry.py`, and `skill_repo_audit.py` are advisory tools inspired by GBrain-style runtime discipline.
- `assets/operator/release_status.py`, `branch_close_pack.py`, `release_surface_check.py`, `decision_review_board.py`, and `lesson_review_board.py` form a portable Operator Control Tower: read-only packets for release readiness, branch closure, public surface drift, durable decision candidates, and lesson promotion review.

No DB, vector store, MCP runtime, background job system, dynamic context engine, or automatic repair loop is shipped by this skill.

## Operator Control Tower

The Control Tower layer is intentionally advisory:

- `release-status` checks repo identity, branch/upstream, push boundary, staged/unstaged files, RAW binary risk, and post-push obligations.
- `branch-close` builds a compact handoff skeleton with repo state, recent commits, memory context, bridge/lesson backlog, risks, and verification commands.
- `release-surface-check` verifies public-facing skill markers such as README narrative, hooks visibility, graph/bridge visibility, license, `AGENTS.md`, and Codex co-author attribution.
- `decision-review` surfaces candidates that may deserve durable routing into shared decisions, wiki synthesis, runbooks, lessons, or public surface notes.
- `lesson-review` keeps private operational lessons in review state; promotion to pattern/principle remains human-reviewed and never automatic.

The lifecycle state for decision review is append-only and belongs under the local/private `12-{agent}/decision-review/` area. Do not publish real review-state or private lesson content.

## Safety Model

1. Markdown and Git remain the source of truth.
2. RAW PDF/DOCX/ZIP files are usually local cache, not canonical Git content.
3. Converted markdown and provenance are Git-safe.
4. Agent-private memory stays isolated in `12-{agent}/`.
5. Derived graph, bridge, retrieval, and audit reports can be deleted and rebuilt.
6. Hooks and operator scripts do not auto-promote suggestions into canonical wiki or memory.
7. Optional runtime layers are local/private/disposable and stay outside the vault.
8. Dynamic context is advisory only and never overrides direct source reading.
9. New retrieval/context patterns need measured gaps and safety-zero trials before adoption.

## Install

Claude/Codex-style install:

```bash
git clone https://github.com/kkonstvol-lab/obsidian-memory ~/.claude/skills/obsidian-memory
```

Generic agent skills install:

```bash
git clone https://github.com/kkonstvol-lab/obsidian-memory ~/.agents/skills/obsidian-memory
```

Restart the agent app after installing or updating skills.

## Requirements

- Obsidian.
- An agent environment with skills support.
- Recommended Obsidian plugins: Dataview, Templater, Obsidian Git.
- Python 3 for optional graph and operator scripts.
- Node.js for optional Codex hook scripts.

## References

- `references/setup.md` - first-time setup.
- `references/wiki-schema.md` - page types, frontmatter, INGEST/QUERY/LINT rules.
- `references/memory-schema.md` - shared/private memory roots, load order, self-improvement loop.
- `references/codex-hooks.md` - hook install, config, smoke tests, and fallback.
- `references/graphify.md` - derived graph/review queue.
- `references/bridge-health.md` - practical bridge health.
- `references/operator-runtime.md` - advisory runtime tools.
- `references/memory-qualification.md` - golden-set, baseline, gap, and read-only trial gates.
- `references/workflow-discipline.md` - Control Tower, branch close, decision review, and lesson review.
- `references/release-safety.md` - RAW, provenance, Git, and artifact safety.

## Credits / Contributors

Built from production use by human operators working with Claude Code and Codex.

- Core pattern: Tobi Lutke's LLM Wiki idea.
- Agent memory influences: witcheer's ALIVE system, gstack-style architecture/runtime discipline, MemPalace-style wings/drawers, and long-running agent memory practice.
- Public skill implementation and later production hardening: Claude Code and Codex, with Codex carrying the bridge-health, GBrain-inspired operator runtime, hook refresh, and public release synchronization work.
- Graph layer influences: Graphify-style extraction and Beads-inspired graph action review.
- Design influences: ClaudSoul-style practical bridge checks and GBrain/GStack-style runtime discipline.

## License

MIT. See `LICENSE`.
