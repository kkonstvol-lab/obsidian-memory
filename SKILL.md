---
name: obsidian-memory
description: "Explicit-only Obsidian memory workflow. Use when the user explicitly asks to work with an Obsidian vault, LLM wiki, agent memory, RAW/source ingest, provenance, QUERY, LINT, or release safety for a markdown knowledge system. Do not auto-route ordinary coding sessions into external vault workflows."
---

# Obsidian Memory — LLM Wiki + Agent Memory System

The agent is the operator. Obsidian is the IDE. The wiki is the codebase.

Use this skill only after an explicit user request. It touches an external vault, so treat every write as an intentional memory operation with provenance, routing, and sync consequences.

---

## Architecture

Recommended vault layout:

```text
vault/
├── wiki/                         # LLM-maintained knowledge base
│   ├── CLAUDE.md or AGENTS.md     # Vault schema and operator rules
│   ├── index.md                   # Catalog of wiki pages
│   ├── log.md                     # Operation log
│   ├── summaries/                 # One digest per source
│   ├── entities/                  # People, companies, tools, products
│   ├── concepts/                  # Methodologies, frameworks, ideas
│   ├── synthesis/                 # Cross-source answers and analysis
│   └── domains/                   # Maps of Content
├── 12-shared/                     # Shared operational memory for all agents
│   ├── memory_decisions.md        # Append-only durable decisions
│   ├── memory_routing.json        # Routing contract
│   └── scripts/                   # Optional operator tooling
├── 12-{agent}/                    # Canonical private memory per agent
│   ├── memory_active.md
│   ├── memory_corrections.md
│   ├── memory_improvements_backlog.md
│   ├── memory_heartbeat.md
│   └── memory_metrics.md
├── raw-sources/
│   ├── converted/                 # Markdown converted from raw sources; Git-tracked
│   ├── provenance/                # Source manifest and provenance docs; Git-tracked
│   ├── pdfs/                      # Local RAW cache; usually Git-ignored
│   ├── 00 RAW INBOX/              # Local intake; usually Git-ignored
│   └── quarantine/                # Conflicts/invalid sources; usually local
└── templates/
```

**Core separation:**

- `wiki/` = accumulated knowledge: what the system knows and which sources support it.
- `12-shared/` = durable shared operating rules, routing, decisions, and optional scripts.
- `12-{agent}/` = private working memory for one agent only. Never mix agent-private context.
- `raw-sources/converted/` + `raw-sources/provenance/` = Git-safe source-derived artifacts.
- RAW binaries such as PDF/DOCX/ZIP are usually local cache, not canonical Git content.

---

## Quick Reference

| Operation | When | Entry point |
|-----------|------|-------------|
| **SETUP** | First time, empty vault | Create folder structure, copy assets, configure sync policy |
| **INGEST** | New source to process | RAW intake → provenance → converted markdown → wiki pages |
| **QUERY** | Need knowledge from wiki | Read index/schema → search → answer with evidence → propose synthesis if useful |
| **LINT** | Weekly or before release | Check links, frontmatter, index drift, unprocessed converted files |
| **MEMORY** | Working with agent context | Load shared + correct private memory roots in order |
| **RELEASE** | Before committing/pushing | Guard RAW, verify provenance, run wiki lint, check isolation |

---

## Operations

### SETUP — First-Time Initialization

1. Create the folder structure above.
2. Copy `assets/vault-CLAUDE.md` to `wiki/CLAUDE.md` or adapt it into `AGENTS.md`.
3. Copy `assets/vault-index.md` to `wiki/index.md`.
4. Copy `assets/vault-log.md` to `wiki/log.md`.
5. Copy `assets/templates/` to `templates/`.
6. Create `12-shared/` and one private `12-{agent}/` folder per agent.
7. Add a `.gitignore` policy that keeps RAW binaries local while tracking wiki, converted markdown, provenance, scripts, and docs.
8. If using Git sync, configure Obsidian Git or another sync path after the RAW policy is in place.

Read `references/setup.md` for the detailed version.

### INGEST — Adding a Source

1. Put RAW files into local intake, usually `raw-sources/00 RAW INBOX/` or `raw-sources/pdfs/`.
2. Compute source identity before conversion: `sha256`, size, filename, source type, and local cache path.
3. Record or update `raw-sources/provenance/raw-local-manifest.jsonl`.
4. Convert source to markdown in `raw-sources/converted/{slug}.md`.
5. Add source frontmatter to the converted markdown.
6. Create `wiki/summaries/summary-{slug}.md` using the summary template.
7. Extract entities mentioned across multiple sources into `wiki/entities/`.
8. Extract durable ideas/frameworks into `wiki/concepts/`.
9. Update the relevant domain MOC in `wiki/domains/`.
10. Update `wiki/index.md`.
11. Append an `INGEST` entry to `wiki/log.md`.

