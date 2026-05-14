# obsidian-memory

Explicit-only skill for building and operating an Obsidian-based LLM wiki plus agent memory system.

**The agent is the operator. Obsidian is the IDE. The wiki is the codebase.**

This repository is the public, portable skill source. It reflects production lessons from an internal Obsidian Memory system without publishing private vault state, local RAW caches, session drafts, or machine-specific paths.

---

## Origin

The skill is built on Tobi Lutke's LLM Wiki pattern: the agent acts like a programmer, Obsidian acts like the IDE, and the knowledge base is treated like a codebase.

It extends that base with agent-memory ideas from witcheer's ALIVE system, gstack-style runtime discipline, MemPalace-style people/project memory, Graphify-derived graph extraction, and a Beads-inspired graph action review queue.

The result is two parallel systems inside one vault:

- `wiki/` — accumulated, source-backed knowledge from books, articles, PDFs, conversations, and other sources;
- `memory/`, `12-shared/`, or `12-{agent}/` — operational context for the agent: current focus, projects, tools, durable decisions, corrections, and handoff state.

---

## What It Does

**LLM Wiki** (`wiki/`) stores durable knowledge:

- turn books, articles, PDFs, conversations, and other sources into structured summaries;
- extract entities and concepts into linked pages;
- organize knowledge through domain Maps of Content;
- create synthesis pages only when they are useful and approved;
- lint links, frontmatter, index drift, and evidence gaps.

This is the base idea of the system: direct file reading and deliberate wiki structure can beat premature RAG for small-to-medium corpora. Sources become summaries, summaries become entities/concepts/domains, and recurring questions become synthesis pages.

**Agent Memory** (`12-shared/` + `12-{agent}/`) stores operating context:

- `12-shared/` holds shared decisions, routing, scripts, and release policy;
- `12-codex/`, `12-claude/`, or another `12-{agent}/` hold private agent memory;
- private memory stays isolated; shared decisions are append-only and attributed.

Operational memory is not the same thing as wiki knowledge. It stores working context: active focus, global decisions, project and tool registries, corrections, and next actions. Load it in layers, from compact identity/routing context to deeper search only when the task needs it.

**Self-Improvement Loop** (`memory_corrections.md` + backlog/metrics/lessons) compounds agent quality:

- record logical and process mistakes as concrete correction entries;
- extract repeated mistakes into reviewed lessons or advisory gates;
- keep improvement ideas in a backlog until they are intentionally shipped;
- read recent corrections before non-trivial work;
- measure and review drift instead of relying on vibes or hidden context.

In mature deployments this loop can be scheduled, for example as a daily review that detects repeated process patterns and proposes improvements without auto-mutating canonical memory.

**RAW + Provenance Safety** (`raw-sources/`) keeps source traceability without bloating Git:

- `raw-sources/converted/` and `raw-sources/provenance/` are Git-safe;
- `raw-sources/pdfs/` and `raw-sources/00 RAW INBOX/` are normally local/ignored;
- source identity is tracked through hash, size, availability, converted paths, and summary links.

---

## Install

Claude Code-style install:

```bash
git clone https://github.com/kkonstvol-lab/obsidian-memory ~/.claude/skills/obsidian-memory
```

Generic agent skills install:

```bash
git clone https://github.com/kkonstvol-lab/obsidian-memory ~/.agents/skills/obsidian-memory
```

Restart the agent app after installing or updating skills.

---

## Quick Start

1. Follow `references/setup.md`.
2. Copy `assets/vault-CLAUDE.md` to `wiki/CLAUDE.md` or adapt it into `AGENTS.md`.
3. Copy `assets/templates/` to your vault's `templates/`.
4. Create `12-shared/` and one `12-{agent}/` private memory folder per agent.
5. Add a `.gitignore` policy before importing RAW binaries.
6. Start with a small INGEST, QUERY, or LINT test.

---

## File Structure

