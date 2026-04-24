# Memory Schema — Agent Operational Context

The `memory/` layer is the agent's operational brain — what it knows about the current work context, decisions made, projects in flight, and tools available.

**Key distinction:** memory ≠ wiki. Memory is session state and operational context. Wiki is accumulated knowledge from sources. Never duplicate content between them.

---

## File Types

### memory_active.md — Current Focus
**Load order: #1, always**

The "what matters right now" file. Maximum 15 lines. Not a journal — a live snapshot.

```markdown
---
updated: YYYY-MM-DDTHH:MM
type: memory-active
---

# Active Memory

## Current Focus
[1-3 lines: what is being worked on right now]

## Infrastructure Status
- [tool/system]: [status]

## Blockers
- [blocker if any, or "none"]

## This Week
- [ ] task 1
- [ ] task 2
```

**Rule:** When this file exceeds 20 lines, trim it. Old focus goes to memory_projects or archive.

---

### memory_in_progress.md — Active Work State
**Load order: after `memory_active.md`, when available**

The "what is actively being worked on" file. Use it for tasks, current repos, blockers, and next actions that should survive across sessions.

Single-agent path: `memory/memory_in_progress.md`.

Multi-agent path: `{private}/memory_in_progress.md`, for example `12-codex/memory_in_progress.md` or `12-claude/memory_in_progress.md`.

```markdown
---
agent: codex
type: memory-in-progress
updated: YYYY-MM-DD
---

# Memory In Progress — Codex

## Active Tasks

### TASK-ID — short title
- repo:
- branch:
- status:
- context:
- next_action:
- last_update:
- source:
- link:

## Current Repos

## Blocked

## Next Actions

## Recently Done
```

**Rule:** Keep this operational, not archival. Completed work should move to `Recently Done`, `memory_projects.md`, or a session drawer.

---

### memory_decisions.md — Global Conventions
**Load order: #2, always**

Architectural and workflow decisions that apply across all work. Things that would take time to re-derive.

```markdown
## Decisions

- Decision description [confidence:high|medium|low] [source:manual|doc|tool|research]
- Another decision...
```

Format each decision as a single line. If a decision is reversed, update the existing line — don't add a new one.

---

### memory_projects.md — Project Registry

Active and planned projects. One section per project.

```markdown
## {Project Name}
- Status: active | planning | paused | completed
- Stack: [technologies]
- Goal: [one line]
- Repo: {repo-link}
- Last updated: YYYY-MM-DD
```

---

### memory_tools.md — Tools and Infrastructure

Every tool, plugin, MCP server, IDE setting that has been set up and verified.

```markdown
## {Tool Name}
- Version: x.x.x
- Status: active | broken | deprecated
- Purpose: [what it does]
- Config: [where config lives]
- Notes: [anything non-obvious]
```

---

### memory_clients.md — Clients and Contacts

For agency/freelance work. One section per client.

```markdown
## {Client Name}
- Status: active | prospect | inactive
- Contact: [name, channel]
- Key context: [what they need, preferences, constraints]
- Projects: [[project-name]]
```

---

### memory_repos.md — Repositories and Codebases

Repos that have been worked on or studied.

```markdown
## {repo-name}
- URL: https://github.com/...
- Purpose: [what it does]
- Status: active | reference | archived
- Key files: [entry points, config, schema]
- Notes: [architecture decisions, gotchas]
```

---

### projects/{name}/ — Per-Project Deep Context

For active projects, create a subdirectory with detailed files:
- `context.md` — product/market/positioning context (read by all project-related agents)
- `decisions.md` — project-specific technical decisions
- `tasks.md` — current task list with status
- `log.md` — project operation log

---

## Self-Improvement Loop (4 files)

Layer for compounding agent quality. Distinct from `voice-corrections.md` (which handles style/tone only).

### memory_corrections.md — Logical/Process Errors
**Load order: #3 — before non-trivial tasks (last 5 entries)**

Prepend-only log of process/logic mistakes the agent made. NOT for style/tone (those go to `voice-corrections.md`).

```markdown
## YYYY-MM-DD — {short title}
- **Error:** what went wrong
- **Context:** task / file / skill
- **Root cause:** which principle was violated, which step skipped
- **Fix:** how to do it correctly next time
- **Rule extracted:** → `feedback_*.md` if generalizable, else N/A
```

Sources: explicit user correction, session-summary self-detection, HEARTBEAT pattern detection.

### memory_improvements_backlog.md — Improvement Ideas

Ideas for improving the agent, skills, memory, or workflow. Three sections: Active / In Progress / Done.

```markdown
- [ ] {Idea} — Impact: H/M/L | Effort: H/M/L | Source: {heartbeat|user|session-summary} | Added: YYYY-MM-DD
```

Done items archived weekly to `archive/`.

### memory_metrics.md — Weekly Snapshot

Updated by HEARTBEAT every Sunday. Single growing table.

| Week | Sessions | Corrections | Backlog done | Error patterns | Improvements shipped |

### memory_heartbeat.md — Daily Self-Check Log

Updated daily at 10:00 MSK by `heartbeat-self-check` cron (`mcp__scheduled-tasks`). Prepend-only.

