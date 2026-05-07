# obsidian-memory

An explicit-only skill for building and operating an Obsidian-based LLM wiki plus agent memory system.

**The agent is the operator. Obsidian is the IDE. The wiki is the codebase.**

This skill is based on production use of a markdown-first knowledge system: Git stores canonical wiki/memory artifacts, while heavy RAW binaries can stay in a local cache with provenance.

---

## What It Does

**LLM Wiki** (`wiki/`) — an accumulated knowledge base that grows with every source:

- Ingest PDF/article/book/conversation sources into structured summaries.
- Extract durable entities and concepts into linked pages.
- Organize knowledge by domain Maps of Content.
- Create synthesis pages only when they are useful and approved.
- Lint links, frontmatter, index drift, and unprocessed sources.

**Agent Memory** (`12-shared/` + `12-{agent}/`) — operational context that persists across sessions:

- `12-shared/` stores durable shared decisions, routing, and optional scripts.
- `12-codex/`, `12-claude/`, or another `12-{agent}/` store private memory per agent.
- Private context stays isolated; shared decisions are append-only and attributed.

**RAW + Provenance Safety** (`raw-sources/`) — source traceability without bloating Git:

- `raw-sources/converted/` stores converted markdown and is Git-safe.
- `raw-sources/provenance/` stores manifests and source identity.
- `raw-sources/pdfs/` and `raw-sources/00 RAW INBOX/` can stay local and Git-ignored.
- RAW files are tracked by hash, size, path, availability, and converted/wiki links.

---

## Install

```bash
git clone https://github.com/kkonstvol-lab/obsidian-memory ~/.claude/skills/obsidian-memory
```

or install into another agent skills directory:

```bash
git clone https://github.com/kkonstvol-lab/obsidian-memory ~/.agents/skills/obsidian-memory
```

Restart the agent app. The skill will be available as `obsidian-memory` when explicitly invoked or when the user asks to work with an Obsidian vault/wiki/memory system.

---

## Quick Start

1. Follow `references/setup.md`.
2. Copy `assets/vault-CLAUDE.md` to `wiki/CLAUDE.md` or adapt it into `AGENTS.md`.
3. Copy `assets/templates/` to your vault's `templates/`.
4. Create `12-shared/` and one `12-{agent}/` private memory folder per agent.
5. Add a `.gitignore` policy before importing RAW binaries.
6. Start with a small INGEST or QUERY test.

---

## File Structure

```text
obsidian-memory/
├── SKILL.md
├── references/
│   ├── wiki-schema.md
│   ├── memory-schema.md
│   ├── release-safety.md
│   ├── graphify.md
│   ├── codex-hooks.md
│   └── setup.md
└── assets/
    ├── graph/
    ├── codex/
    ├── vault-CLAUDE.md
    ├── vault-index.md
    ├── vault-log.md
    ├── identity.md
    └── templates/
        ├── wiki-summary.md
        ├── wiki-entity.md
        ├── wiki-concept.md
        ├── wiki-synthesis.md
        ├── wiki-domain.md
        ├── drawer.md
        ├── wing-person.md
        └── wing-project.md
```

---

## Optional Extensions

- `references/graphify.md` and `assets/graph/` describe an optional derived knowledge-graph layer. Obsidian markdown remains the source of truth; graph outputs are rebuildable.
- `references/codex-hooks.md` and `assets/codex/` describe optional Codex lifecycle hooks. Treat hooks as runtime-dependent and verify they actually run before relying on automatic behavior.
- `assets/templates/drawer.md`, `wing-person.md`, and `wing-project.md` preserve MemPalace-style memory patterns for vaults that use wings/drawers.

---

## Operations

| Operation | When to use |
|-----------|-------------|
| SETUP | First-time vault initialization |
| INGEST | Add and process a source |
| QUERY | Search and synthesize knowledge |
| LINT | Check wiki health |
| MEMORY | Load or update agent context |
| RELEASE | Verify provenance, RAW guard, and Git safety before push |

---

## Key Principles

1. **Explicit-only:** do not touch the vault unless the user asked for vault/wiki/memory work.
2. **Evidence-first:** wiki answers should cite the pages or converted sources used.
3. **Synthesis by approval:** propose durable synthesis pages when useful; create after approval or direct request.
4. **Private memory isolation:** never mix `12-codex/`, `12-claude/`, or other agent-private context.
5. **Markdown is canonical:** Git should contain wiki, converted markdown, provenance, scripts, docs, and routing.
6. **RAW is usually local:** PDF/DOCX/ZIP files can stay outside Git while still being tracked in provenance.
7. **No performative writes:** write when it improves future retrieval, traceability, or safety, not just because a file was read.

---

## Requirements

- Obsidian.
- An agent environment with skills support.
- Recommended Obsidian plugins: Dataview, Templater, Obsidian Git.
- Optional MCP or filesystem access for direct vault operations.

---

Built from production use. Inspired by Tobi Lutke's LLM Wiki pattern and long-running agent memory systems.
