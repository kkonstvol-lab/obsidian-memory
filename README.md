# obsidian-memory

A Claude Code skill for building and maintaining a persistent knowledge + memory system in Obsidian — based on the LLM Wiki pattern (Karpathy) and Robby Palace (MemPalace-inspired wings/halls/drawers).

**Claude is the programmer. Obsidian is the IDE. The wiki is the codebase.**

---

## What it does

Enables Claude to operate two persistent systems inside your Obsidian vault:

**LLM Wiki** (`wiki/`) — an accumulated knowledge base that grows with every source you process:
- Ingest any source (PDF, article, book, conversation) → structured summary page
- Extract entities and concepts → linked pages with wikilinks
- Organize by domain → thematic Maps of Content
- Health-check weekly with LINT → broken links, orphans, stale content

**Robby Palace** (`wiki/wings/` + `wiki/drawers/`) — persistent per-person and per-project memory:
- Create a wing for any person or project → 5 structured halls: Facts, Events, Discoveries, Preferences, Advice/Decisions
- Every session creates an immutable drawer (session log) → COMPILE updates wings automatically
- Provenance: every fact in a wing links back to its source drawer
- Tunnels: cross-wing connections via wikilinks, discoverable by LINT

**Agent Memory** (`memory/`) — operational context that persists across sessions:
- Current focus, active projects, global decisions
- 4-layer loading model: L0 identity → L1 critical → L2 wings → L3 deep search
- Compounds over time: each session makes the next one faster

**Self-Improvement Loop** (`memory/memory_corrections.md` + 3 files) — compounding agent quality:
- Log every logical/process mistake → detect patterns over time
- Track improvement ideas → ship them into skills
- Daily HEARTBEAT cron at 10:00 — reads corrections, surfaces patterns, stays calibrated

---

## Install

```bash
git clone https://github.com/kkonstvol-lab/obsidian-memory ~/.claude/skills/obsidian-memory
```

Restart Claude Code. The skill will be available as `/obsidian-memory`.

---

## Quick Start

1. **Set up your vault** — follow `references/setup.md`
2. **Drop in the schema** — copy `assets/vault-CLAUDE.md` → `wiki/CLAUDE.md` in your vault
3. **Copy templates** — copy `assets/templates/` → `templates/` in your vault
4. **Set up identity** — copy `assets/identity.md` → `identity.md` in your vault root, fill in name and role
5. **First ingest** — say "ingest [source name] into my wiki"
6. **First session summary** — at end of session, run `/session-summary` → creates drawer → run `/compile` → updates wings

---

## File Structure

```
obsidian-memory/
├── SKILL.md                     # Main skill — trigger + all operations
├── references/
│   ├── wiki-schema.md           # Full wiki schema: page types, frontmatter, tags, workflows
│   ├── memory-schema.md         # Memory layer: file types, load order, routing, principles
│   └── setup.md                 # Step-by-step installation guide
└── assets/
    ├── vault-CLAUDE.md          # Drop-in schema for wiki/CLAUDE.md
    ├── vault-index.md           # Template for wiki/index.md (with Wings + Drawers sections)
    ├── vault-log.md             # Template for wiki/log.md
    ├── identity.md              # Template for vault root identity.md (L0 context)
    └── templates/
        ├── wiki-summary.md      # Source digest template
        ├── wiki-entity.md       # Person/company/tool template
        ├── wiki-concept.md      # Methodology/framework template
        ├── wiki-synthesis.md    # Cross-source analysis template
        ├── wiki-domain.md       # Map of Content template
        ├── wing-person.md       # Person wing — 5 halls (Facts/Events/Discoveries/Preferences/Advice)
        ├── wing-project.md      # Project wing — 5 halls (Facts/Events/Discoveries/Preferences/Decisions)
        └── drawer.md            # Immutable session log template
```

---

## Operations

| Command | When to use |
|---------|-------------|
| SETUP | First-time vault initialization |
| INGEST | Add a source to the wiki |
| QUERY | Search and synthesize knowledge |
| LINT | Weekly health check (wiki + Palace checks) |
| MEMORY | Load agent context at session start |
| COMPILE | After each session — process drawers into wings |
| WING | Create a person or project wing profile |

