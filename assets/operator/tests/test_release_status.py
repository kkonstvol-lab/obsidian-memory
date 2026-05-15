#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "release_status.py"
SCRIPTS_DIR = SCRIPT.parent


def load_module():
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("release_status", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=cwd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert result.returncode == 0, result.stderr
    return result


def init_repo(root: Path, *, upstream: bool = False, remote_url: str | None = None) -> None:
    run(["git", "init"], root)
    run(["git", "config", "user.email", "test@example.com"], root)
    run(["git", "config", "user.name", "Test"], root)
    (root / "README.md").write_text("fixture\n", encoding="utf-8")
    run(["git", "add", "README.md"], root)
    run(["git", "commit", "-m", "init"], root)
    run(["git", "branch", "-M", "main"], root)
    if upstream:
        remote = root.parent / "remote.git"
        run(["git", "init", "--bare", str(remote)], root)
        run(["git", "remote", "add", "origin", str(remote)], root)
        run(["git", "push", "-u", "origin", "main"], root)
        if remote_url:
            run(["git", "remote", "set-url", "origin", remote_url], root)
    elif remote_url:
        run(["git", "remote", "add", "origin", remote_url], root)


def args(**kwargs):
    data = {"repo": ".", "intent": "generic", "expected_branch": "", "expected_remote": "", "strict": False, "json": False}
    data.update(kwargs)
    return type("Args", (), data)()


def cli(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), "--repo", str(root), *extra], check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def test_clean_repo_with_upstream_is_ready() -> None:
    release = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        root.mkdir()
        init_repo(root, upstream=True)
        report = release.collect(args(repo=str(root)))
        assert report["verdict"] == "ready"


def test_dirty_repo_needs_review() -> None:
    release = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        root.mkdir()
        init_repo(root, upstream=True)
        (root / "README.md").write_text("dirty\n", encoding="utf-8")
        report = release.collect(args(repo=str(root)))
        assert report["verdict"] == "needs_review"
        assert any(risk["code"] == "dirty_worktree" for risk in report["risks"])


def test_expected_branch_mismatch_strict_blocks_cli() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        root.mkdir()
        init_repo(root, upstream=True)
        result = cli(root, "--expected-branch", "release", "--strict", "--json")
        assert result.returncode == 1
        report = json.loads(result.stdout)
        assert report["verdict"] == "blocked"


def test_staged_raw_binary_blocks() -> None:
    release = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        root.mkdir()
        init_repo(root, upstream=True)
        raw = root / "raw-sources/pdfs/source.pdf"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(b"%PDF-1.4\n")
        run(["git", "add", str(raw.relative_to(root))], root)
        report = release.collect(args(repo=str(root)))
        assert report["verdict"] == "blocked"
        assert any(risk["code"] == "staged_raw_binary" for risk in report["risks"])


def test_agents_monorepo_obsidian_memory_has_standalone_blocker() -> None:
    release = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "agents"
        root.mkdir()
        init_repo(root, upstream=True, remote_url="git@github.com:example/agents.git")
        readme = root / "agent-skills/obsidian-memory/README.md"
        readme.parent.mkdir(parents=True, exist_ok=True)
        readme.write_text("# obsidian-memory\n", encoding="utf-8")
        report = release.collect(args(repo=str(root), intent="public-obsidian-memory"))
        assert report["surface"]["type"] == "agents-monorepo-obsidian-memory"
        assert any(risk["code"] == "standalone_verification_required" for risk in report["risks"])
        assert report["verdict"] == "blocked"


def test_json_output_contains_stable_keys_and_ready_exit_zero() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        root.mkdir()
        init_repo(root, upstream=True)
        result = cli(root, "--json")
        assert result.returncode == 0
        report = json.loads(result.stdout)
        assert set(report) == {"mode", "verdict", "repo", "push_boundary", "working_tree", "surface", "risks", "release_packet", "recommended_commands", "post_push_obligations"}
        assert report["verdict"] == "ready"


if __name__ == "__main__":
    test_clean_repo_with_upstream_is_ready()
    test_dirty_repo_needs_review()
    test_expected_branch_mismatch_strict_blocks_cli()
    test_staged_raw_binary_blocks()
    test_agents_monorepo_obsidian_memory_has_standalone_blocker()
    test_json_output_contains_stable_keys_and_ready_exit_zero()
    print("release_status tests passed")
