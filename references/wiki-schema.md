# Wiki Schema — Detailed Reference

The wiki layer stores accumulated knowledge from sources. It should be linked, searchable, provenance-aware, and safe to synchronize through Git.

---

## Page Types

| Type | Folder | Naming | Purpose |
|------|--------|--------|---------|
| summary | `wiki/summaries/` | `summary-{slug}.md` | Digest of one source |
| entity | `wiki/entities/` | `{name}.md` | Person, company, tool, product |
| concept | `wiki/concepts/` | `{name}.md` | Methodology, framework, idea |
| synthesis | `wiki/synthesis/` | `synthesis-{topic}.md` | Cross-source answer or analysis |
| domain | `wiki/domains/` | `domain-{name}.md` | Map of Content |

Slug format: lowercase, hyphens instead of spaces, no special characters unless the vault explicitly supports them.

Entity rule: create a separate entity file only when the entity appears in two or more sources or is strategically important. Otherwise mention it inline.

---

## Frontmatter Standard

Every wiki page:

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

### Summary Source Fields

```yaml
source_file: "[[raw-sources/converted/filename]]"
source_type: pdf | docx | article | video | book | conversation | note | unknown
source_author: "Author Name"
source_id: "sha256:<hash>"
source_sha256: "<hash>"
source_size_bytes: 12345
source_local_cache: "raw-sources/pdfs/source.pdf"
source_availability: local_macbook | missing | optional_external
source_archive_status: local_verified | local_missing | blocked_zero_byte | optional_external_uploaded
```

### Converted Markdown Source Fields

Converted markdown in `raw-sources/converted/` should also carry source fields:

```yaml
---
title: "Converted Source Title"
type: converted-source
source_id: "sha256:<hash>"
source_sha256: "<hash>"
source_size_bytes: 12345
source_local_cache: "raw-sources/pdfs/source.pdf"
source_availability: local_macbook | missing | optional_external
source_archive_status: local_verified | local_missing | blocked_zero_byte | optional_external_uploaded
converted_at: YYYY-MM-DDTHH:MM
---
```

### Entity Fields

```yaml
entity_type: person | company | tool | product | project | source
```

---

## Provenance Manifest

Recommended manifest path:

```text
raw-sources/provenance/raw-local-manifest.jsonl
```

One JSONL row per RAW source:

```json
{
  "source_id": "sha256:<hash>",
  "source_filename": "source.pdf",
  "source_type": "pdf",
  "sha256": "<hash>",
  "size_bytes": 12345,
  "local_cache_path": "raw-sources/pdfs/source.pdf",
  "source_availability": "local_macbook",
  "archive_status": "local_verified",
  "external_archive_uri": "",
  "converted_path": "raw-sources/converted/source.md",
  "wiki_summary_path": "wiki/summaries/summary-source.md",
  "import_batch_id": "YYYYMMDDTHHMMSS",
  "updated_at": "YYYY-MM-DDTHH:MM"
}
```

Use `blocked_zero_byte` for zero-byte files. Do not treat them as valid sources until replaced.

---

## Tag Taxonomy

Structural tags:

- `wiki`
- `wiki/summary`
- `wiki/entity`
- `wiki/concept`
- `wiki/synthesis`
- `wiki/domain`

Domain tags are user-defined:

- `domain/ai`
- `domain/marketing`
- `domain/business`
- `domain/learning`
- `domain/engineering`

Status tags are optional:

- `status/draft`
- `status/active`
- `status/stale`

---

## INGEST Workflow

1. Place RAW source in local cache or intake.
2. Compute `sha256`, size, normalized filename, and target paths.
3. Update provenance manifest.
4. Convert the source to `raw-sources/converted/{slug}.md`.
5. Add source frontmatter to converted markdown.
6. Read converted/source content before writing wiki pages.
7. Create `wiki/summaries/summary-{slug}.md`.
8. Create or update entities only when justified.
9. Create or update concepts for durable ideas/frameworks.
10. Update relevant domain MOCs.
11. Update `wiki/index.md`.
12. Append to `wiki/log.md`.

Conflict policy:

- Identical target exists: skip or reuse.
- Same filename, different hash: quarantine/report; do not overwrite.
- Zero-byte/invalid/unsafe: quarantine/report; do not ingest as valid source.

---

## QUERY Workflow

1. Orient with `wiki/CLAUDE.md` or `AGENTS.md`.
2. Read `wiki/index.md`.
3. Search relevant wiki pages and converted markdown.
4. Read the strongest evidence pages.
5. Answer in natural language with a short evidence section.
6. If the topic is recurring, strategic, or assembled from several sources, propose a synthesis page.
7. Create synthesis only after user approval or direct instruction.
8. Log the QUERY when it produces a durable wiki change or an important research trail.

Suggested answer shape:

```markdown
## Answer
[direct answer]

## Used Evidence
- [[page-one]]
- [[page-two]]

## Suggested Wiki Upgrade
[optional synthesis/runbook/index update proposal]
```

---

## Synthesis Criteria

Create or propose `wiki/synthesis/synthesis-{topic}.md` when:

- the answer combines several sources;
- the question is likely to recur;
- the topic is strategic or operationally important;
- a future agent would otherwise need to reassemble the same evidence;
- the synthesis can become a decision, runbook, or domain map.

Do not create synthesis just because a question was answered.

---

## LINT Checklist

| Check | Fix |
|-------|-----|
| Broken wikilinks | Update link or create missing page |
| Orphan pages | Link from index/domain/related page or mark intentional |
| Missing frontmatter | Fill required fields |
| Stale pages | Review, update, or mark stale |
| Converted without summary | Run INGEST or mark deferred |
| Index drift | Add missing rows |
| Duplicate entities | Merge and update references |
| Provenance gaps | Repair manifest/frontmatter/source links |

After LINT, log findings if they are useful for future operators.

---

## `index.md` Structure

```markdown
# Wiki Index

## Domains

| File | Description | Pages |
|------|-------------|-------|
| [[domain-ai]] | AI, LLMs, prompts, agents | 12 |

## Summaries

| File | Source | Type | Domain | Date |
|------|--------|------|--------|------|
| [[summary-example]] | Source Title | pdf | ai | YYYY-MM-DD |

## Entities

| File | Type | Domain | Date |
|------|------|--------|------|
| [[entity-name]] | company | ai | YYYY-MM-DD |

## Concepts

| File | Domain | Date |
|------|--------|------|
| [[concept-name]] | ai | YYYY-MM-DD |

## Synthesis

| File | Theme | Domain | Date |
|------|-------|--------|------|
| [[synthesis-topic]] | Topic | ai | YYYY-MM-DD |
```

---

## `log.md` Format

Newest entries first.

```markdown
# Wiki Log

## YYYY-MM-DDTHH:MM — INGEST | Source Name

- Source: description
- Created: files
- Updated: files
- Notes: context

## YYYY-MM-DDTHH:MM — QUERY | Question

- Query: question
- Sources used: [[page1]], [[page2]]
- Synthesis saved: [[synthesis-topic]] or none

## YYYY-MM-DDTHH:MM — LINT | Health check

- Checked: scope
- Fixed: issues
- Remaining: deferred issues
```
