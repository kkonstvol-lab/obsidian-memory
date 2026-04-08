---
name: obsidian-memory
description: "Build and maintain a persistent knowledge + memory system in Obsidian using the LLM Wiki pattern. Invoke when: (1) SETUP — user wants to initialize an agent knowledge base in their Obsidian vault for the first time; (2) INGEST — adding a source (PDF, article, book, conversation, note) to the wiki knowledge base; (3) QUERY — searching or synthesizing knowledge from accumulated wiki pages; (4) LINT — health-check of wiki (broken links, orphan pages, stale content, index drift); (5) MEMORY — routing agent context by loading the right memory files before starting work. Triggers: 'ingest', 'add to wiki', 'add to knowledge base', 'query wiki', 'lint wiki', 'obsidian memory', 'obsidian wiki', '/obsidian-memory', 'llm wiki', 'knowledge base', 'wiki setup'."
---

# Obsidian Memory — LLM Wiki + Agent Memory System

Claude is the "programmer". Obsidian is the "IDE". The wiki is the "codebase".

---

## Architecture

Three layers in a single Obsidian vault:

```
vault/
├── wiki/                 # LLM-generated knowledge base (Claude manages)
│   ├── CLAUDE.md         # Schema — rules for this vault (copy from assets/)
│   ├── index.md          # Catalog of all wiki pages
│   ├── log.md            # Chronological operation log
│   ├── summaries/        # One file per source ingested
│   ├── entities/         # People, companies, tools, products
│   ├── concepts/         # Methodologies, frameworks, ideas
│   ├── synthesis/        # Cross-source analysis, answers to questions
│   └── domains/          # Maps of Content — thematic hubs
├── memory/               # Agent operational context (Claude manages)
│   ├── memory_active.md  # Current focus — max 15 lines, always load first
│   ├── memory_decisions.md  # Global conventions and decisions
│   ├── memory_projects.md   # Project registry
│   ├── memory_tools.md      # Tools, plugins, MCP servers
│   ├── memory_clients.md    # Clients and contacts
│   ├── memory_repos.md      # Repos and codebases
│   └── projects/{name}/     # Deep context per project
└── raw-sources/          # Immutable originals — Claude NEVER edits these
    ├── pdfs/
    ├── articles/
    └── converted/        # Markdown converted from PDFs
```

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
| **QUERY** | Need knowledge from wiki | Read index.md → grep → synthesize → optionally save synthesis |
| **LINT** | Weekly or before major work | Check links, orphans, frontmatter, index drift |
| **MEMORY** | Start of any work session | Load memory files in correct order before working |

---

## Operations

### SETUP — First-time initialization

1. Create folder structure (see Architecture above)
2. Copy `assets/vault-CLAUDE.md` → `wiki/CLAUDE.md` in your vault
3. Copy `assets/vault-index.md` → `wiki/index.md`
4. Copy `assets/vault-log.md` → `wiki/log.md`
5. Copy `assets/templates/` → your vault's `templates/` folder
6. Configure MCP server (see `references/setup.md`)
7. Install required Obsidian plugins: Dataview, Templater
8. Write first log entry: `YYYY-MM-DDTHH:MM — INIT | System initialization`

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

1. Read `wiki/CLAUDE.md` to orient (if not already in context)
2. Read `wiki/index.md` to navigate
3. Search relevant pages (grep across `wiki/`)
4. Read the found pages
5. Synthesize an answer using `[[wikilinks]]` to reference sources
6. If the synthesis is valuable (cross-source insight) → save as `wiki/synthesis/synthesis-{topic}.md`
7. Append QUERY entry to `wiki/log.md`

### LINT — Health check

Check and report:
1. **Broken wikilinks** — `[[links]]` pointing to non-existent files
2. **Orphan pages** — no incoming links (except from index.md)
3. **Incomplete frontmatter** — missing required fields
4. **Stale pages** — `updated` older than 90 days
5. **Unprocessed sources** — files in `raw-sources/converted/` without a summary
6. **Index drift** — pages exist but not in `index.md`
7. **Duplicate entities** — two files about the same entity

Write a LINT entry to `wiki/log.md` with findings and actions taken.

### MEMORY — Loading agent context

Load in this order at the start of a session:
1. `memory/memory_active.md` — ALWAYS first (current focus, blockers)
2. `memory/memory_decisions.md` — ALWAYS second (global conventions)
3. Domain memory based on session context (see `references/memory-schema.md`)
4. Project-specific files if working on a specific project
5. Maximum 2 additional related domain files

---

## Core Rules

1. **Links:** Use only `[[wikilinks]]`, never markdown links `[text](url)`.
2. **Connectivity:** Every wiki page must have at least one incoming link.
3. **Timestamps:** Update `updated:` field in frontmatter on every change.
4. **No duplication:** Never duplicate content between `wiki/` and `memory/`.
5. **Raw sources:** Never edit files in `raw-sources/`. They are permanent originals.
6. **Quality over quantity:** 5 well-linked pages beat 20 isolated ones.
7. **Writes required:** Any session that reads from wiki/memory must write something back (update log, add note, record synthesis). A session with no writes is a failure.

---

## References

- `references/wiki-schema.md` — Full wiki layer schema: page types, frontmatter, tag taxonomy, detailed operations
- `references/memory-schema.md` — Memory layer: file types, load order, routing, key principles
- `references/setup.md` — Step-by-step first-time setup guide (plugins, MCP, git sync)
- `assets/vault-CLAUDE.md` — Drop-in schema file for `wiki/CLAUDE.md`
- `assets/templates/` — Page templates for all 5 wiki page types
