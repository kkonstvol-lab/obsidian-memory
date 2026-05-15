#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "lesson_lint.py"
SCRIPTS_DIR = SCRIPT.parent


def load_module():
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("lesson_lint", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def lesson_text() -> str:
    return """---
id: case-fixture
type: case
status: draft
created: 2026-01-01
updated: 2026-01-01
source: test
confidence_1_5: 4
impact_1_5: 4
confirmed_count: 1
contradicted_count: 0
human_reviewed: true
anchors:
  domain: memory
  situation: fixture
  trigger: test
  stakes: safety
  actors: agent,user
  environment: fixture
  circumstances: dry-run
  purpose: prevent-repeat-error
  method: test
summary: fixture summary
rule: fixture rule
evidence:
  - source: test
    note: fixture
contradictions: []
---

# case-fixture
"""


def test_valid_case_has_no_blockers() -> None:
    lesson_lint = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        base = root / "12-agent/lessons"
        base.mkdir(parents=True)
        (base / "README.md").write_text("# Lessons\n", encoding="utf-8")
        (base / "case-fixture.md").write_text(lesson_text(), encoding="utf-8")
        findings = lesson_lint.lint(root)
        assert not [item for item in findings if item.severity == "blocker"]


def test_active_unreviewed_pattern_blocks() -> None:
    lesson_lint = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        base = root / "12-agent/lessons"
        base.mkdir(parents=True)
        (base / "README.md").write_text("# Lessons\n", encoding="utf-8")
        text = lesson_text().replace("id: case-fixture", "id: pattern-fixture").replace("type: case", "type: pattern").replace("status: draft", "status: active").replace("human_reviewed: true", "human_reviewed: false")
        (base / "pattern-fixture.md").write_text(text, encoding="utf-8")
        findings = lesson_lint.lint(root)
        assert any(item.severity == "blocker" for item in findings)


if __name__ == "__main__":
    test_valid_case_has_no_blockers()
    test_active_unreviewed_pattern_blocks()
    print("lesson_lint tests passed")
