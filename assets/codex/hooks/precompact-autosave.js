#!/usr/bin/env node
/*
Precompact/session-end autosave for Obsidian memory.

Writes a non-canonical draft drawer into the agent private memory area.
It never edits wiki/, wiki/wings/, or raw-sources/.
*/

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

function slug(value) {
  return String(value || "session")
    .toLowerCase()
    .replace(/[^a-z0-9а-я]+/gi, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80) || "session";
}

function stableId(...parts) {
  return crypto.createHash("sha1").update(parts.join("\u241f")).digest("hex").slice(0, 10);
}

function readStdin() {
  return new Promise((resolve) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => {
      data += chunk;
    });
    process.stdin.on("end", () => resolve(data));
  });
}

function renderDraft(payload, options = {}) {
  const now = options.now || new Date().toISOString();
  const day = now.slice(0, 10);
  const agentId = payload.agent_id || process.env.OBSIDIAN_AGENT_ID || "codex";
  const goal = payload.user_goal || payload.goal || payload.prompt || "";
  const sessionId = payload.session_id || stableId(agentId, goal, day);
  const title = `Autosave ${day} ${slug(goal).slice(0, 48)}`;
  const decisions = Array.isArray(payload.important_decisions) ? payload.important_decisions : [];
  const files = Array.isArray(payload.files_touched) ? payload.files_touched : [];
  const commands = Array.isArray(payload.commands_touched) ? payload.commands_touched : [];

  return {
    sessionId,
    fileName: `draft-${day}-${agentId}-${sessionId}.md`,
    text: `---\n` +
      `title: "${title}"\n` +
      `type: drawer-draft\n` +
      `created: ${now}\n` +
      `updated: ${now}\n` +
      `session_date: ${day}\n` +
      `agent_id: ${agentId}\n` +
      `session_id: ${sessionId}\n` +
      `compiled: false\n` +
      `status: draft\n` +
      `canonical: false\n` +
      `tags:\n` +
      `  - memory\n` +
      `  - session-draft\n` +
      `source: precompact-autosave\n` +
      `---\n\n` +
      `# ${title}\n\n` +
      `> Draft safety net. Not canonical memory until reviewed by /session-summary or COMPILE.\n\n` +
      `## Session Context\n\n` +
      `- Agent: ${agentId}\n` +
      `- Repo / task: ${payload.active_repo || payload.active_task || ""}\n` +
      `- User goal: ${goal}\n` +
      `- Trigger: ${payload.trigger || "precompact"}\n\n` +
      `## Important Decisions\n\n` +
      `${decisions.map((item) => `- ${item}`).join("\n") || "- "}\n\n` +
      `## Files / Commands Touched\n\n` +
      `${files.map((item) => `- file: \`${item}\``).join("\n") || "- file: "}\n` +
      `${commands.map((item) => `- command: \`${item}\``).join("\n") || ""}\n\n` +
      `## Unresolved Next Action\n\n` +
      `- ${payload.unresolved_next_action || ""}\n\n` +
      `## Source Evidence\n\n` +
      `- Conversation/session artifact: ${payload.source_artifact || ""}\n`
  };
}

function writeDraft(vaultPath, payload, options = {}) {
  const agentId = payload.agent_id || process.env.OBSIDIAN_AGENT_ID || "codex";
  const draftRoot = options.draftRoot || process.env.OBSIDIAN_DRAFT_ROOT || path.join(vaultPath, `12-${agentId}`, "session-drafts");
  const rendered = renderDraft(payload, options);
  fs.mkdirSync(draftRoot, { recursive: true });
  const target = path.join(draftRoot, rendered.fileName);
  if (!fs.existsSync(target)) {
    fs.writeFileSync(target, rendered.text, "utf8");
  }
  return target;
}

async function main() {
  const raw = await readStdin();
  const payload = raw.trim() ? JSON.parse(raw) : {};
  const vaultPath = payload.vault_path || process.env.OBSIDIAN_VAULT_PATH;
  if (!vaultPath) {
    throw new Error("OBSIDIAN_VAULT_PATH or payload.vault_path is required");
  }
  const target = writeDraft(vaultPath, payload);
  console.log(`precompact autosave draft: ${target}`);
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error.message);
    process.exit(1);
  });
}

module.exports = { renderDraft, writeDraft };
