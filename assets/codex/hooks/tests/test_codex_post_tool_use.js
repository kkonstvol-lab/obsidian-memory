#!/usr/bin/env node
"use strict";

const assert = require("assert");
const { isGitPush } = require("../codex-post-tool-use.js");

const cases = [
  ["git push", true],
  ["git -C /tmp/repo push", true],
  ["git -C/tmp/repo push", true],
  ["/usr/bin/git push origin main", true],
  ["git status && git push", true],
  ["rg -n '\"status\": \"ok\"|git push|\\\"command\\\"' /tmp", false],
  ["printf 'quoted |git push| smoke\\n'", false],
  ["echo git push", false],
  ["git status", false],
];

for (const [command, expected] of cases) {
  assert.strictEqual(isGitPush(command), expected, command);
}

console.log("codex post-tool-use tests passed");
