# LLM Wiki — Schema

> This file defines the rules for Claude working with the wiki layer of this vault.
> Read this file at the start of every wiki operation.

## Architecture

Obsidian Markdown is the canonical source of truth. Runtime indexes, graph files, retrieval candidates, and autosave drafts are derived or reviewable artifacts.

Three core layers:

1. **Raw Sources** (`raw-sources/`) — immutable originals. PDFs, articles, notes. Claude NEVER edits these files.
2. **Wiki** (`wiki/`) — LLM-generated and maintained pages. Linked, frontmatter-tagged, searchable.
3. **Schema** (this file) — the rules Claude follows when working with wiki.

**Separation from memory/:** `memory/` = agent operational context ("what I do and how"). `wiki/` = accumulated knowledge ("what I know and from where"). Never duplicate content between them.

MemPalace-derived practices in this vault:

- **Verbatim-first:** every important claim links to a verbatim source (`raw-sources/`, `wiki/drawers/`, or a conversation/session artifact).
- **Temporal validity:** decisions, facts, and project/client state carry validity in time; new decisions supersede old ones instead of silently rewriting them.
- **Hybrid retrieval:** QUERY starts with graph/retrieval candidates, then file search, then source reading.
- **Precompact autosave:** autosave drafts are a safety net, not canonical memory until `/session-summary` or COMPILE.

---

## Page Types

| Type | Folder | Naming | Purpose |
|------|--------|--------|---------|
| summary | `wiki/summaries/` | `summary-{slug}.md` | Digest of a single source |
| entity | `wiki/entities/` | `{name}.md` | Person, company, tool, product |
| concept | `wiki/concepts/` | `{name}.md` | Methodology, framework, idea |
| synthesis | `wiki/synthesis/` | `synthesis-{topic}.md` | Cross-source analysis or answer |
| domain | `wiki/domains/` | `domain-{name}.md` | Map of Content — thematic hub |
| wing | `wiki/wings/` | `person-{slug}.md` / `project-{slug}.md` | Person or project profile (5 halls: facts, events, discoveries, preferences, advice/decisions) |
| drawer | `wiki/drawers/` | `drawer-YYYY-MM-DD-{slug}.md` | Immutable session log. NEVER edit after creation |

**Entity rule:** Only create a separate entity file if the entity appears in 2+ sources. Otherwise mention inline in the summary.

**Slug format:** lowercase, hyphens instead of spaces, no special characters.
Example: `summary-atomic-habits.md`, `summary-ycombinator-essay.md`

---

## Frontmatter Standard

Required for EVERY wiki page:

```yaml
---
title: "Page Title"
type: summary | entity | concept | synthesis | domain
created: YYYY-MM-DD
updated: YYYY-MM-DDTHH:MM
domain:
  - ai
status: active | draft | stale
confidence: high | medium | low
valid_from: YYYY-MM-DD
valid_to:
supersedes:
superseded_by:
source: ""
tags:
  - wiki
  - wiki/summary
  - domain/ai
---
```

### Additional fields for summary:
```yaml
source_file: "[[raw-sources/converted/filename]]"
source_type: pdf | article | video | book | conversation | note
source_author: "Author Name"
```

### Additional field for entity:
```yaml
entity_type: person | company | tool | product
```

### Additional fields for wing:
```yaml
wing_type: person | project
relationship: client | mentor | contact | colleague | partner  # person only
client: "[[person-slug]]"  # project only
```

### Additional fields for drawer:
```yaml
session_date: YYYY-MM-DD
compiled: false | true
wings_updated: []  # filled after COMPILE
status: locked  # always locked — drawers are immutable
agent_id: codex | claude | other
```

---

## Tag Taxonomy

**Structural:** `wiki`, `wiki/summary`, `wiki/entity`, `wiki/concept`, `wiki/synthesis`, `wiki/domain`, `wiki/wing`, `wing/person`, `wing/project`, `wiki/drawer`, `raw-source`

**Domain** (define your own, examples): `domain/ai`, `domain/marketing`, `domain/business`, `domain/learning`, `domain/engineering`, `domain/psychology`, `domain/personal`

**MemPalace:** `wiki/wing`, `wing/person`, `wing/project`, `wiki/drawer`

**Status:** `status/draft`, `status/active`, `status/stale`, `status/locked`

Obsidian slash notation: slash = hierarchy in Tag Pane.

---

## Operations

### INGEST — Adding a source

1. Place source in `raw-sources/` (PDFs in `pdfs/`, articles in `articles/`)
2. If PDF: convert to markdown → `raw-sources/converted/{slug}.md`
3. Read the source in full
4. Create `wiki/summaries/summary-{slug}.md` using the wiki-summary template
5. Extract entities → create/update files in `wiki/entities/`
6. Extract concepts → create/update files in `wiki/concepts/`
7. Update relevant domain MOC in `wiki/domains/`
8. Update `wiki/index.md` — add new rows
9. Append to `wiki/log.md` with date, operation type, files created/updated

