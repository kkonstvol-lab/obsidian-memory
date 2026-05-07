# LLM Wiki — Vault Operator Schema

Read this file at the start of explicit wiki operations.

---

## Architecture

The vault has four logical layers:

1. `wiki/` — LLM-maintained knowledge base.
2. `raw-sources/converted/` and `raw-sources/provenance/` — Git-safe source-derived artifacts.
3. Local RAW cache such as `raw-sources/pdfs/` and `raw-sources/00 RAW INBOX/` — original binaries, usually Git-ignored.
4. `12-shared/` and `12-{agent}/` — shared and private agent operating memory.

Do not duplicate content between wiki and memory. Wiki stores knowledge from sources. Memory stores operating context.

---

## Page Types

| Type | Folder | Naming | Purpose |
|------|--------|--------|---------|
| summary | `wiki/summaries/` | `summary-{slug}.md` | Digest of one source |
| entity | `wiki/entities/` | `{name}.md` | Person, company, tool, product |
| concept | `wiki/concepts/` | `{name}.md` | Methodology, framework, idea |
| synthesis | `wiki/synthesis/` | `synthesis-{topic}.md` | Cross-source answer or analysis |
| domain | `wiki/domains/` | `domain-{name}.md` | Map of Content |

Entity rule: create an entity page only when the entity appears in two or more sources or is strategically important.

---

## Required Frontmatter

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

Summary pages should also include source provenance:

```yaml
source_file: "[[raw-sources/converted/filename]]"
source_type: pdf | docx | article | video | book | conversation | note | unknown
source_author: ""
source_id: "sha256:<hash>"
source_sha256: "<hash>"
source_size_bytes: 12345
source_local_cache: "raw-sources/pdfs/source.pdf"
source_availability: local_macbook | missing | optional_external
source_archive_status: local_verified | local_missing | blocked_zero_byte | optional_external_uploaded
```

---

## Operations

### INGEST

1. Identify RAW source and compute provenance.
2. Convert to `raw-sources/converted/{slug}.md`.
3. Create or update summary, entities, concepts, domain MOC, and index.
4. Log the operation.

Never overwrite same-name/different-hash RAW files. Quarantine/report conflicts.

### QUERY

1. Read `wiki/index.md`.
2. Search and read relevant pages.
3. Answer with evidence using `[[wikilinks]]`.
4. Propose synthesis when the answer spans multiple sources or will recur.
5. Create synthesis only after user approval or direct request.

### LINT

Check broken wikilinks, orphans, frontmatter, stale pages, converted-without-summary, index drift, duplicate entities, and provenance gaps.

---

## Rules

1. Use the user's primary language consistently.
2. Use `[[wikilinks]]` inside wiki pages.
3. Keep every durable page reachable from index, domain MOC, or related pages.
4. Update `updated:` on changed pages.
5. Do not edit RAW binaries as part of wiki work.
6. Do not commit RAW PDF/DOCX/ZIP files unless the vault policy explicitly allows it.
7. Do not mix private memory across agents.
8. Do not write just because you read. Write when it improves retrieval, traceability, or safety.
