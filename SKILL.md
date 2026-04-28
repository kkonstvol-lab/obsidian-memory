---
name: obsidian-memory
description: "Создаёт и поддерживает систему постоянной памяти для AI-агентов на базе Obsidian. Скил объединяет три взаимосвязанные системы: (1) LLM Wiki — курируемая база знаний из конспектов, сущностей и концептов, извлечённых из книг, статей и PDF, связанных wikilinks и Maps of Content; (2) MemPalace — слой Wings (профили людей и проектов) и Drawers (неизменяемые логи сессий), которые компилируют накопленный опыт в структурированный контекст, с verbatim-first evidence и temporal validity; (3) Self-Improvement Loop — приватная оперативная память каждого агента (текущий фокус, ошибки, in-progress задачи, бэклог, heartbeat, метрики), которая учится на своих ошибках без смешивания контекстов. Поверх всех трёх систем работает Graphify knowledge graph — автоматически находит связи между страницами, строит Leiden communities, генерирует Beads-style очередь ревью `GRAPH_READY.md`, hybrid retrieval candidates и предоставляет граф через MCP tools, поэтому агенты делают graph query перед grep. Поддерживает мультиагентные сетапы (Claude Code + Codex): мировые факты общие, оперативная память полностью изолирована по агентам. Codex hooks включают session start, post-push reminder и precompact autosave drafts. Операции: SETUP, INGEST, QUERY, LINT, GRAPH, MEMORY, CODEX-HOOKS, COMPILE, WING. Triggers: 'ingest', 'add to wiki', 'query wiki', 'lint wiki', 'obsidian memory', 'obsidian wiki', '/obsidian-memory', 'llm wiki', 'knowledge base', 'wiki setup', 'codex hooks', 'codex memory hooks', 'precompact autosave', 'compile', 'create wing', 'person profile', 'project profile', 'knowledge graph', 'graphify', 'graph ready', 'hybrid retrieval', 'missing links'."
---

# Obsidian Memory — LLM Wiki + Agent Memory System

Claude is the "programmer". Obsidian is the "IDE". The wiki is the "codebase".

---

## Architecture

Four layers in a single Obsidian vault:

```
vault/
├── identity.md           # L0 context — loaded every session (~100 tokens)
├── wiki/                 # LLM-generated knowledge base (Claude manages)
│   ├── CLAUDE.md         # Schema — rules for this vault (copy from assets/)
│   ├── index.md          # Catalog of all wiki pages
│   ├── log.md            # Chronological operation log
│   ├── summaries/        # One file per source ingested
│   ├── entities/         # People, companies, tools, products
│   ├── concepts/         # Methodologies, frameworks, ideas
│   ├── synthesis/        # Cross-source analysis, answers to questions
│   ├── domains/          # Maps of Content — thematic hubs
│   ├── wings/            # Person & project profiles — MemPalace
│   │   ├── person-{slug}.md   # Per-person: facts/events/discoveries/preferences/advice
│   │   └── project-{slug}.md  # Per-project: facts/events/discoveries/preferences/decisions
│   └── drawers/          # Immutable session logs — MemPalace
│       └── drawer-YYYY-MM-DD-{slug}.md
├── memory/               # Agent operational context (Claude manages)
│   ├── memory_active.md  # Current focus — max 15 lines, always load first
│   ├── memory_in_progress.md  # Active tasks, repos, blockers, next actions
│   ├── memory_decisions.md  # Global conventions and decisions
│   ├── memory_projects.md   # Project registry
│   ├── memory_tools.md      # Tools, plugins, MCP servers
│   ├── memory_clients.md    # Clients and contacts
│   ├── memory_repos.md      # Repos and codebases
│   ├── memory_corrections.md  # Logical/process errors (NOT style — see voice-corrections)
│   ├── memory_improvements_backlog.md  # Improvement ideas (Active/In Progress/Done)
│   ├── memory_metrics.md    # Weekly snapshot (HEARTBEAT Sundays)
│   ├── memory_heartbeat.md  # Daily self-check log (cron 10:00 MSK)
│   └── projects/{name}/     # Deep context per project
├── output/               # Regeneratable artifacts (Karpathy "code" layer)
│   ├── dashboards/       # Dataview dashboards — auto-updating in Obsidian
│   └── reports/          # Weekly reports, generated from wings
└── raw-sources/          # Immutable originals — Claude NEVER edits these
    ├── pdfs/
    ├── articles/
    └── converted/        # Markdown converted from PDFs
```

**4-layer context loading model:**

