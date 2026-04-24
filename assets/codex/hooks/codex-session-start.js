#!/usr/bin/env node
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");

const MAX_TOTAL_CHARS = Number(process.env.OBSIDIAN_CONTEXT_MAX_CHARS || 12000);

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

function readFileSafe(filePath, maxChars) {
  try {
    if (!filePath || !fs.existsSync(filePath)) return "";
    const text = fs.readFileSync(filePath, "utf8").replace(/\r\n/g, "\n");
    return text.length > maxChars ? `${text.slice(0, maxChars)}\n...[truncated]` : text;
  } catch {
    return "";
  }
}

function configPath() {
  return path.join(os.homedir(), ".codex", "obsidian-memory.json");
}

function loadConfig() {
  const filePath = configPath();
  if (!fs.existsSync(filePath)) return {};
  return parseJson(readFileSafe(filePath, 20000));
}

function resolveSettings() {
  const config = loadConfig();
  const vaultPath = process.env.OBSIDIAN_VAULT_PATH || config.vaultPath || "";
  const agentId = process.env.OBSIDIAN_AGENT_ID || config.agentId || "codex";
  const sharedRootName = process.env.OBSIDIAN_SHARED_ROOT || config.sharedRoot || "12-shared";
  const privateRootName =
    process.env.OBSIDIAN_PRIVATE_ROOT || config.privateRoot || `12-${agentId}`;

  if (!vaultPath) {
    return { vaultPath: "", agentId, privateRoot: "", sharedRoot: "", mode: "missing" };
  }

  const multiPrivate = path.join(vaultPath, privateRootName);
  const multiShared = path.join(vaultPath, sharedRootName);
  const singleMemory = path.join(vaultPath, "memory");

  if (fs.existsSync(multiPrivate)) {
    return {
      vaultPath,
      agentId,
      privateRoot: multiPrivate,
      sharedRoot: fs.existsSync(multiShared) ? multiShared : multiPrivate,
      mode: "multi-agent",
    };
  }

  return {
    vaultPath,
    agentId,
    privateRoot: singleMemory,
    sharedRoot: singleMemory,
    mode: "single-agent",
  };
}

function gitValue(cwd, args) {
  try {
    return execFileSync("git", ["-C", cwd, ...args], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
      timeout: 2000,
    }).trim();
  } catch {
    return "";
  }
}

function getRepoInfo(cwd) {
  const root = gitValue(cwd, ["rev-parse", "--show-toplevel"]);
  if (!root) {
    return {
      cwd,
      gitRoot: "",
      branch: "",
      remote: "",
      needles: [path.basename(cwd || "")].filter(Boolean),
    };
  }

  const branch = gitValue(root, ["branch", "--show-current"]);
  const remote = gitValue(root, ["remote", "get-url", "origin"]);
  const repoName = path.basename(root);
  const remoteSlug = remote
    .replace(/^git@github\.com:/, "")
    .replace(/^https:\/\/github\.com\//, "")
    .replace(/\.git$/, "");

  return {
    cwd,
    gitRoot: root,
    branch,
    remote,
    needles: [repoName, remoteSlug, root, remote].filter(Boolean),
  };
}

function latestSections(markdown, maxSections) {
  const lines = markdown.split("\n");
  const out = [];
  let sections = 0;

  for (const line of lines) {
    if (/^##\s+/.test(line)) sections += 1;
    if (sections > maxSections) break;
    out.push(line);
  }

  return out.join("\n").trim();
}

function relevantSharedExcerpt(markdown, needles, maxChars) {
  const lowerNeedles = needles
    .map((needle) => String(needle).toLowerCase())
    .filter((needle) => needle.length >= 3);

  const sections = markdown.split(/(?=^#{2,3}\s+)/m);
  const matches = sections.filter((section) => {
    const lower = section.toLowerCase();
    return lowerNeedles.some((needle) => lower.includes(needle));
  });

  const text = (matches.length ? matches : sections.slice(0, 2)).join("\n").trim();
  return text.length > maxChars ? `${text.slice(0, maxChars)}\n...[truncated]` : text;
}

function addBlock(blocks, title, body) {
  const trimmed = (body || "").trim();
  if (!trimmed) return;
  blocks.push(`## ${title}\n\n${trimmed}`);
}

function missingVaultContext() {
  return [
    "# Obsidian Memory Context Not Loaded",
    "",
    "Set `OBSIDIAN_VAULT_PATH` or create `~/.codex/obsidian-memory.json`:",
    "",
    "```json",
    "{",
    "  \"vaultPath\": \"/absolute/path/to/obsidian-vault\",",
    "  \"agentId\": \"codex\"",
    "}",
    "```",
  ].join("\n");
}

function main() {
  const input = parseJson(readStdin());
  if (input.source && input.source !== "startup") return;

  const cwd = input.cwd || process.cwd();
  const settings = resolveSettings();

  if (!settings.vaultPath) {
    process.stdout.write(`${missingVaultContext()}\n`);
    return;
  }

  const repo = getRepoInfo(cwd);
  const blocks = [];

  addBlock(
    blocks,
    "Session",
    [
      `cwd: ${repo.cwd || "(unknown)"}`,
      repo.gitRoot ? `git_root: ${repo.gitRoot}` : "git_root: (not a git repo)",
      repo.branch ? `branch: ${repo.branch}` : "",
      repo.remote ? `remote: ${repo.remote}` : "",
      `vault: ${settings.vaultPath}`,
      `agent_id: ${settings.agentId}`,
      `memory_mode: ${settings.mode}`,
    ]
      .filter(Boolean)
      .join("\n")
  );

  addBlock(
    blocks,
    "memory_active.md",
    readFileSafe(path.join(settings.privateRoot, "memory_active.md"), 2500)
  );

  addBlock(
    blocks,
    "memory_in_progress.md",
    readFileSafe(path.join(settings.privateRoot, "memory_in_progress.md"), 3500) ||
      "No `memory_in_progress.md` found."
  );

  const corrections = readFileSafe(path.join(settings.privateRoot, "memory_corrections.md"), 5000);
  addBlock(blocks, "recent memory_corrections.md", latestSections(corrections, 3));

  for (const file of ["memory_repos.md", "memory_tools.md", "memory_decisions.md"]) {
    const content = readFileSafe(path.join(settings.sharedRoot, file), 9000);
    addBlock(blocks, file, relevantSharedExcerpt(content, repo.needles, 1800));
  }

  let context = `# Auto-loaded Obsidian Memory Context\n\n${blocks.join("\n\n---\n\n")}`.trim();
  if (context.length > MAX_TOTAL_CHARS) {
    context = `${context.slice(0, MAX_TOTAL_CHARS)}\n\n...[context truncated by obsidian-memory hook]`;
  }

  process.stdout.write(`${context}\n`);
}

main();