### QUERY — Searching the wiki

1. If Graphify is available, read `memory/graph/graphify-out/retrieval_candidates.jsonl` or run graph query first.
2. Read `wiki/index.md` for navigation.
3. Search relevant pages with grep/search and graph/retrieval hints.
4. Read found pages and their verbatim evidence (`raw-sources/`, `wiki/drawers/`).
5. Synthesize answer using `[[wikilinks]]` to reference sources.
6. Include `Used Evidence`: drawers/raw/wiki pages actually used.
7. If synthesis is valuable → save as `wiki/synthesis/synthesis-{topic}.md`.
8. Update `wiki/log.md`.

### COMPILE — Compiling drawers into wings

Run after `/session-summary` or manually.

1. Find all drawers in `wiki/drawers/` where `compiled: false`
2. For each drawer, extract:
   a. People mentioned → find or create `wiki/wings/person-{slug}.md`
   b. Projects mentioned → find or create `wiki/wings/project-{slug}.md`
   c. Decisions → add to **Decisions** section of relevant wing
   d. Facts → add to **Facts** section
   e. Events → add to **Events** section with date
   f. Insights → add to **Discoveries** section
   g. Preferences → add to **Preferences** section
   h. New concepts/entities → update `wiki/concepts/`, `wiki/entities/` if significant
3. In each updated wing:
   - Append info to the appropriate hall (section)
   - Put active facts in `Current State`; move superseded facts to `History`
   - Update `updated` in frontmatter
   - Add provenance: every new line ends with `← [[drawer-YYYY-MM-DD-slug]]`
   - If a fact replaces an older one, set `valid_to` on the older claim and link the new one with `supersedes`
   - Add `[[drawer-YYYY-MM-DD-slug]]` to **Source Evidence** section
4. Mark drawer as compiled:
   - `compiled: true`
   - `wings_updated: [list of updated wings]`
5. Update `wiki/index.md` if new wings were created
6. Append COMPILE entry to `wiki/log.md`
7. Mini-lint: verify wikilinks in updated files

**Provenance in wings** — each fact references its drawer source:
```markdown
## Facts
- Works at Acme Corp, engineering lead ← [[drawer-2026-04-11-meeting]]
```

---

### LINT — Health check

Run periodically. Check:

1. Broken `[[wikilinks]]` — links to non-existent files
2. Orphan pages — no incoming links (except index.md)
3. Incomplete frontmatter — missing required fields
4. Stale pages — `updated` older than 90 days
5. Unprocessed sources — files in `raw-sources/converted/` without a summary
6. Index drift — pages exist but not in `wiki/index.md`
7. Duplicate entities — two files about the same entity

**Palace-specific checks:**

8. Uncompiled drawers — `compiled: false` older than 3 days
9. Empty halls — wing sections with no content after 30 days
10. Tunnel candidates — same entity mentioned in 3+ wings without a cross-link
11. Staleness by type — person wings > 60 days, project wings > 30 days without update
12. Contradictions — same fact with different values across wings
13. Orphan claims — important claims in summaries/synthesis/wings without evidence/source links
14. Temporal conflicts — two active facts with the same `claim_id`, different `claim_value`, and empty `valid_to`

Write a LINT entry to `wiki/log.md` with findings and actions taken.

---

## Rules

1. **Language:** Use your primary language consistently. Technical terms in English are fine.
2. **Links:** Only `[[wikilinks]]`, never markdown links `[text](url)`.
3. **Connectivity:** Every page must have at least one incoming link.
4. **Timestamps:** Update `updated:` field in frontmatter on any change.
5. **No duplication:** Don't duplicate information between `wiki/` and `memory/`.
6. **Raw sources:** NEVER edit files in `raw-sources/`.
7. **Quality over quantity:** 5 well-linked pages beat 20 isolated ones.
8. **Drawers are immutable:** after creation, a drawer is NEVER edited. It is the source of truth for what happened.
9. **Entity vs Wing:** entity = what it IS (company, tool). Wing = your relationship with it (project work, person interactions). Don't duplicate.
10. **Compile after sessions:** every significant session ends with drawer → compile → wing updates.
11. **Verbatim-first:** summaries/synthesis/wings may interpret, but they must link to source evidence.
12. **Temporal append-only:** never silently rewrite decisions/facts; use `valid_to`, `supersedes`, and `superseded_by`.
13. **Drafts are not memory:** precompact/session autosave drafts are non-canonical until human/session-summary review.
