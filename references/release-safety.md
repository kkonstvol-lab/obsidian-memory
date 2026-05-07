# Release Safety — Git, RAW, Provenance

This reference describes a safe release contract for an Obsidian Memory vault.

---

## Goal

Git should contain the memory system and source-derived markdown artifacts, not heavy RAW binaries.

Canonical Git content:

- `wiki/**`
- `raw-sources/converted/**`
- `raw-sources/provenance/**`
- `12-shared/**`
- `12-{agent}/**`
- templates, docs, routing, scripts

Local RAW cache:

- `raw-sources/pdfs/**`
- `raw-sources/00 RAW INBOX/**`
- source PDF/DOCX/ZIP files

Optional external archive:

- leave `external_archive_uri` empty until a deliberate archive plan exists;
- do not upload/delete RAW automatically as part of ingest.

---

## Provenance Contract

Use `raw-sources/provenance/raw-local-manifest.jsonl`.

Each row should include:

- `source_id`: usually `sha256:<hash>`;
- `source_filename`;
- `source_type`;
- `sha256`;
- `size_bytes`;
- `local_cache_path`;
- `source_availability`;
- `archive_status`;
- `external_archive_uri`;
- `converted_path`;
- `wiki_summary_path`;
- `import_batch_id`;
- `updated_at`.

Converted markdown and wiki summaries should include matching source fields in frontmatter:

- `source_id`;
- `source_sha256`;
- `source_size_bytes`;
- `source_local_cache`;
- `source_availability`;
- `source_archive_status`.

---

## Status Semantics

Use clear statuses:

- `local_verified`: local RAW exists and hash matches manifest.
- `local_missing`: markdown exists, but local RAW is currently unavailable.
- `blocked_zero_byte`: source is invalid until replaced.
- `optional_external_uploaded`: external copy exists, with URI in manifest.

Warnings are acceptable for `local_missing`, empty `external_archive_uri`, or `blocked_zero_byte` if the markdown/provenance state is intentional.

Blocking failures:

- converted/wiki source hash does not match manifest;
- manifest says `local_verified` but the file is missing or hash differs;
- fresh converted markdown has no source frontmatter;
- RAW binaries are staged for Git when policy says they are local-only.

---

## Pre-Commit Guard Pattern

If you add scripts, provide a pre-commit hook that runs:

```bash
python3 12-shared/scripts/git_raw_guard.py
python3 12-shared/scripts/memory_operator.py verify-provenance
```

The guard should block:

- PDF/DOCX/ZIP files in local RAW cache folders;
- unexpectedly large files above the vault's size threshold;
- private memory writes into the wrong agent folder;
- broken provenance for newly staged converted/wiki files.

---

## One-Command Release Gate

A useful `memory_operator.py check-all` command should run:

1. RAW Git guard.
2. Provenance verification.
3. Wiki lint.
4. Conversion plan dry-run.
5. Git whitespace/diff check.
6. Agent-private isolation check.
7. RAW tracking check.

It should exit non-zero on blocking failures and may print non-blocking lint debt separately.

---

## Retention Policy

Suggested default:

- Keep local RAW PDF/DOCX/ZIP for at least 90 days after successful converted/wiki ingest.
- After 90 days, mark as `eligible_for_cleanup`, but do not delete automatically.
- Cleanup is plan/apply only and requires explicit user approval.

Never propose cleanup if:

- no converted markdown exists;
- no wiki summary exists;
- provenance verification fails;
- file is marked `retention: keep`;
- file is the only available source for unfinished work.

---

## Broken Provenance Runbook

If provenance verification fails:

1. Do not commit.
2. Generate or read a provenance report.
3. Classify the error:
   - missing manifest entry;
   - frontmatter hash mismatch;
   - local file missing;
   - local hash changed;
   - converted/wiki missing source fields;
   - blocked zero-byte.
4. For missing manifest entry, rescan local RAW cache and add the row.
5. For hash mismatch, do not overwrite silently; create a new `source_id` if the source is truly new.
6. For local missing, mark `local_missing` or restore the file.
7. For missing frontmatter, copy fields from manifest.
8. For zero-byte, keep `blocked_zero_byte` until a valid replacement appears.

---

## Commit Grouping

Prefer meaningful groups:

1. Operator tooling/docs/safety.
2. Converted markdown and wiki content.
3. Provenance/index/policy updates.

Before each commit, inspect staged files and confirm no RAW binaries are staged.