| Layer | Size | Files | When |
|-------|------|-------|------|
| L0 Identity | ~100 tokens | `identity.md` | Every session |
| L1 Critical | ~500 tokens | `memory_active.md` + `memory_decisions.md` | Every session |
| L2 Wings | ~200 tokens each | `wiki/wings/person-*.md`, `project-*.md` | On-demand by context |
| L3 Deep | unlimited | `wiki/drawers/*`, `raw-sources/*` | Explicit search |

**Core separation:**
- `wiki/` = accumulated knowledge ("what I know and from where") — linked, tagged, searchable
- `memory/` = agent operational context ("what I do and how") — session state, decisions, projects
- Never duplicate content between wiki and memory

---

## Quick Reference

| Operation | When | Entry point |
|-----------|------|-------------|
| **SETUP** | First time, empty vault | Create folder structure + copy assets/ |
| **INGEST** | New source to process | Read source → create summary → extract entities/concepts |
| **QUERY** | Need knowledge from wiki | Graph/retrieval candidates → grep → source evidence → synthesize |
| **LINT** | Weekly or before major work | Check links, orphans, frontmatter, index drift + Palace checks |
| **GRAPH** | After bulk ingests (5+ pages) | Regenerate graph + review queue |
| **MEMORY** | Start of any work session | Load memory files in correct order before working |
| **CODEX-HOOKS** | Optional Codex automation | Install lifecycle hooks, push reminders, and precompact autosave drafts |
| **COMPILE** | After each session | Process uncompiled drawers → update wings |
| **WING** | When creating a person/project profile | `/wing person Name` or `/wing project Name` |

---

## Operations

### SETUP — First-time initialization

1. Create folder structure (see Architecture above), including `wiki/wings/`, `wiki/drawers/`, `output/dashboards/`, `output/reports/`
2. Copy `assets/vault-CLAUDE.md` → `wiki/CLAUDE.md` in your vault
3. Copy `assets/vault-index.md` → `wiki/index.md`
4. Copy `assets/vault-log.md` → `wiki/log.md`
5. Copy `assets/templates/` → your vault's `templates/` folder (includes wing-person, wing-project, drawer templates)
6. Copy `assets/identity.md` → `identity.md` in vault root — fill in your name, role, and key rules
7. Configure MCP server (see `references/setup.md`)
8. Install required Obsidian plugins: Dataview, Templater
9. Write first log entry: `YYYY-MM-DDTHH:MM — INIT | System initialization`

### INGEST — Adding a source

