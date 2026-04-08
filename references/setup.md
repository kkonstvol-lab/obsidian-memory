# Setup Guide — First-Time Installation

Step-by-step guide to deploy the obsidian-memory system in a new Obsidian vault.

---

## Step 1: Obsidian Plugins

Install these in Obsidian Settings → Community Plugins:

### Required

**Dataview** — Query your wiki by frontmatter fields. Powers the auto-updating tables in index.md.
- After install: Enable JavaScript queries in Dataview settings

**Templater** — Advanced templates with date variables and logic. Powers the `{{date}}` and `{{title}}` placeholders in page templates.
- After install: Set "Template folder location" to your vault's `templates/` folder

### Recommended

**obsidian-git** — Auto-commit and sync vault to GitHub. Essential for multi-device setups (laptop + phone + VPS).
- Settings: Auto commit every 30 min, Auto pull every 60 min
- Merge strategy: `ort` (handles divergent branches cleanly)

### Optional

**Tag Wrangler** — Rename, merge, and manage tags in bulk. Useful when you want to reorganize domain tags.

---

## Step 2: Vault Folder Structure

Create these folders in your vault:

```
vault/
├── wiki/
│   ├── summaries/
│   ├── entities/
│   ├── concepts/
│   ├── synthesis/
│   └── domains/
├── memory/
│   └── projects/
├── raw-sources/
│   ├── pdfs/
│   ├── articles/
│   └── converted/
└── templates/
```

---

## Step 3: Drop-in Files

Copy from this skill's `assets/` folder to your vault:

| From (assets/) | To (vault/) | Purpose |
|----------------|-------------|---------|
| `vault-CLAUDE.md` | `wiki/CLAUDE.md` | Schema — tells Claude the rules |
| `vault-index.md` | `wiki/index.md` | Catalog of all wiki pages |
| `vault-log.md` | `wiki/log.md` | Operation log |
| `templates/wiki-summary.md` | `templates/wiki-summary.md` | Summary page template |
| `templates/wiki-entity.md` | `templates/wiki-entity.md` | Entity page template |
| `templates/wiki-concept.md` | `templates/wiki-concept.md` | Concept page template |
| `templates/wiki-synthesis.md` | `templates/wiki-synthesis.md` | Synthesis page template |
| `templates/wiki-domain.md` | `templates/wiki-domain.md` | Domain MOC template |

Then create initial memory files:

```
memory/memory_active.md
memory/memory_decisions.md
memory/memory_projects.md
memory/memory_tools.md
memory/memory_clients.md    (optional — for client work)
memory/memory_repos.md      (optional — for engineering work)
```

Use the file type templates from `references/memory-schema.md` as starting content.

---

## Step 4: MCP Configuration (optional but recommended)

MCP (Model Context Protocol) servers allow Claude Code to read and write files in your vault directly. Use `@bitbonsai/mcpvault` for scoped access to specific vault folders.

### Install mcpvault

```bash
npm install -g @bitbonsai/mcpvault
# or use npx (no global install needed)
```

### Configure in claude-workspace/.mcp.json

```json
{
  "mcpServers": {
    "obsidian-wiki": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "--yes",
        "@bitbonsai/mcpvault@latest",
        "{YOUR_VAULT_PATH}/wiki"
      ],
      "env": {}
    },
    "obsidian-memory": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "--yes",
        "@bitbonsai/mcpvault@latest",
        "{YOUR_VAULT_PATH}/memory"
      ],
      "env": {}
    }
  }
}
```

Replace `{YOUR_VAULT_PATH}` with your absolute vault path.

**Two separate MCP instances:**
- `obsidian-wiki` → scoped to `wiki/` — knowledge base access
- `obsidian-memory` → scoped to `memory/` — operational context access

This keeps the two systems cleanly separated in Claude's tool calls.

### Windows note