**Safety:** never overwrite conflicting RAW files silently. If the same filename has a different hash, quarantine/report it and ask the user.

### QUERY — Searching the Wiki

1. Read `wiki/CLAUDE.md` or `AGENTS.md` if not already in context.
2. Read `wiki/index.md` to identify domains and candidate pages.
3. Search `wiki/` and, when helpful, `raw-sources/converted/`.
4. Read the most relevant pages.
5. Answer with an evidence section naming the pages used.
6. If the answer requires 3+ sources, is strategically recurring, or would save future work, propose a synthesis page.
7. Create `wiki/synthesis/synthesis-{topic}.md` only after user approval or a direct request.
8. Log meaningful QUERY operations in `wiki/log.md`, especially if a synthesis/runbook/index update was made.

**Default QUERY behavior:** answer first, propose the durable artifact second. Do not turn every useful answer into a page automatically.

### LINT — Health Check

Check and report:

1. Broken wikilinks.
2. Orphan pages with no incoming links.
3. Incomplete frontmatter.
4. Stale pages.
5. Converted markdown without wiki summary.
6. Index drift.
7. Duplicate entities.
8. Provenance gaps between RAW manifest, converted markdown, and wiki summaries.

After LINT, write a `LINT` entry only when the operation changed files or produced a meaningful report worth preserving.

### MEMORY — Loading Agent Context

Determine the current `agent_id` before reading private memory.

Recommended roots:

- Shared: `12-shared/`
- Codex private: `12-codex/`
- Claude private: `12-claude/`
- Optional project-local auxiliary layer: `agent-memory-{agent}/`

Load in this order:

1. `12-{agent}/memory_active.md` — current focus and blockers.
2. `12-shared/memory_decisions.md` — durable shared conventions.
3. `12-{agent}/memory_corrections.md` — last relevant process mistakes before non-trivial tasks.
4. Domain/project files from `12-shared/` based on routing.
5. At most two extra related files unless the user explicitly asks for a broad audit.

Write rules:

- Private operational files go only to the current agent's `12-{agent}/`.
- Shared decisions go append-only to `12-shared/memory_decisions.md` with attribution.
- Never write one agent's private context into another agent's folder.
- Project-local `agent-memory-{agent}/` is auxiliary, not canonical, unless the vault explicitly says otherwise.

### RELEASE — Commit/Push Safety

Before committing or pushing a vault:

1. Ensure RAW PDF/DOCX/ZIP files are not staged.
2. Verify provenance links between manifest, converted markdown, and wiki pages.
3. Run wiki lint.
4. Check that agent-private memory isolation is preserved.
5. Confirm `git status` contains only expected changes.
6. Commit in meaningful groups: tooling/docs, wiki content, provenance/index updates.

Read `references/release-safety.md` for a concrete policy and command pattern.

---

## Core Rules

1. **Explicit only:** use this skill only for direct vault/wiki/memory requests.
2. **Evidence first:** QUERY answers must name the wiki pages or converted sources used.
3. **Synthesis by approval:** propose durable synthesis when useful; create it after approval or direct instruction.
4. **No raw overwrite:** never overwrite RAW files with the same name but different hash.
5. **No RAW in Git by default:** Git should usually contain wiki, converted markdown, provenance, scripts, docs, and routing, not heavy source binaries.
6. **Private memory isolation:** one agent never reads/writes another agent's private folder unless the user explicitly asks for an audit.
7. **Wikilinks:** use `[[wikilinks]]` inside wiki pages; external URLs belong in source/provenance fields when needed.
8. **Connectivity:** every durable wiki page should be reachable from `index.md`, a domain MOC, or a related page.
9. **Timestamps:** update `updated:` frontmatter on changed wiki pages.
10. **No duplication:** wiki stores knowledge; memory stores operating context.
11. **Quality over quantity:** one well-linked synthesis can beat ten isolated summaries.
12. **No performative writes:** if a read-only answer is sufficient, do not write just to satisfy a rule. Write when it improves future retrieval, traceability, or operation safety.

---

## References

- `references/wiki-schema.md` — wiki page types, frontmatter, provenance fields, INGEST/QUERY/LINT details.
- `references/memory-schema.md` — shared/private memory roots, load order, routing, self-improvement loop.
- `references/release-safety.md` — Git/RAW/provenance safety contract.
- `references/setup.md` — first-time setup guide.
- `references/graphify.md` — optional derived graph/retrieval layer; Obsidian markdown remains source of truth.
- `references/codex-hooks.md` — optional Codex lifecycle hooks; verify runtime support before relying on them.
- `assets/vault-CLAUDE.md` — drop-in schema file for `wiki/CLAUDE.md`.
- `assets/templates/` — page templates for summary/entity/concept/synthesis/domain pages plus optional MemPalace-style wings/drawers.
