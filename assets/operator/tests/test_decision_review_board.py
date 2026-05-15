#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "decision_review_board.py"
SCRIPTS_DIR = SCRIPT.parent


def load_module():
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("decision_review_board", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=cwd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert result.returncode == 0, result.stderr
    return result


def init_repo(root: Path, *, backup_commit: bool = False) -> None:
    run(["git", "init"], root)
    run(["git", "config", "user.email", "test@example.com"], root)
    run(["git", "config", "user.name", "Test"], root)
    (root / "12-agent/session-drafts").mkdir(parents=True)
    (root / "12-agent/lessons").mkdir(parents=True)
    (root / "12-shared").mkdir(parents=True)
    (root / "wiki").mkdir(parents=True)
    (root / "12-agent/memory_in_progress.md").write_text("", encoding="utf-8")
    (root / "12-agent/memory_corrections.md").write_text("", encoding="utf-8")
    (root / "12-shared/memory_decisions.md").write_text("", encoding="utf-8")
    (root / "12-shared/memory_ops.md").write_text("", encoding="utf-8")
    (root / "wiki/log.md").write_text("", encoding="utf-8")
    (root / "12-agent/lessons/README.md").write_text("# Lessons\n", encoding="utf-8")
    (root / "README.md").write_text("fixture\n", encoding="utf-8")
    run(["git", "add", "."], root)
    commit_message = "vault backup: 2026-01-01 00:00:00" if backup_commit else "init"
    run(["git", "commit", "-m", commit_message], root)


def cli(root: Path, *extra: str, approved: bool = False) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if approved:
        env["MEMORY_OPERATOR_APPROVED"] = "1"
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *extra], env=env, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def candidates(report: dict) -> list[dict]:
    return list(report["candidates"])


def test_wrong_release_target_correction_routes_to_agent_lesson_high_confidence() -> None:
    module = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        init_repo(root)
        (root / "12-agent/memory_corrections.md").write_text(
            "## 2026-05-07 - Verified wrong public skill target too late\n"
            "- **Error:** Released to wrong target repo.\n"
            "- **Fix:** Verify canonical release target before public release.\n"
            "- **Rule extracted:** Always verify remote and source of truth before release.\n",
            encoding="utf-8",
        )
        report = module.collect(root)
        item = next(item for item in candidates(report) if item["source_type"] == "memory_correction")
        assert item["recommended_artifact"] == "agent_lesson"
        assert item["confidence"] == "high"


def test_public_readme_hook_narrative_routes_to_public_surface_note() -> None:
    module = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        init_repo(root)
        (root / "wiki/log.md").write_text(
            "## 2026-05-14 - PUBLIC | README hooks narrative\n"
            "- Operation: promoted hooks in public README first-level narrative.\n"
            "- Notes: public skill must show hook runtime capability before release.\n",
            encoding="utf-8",
        )
        report = module.collect(root)
        item = next(item for item in candidates(report) if item["source_type"] == "wiki_log")
        assert item["recommended_artifact"] == "public_surface_note"


def test_vault_backup_commit_is_counted_as_noise_and_hidden_by_default() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        init_repo(root, backup_commit=True)
        result = cli(root, "--json")
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        assert report["schema_version"] == "decision-review-board.v1"
        assert report["summary"]["no_durable_write"] == 1
        assert all(item["recommended_artifact"] != "no_durable_write" for item in report["candidates"])
        verbose = cli(root, "--json", "--verbose")
        verbose_report = json.loads(verbose.stdout)
        assert any(item["recommended_artifact"] == "no_durable_write" for item in verbose_report["candidates"])


def test_review_state_mark_requires_approval_and_note() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        init_repo(root)
        (root / "12-agent/memory_in_progress.md").write_text("- Policy: archive max 150-220 lines for branch close handoff.\n", encoding="utf-8")
        report = json.loads(cli(root, "--json").stdout)
        candidate_id = report["candidates"][0]["id"]
        denied = cli(root, "--mark", candidate_id, "--status", "skipped", "--note", "low value")
        assert denied.returncode != 0
        missing_note = cli(root, "--mark", candidate_id, "--status", "skipped", approved=True)
        assert missing_note.returncode != 0
        assert not (root / "12-agent/decision-review/review-state.jsonl").exists()


def test_review_state_hides_resolved_candidates_by_default() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        init_repo(root)
        (root / "12-agent/memory_in_progress.md").write_text("- Policy: release target must be verified before public surface handoff.\n", encoding="utf-8")
        report = json.loads(cli(root, "--json").stdout)
        candidate_id = report["candidates"][0]["id"]
        mark = cli(root, "--mark", candidate_id, "--status", "accepted", "--note", "captured in memory_decisions", approved=True)
        assert mark.returncode == 0, mark.stderr
        default_report = json.loads(cli(root, "--json").stdout)
        assert default_report["summary"]["accepted"] == 1
        assert all(item["id"] != candidate_id for item in default_report["candidates"])
        included_report = json.loads(cli(root, "--json", "--include-reviewed").stdout)
        reviewed = next(item for item in included_report["candidates"] if item["id"] == candidate_id)
        assert reviewed["review_status"] == "accepted"


if __name__ == "__main__":
    test_wrong_release_target_correction_routes_to_agent_lesson_high_confidence()
    test_public_readme_hook_narrative_routes_to_public_surface_note()
    test_vault_backup_commit_is_counted_as_noise_and_hidden_by_default()
    test_review_state_mark_requires_approval_and_note()
    test_review_state_hides_resolved_candidates_by_default()
    print("decision_review_board tests passed")
