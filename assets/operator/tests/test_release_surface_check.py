#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "release_surface_check.py"
SCRIPTS_DIR = SCRIPT.parent


def load_module():
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("release_surface_check", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=cwd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert result.returncode == 0, result.stderr
    return result


def init_repo(root: Path, remote_url: str, readme: str | None = None) -> None:
    run(["git", "init"], root)
    run(["git", "config", "user.email", "test@example.com"], root)
    run(["git", "config", "user.name", "Test"], root)
    (root / "README.md").write_text(readme or "# Obsidian Memory\n\nInstall\nhooks\ngraph bridge\nControl Tower workflow discipline\n", encoding="utf-8")
    (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
    (root / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
    run(["git", "add", "."], root)
    run(["git", "commit", "-m", "init\n\nCo-authored-by: Codex <noreply@openai.com>"], root)
    run(["git", "branch", "-M", "main"], root)
    run(["git", "remote", "add", "origin", remote_url], root)


def cli(*extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *extra], check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def test_vault_profile_passes_marker_detection_in_fixture() -> None:
    module = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "obsidian-vault"
        root.mkdir()
        init_repo(root, "git@github.com:x/obsidian-vault.git")
        (root / "wiki").mkdir()
        (root / "wiki/CLAUDE.md").write_text("# schema\n", encoding="utf-8")
        (root / "12-shared").mkdir()
        run(["git", "add", "."], root)
        run(["git", "commit", "-m", "markers"], root)
        args = argparse.Namespace(profile="vault", root=str(root), standalone="", monorepo="")
        report = module.collect(args)
        assert not any(f["severity"] == "blocker" for f in report["findings"])


def test_public_skill_missing_mandatory_files_blocks() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        standalone = Path(tmp) / "obsidian-memory"
        standalone.mkdir()
        init_repo(standalone, "git@github.com:x/obsidian-memory.git")
        (standalone / "LICENSE").unlink()
        run(["git", "add", "-A"], standalone)
        run(["git", "commit", "-m", "remove license"], standalone)
        result = cli("--profile", "public-skill", "--standalone", str(standalone), "--json")
        assert result.returncode == 2
        report = json.loads(result.stdout)
        assert any(f["code"] == "license" for f in report["findings"])


def test_public_skill_warns_when_control_tower_is_hidden() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        standalone = Path(tmp) / "obsidian-memory"
        standalone.mkdir()
        init_repo(standalone, "git@github.com:x/obsidian-memory.git", readme="# Obsidian Memory\n\nInstall\nhooks\ngraph bridge\n")
        result = cli("--profile", "public-skill", "--standalone", str(standalone), "--json")
        assert result.returncode == 0
        report = json.loads(result.stdout)
        assert any(f["code"] == "readme_control_tower" and f["severity"] == "warn" for f in report["findings"])


if __name__ == "__main__":
    test_vault_profile_passes_marker_detection_in_fixture()
    test_public_skill_missing_mandatory_files_blocks()
    test_public_skill_warns_when_control_tower_is_hidden()
    print("release_surface_check tests passed")
