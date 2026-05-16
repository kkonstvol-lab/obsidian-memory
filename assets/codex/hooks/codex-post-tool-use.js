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
  const tokens = shellTokens(command);
  for (let index = 0; index < tokens.length; index += 1) {
    const token = tokens[index];
    if (token.type === "operator" || !isSegmentStart(tokens, index) || !isGitToken(token.value)) continue;

    let cursor = index + 1;
    if (tokens[cursor]?.value === "-C") {
      cursor += 2;
    } else if (tokens[cursor]?.value?.startsWith("-C") && tokens[cursor].value.length > 2) {
      cursor += 1;
    }

    if (tokens[cursor]?.value === "push") return true;
  }
  return false;
}

function isGitToken(value) {
  return value === "git" || value.endsWith("/git");
}

function isSegmentStart(tokens, index) {
  if (index === 0) return true;
  return tokens[index - 1]?.type === "operator";
}

function shellTokens(command) {
  const tokens = [];
  let current = "";
  let quote = "";
  let escaped = false;

  function flush() {
    if (!current) return;
    tokens.push({ type: "word", value: current });
    current = "";
  }

  for (const char of String(command)) {
    if (escaped) {
      current += char;
      escaped = false;
      continue;
    }
    if (quote) {
      if (char === quote) {
        quote = "";
      } else if (char === "\\" && quote === '"') {
        escaped = true;
      } else {
        current += char;
      }
      continue;
    }
    if (char === "\\") {
      escaped = true;
      continue;
    }
    if (char === "'" || char === '"') {
      quote = char;
      continue;
    }
    if (/\s/.test(char)) {
      flush();
      continue;
    }
    if (";&|()\n".includes(char)) {
      flush();
      tokens.push({ type: "operator", value: char });
      continue;
    }
    current += char;
  }
  flush();
  return tokens;
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
  const toolName = input.tool_name || input.name || "";
  const supportedTools = new Set(["Bash", "exec_command", "functions.exec_command"]);
  if (!supportedTools.has(toolName)) return;

  const toolInput = input.tool_input || input.input || {};
  const command = toolInput.command || toolInput.cmd || "";
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

if (require.main === module) {
  main();
}

module.exports = { isGitPush, shellTokens };
