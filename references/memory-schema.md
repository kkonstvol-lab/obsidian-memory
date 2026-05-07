# Memory Schema — Agent Operational Context

The memory layer stores operating context: what the agent is doing, which decisions are durable, which process errors must not repeat, and which projects/tools matter.

Memory is not the wiki. Wiki pages store knowledge from sources. Memory files store how the agent should operate.

---

## Recommended Roots

```text
vault/
├── 12-shared/
│   ├── memory_decisions.md
│   ├── memory_routing.json
│   ├── memory_projects.md
│   ├── memory_tools.md
│   ├── memory_repos.md
│   └── scripts/
├── 12-codex/
│   ├── memory_active.md
│   ├── memory_corrections.md
│   ├── memory_improvements_backlog.md
│   ├── memory_heartbeat.md
│   └── memory_metrics.md
└── 12-claude/
    ├── memory_active.md
    ├── memory_corrections.md
    ├── memory_improvements_backlog.md
    ├── memory_heartbeat.md
    └── memory_metrics.md
```

Use `12-{agent}/` for each additional agent. Keep agent-private folders strictly separated.

Optional project-local auxiliary memory can live outside the vault or in a project workspace, for example `agent-memory-codex/`. Treat it as a local helper layer, not the canonical private memory, unless the vault's own routing contract says otherwise.

---

## Shared Files

### `12-shared/memory_decisions.md`

Durable decisions that apply across agents and sessions. Append-only unless a decision must be explicitly superseded.

Recommended line format:

```markdown
- YYYY-MM-DD: Decision text. Attribution: user | agent | source. Status: active | superseded.
```

Use this for architecture contracts, routing decisions, Git/RAW policy, and recurring workflow rules.

### `12-shared/memory_routing.json`

Machine-readable routing contract. It should distinguish:

- shared memory files;
- canonical private files per agent;
- optional project-local auxiliary files;
- wiki roots;
- RAW/provenance roots.

For multi-agent vaults, avoid one ambiguous `private_files` bucket. Use explicit categories such as `vault_private_files` and `project_private_files`.

### `12-shared/memory_projects.md`

Project registry.

```markdown
## {Project Name}
- Status: active | planning | paused | completed
- Goal: one line
- Canonical files: [[...]]
- Repo: URL or path
- Last updated: YYYY-MM-DD
```

### `12-shared/memory_tools.md`

Tools, plugins, MCP servers, automations, and verified command paths.

### `12-shared/memory_repos.md`

Repos and codebases the agents operate.

---

## Private Files

### `memory_active.md`

Load order: first private file.

Purpose: current focus, immediate constraints, blockers, and fresh operational context.

Keep it compact. It is a live snapshot, not a journal.

```markdown
---
updated: YYYY-MM-DD
type: memory-active
agent: codex
---

# Active Memory

## Current Focus
- ...

## Blockers
- none

## Recently Done
- YYYY-MM-DD: ...
```

### `memory_corrections.md`

Load before non-trivial tasks. Prepend-only log of logic/process mistakes, not style preferences.

```markdown
## YYYY-MM-DD — Short title
- Error: what went wrong
- Context: task/files
- Root cause: skipped assumption, wrong routing, unsafe operation, etc.
- Fix: concrete future behavior
```

### `memory_improvements_backlog.md`

Improvement ideas for the agent, skill, scripts, or process.

Use sections such as Active, In Progress, Done.

```markdown
- [ ] Idea — Impact: H/M/L | Effort: H/M/L | Source: user|heartbeat|session | Added: YYYY-MM-DD
```

### `memory_heartbeat.md`

Periodic self-check log. Useful for detecting recurring mistakes and stale improvement ideas.

### `memory_metrics.md`

Weekly or periodic snapshot of corrections, improvements shipped, verification failures, and operator quality.

---

## Load Order

At the start of explicit MEMORY work:

1. Determine `agent_id`.
2. Load `12-{agent}/memory_active.md`.
3. Load `12-shared/memory_decisions.md`.
4. Load recent relevant entries from `12-{agent}/memory_corrections.md`.
5. Load route-specific shared/project files.
6. Load at most two extra related files unless the user asked for a broad audit.

Avoid bulk-loading the entire vault unless the task is explicitly an audit or migration.

---

## Write Routing

| Content | Destination |
|---------|-------------|
| Current focus, blockers, session context | `12-{agent}/memory_active.md` |
| Process mistake by one agent | `12-{agent}/memory_corrections.md` |
| Agent improvement idea | `12-{agent}/memory_improvements_backlog.md` |
| Durable shared policy | `12-shared/memory_decisions.md` |
| Project registry | `12-shared/memory_projects.md` |
| Tool or command contract | `12-shared/memory_tools.md` |
| Knowledge from source material | `wiki/`, not memory |

---

## Routing JSON Pattern

Example shape:

```json
{
  "agents": {
    "codex": {
      "vault_private_root": "12-codex",
      "project_private_root": "agent-memory-codex",
      "vault_private_files": [
        "memory_active.md",
        "memory_corrections.md",
        "memory_improvements_backlog.md",
        "memory_heartbeat.md",
        "memory_metrics.md"
      ],
      "project_private_files": [
        "memory_introspection.md",
        "memory_daily/",
        "HEARTBEAT.md"
      ]
    }
  },
  "shared_root": "12-shared",
  "wiki_root": "wiki",
  "raw_roots": {
    "converted": "raw-sources/converted",
    "provenance": "raw-sources/provenance",
    "local_cache": ["raw-sources/pdfs", "raw-sources/00 RAW INBOX"]
  }
}
```

The exact schema can differ, but the categories must be explicit enough that scripts do not accidentally resolve Codex paths into Claude memory or vice versa.

---

## Principles

1. **Private means private:** never blend one agent's operational context into another agent's folder.
2. **Shared means durable:** shared memory should contain stable rules, not transient scratch notes.
3. **Append with attribution:** shared decisions need date and source.
4. **Do not duplicate wiki knowledge:** summarize source-derived knowledge in `wiki/`, not in `memory_active.md`.
5. **Load narrowly:** memory improves context only when it is relevant.
6. **No performative writes:** write memory when it makes future work safer, faster, or more accurate.
