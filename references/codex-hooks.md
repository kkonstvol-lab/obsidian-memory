# Codex Hooks — Obsidian Memory Extension

Codex hooks can make Obsidian memory visible during the Codex lifecycle:

- `SessionStart` can load bounded memory context at startup.
- `PostToolUse` can remind the agent to update memory after `git push`.
- `PreCompact` can write a non-canonical draft before compaction/session end.

Hooks are runtime-dependent. Do not claim live automatic behavior until the current Codex runtime actually runs the hooks and `hooks-status` or equivalent smoke checks confirm it.

---

## Files

Skill assets:

- `assets/codex/hooks/codex-session-start.js`
- `assets/codex/hooks/codex-post-tool-use.js`
- `assets/codex/hooks/precompact-autosave.js`
- `assets/codex/hooks/tests/test_precompact_autosave.js`
- `assets/codex/hooks/hooks.json.template`
- `assets/codex/env.example`

Installed locations normally look like:

- `~/.codex/hooks/codex-session-start.js`
- `~/.codex/hooks/codex-post-tool-use.js`
- `~/.codex/hooks/precompact-autosave.js`
- `~/.codex/hooks.json`
- `~/.codex/obsidian-memory.json` (optional config)

---

## Configuration

Hooks resolve vault settings in this order:

1. Environment variables:
   - `OBSIDIAN_VAULT_PATH`
   - `OBSIDIAN_AGENT_ID`
   - `OBSIDIAN_PRIVATE_ROOT`
   - `OBSIDIAN_SHARED_ROOT`
   - `OBSIDIAN_CONTEXT_MAX_CHARS`
   - `OBSIDIAN_DRAFT_ROOT`
2. Optional config file: `~/.codex/obsidian-memory.json`
3. Defaults:
   - `agentId`: `codex`
   - private root: `12-{agentId}`
   - shared root: `12-shared`
   - fallback single-agent root: `memory/`

Example config:

```json
{
  "vaultPath": "/absolute/path/to/obsidian-vault",
  "agentId": "codex"
}
```

---

## SessionStart

The startup hook:

- should match `startup`, not `resume`;
- reads bounded snippets from private and shared memory;
- detects current Git repo, branch, and remote when available;
- writes plain text to stdout for additional context;
- prints setup instructions if no vault path is configured.

It must not mutate canonical memory.

---

## PostToolUse

The post-tool hook:

- supports current Codex Desktop tool names: `functions.exec_command` and `exec_command`;
- keeps a `Bash` matcher fallback for older runtimes;
- inspects `command` or `cmd`;
- responds only to `git push`;
- returns `hookSpecificOutput.hookEventName = "PostToolUse"` with additional context.

It only reminds the agent to update memory. It does not edit memory files.

---

## PreCompact Autosave

The autosave hook writes a draft only. It never edits `wiki/`, `wiki/wings/`, `raw-sources/`, shared memory, or canonical memory.

Default draft path:

- multi-agent: `{vault}/12-{agent_id}/session-drafts/`
- override: `OBSIDIAN_DRAFT_ROOT`

The draft is marked:

- `type: drawer-draft`
- `status: draft`
- `canonical: false`

It remains non-canonical until a human/session-summary review copies durable facts into memory.

---

## Manual Fallback

When hooks are not live, use local operator commands instead:

```bash
python3 12-shared/scripts/memory_operator.py session-start
python3 12-shared/scripts/memory_operator.py session-end --note "short summary"
python3 12-shared/scripts/memory_operator.py hooks-status
```

If `hooks-status` reports fallback-only, not-wired, matcher drift, or no recent markers, use manual fallback instead of assuming hidden hooks are active.

---

## Manual Tests

Check JavaScript syntax:

```bash
node --check assets/codex/hooks/codex-session-start.js
node --check assets/codex/hooks/codex-post-tool-use.js
node --check assets/codex/hooks/precompact-autosave.js
node assets/codex/hooks/tests/test_precompact_autosave.js
```

Test startup:

```bash
export OBSIDIAN_VAULT_PATH="/absolute/path/to/obsidian-vault"
echo '{"source":"startup","cwd":"/path/to/repo","hook_event_name":"SessionStart"}' \
  | node assets/codex/hooks/codex-session-start.js
```

Test resume silence:

```bash
echo '{"source":"resume","cwd":"/path/to/repo","hook_event_name":"SessionStart"}' \
  | node assets/codex/hooks/codex-session-start.js
```

Test push reminder with current Codex Desktop shape:

```bash
echo '{"tool_name":"functions.exec_command","tool_input":{"cmd":"git push origin main"},"cwd":"/path/to/repo","hook_event_name":"PostToolUse"}' \
  | node assets/codex/hooks/codex-post-tool-use.js
```

Test old Bash fallback:

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"git push origin main"},"cwd":"/path/to/repo","hook_event_name":"PostToolUse"}' \
  | node assets/codex/hooks/codex-post-tool-use.js
```

Test non-push silence:

```bash
echo '{"tool_name":"functions.exec_command","tool_input":{"cmd":"git status"},"cwd":"/path/to/repo","hook_event_name":"PostToolUse"}' \
  | node assets/codex/hooks/codex-post-tool-use.js
```

Test precompact autosave:

```bash
export OBSIDIAN_VAULT_PATH="/absolute/path/to/obsidian-vault"
echo '{"agent_id":"codex","session_id":"demo","user_goal":"test autosave","important_decisions":["Markdown remains canonical"],"trigger":"precompact"}' \
  | node assets/codex/hooks/precompact-autosave.js
```

---

## Safety Rules

- Do not store secrets in Obsidian memory.
- Keep `memory_in_progress.md` short and operational.
- Treat `memory_active.md` as a dashboard, not a journal.
- In multi-agent setups, write private operational files only in the current agent's private root.
- Append to shared memory only for durable world-level facts and include source attribution.
- Treat autosave drafts as safety nets, not canonical memory.
