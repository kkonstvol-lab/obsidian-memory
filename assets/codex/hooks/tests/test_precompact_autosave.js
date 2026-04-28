const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");

const { writeDraft } = require("../precompact-autosave");

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "precompact-autosave-"));

try {
  const vault = path.join(tmp, "vault");
  const payload = {
    agent_id: "codex",
    session_id: "fixture-session",
    user_goal: "Implement MemPalace practices",
    active_repo: "obsidian-vault",
    important_decisions: ["Markdown remains canonical"],
    files_touched: ["12-shared/graph/extract_vault.py"],
    commands_touched: ["python tests/test_graphify_beads.py"],
    unresolved_next_action: "Review generated GRAPH_READY.md",
    trigger: "precompact"
  };

  const first = writeDraft(vault, payload, { now: "2026-04-28T10:00:00.000Z" });
  const text1 = fs.readFileSync(first, "utf8");
  const second = writeDraft(vault, payload, { now: "2026-04-28T10:05:00.000Z" });
  const text2 = fs.readFileSync(second, "utf8");

  assert.strictEqual(first, second, "same session should write the same draft path");
  assert.strictEqual(text1, text2, "second run should not overwrite existing draft");
  assert.ok(first.includes(path.join("12-codex", "session-drafts")), "draft should live in private agent memory");
  assert.ok(!first.includes(path.join("wiki", "wings")), "draft must not touch canonical wings");
  assert.ok(!first.includes("raw-sources"), "draft must not touch raw sources");
  assert.ok(text1.includes("canonical: false"), "draft must be marked non-canonical");
  assert.ok(text1.includes("Markdown remains canonical"), "important decisions should be captured");

  console.log("precompact autosave checks passed");
} finally {
  fs.rmSync(tmp, { recursive: true, force: true });
}
