# Wiki Schema — Detailed Reference

Full specification for the `wiki/` knowledge layer. This file extends the SKILL.md operations with complete detail.

---

## Page Types

| Type | Folder | Naming | Purpose |
|------|--------|--------|---------|
| summary | `wiki/summaries/` | `summary-{slug}.md` | Digest of a single source |
| entity | `wiki/entities/` | `{name}.md` | Person, company, tool, product — what it IS |
| concept | `wiki/concepts/` | `{name}.md` | Methodology, framework, idea |
| synthesis | `wiki/synthesis/` | `synthesis-{topic}.md` | Cross-source analysis or answer |
| domain | `wiki/domains/` | `domain-{name}.md` | Map of Content — thematic hub |
| wing | `wiki/wings/` | `person-{slug}.md` / `project-{slug}.md` | Your relationship with a person or project (5 halls) |
| drawer | `wiki/drawers/` | `drawer-YYYY-MM-DD-{slug}.md` | Immutable session log — never edit after creation |

**Entity vs Wing distinction:** An entity captures *what something is* (Anthropic = AI safety company). A wing captures *your relationship with it* (project-anthropic-integration = timeline of your work with them). Don't duplicate between them — cross-link instead.

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
wings_updated: []  # filled after COMPILE — list of wing files updated
status: locked    # always locked — drawers are immutable
```

---

## Tag Taxonomy

Tags use Obsidian slash notation (slash = hierarchy in Tag Pane).

### Structural tags (always use these):
- `wiki` — all wiki pages
- `wiki/summary`, `wiki/entity`, `wiki/concept`, `wiki/synthesis`, `wiki/domain`
- `wiki/wing`, `wing/person`, `wing/project` — MemPalace wing pages
- `wiki/drawer` — MemPalace session log pages
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

**Palace-specific checks (add to weekly LINT):**

| Check | How | Fix |
|-------|-----|-----|
| Uncompiled drawers | Find drawers with `compiled: false` older than 3 days | Run COMPILE |
| Empty halls | Wing sections with no content, wing > 30 days old | Add or note as not applicable |
| Tunnel candidates | Entity name appears in 3+ wings without cross-link | Add `[[wikilink]]` to Relations sections |
| Stale wings by type | Person wings > 60 days, project wings > 30 days without `updated` change | Review, update, or change status |
| Contradictions | Same fact with different values across wings | Verify with drawer sources, fix the wing with wrong value |

After LINT: write a LINT entry to `wiki/log.md` with findings and what was fixed.

---

## COMPILE — Workflow Detail

Triggered after `/session-summary` or by running `/compile` manually.

1. List all files in `wiki/drawers/` — filter those with `compiled: false`
2. For each uncompiled drawer:
   - Read full content
   - Identify people mentioned → map to `person-{slug}` wings
   - Identify projects mentioned → map to `project-{slug}` wings
   - Classify each piece of information into a hall:
     - **Facts** — stable attributes (role, stack, budget, city)
     - **Events** — dated occurrences (meetings, releases, decisions)
     - **Discoveries** — insights and learnings
     - **Preferences** — how to work with them, requirements
     - **Advice/Decisions** — strategic choices, recommendations
3. For each wing to update:
   - Read current wing content
   - Append new entries to appropriate halls (do not duplicate)
   - Provenance: each new entry ends with `← [[drawer-YYYY-MM-DD-slug]]`
   - Update `updated` in frontmatter
   - Add drawer to **Sources** section
4. Mark drawer: `compiled: true`, `wings_updated: [list of wings]`
5. Update `wiki/index.md` — add any new wings to the Wings tables
6. Append COMPILE entry to `wiki/log.md`:
   ```
   ## YYYY-MM-DDTHH:MM — COMPILE | N drawers processed
   - Drawers: drawer-YYYY-MM-DD-slug
   - Wings updated: [list]
   - Wings created: [list or —]
   ```

## WING — Creating a Profile

Usage: `/wing person Name` or `/wing project Name`

1. Generate slug: lowercase, hyphens (e.g., `person-john-smith`, `project-acme-redesign`)
2. Check `wiki/wings/{slug}.md` doesn't already exist
3. Search existing data for pre-fill:
   - `wiki/entities/` — for matching entity page
   - `wiki/summaries/` — for mentions
   - `memory/memory_clients.md` — for client data
4. Create from `templates/wing-person.md` or `templates/wing-project.md`
5. Pre-fill halls from found data; add provenance `← [[source]]`
6. Update `wiki/index.md` — add row to Wings section
7. Append WING entry to `wiki/log.md`

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

## Wings (MemPalace)

### Projects

| File | Client | Status | Updated |
|------|--------|--------|---------|
| [[project-example]] | [[person-client]] | active | 2026-01-01 |

### People

| File | Relationship | Domain | Updated |
|------|-------------|--------|---------|
| [[person-example]] | client | marketing | 2026-01-01 |

## Drawers (Session Logs)

| File | Date | Compiled | Wings Updated |
|------|------|----------|---------------|
| [[drawer-2026-01-01-example]] | 2026-01-01 | true | project-example |

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

---

## YYYY-MM-DDTHH:MM — COMPILE | N drawers processed

- Drawers: drawer-YYYY-MM-DD-slug
- Wings updated: person-example, project-example
- Wings created: —

---

## YYYY-MM-DDTHH:MM — WING | Created person-example

- Type: person
- Pre-filled from: [[entity-example]], [[summary-example]]
```
