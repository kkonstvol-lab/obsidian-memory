#!/usr/bin/env node
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");

function readStdin() {
  return fs.readFileSync(0, "utf8");
}

function parseJson(raw) {
  try {
    return raw && raw.trim() ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function readConfig() {
  const filePath = path.join(os.homedir(), ".codex", "obsidian-memory.json");
  try {
    if (!fs.existsSync(filePath)) return {};
    return parseJson(fs.readFileSync(filePath, "utf8"));
  } catch {
    return {};
  }
}

function isGitPush(command) {
  if (!command || typeof command !== "string") return false;
  return /(^|[;&|]\s*|\r?\n\s*)git(\s+-C\s+("[^"]+"|'[^']+'|\S+))?\s+push\b/.test(command);
}

function resolveMemoryRoots(vaultPath, config, agentId) {
  const sharedRootName = process.env.OBSIDIAN_SHARED_ROOT || config.sharedRoot || "12-shared";
  const privateRootName =
    process.env.OBSIDIAN_PRIVATE_ROOT || config.privateRoot || `12-${agentId}`;

  if (!vaultPath || vaultPath === "{YOUR_VAULT_PATH}") {
    return {
      privateRoot: path.join(vaultPath, privateRootName),
      sharedRoot: path.join(vaultPath, sharedRootName),
    };
  }

  const multiPrivate = path.join(vaultPath, privateRootName);
  const multiShared = path.join(vaultPath, sharedRootName);
  const singleMemory = path.join(vaultPath, "memory");

  if (fs.existsSync(multiPrivate)) {
    return {
      privateRoot: multiPrivate,
      sharedRoot: fs.existsSync(multiShared) ? multiShared : multiPrivate,
    };
  }

  return {
    privateRoot: singleMemory,
    sharedRoot: singleMemory,
  };
}

function main() {
  const input = parseJson(readStdin());
  if (input.tool_name !== "Bash") return;

  const command = input.tool_input && input.tool_input.command;
  if (!isGitPush(command)) return;

  const config = readConfig();
  const vaultPath = process.env.OBSIDIAN_VAULT_PATH || config.vaultPath || "{YOUR_VAULT_PATH}";
  const agentId = process.env.OBSIDIAN_AGENT_ID || config.agentId || "codex";
  const roots = resolveMemoryRoots(vaultPath, config, agentId);
  const cwd = input.cwd || "(unknown cwd)";

  const memoryPath = path.join(roots.privateRoot, "memory_in_progress.md");
  const correctionsPath = path.join(roots.privateRoot, "memory_corrections.md");
  const decisionsPath = path.join(roots.sharedRoot, "memory_decisions.md");

  const additionalContext = [
    "After `git push`, update Obsidian operational memory if this work changed task state:",
    "",
    `- Update \`${memoryPath}\` with current status and next action.`,
    "- If the task is done, move a short note to `Recently Done` or `memory_active.md`.",
    `- If this produced a durable cross-project decision, append it to \`${decisionsPath}\` with source attribution.`,
    `- If there was a logical/process mistake, prepend an entry to \`${correctionsPath}\`.`,
    "- If vault files changed, sync the Obsidian vault separately.",
    "",
    `cwd: ${cwd}`,
  ].join("\n");

  process.stdout.write(
    `${JSON.stringify(
      {
        hookSpecificOutput: {
          hookEventName: "PostToolUse",
          additionalContext,
        },
      },
      null,
      2
    )}\n`
  );
}

main();
