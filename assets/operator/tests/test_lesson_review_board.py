#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "lesson_review_board.py"
SCRIPTS_DIR = SCRIPT.parent


def load_module():
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("lesson_review_board", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def lesson_text(lesson_id: str, *, status: str = "draft", lesson_type: str = "case", reviewed: str = "false", confirmed: int = 1, method: str = "same-method") -> str:
    return f"""---
id: {lesson_id}
type: {lesson_type}
status: {status}
created: 2026-01-01
updated: 2026-01-01
source: test
confidence_1_5: 4
impact_1_5: 4
confirmed_count: {confirmed}
contradicted_count: 0
human_reviewed: {reviewed}
anchors:
  domain: memory
  situation: fixture
  trigger: test
  stakes: safety
  actors: agent,user
  environment: fixture
  circumstances: dry-run
  purpose: prevent-repeat-error
  method: {method}
summary: fixture summary
rule: fixture rule
evidence:
  - source: test
    note: fixture
contradictions: []
---

# {lesson_id}
"""


def write_lesson(root: Path, lesson_id: str, text: str, agent: str = "agent") -> None:
    base = root / f"12-{agent}/lessons"
    base.mkdir(parents=True, exist_ok=True)
    (base / "README.md").write_text("# Lessons\n", encoding="utf-8")
    (base / f"{lesson_id}.md").write_text(text, encoding="utf-8")


def cli(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *extra], check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def test_two_matching_cases_create_promotion_group() -> None:
    module = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_lesson(root, "case-a", lesson_text("case-a"))
        write_lesson(root, "case-b", lesson_text("case-b"))
        report = module.collect(root)
        assert report["promotion_groups"]
        assert report["promotion_groups"][0]["eligible_for_pattern_review"] is True
        assert {item["classification"] for item in report["lessons"]} == {"promotion_candidate"}


def test_active_unreviewed_pattern_returns_two() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_lesson(root, "pattern-a", lesson_text("pattern-a", lesson_type="pattern", status="active", reviewed="false"))
        result = cli(root, "--json")
        assert result.returncode == 2
        report = json.loads(result.stdout)
        assert any(item["severity"] == "blocker" for item in report["findings"])


def test_missing_lessons_dir_warns_not_blocks() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = cli(root, "--json")
        assert result.returncode == 0
        report = json.loads(result.stdout)
        assert report["summary"]["total"] == 0


if __name__ == "__main__":
    test_two_matching_cases_create_promotion_group()
    test_active_unreviewed_pattern_returns_two()
    test_missing_lessons_dir_warns_not_blocks()
    print("lesson_review_board tests passed")