On Windows, if `npx` is not in PATH, use the full path:
```
"command": "C:\\path\\to\\node\\npx.cmd"
```

---

## Step 5: Git Sync (optional — for multi-device)

To sync your vault across devices (laptop + phone + VPS):

```bash
cd {YOUR_VAULT_PATH}
git init
git remote add origin git@github.com:{YOUR_USERNAME}/{YOUR_VAULT_REPO}.git
git add .
git commit -m "init: obsidian vault with LLM wiki + memory system"
git push -u origin main
```

Install obsidian-git plugin on each device and configure pull on startup.

**Note:** Add sensitive paths to `.gitignore` if needed. The vault itself is usually safe to sync publicly if you don't store credentials in it.

---

## Step 6: Register Vault Path in Claude's Memory

**This step is critical.** Without it, Claude won't know where your vault is in new sessions and will ask every time.

### 6a. Global fallback — `~/.claude/CLAUDE.md`

Create this file so Claude knows your vault path in any session, regardless of working directory:

**macOS/Linux:** `~/.claude/CLAUDE.md`
**Windows:** `C:\Users\{YOU}\.claude\CLAUDE.md`

```markdown
# Global Claude Code Instructions

## Obsidian Vault

**Path:** `/path/to/your/obsidian-vault/`

Key folders:
- `inbox/` — incoming files (or `00-inbox/` — whatever you named it)
- `wiki/` — LLM knowledge base (Claude manages)
- `memory/` — agent operational memory
- `raw-sources/` — original sources (pdfs/, articles/, converted/)
- `templates/` — page templates
```

Replace `/path/to/your/obsidian-vault/` with your actual vault path.

### 6b. Project-level infrastructure file

If you work from a specific Claude Code workspace directory, create an `infrastructure.md` in that project's native memory folder. This gets auto-loaded as system context in every session.

**Claude Code project memory location:**
- macOS/Linux: `~/.claude/projects/{project-slug}/memory/infrastructure.md`
- Windows: `C:\Users\{YOU}\.claude\projects\{project-slug}\memory\infrastructure.md`

The `{project-slug}` matches your workspace path with slashes replaced by dashes.

```markdown
# Infrastructure — Key Paths

## Obsidian Vault

**Vault root:** `/path/to/your/obsidian-vault/`

Key folders:
- `inbox/` — incoming files for processing
- `wiki/` — LLM Wiki (knowledge, Claude manages)
- `memory/` — agent operational context
- `raw-sources/` — originals (pdfs/, articles/, converted/)
- `templates/` — page templates

**Git remote:** `git@github.com:{username}/{vault-repo}.git`
```

Then add a line to that project's `MEMORY.md` index:
```markdown
- [Infrastructure](infrastructure.md) — vault path, key folders, git remote
```

**Why both files?** The global `CLAUDE.md` covers any session. The project `infrastructure.md` gets auto-loaded with richer context when working from your main workspace.

---

## Step 7: First Log Entry

Write the initialization entry in `wiki/log.md`:

```markdown
## YYYY-MM-DDTHH:MM — INIT | System initialization

- Created: wiki/, memory/, raw-sources/ structure
- Created: wiki/CLAUDE.md, wiki/index.md, wiki/log.md
- Created: templates/ (5 wiki templates)
- Notes: LLM Wiki + Agent Memory system deployed.
```

---

## You're Ready

Your vault now has:
- ✅ Wiki layer for accumulated knowledge (INGEST, QUERY, LINT)
- ✅ Memory layer for agent operational context (load order, routing)
- ✅ Templates for all 5 wiki page types
- ✅ Schema file telling Claude the rules (`wiki/CLAUDE.md`)
- ✅ Operation log tracking everything that happens
- ✅ Vault path registered in Claude's memory — no more "where is your vault?" in new sessions

**Next step:** Start your first INGEST. Pick a book, article, or PDF you've read recently and process it into the wiki. See the INGEST workflow in SKILL.md.
