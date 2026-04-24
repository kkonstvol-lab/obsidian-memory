# Codex Hooks — Obsidian Memory Extension

Codex hooks can make the Obsidian memory layer part of the Codex lifecycle:

- `SessionStart` loads current memory into Codex context.
- `PostToolUse` reminds Codex to update memory after publishing work with `git push`.

This extension is Obsidian-first. It does not depend on GitHub Issues.

## Runtime Status

Codex hooks are experimental. The official Codex hooks documentation currently says Windows support is temporarily disabled.

Use this reference to install and test the infrastructure. Only claim live automatic behavior after verifying that your Codex runtime actually runs hooks.

## Files

Skill assets:

- `assets/codex/hooks/codex-session-start.js`
- `assets/codex/hooks/codex-post-tool-use.js`
- `assets/codex/hooks/hooks.json.template`
- `assets/codex/memory_in_progress.md`
- `assets/codex/env.example`

Installed locations:

- `~/.codex/hooks/codex-session-start.js`
- `~/.codex/hooks/codex-post-tool-use.js`
- `~/.codex/hooks.json`
- `~/.codex/obsidian-memory.json` (optional config)

## Configuration

The hooks resolve vault settings in this order:

1. Environment variables:
   - `OBSIDIAN_VAULT_PATH`
   - `OBSIDIAN_AGENT_ID`
   - `OBSIDIAN_PRIVATE_ROOT`
   - `OBSIDIAN_SHARED_ROOT`
   - `OBSIDIAN_CONTEXT_MAX_CHARS`
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

## SessionStart

The startup hook:

- matches `startup`, not `resume`;
- reads bounded snippets from:
  - `memory_active.md`
  - `memory_in_progress.md`
  - recent sections of `memory_corrections.md`
  - relevant excerpts from `memory_repos.md`, `memory_tools.md`, and `memory_decisions.md`
- detects current git root, branch, and remote when available;
- writes plain text to stdout, which Codex adds as extra developer context.

If no vault path is configured, it prints a diagnostic context block explaining how to set `OBSIDIAN_VAULT_PATH` or `~/.codex/obsidian-memory.json`.

## PostToolUse

The post-tool hook:

- matches `Bash`;
- inspects `tool_input.command`;
- responds only to `git push`;
- returns JSON with `hookSpecificOutput.hookEventName = "PostToolUse"` and `additionalContext`;
- reminds Codex to update Obsidian memory after publishing work.

It does not use GitHub Issues. Links to GitHub, Linear, or Obsidian notes can be stored in `memory_in_progress.md` as optional `link` fields.

## Manual Tests

Check JavaScript syntax:

```bash
node --check assets/codex/hooks/codex-session-start.js
node --check assets/codex/hooks/codex-post-tool-use.js
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

Test push reminder:

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"git push origin main"},"cwd":"/path/to/repo","hook_event_name":"PostToolUse"}' \
  | node assets/codex/hooks/codex-post-tool-use.js
```

Test non-push silence:

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"git status"},"cwd":"/path/to/repo","hook_event_name":"PostToolUse"}' \
  | node assets/codex/hooks/codex-post-tool-use.js
```

## Safety Rules

- Do not store secrets in Obsidian memory.
- Keep `memory_in_progress.md` short and operational.
- Treat `memory_active.md` as a dashboard, not a journal.
- In multi-agent setups, write private operational files only in the current agent's private root.
- Append to shared memory only for durable world-level facts and include source attribution.
