#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "branch_close_pack.py"


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=cwd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert result.returncode == 0, result.stderr
    return result


def init_repo(root: Path) -> None:
    run(["git", "init"], root)
    run(["git", "config", "user.email", "test@example.com"], root)
    run(["git", "config", "user.name", "Test"], root)
    (root / "12-shared/graph/graphify-out").mkdir(parents=True)
    (root / "12-shared/scripts").mkdir(parents=True)
    (root / "12-agent/lessons").mkdir(parents=True)
    (root / "wiki/summaries").mkdir(parents=True)
    (root / "wiki/domains").mkdir(parents=True)
    (root / "raw-sources/provenance").mkdir(parents=True)
    (root / "12-shared/graph/graphify-out/GRAPH_READY.md").write_text("# ready\n", encoding="utf-8")
    (root / "12-shared/graph/graphify-out/GRAPH_REPORT.md").write_text("# report\n", encoding="utf-8")
    (root / "12-shared/scripts/lesson_lint.py").write_text("# fixture\n", encoding="utf-8")
    (root / "12-shared/scripts/memory_operator.py").write_text("lesson_lint.py\ncheck-all\n", encoding="utf-8")
    (root / "12-agent/lessons/README.md").write_text("# Lessons\n", encoding="utf-8")
    (root / "12-agent/memory_active.md").write_text("## Active\n- next\n", encoding="utf-8")
    (root / "12-agent/memory_in_progress.md").write_text("## Done\n- shipped\n", encoding="utf-8")
    (root / "12-agent/memory_corrections.md").write_text("## 2026-01-01 - correction\n", encoding="utf-8")
    (root / "raw-sources/provenance/raw-local-manifest.jsonl").write_text("", encoding="utf-8")
    run(["git", "add", "."], root)
    run(["git", "commit", "-m", "init"], root)
    run(["git", "branch", "-M", "main"], root)
    remote = root.parent / "remote.git"
    run(["git", "init", "--bare", str(remote)], root)
    run(["git", "remote", "add", "origin", str(remote)], root)
    run(["git", "push", "-u", "origin", "main"], root)


def cli(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *extra], check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def test_clean_fixture_returns_zero_and_json_contract() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        root.mkdir()
        init_repo(root)
        result = cli(root, "--json")
        assert result.returncode == 0, result.stdout + result.stderr
        report = json.loads(result.stdout)
        assert report["schema_version"] == "branch-close-pack.v1"
        assert {"repo", "working_tree", "recent_commits", "memory", "backlog", "handoff", "findings"} <= set(report)


def test_dirty_untracked_or_staged_returns_two() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        root.mkdir()
        init_repo(root)
        (root / "new.txt").write_text("dirty\n", encoding="utf-8")
        result = cli(root, "--json")
        assert result.returncode == 2
        report = json.loads(result.stdout)
        assert any(item["code"] == "dirty_worktree" for item in report["findings"])
        run(["git", "add", "new.txt"], root)
        result = cli(root, "--json")
        assert result.returncode == 2
        report = json.loads(result.stdout)
        assert any(item["code"] == "staged_scope_present" for item in report["findings"])


def test_markdown_line_cap_and_no_mutation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        root.mkdir()
        init_repo(root)
        before = run(["git", "status", "--porcelain"], root).stdout
        result = cli(root, "--md")
        after = run(["git", "status", "--porcelain"], root).stdout
        assert result.returncode == 0
        assert len(result.stdout.splitlines()) <= 180
        assert before == after


if __name__ == "__main__":
    test_clean_fixture_returns_zero_and_json_contract()
    test_dirty_untracked_or_staged_returns_two()
    test_markdown_line_cap_and_no_mutation()
    print("branch_close_pack tests passed")
