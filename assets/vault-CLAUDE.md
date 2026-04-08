# LLM Wiki — Schema

> This file defines the rules for Claude working with the wiki layer of this vault.
> Read this file at the start of every wiki operation.

## Architecture

Three layers:

1. **Raw Sources** (`raw-sources/`) — immutable originals. PDFs, articles, notes. Claude NEVER edits these files.
2. **Wiki** (`wiki/`) — LLM-generated and maintained pages. Linked, frontmatter-tagged, searchable.
3. **Schema** (this file) — the rules Claude follows when working with wiki.

**Separation from memory/:** `memory/` = agent operational context ("what I do and how"). `wiki/` = accumulated knowledge ("what I know and from where"). Never duplicate content between them.

---

## Page Types

| Type | Folder | Naming | Purpose |
|------|--------|--------|---------|
| summary | `wiki/summaries/` | `summary-{slug}.md` | Digest of a single source |
| entity | `wiki/entities/` | `{name}.md` | Person, company, tool, product |
| concept | `wiki/concepts/` | `{name}.md` | Methodology, framework, idea |
| synthesis | `wiki/synthesis/` | `synthesis-{topic}.md` | Cross-source analysis or answer |
| domain | `wiki/domains/` | `domain-{name}.md` | Map of Content — thematic hub |

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

---

## Tag Taxonomy

**Structural:** `wiki`, `wiki/summary`, `wiki/entity`, `wiki/concept`, `wiki/synthesis`, `wiki/domain`, `raw-source`

**Domain** (define your own, examples): `domain/ai`, `domain/marketing`, `domain/business`, `domain/learning`, `domain/engineering`, `domain/psychology`, `domain/personal`

**Status:** `status/draft`, `status/active`, `status/stale`

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

1. Read `wiki/index.md` for navigation
2. Search relevant pages (grep across `wiki/`)
3. Read found pages
4. Synthesize answer using `[[wikilinks]]` to reference sources
5. If synthesis is valuable → save as `wiki/synthesis/synthesis-{topic}.md`
6. Update `wiki/log.md`

### LINT — Health check

Run periodically. Check:

1. Broken `[[wikilinks]]` — links to non-existent files
2. Orphan pages — no incoming links (except index.md)
3. Incomplete frontmatter — missing required fields
4. Stale pages — `updated` older than 90 days
5. Unprocessed sources — files in `raw-sources/converted/` without a summary
6. Index drift — pages exist but not in `wiki/index.md`
7. Duplicate entities — two files about the same entity

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