```markdown
## YYYY-MM-DD
- **Read:** memory_active, corrections (10), backlog active, insights
- **Patterns in corrections:** {repeating? clean slate?}
- **Stale backlog:** {items idle 7+ days}
- **New ideas:** {from prior day's work}
- **Will try today:** {1-2 concrete behavior changes}
- **Metrics update:** N/A or "weekly snapshot updated"
```

**The "session with no writes is a failure" rule applies:** if nothing to record, write "clean slate, no new patterns".

---

## Load Order

At the start of any agent session, load memory files in this order:

```
0) identity.md               ← L0 context — ALWAYS first (~100 tokens, vault root)
1) memory_active.md          ← ALWAYS (current focus, blockers)
2) memory_in_progress.md     ← if available (active tasks and next actions)
3) memory_decisions.md       ← ALWAYS (global conventions)
4) memory_corrections.md     ← BEFORE non-trivial tasks (last 5 entries)
5) domain memory by context  ← route by session keywords (see Routing)
6) project-specific files    ← if working on a specific project
7) max 2 related domains     ← by trigger keywords
8) wiki/wings/relevant-*.md  ← L2: if working with a specific person or project
```

**4-layer context loading model:**

| Layer | Size | Files | When |
|-------|------|-------|------|
| L0 Identity | ~100 tokens | `identity.md` (vault root) | Every session |
| L1 Critical | ~500-1000 tokens | `memory_active.md` + `memory_in_progress.md` + `memory_decisions.md` | Every session |
| L2 Wings | ~200 tokens each | `wiki/wings/person-*.md`, `project-*.md` | On-demand by context |
| L3 Deep | unlimited | `wiki/drawers/*`, `raw-sources/*` | Explicit search |

Loading too much memory = slow, unfocused sessions. Load the minimum needed.

---

## Routing

Context-aware routing: match session keywords to memory files.

**routing.json schema:**

```json
{
  "routes": {
    "coding": {
      "primary": ["memory_decisions.md", "memory_tools.md", "memory_repos.md"],
      "relation_triggers": {
        "to_projects": "project_triggers",
        "to_clients": "client_triggers"
      }
    },
    "project-mgmt": {
      "primary": ["memory_decisions.md", "memory_projects.md", "memory_clients.md"],
      "relation_triggers": {
        "to_repos": "repo_triggers",
        "to_tools": "tool_triggers"
      }
    },
    "research": {
      "primary": ["memory_decisions.md", "memory_repos.md"],
      "relation_triggers": {
        "to_tools": "tool_triggers"
      }
    },
    "wing-context": {
      "primary": ["memory_decisions.md", "memory_clients.md"],
      "relation_triggers": {
        "to_wings": "wing_triggers"
      }
    },
    "default": {
      "primary": ["memory_decisions.md"],
      "relation_triggers": {
        "to_projects": "project_triggers",
        "to_tools": "tool_triggers"
      }
    }
  },
  "relations": {
    "to_projects": ["memory_projects.md"],
    "to_clients": ["memory_clients.md"],
    "to_repos": ["memory_repos.md"],
    "to_tools": ["memory_tools.md"],
    "to_wings": ["wiki/wings/"]
  },
  "trigger_sets": {
    "project_triggers": ["project", "deadline", "milestone", "status", "MVP"],
    "client_triggers": ["client", "customer", "requirements", "brief"],
    "repo_triggers": ["github", "repo", "codebase", "git", "branch", "PR", "commit"],
    "tool_triggers": ["MCP", "plugin", "obsidian", "claude", "IDE", "npm", "tool"],
    "wing_triggers": ["person", "client", "contact", "profile", "wing", "who is", "tell me about"]
  }
}
```

Add your own routes and trigger sets as your context grows.

---

## Key Principles

These are distilled from production agent systems (witcheer, ALIVE, gstack):

### 1. A session with no writes is a failure
Any session that reads from memory or wiki must write something back — update log, record a decision, capture a finding. If nothing was worth writing, the session was passive, not active.

### 2. Corrections > abstract rules
151 concrete examples beat 39,000 characters of abstract instructions. When you edit an AI draft, log what changed and why. Save these corrections in a `voice-corrections.md` file. All future drafts read this file before generating.

```markdown
# Voice Corrections

## YYYY-MM-DD
- Changed: [what the AI wrote]
- To: [what you rewrote it as]
- Why: [the principle behind the change]
```

### 3. Session idle timeout
Set Claude Code session idle timeout to 60 minutes, not the default 1440. Long sessions accumulate stale context. Short sessions stay focused.

### 4. Source diversity
In research prompts, explicitly specify source order. Without instructions, models default to the same sources for everything (e.g., Reddit for all research). Specify: "Check academic papers first, then industry reports, then community forums."

### 5. Compounding context
The memory system compounds over time. Each session that writes high-quality notes makes the next session faster. The value is not in any single session — it's in the accumulation.

### 6. Memory ≠ journal
memory_active.md is not a log. It's a dashboard. Maximum 15 lines. Old focus goes to projects/ or archive. If you find yourself appending, you're journaling — trim instead.

---

## Maintenance

Weekly:
- Review `memory_active.md` — trim anything that's no longer active
- Scan `memory_decisions.md` — are any decisions outdated?
- Archive completed projects from `memory_projects.md` to `archive/`
- Run LINT on wiki (see wiki-schema.md)

Monthly:
- Review all memory files for accuracy
- Prune stale tool entries from `memory_tools.md`
- Update `routing.json` if new domains have emerged