```text
obsidian-memory/
├── AGENTS.md
├── README.md
├── SKILL.md
├── references/
│   ├── bridge-health.md
│   ├── codex-hooks.md
│   ├── graphify.md
│   ├── memory-schema.md
│   ├── operator-runtime.md
│   ├── release-safety.md
│   ├── setup.md
│   └── wiki-schema.md
└── assets/
    ├── codex/
    │   ├── env.example
    │   ├── hooks/
    │   └── memory_in_progress.md
    ├── graph/
    ├── operator/
    │   ├── bridge_health.py
    │   ├── operation_registry.py
    │   ├── retrieval_eval.py
    │   ├── skill_repo_audit.py
    │   └── tests/
    ├── templates/
    ├── identity.md
    ├── vault-CLAUDE.md
    ├── vault-index.md
    └── vault-log.md
```

---

## Core System And Optional Extensions

Core system:

- `wiki/` implements the Obsidian LLM Wiki pattern: source-backed summaries, entities, concepts, domains, and synthesis pages.
- `12-shared/` plus `12-{agent}/` implements multi-agent operational memory with private isolation.
- `memory_corrections.md`, improvement backlog, metrics, and optional lessons implement the self-improvement loop.
- `assets/templates/drawer.md`, `wing-person.md`, and `wing-project.md` preserve MemPalace-style people/project memory: wings for durable people/project state and drawers for immutable session capture before reviewed compilation.

Optional extensions:

- `references/bridge-health.md` and `assets/operator/bridge_health.py` describe ClaudSoul-style practical bridges: script-checkable links between RAW, converted markdown, summaries, domains, graph actions, lessons, and session drafts. This is not a full ontology or persona architecture.
- `references/operator-runtime.md` and `assets/operator/` describe GBrain-inspired runtime discipline: operation registry, retrieval replay, bridge/storage dashboard, and resolver audit. This is not a migration to GBrain, a DB layer, vector search, or MCP runtime.
- `references/graphify.md` and `assets/graph/` describe an optional derived graph/retrieval layer combining Graphify-style extraction with a Beads-inspired review queue. Obsidian Markdown remains the source of truth; graph outputs are rebuildable.
- `references/codex-hooks.md` and `assets/codex/` describe optional Codex lifecycle hooks. Hooks are live only after the runtime is configured and `hooks-status` or equivalent smoke checks confirm they run.

---

## Operations

| Operation | When to use |
|-----------|-------------|
| SETUP | First-time vault initialization |
| INGEST | Add and process a source |
| QUERY | Search and synthesize knowledge |
| LINT | Check wiki health |
| MEMORY | Load or update agent context |
| BRIDGE | Check practical bridges between memory layers |
| RELEASE | Verify provenance, RAW guard, and Git safety before push |

---

## Key Principles

1. **Explicit-only:** do not touch the vault unless the user asked for vault/wiki/memory work.
2. **Evidence-first:** wiki answers should cite the pages or converted sources used.
3. **Synthesis by approval:** propose durable synthesis pages when useful; create after approval or direct request.
4. **Private memory isolation:** never mix `12-codex/`, `12-claude/`, or other agent-private context.
5. **Markdown is canonical:** Git should contain wiki, converted markdown, provenance, scripts, docs, and routing.
6. **Derived reports are rebuildable:** graph, bridge, retrieval, and audit reports are optional outputs, not source of truth.
7. **RAW is usually local:** PDF/DOCX/ZIP files can stay outside Git while still being tracked in provenance.
8. **No auto-mutation:** graph suggestions, hooks, bridge reports, and retrieval reports do not edit canonical memory automatically.

---

## Requirements

- Obsidian.
- An agent environment with skills support.
- Recommended Obsidian plugins: Dataview, Templater, Obsidian Git.
- Python 3 for optional operator scripts.
- Node.js for optional Codex hook scripts.

---

## Credits / Contributors

Built from production use by human operators working with Claude Code and Codex.

- Core pattern: Tobi Lutke's LLM Wiki idea.
- Agent memory influences: witcheer's ALIVE system, gstack-style architecture/runtime discipline, MemPalace-style wings/drawers, and long-running agent memory practice.
- Public skill implementation and later production hardening: Claude Code and Codex, with Codex carrying the bridge-health, GBrain-inspired operator runtime, hook refresh, and public release synchronization work.
- Graph layer influences: Graphify-style extraction and Beads-inspired graph action review.
- Design influences: ClaudSoul-style practical bridge checks and GBrain/GStack-style runtime discipline.