1. Place source file in `raw-sources/` (PDFs in `pdfs/`, articles in `articles/`)
2. If PDF: convert to markdown → `raw-sources/converted/{slug}.md`
3. Read the source in full
4. Create `wiki/summaries/summary-{slug}.md` using the summary template
5. Extract entities mentioned 2+ times → create/update files in `wiki/entities/`
6. Extract concepts/frameworks → create/update files in `wiki/concepts/`
7. Update the relevant domain MOC in `wiki/domains/` (create if doesn't exist)
8. Update `wiki/index.md` — add rows to the appropriate tables
9. Append to `wiki/log.md`:
   ```
   ## YYYY-MM-DDTHH:MM — INGEST | Source name
   - Source: [description]
   - Created: [list of new files]
   - Updated: [list of updated files]
   - Notes: [any relevant context]
   ```

**Entity rule:** Only create a separate entity file if the entity appears in 2+ sources. Otherwise mention inline in the summary.

### QUERY — Searching the wiki

**Step 0 — Graph query (if graphify MCP is available):**
Before touching files, call `mcp__graphify__query_graph` with the question as natural language.
- Results include EXTRACTED nodes → use their `source_file` paths as starting points for step 3
- Results are empty or confidence weak → skip to step 1 as normal
- If `graphify-out/retrieval_candidates.jsonl` exists, use it as a ranked hint list, not as source of truth.

1. Read `wiki/CLAUDE.md` to orient (if not already in context)
2. Read `wiki/index.md` to navigate
3. Search relevant pages (grep across `wiki/`, or follow `source_file` hints from graph query)
4. Read the found pages and their verbatim evidence (`raw-sources/`, `wiki/drawers/`)
5. Synthesize an answer using `[[wikilinks]]` to reference sources
6. Include `Used Evidence`: drawers/raw/wiki pages actually used
7. If the synthesis is valuable (cross-source insight) → save as `wiki/synthesis/synthesis-{topic}.md`
8. Append QUERY entry to `wiki/log.md`

**Graphify MCP tools (if installed):**
- `mcp__graphify__query_graph` — semantic BFS/DFS traversal by question (use first)
- `mcp__graphify__shortest_path` — path between two concepts
- `mcp__graphify__get_neighbors` — all connections of a concept
- `mcp__graphify__god_nodes` — most connected nodes (core abstractions)
- `mcp__graphify__graph_stats` — corpus overview

### LINT — Health check

Check and report:
1. **Broken wikilinks** — `[[links]]` pointing to non-existent files
2. **Orphan pages** — no incoming links (except from index.md)
3. **Incomplete frontmatter** — missing required fields
4. **Stale pages** — `updated` older than 90 days
5. **Unprocessed sources** — files in `raw-sources/converted/` without a summary
6. **Index drift** — pages exist but not in `index.md`
7. **Duplicate entities** — two files about the same entity
8. **Orphan claims** — important claims in summaries/synthesis/wings without source evidence
9. **Temporal conflicts** — active facts with same `claim_id`, different `claim_value`, and empty `valid_to`

Write a LINT entry to `wiki/log.md` with findings and actions taken.

### GRAPH — Regenerating the knowledge graph

1. Read `references/graphify.md` first.
2. If graph files are not installed, copy `assets/graph/` into:
   - single-agent: `memory/graph/`
   - multi-agent: `12-shared/graph/`
3. Run `python extract_vault.py`, then `python suggest_wikilinks.py` from the graph folder.
4. Optionally run `python hybrid_retrieval.py "your query"` to build `graphify-out/retrieval_candidates.jsonl`.
5. Review `graphify-out/GRAPH_READY.md` before editing any wiki pages.
6. Use `review-state.jsonl` for accepted/skipped/obsolete actions. Do not manually edit generated reports as source of truth.
7. Never let graph scripts modify `wiki/` or `raw-sources/`; they only generate reports.
8. For validation, run `python tests/test_graphify_beads.py`.

### MEMORY — Loading agent context

**Step 0 — Determine agent_id (multi-agent setups only):**
If running multiple agents from the same vault, each agent has its own private memory root.
Read your entry-point file (`CLAUDE.md` or `AGENTS.md`) to find:
- `agent_id` — who you are (e.g. `claude`, `codex`)
- `private` — your private memory dir (e.g. `memory/` for single-agent, `12-claude/` for multi-agent)
- `shared` — world-level facts dir (e.g. `12-shared/` in multi-agent setups)

For single-agent setups: skip this step, use `memory/` for everything.

Load in this order at the start of a session:
0. `identity.md` — L0 context, ALWAYS first (~100 tokens)
1. `{private}/memory_active.md` — L1 critical, ALWAYS (current focus, blockers)
2. `{private}/memory_in_progress.md` — if available (active tasks and next actions)
3. `{shared}/memory_decisions.md` — L1 critical, ALWAYS (global conventions)
4. `{private}/memory_corrections.md` — BEFORE non-trivial tasks, last 5 entries (avoid repeating past mistakes)
5. Domain memory based on session context (see `references/memory-schema.md`)
6. Project-specific files if working on a specific project
7. `wiki/wings/{relevant}.md` — L2: load if working with a specific person or project
8. Maximum 2 additional related domain files

**Self-improvement loop files** (read on demand, not always):
- `{private}/memory_improvements_backlog.md` — when reflecting on agent quality, planning improvements
- `{private}/memory_heartbeat.md` — last entry, when checking systemic patterns
- `{private}/memory_metrics.md` — when reviewing weekly performance

**Write rules:**
- Private operational files (`memory_active`, `memory_corrections`, etc.) → write to your `{private}` path only.
- World-level facts (`memory_decisions`, `memory_projects`, etc.) → in multi-agent setups, append-only to `{shared}` with source attribution.

### CODEX-HOOKS — Optional Codex lifecycle automation

Use this operation when the user wants Codex to load Obsidian memory automatically at session startup and remind itself to update memory after publishing work.

1. Read `references/codex-hooks.md` first.
2. Copy `assets/codex/hooks/codex-session-start.js` and `assets/codex/hooks/codex-post-tool-use.js` into `~/.codex/hooks/`.
3. Copy `assets/codex/hooks/precompact-autosave.js` if you want non-canonical session draft autosave.
4. Copy `assets/codex/hooks/hooks.json.template` to `~/.codex/hooks.json`.
5. Configure the vault path with `OBSIDIAN_VAULT_PATH` or `~/.codex/obsidian-memory.json`.
6. Copy `assets/codex/memory_in_progress.md` into the agent private memory root if it does not exist.
7. Enable `[features].codex_hooks = true` only after confirming the local Codex runtime supports hooks.
8. Run the manual smoke tests from `references/codex-hooks.md`.

**Do not depend on GitHub Issues.** Store active work state in Obsidian memory. Links to GitHub, Linear, or Obsidian notes are optional task metadata.

### COMPILE — Compiling session drawers into wings

1. Find all `wiki/drawers/` files where `compiled: false`
2. If none — report: "All drawers compiled, nothing to process."
3. For each uncompiled drawer, extract:
   - People mentioned → find or create `wiki/wings/person-{slug}.md`
   - Projects mentioned → find or create `wiki/wings/project-{slug}.md`
   - Classify into halls: Facts / Events / Discoveries / Preferences / Decisions
4. Update each affected wing:
   - Append new info to the correct hall section
   - Put active facts in `Current State`; move superseded facts to `History`
   - Do not duplicate existing entries
   - Add provenance: each new line ends with `← [[drawer-YYYY-MM-DD-slug]]`
   - If a fact replaces an older one, set temporal metadata (`valid_to`, `supersedes`, `superseded_by`)
   - Update `updated` in frontmatter
   - Add drawer to **Source Evidence** section
5. Mark drawer as compiled: `compiled: true`, `wings_updated: [list]`
6. Update `wiki/index.md` if new wings were created
7. Append COMPILE entry to `wiki/log.md`
8. Mini-lint: verify wikilinks in updated files
9. Report: "Compiled N drawers → updated: [wings list]"

### WING — Creating a person or project profile

Usage: `/wing person John Smith` or `/wing project Acme Redesign`

1. Parse type (`person` or `project`) and generate slug (lowercase, hyphens)
2. Check that `wiki/wings/{slug}.md` doesn't already exist
3. Search existing data for pre-fill:
   - Grep `wiki/entities/`, `wiki/summaries/`, `memory/memory_clients.md` for mentions
4. Create wing from the appropriate template (`wing-person.md` or `wing-project.md`)
5. Pre-fill halls with found data, adding provenance `← [[source]]`
6. Update `wiki/index.md` — add row to Wings section
7. Append WING entry to `wiki/log.md`
8. Report: "Wing created: wiki/wings/{slug}.md — N halls pre-filled"

---

## Core Rules

1. **Links:** Use only `[[wikilinks]]`, never markdown links `[text](url)`.
2. **Connectivity:** Every wiki page must have at least one incoming link.
3. **Timestamps:** Update `updated:` field in frontmatter on every change.
4. **No duplication:** Never duplicate content between `wiki/` and `memory/`.
5. **Raw sources:** Never edit files in `raw-sources/`. They are permanent originals.
6. **Quality over quantity:** 5 well-linked pages beat 20 isolated ones.
7. **Writes required:** Any session that reads from wiki/memory must write something back (update log, add note, record synthesis). A session with no writes is a failure.
8. **Drawers are immutable:** After creation, a drawer is NEVER edited. It is the source of truth for the past. The only permitted change is setting `compiled: true`.
9. **Entity vs Wing:** Entity = what it IS (company, tool). Wing = your relationship with it (project work, person interactions). Don't duplicate between them.
10. **Compile after sessions:** Every significant session ends with: create drawer → run COMPILE → wings updated.
11. **Verbatim-first:** Important conclusions in summaries, synthesis, wings, or decisions link to raw sources, drawers, or session artifacts.
12. **Temporal append-only:** New decisions/facts supersede older ones instead of silently rewriting them.
13. **Drafts are not memory:** Precompact/session autosave drafts are non-canonical until reviewed by `/session-summary` or COMPILE.

---

## References

- `references/wiki-schema.md` — Full wiki layer schema: page types, frontmatter, tag taxonomy, detailed operations
- `references/memory-schema.md` — Memory layer: file types, load order, routing, key principles
- `references/graphify.md` — Graph layer installation, Beads-style review queue, validation
- `references/codex-hooks.md` — Optional Codex hooks that load Obsidian memory and remind after `git push`
- `references/setup.md` — Step-by-step first-time setup guide (plugins, MCP, git sync)
- `assets/vault-CLAUDE.md` — Drop-in schema file for `wiki/CLAUDE.md`
- `assets/vault-index.md` — Template for `wiki/index.md` (includes Wings and Drawers sections)
- `assets/identity.md` — Template for vault root `identity.md` (L0 context)
- `assets/templates/` — Page templates: wiki-summary, wiki-entity, wiki-concept, wiki-synthesis, wiki-domain, wing-person, wing-project, drawer
