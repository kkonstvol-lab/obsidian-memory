# Wiki Schema — Detailed Reference

Full specification for the `wiki/` knowledge layer. This file extends the SKILL.md operations with complete detail.

---

## Page Types

| Type | Folder | Naming | Purpose |
|------|--------|--------|---------|
| summary | `wiki/summaries/` | `summary-{slug}.md` | Digest of a single source |
| entity | `wiki/entities/` | `{name}.md` | Person, company, tool, product |
| concept | `wiki/concepts/` | `{name}.md` | Methodology, framework, idea |
| synthesis | `wiki/synthesis/` | `synthesis-{topic}.md` | Cross-source analysis or answer |
| domain | `wiki/domains/` | `domain-{name}.md` | Map of Content — thematic hub |

**Slug format:** lowercase, hyphens instead of spaces, no special characters.
Examples: `summary-atomic-habits.md`, `summary-ycombinator-startup-manual.md`

**Entity rule:** Only create a separate entity file if the entity is mentioned across 2+ different sources. For a single mention — keep inline in the summary.

---

## Frontmatter Standard

Every wiki page must have this frontmatter:

```yaml
---
title: "Page Title"
type: summary | entity | concept | synthesis | domain
created: YYYY-MM-DD
updated: YYYY-MM-DDTHH:MM
domain:
  - ai
  - marketing
status: active | draft | stale
confidence: high | medium | low
tags:
  - wiki
  - wiki/summary      # replace with wiki/{type}
  - domain/ai         # replace with domain/{your-domain}
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

Tags use Obsidian slash notation (slash = hierarchy in Tag Pane).

### Structural tags (always use these):
- `wiki` — all wiki pages
- `wiki/summary`, `wiki/entity`, `wiki/concept`, `wiki/synthesis`, `wiki/domain`
- `raw-source` — for files in raw-sources/ if you tag them

### Domain tags (define your own, examples):
- `domain/ai` — AI, LLMs, agents, prompts
- `domain/marketing` — marketing, positioning, SEO, funnels
- `domain/business` — strategy, growth, operations
- `domain/learning` — books, courses, skill development
- `domain/engineering` — code, architecture, DevOps
- `domain/psychology` — behavior, habits, decision-making
- `domain/personal` — personal development, health, relationships

**Domain tags are user-defined** — create the domains that match your knowledge areas.

### Status tags (optional):
- `status/draft` — incomplete, needs work
- `status/active` — current and maintained
- `status/stale` — older than 90 days, may need review

---

## INGEST — Detailed Workflow

1. **Place source** in `raw-sources/` (PDFs → `pdfs/`, saved articles → `articles/`)
2. **Convert PDF** if needed: use any PDF-to-markdown tool → `raw-sources/converted/{slug}.md`
3. **Read source** in full before writing anything
4. **Create summary** at `wiki/summaries/summary-{slug}.md`:
   - Use the `wiki-summary` template
   - Key ideas: 3–7 bullet points, most important insights
   - Detailed digest: organized by the source's structure
   - Extracted entities: list what should become entity pages
   - Related concepts: list what should become concept pages
   - Conclusions: your interpretation, what this means for your domains
5. **Create/update entities** in `wiki/entities/`:
   - Only for entities appearing in 2+ sources
   - Add incoming link from the summary: `[[entity-name]]`
6. **Create/update concepts** in `wiki/concepts/`:
   - Each concept gets its own file
   - Add incoming link from the summary
7. **Update domain MOC** in `wiki/domains/domain-{name}.md`:
   - Add the new summary to the Summaries section
   - Add any new concepts to the Concepts section
   - Add any new entities to the Entities section
   - Create the domain file if it doesn't exist yet
8. **Update `wiki/index.md`**:
   - Add row in the Summaries table
   - Add rows for any new entities/concepts
9. **Append to `wiki/log.md`**:
   ```
   ## YYYY-MM-DDTHH:MM — INGEST | Source Name
   - Source: [what it is]
   - Created: [new files]
   - Updated: [modified files]
   - Notes: [context, discoveries, decisions]
   ```

---

## QUERY — Detailed Workflow

1. **Orient:** Read `wiki/CLAUDE.md` (if not in context) to understand the schema
2. **Navigate:** Read `wiki/index.md` to find relevant domains and page types
3. **Search:** Grep across `wiki/` for relevant terms, concepts, entities
4. **Read:** Load the most relevant pages into context
5. **Synthesize:** Construct the answer, citing sources with `[[wikilinks]]`
6. **Save synthesis** (if valuable): Create `wiki/synthesis/synthesis-{topic}.md`
   - Use the `wiki-synthesis` template
   - Include: question/theme, sources used, analysis, conclusions
7. **Log:** Append QUERY entry to `wiki/log.md`

---

## LINT — Checklist

Run weekly or before major work sessions. Check each item:

| Check | How | Fix |
|-------|-----|-----|
| Broken wikilinks | Search for `[[` patterns, verify each target exists | Update link or create missing page |
| Orphan pages | Pages with no incoming links (except index.md) | Add link from relevant domain MOC |
| Incomplete frontmatter | Check for missing required fields | Fill in missing fields |
| Stale pages | `updated` older than 90 days | Review, update or mark `status: stale` |
| Unprocessed sources | Files in `raw-sources/converted/` without a summary | Run INGEST for each |
| Index drift | Wiki pages missing from `wiki/index.md` | Add missing rows to index |
| Duplicate entities | Two files for the same entity | Merge into one, update all references |

After LINT: write a LINT entry to `wiki/log.md` with findings and what was fixed.

---

## index.md Structure

```markdown
# Wiki Index

## Domains (Maps of Content)

| File | Description | Pages |
|------|-------------|-------|
| [[domain-ai]] | AI, LLMs, prompts, agents | 12 |

## Summaries

| File | Source | Type | Domain | Date |
|------|--------|------|--------|------|
| [[summary-example]] | Book Title — Author | book | learning | 2026-01-01 |

## Entities

| File | Type | Domain | Date |
|------|------|--------|------|
| [[entity-name]] | company | ai | 2026-01-01 |

## Concepts

| File | Domain | Date |
|------|--------|------|
| [[concept-name]] | ai | 2026-01-01 |

## Synthesis

| File | Theme | Domain | Date |
|------|-------|--------|------|
| [[synthesis-topic]] | Topic | ai | 2026-01-01 |

---

## Dataview (auto-backup)

\`\`\`dataview
TABLE type AS "Type", status AS "Status", domain AS "Domain", updated AS "Updated"
FROM "wiki"
WHERE type != null
SORT updated DESC
\`\`\`
```

---

## log.md Format

Reverse-chronological. Newest entries at the top.

```markdown
# Wiki Log

Chronological log of all operations.

---

## YYYY-MM-DDTHH:MM — INGEST | Source Name

- Source: What was ingested (type, author, topic)
- Created: list of new files
- Updated: list of modified files
- Notes: Decisions made, things discovered, context

---

## YYYY-MM-DDTHH:MM — QUERY | Question

- Query: What was asked
- Sources used: [[page1]], [[page2]]
- Synthesis saved: [[synthesis-topic]] (if applicable)

---

## YYYY-MM-DDTHH:MM — LINT | Weekly check

- Checked: N pages
- Fixed: list of issues fixed
- Remaining: known issues deferred
```
