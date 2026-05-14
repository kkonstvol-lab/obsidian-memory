# Setup Guide — First-Time Installation

Use this guide to deploy an Obsidian Memory system in a new vault.

---

## Step 1: Obsidian Plugins

Required:

- **Dataview** — query wiki pages by frontmatter.
- **Templater** — create pages from templates.

Recommended:

- **Obsidian Git** — sync markdown vault state through GitHub or another Git remote.
- **Tag Wrangler** — manage tags in bulk.

Configure Git sync only after `.gitignore` is in place, so RAW binaries are not accidentally committed.

---

## Step 2: Vault Folder Structure

Create:

```text
vault/
├── wiki/
│   ├── summaries/
│   ├── entities/
│   ├── concepts/
│   ├── synthesis/
│   └── domains/
├── 12-shared/
│   └── scripts/
├── 12-codex/
├── 12-claude/
├── raw-sources/
│   ├── converted/
│   ├── provenance/
│   ├── pdfs/
│   ├── 00 RAW INBOX/
│   └── quarantine/
└── templates/
```

If you use different agent names, create `12-{agent}/` folders instead.

---

## Step 3: Drop-In Files

Copy from this skill:

| From | To | Purpose |
|------|----|---------|
| `assets/vault-CLAUDE.md` | `wiki/CLAUDE.md` or adapt into `AGENTS.md` | Vault schema and operator rules |
| `assets/vault-index.md` | `wiki/index.md` | Catalog |
| `assets/vault-log.md` | `wiki/log.md` | Operation log |
| `assets/templates/wiki-summary.md` | `templates/wiki-summary.md` | Summary template |
| `assets/templates/wiki-entity.md` | `templates/wiki-entity.md` | Entity template |
| `assets/templates/wiki-concept.md` | `templates/wiki-concept.md` | Concept template |
| `assets/templates/wiki-synthesis.md` | `templates/wiki-synthesis.md` | Synthesis template |
| `assets/templates/wiki-domain.md` | `templates/wiki-domain.md` | Domain MOC template |
| `assets/codex/hooks/` | `~/.codex/hooks/` | Optional Codex lifecycle hooks |
| `assets/codex/env.example` | shell/Codex launch environment | Optional hook configuration |

---

## Step 4: Initial Memory Files

Create for each agent:

```text
12-{agent}/memory_active.md
12-{agent}/memory_corrections.md
12-{agent}/memory_improvements_backlog.md
12-{agent}/memory_heartbeat.md
12-{agent}/memory_metrics.md
```

Create shared files:

```text
12-shared/memory_decisions.md
12-shared/memory_routing.json
12-shared/memory_projects.md
12-shared/memory_tools.md
12-shared/memory_repos.md
```

See `references/memory-schema.md` for templates and routing guidance.

---

## Step 5: RAW/Git Policy

Recommended `.gitignore`:

```gitignore
# Local RAW cache
raw-sources/pdfs/**/*.pdf
raw-sources/00 RAW INBOX/**/*.pdf
raw-sources/00 RAW INBOX/**/*.docx
raw-sources/00 RAW INBOX/**/*.zip
raw-sources/quarantine/**

# Local operator output
output/memory-operator/**

# Keep these tracked
!raw-sources/converted/**
!raw-sources/provenance/**
```

Git should usually track:

- `wiki/**`
- `raw-sources/converted/**`
- `raw-sources/provenance/**`
- `12-shared/**`
- `12-{agent}/**`
- docs, templates, routing, scripts

Git should usually not track:

- RAW PDF/DOCX/ZIP source binaries;
- temporary conversion output;
- quarantine conflicts unless intentionally documented as markdown.

---

## Step 6: Provenance Manifest

Create:

```text
raw-sources/provenance/raw-local-manifest.jsonl
raw-sources/provenance/README.md
```

Each RAW source should have a JSONL row with:

- `source_id`
- `source_filename`
- `source_type`
- `sha256`
- `size_bytes`
- `local_cache_path`
- `source_availability`
- `archive_status`
- `external_archive_uri`
- `converted_path`
- `wiki_summary_path`
- `import_batch_id`
- `updated_at`

Use this manifest even when RAW files are local-only. It gives Git-tracked markdown a verifiable source identity.

---

## Step 7: Optional Runtime Checks

Before configuring any external runtime, verify the local scripts directly:

```bash
node --check assets/codex/hooks/codex-session-start.js
node --check assets/codex/hooks/codex-post-tool-use.js
node --check assets/codex/hooks/precompact-autosave.js
node assets/codex/hooks/tests/test_precompact_autosave.js
python3 -m py_compile assets/graph/*.py assets/graph/tests/test_graphify_beads.py
python3 assets/graph/tests/test_graphify_beads.py
```

The bundled graph scripts run without required third-party packages. `assets/graph/requirements.txt` is optional and only for external graph inspection tooling.

If your agent supports MCP or scoped filesystem access, configure narrow scopes:

- wiki scope: `wiki/`
- shared memory scope: `12-shared/`
- current agent private scope: `12-{agent}/`

Avoid giving a generic agent broad write access to every private memory folder.

---

## Step 8: Git Sync

Initialize after RAW policy:

```bash
cd {YOUR_VAULT_PATH}
git init
git remote add origin git@github.com:{YOUR_USERNAME}/{YOUR_VAULT_REPO}.git
git add .gitignore wiki 12-shared raw-sources/converted raw-sources/provenance templates
git commit -m "init: obsidian memory wiki system"
git push -u origin main
```

If using Obsidian Git on mobile:

- Pull on startup/open.
- Commit/push after editing.
- Keep attachments and RAW binaries out of Git unless intentionally small and safe.
- If mobile sync breaks, first inspect Obsidian Git auth/logs before changing vault files.

---

## Step 9: First Log Entry

Add to `wiki/log.md`:

```markdown
## YYYY-MM-DDTHH:MM — INIT | System initialization

- Created: wiki/, 12-shared/, 12-{agent}/, raw-sources/, templates/
- Created: schema, index, log, templates
- Policy: Git tracks wiki/converted/provenance/memory; RAW binaries stay local by default
- Notes: Obsidian Memory system initialized.
```

---

## Ready Check

Before the first real ingest:

- `wiki/index.md` exists.
- `wiki/log.md` exists.
- At least one private `12-{agent}/memory_active.md` exists.
- `12-shared/memory_decisions.md` exists.
- RAW binaries are ignored by Git.
- Provenance manifest path exists.

Next step: run a small INGEST or QUERY test before bulk importing a large folder.