---

## Vault Structure

After setup, your vault will have:

```
vault/
├── identity.md          ← L0 context, loaded every session (~100 tokens)
├── wiki/
│   ├── CLAUDE.md        ← schema (from assets/vault-CLAUDE.md)
│   ├── index.md         ← catalog of all pages
│   ├── log.md           ← operation log
│   ├── summaries/       ← one file per source ingested
│   ├── entities/        ← people, companies, tools (what they ARE)
│   ├── concepts/        ← frameworks, methodologies
│   ├── synthesis/       ← cross-source analysis
│   ├── domains/         ← thematic hubs (Maps of Content)
│   ├── wings/           ← Robby Palace: per-person and per-project profiles
│   │   ├── person-{slug}.md   ← 5 halls: Facts / Events / Discoveries / Preferences / Advice
│   │   └── project-{slug}.md  ← 5 halls: Facts / Events / Discoveries / Preferences / Decisions
│   └── drawers/         ← immutable session logs (compiled: true/false)
│       └── drawer-YYYY-MM-DD-{slug}.md
├── output/              ← regeneratable artifacts (dashboards, reports)
│   ├── dashboards/
│   └── reports/
├── memory/
│   ├── memory_active.md
│   ├── memory_decisions.md
│   ├── memory_projects.md
│   ├── memory_tools.md
│   ├── memory_corrections.md     ← self-improvement: logical/process errors
│   ├── memory_improvements_backlog.md  ← improvement ideas (Active/Done)
│   ├── memory_metrics.md         ← weekly snapshot
│   ├── memory_heartbeat.md       ← daily self-check log (cron 10:00)
│   └── projects/{name}/
└── raw-sources/
    ├── pdfs/
    ├── articles/
    └── converted/
```

---

## Key Principles

1. **Writes required** — any session that reads must write something back
2. **Corrections > rules** — 151 concrete edits beat 39K chars of abstract instructions
3. **Separation** — wiki = knowledge, memory = operational context, never duplicate
4. **Quality > quantity** — 5 well-linked pages beat 20 isolated ones
5. **Compound context** — every session makes the next one faster
6. **Self-improvement loop** — log errors in `memory_corrections.md`, run daily HEARTBEAT to detect patterns, ship fixes into skills
7. **Drawers are immutable** — session logs are never edited after creation; they are source of truth for the past
8. **Entity vs Wing** — entity = what something IS; wing = your relationship with it. Don't duplicate
9. **Compile loop** — every significant session: create drawer → COMPILE → wings updated

## Self-Improvement Loop

The memory layer includes a 4-file self-improvement system:

| File | Purpose | Who writes |
|------|---------|-----------|
| `memory_corrections.md` | Logical/process errors (NOT style/tone) | User correction + session-summary |
| `memory_improvements_backlog.md` | Improvement ideas (Active/Done) | HEARTBEAT + session-summary |
| `memory_metrics.md` | Weekly snapshot (errors, improvements shipped) | HEARTBEAT every Sunday |
| `memory_heartbeat.md` | Daily self-check log | HEARTBEAT cron at 10:00 local time |

**Distinct from style corrections:** `memory_corrections.md` captures *what the agent did wrong procedurally* (skipped a step, missed a file). Style and tone edits belong in a separate `voice-corrections.md` (see `references/memory-schema.md` principle #2).

**HEARTBEAT cron:** create via `mcp__scheduled-tasks__create_scheduled_task` with `cronExpression: "0 10 * * *"`. The cron reads corrections, detects repeating patterns (2+ same root cause), flags stale backlog items, and prepends a daily entry.

---

## Requirements

- Claude Code with skills support
- Obsidian with Dataview + Templater plugins
- Optional: obsidian-git (for multi-device sync), @bitbonsai/mcpvault (for MCP access)

---

Built from production use. Inspired by Tobi Lutke/Karpathy LLM Wiki pattern, MemPalace (Milla Jovovich), and witcheer's ALIVE memory system.
