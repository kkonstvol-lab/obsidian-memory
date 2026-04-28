---
title: "Wiki Index"
type: domain
created: {{date}}
updated: {{date}}
domain: []
tags:
  - wiki
  - wiki/domain
status: active
confidence: high
---

# Wiki Index

Catalog of all wiki pages. Updated on every INGEST operation.

## Domains (Maps of Content)

| File | Description | Pages |
|------|-------------|-------|
| — | — | — |

## Summaries (Source Digests)

| File | Source | Type | Domain | Date |
|------|--------|------|--------|------|
| — | — | — | — | — |

## Entities

| File | Type | Domain | Date |
|------|------|--------|------|
| — | — | — | — |

## Concepts

| File | Domain | Date |
|------|--------|------|
| — | — | — |

## Wings (MemPalace)

### Projects

| File | Client | Status | Updated |
|------|--------|--------|---------|
| — | — | — | — |

### People

| File | Relationship | Domain | Updated |
|------|-------------|--------|---------|
| — | — | — | — |

```dataview
TABLE wing_type AS "Type", status AS "Status", updated AS "Updated"
FROM "wiki/wings"
WHERE type = "wing"
SORT updated DESC
```

## Drawers (Session Logs)

| File | Date | Compiled | Wings Updated |
|------|------|----------|---------------|
| — | — | — | — |

```dataview
TABLE session_date AS "Date", compiled AS "Compiled", wings_updated AS "Wings"
FROM "wiki/drawers"
WHERE type = "drawer"
SORT session_date DESC
```

## Synthesis

| File | Theme | Domain | Date |
|------|-------|--------|------|
| — | — | — | — |

---

## Dataview (auto-backup)

```dataview
TABLE type AS "Type", status AS "Status", domain AS "Domain", updated AS "Updated"
FROM "wiki"
WHERE type != null
SORT updated DESC
```
