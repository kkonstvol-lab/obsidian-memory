#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill_repo_audit.py"
SCRIPTS_DIR = SCRIPT.parent


def load_module():
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("skill_repo_audit", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_resolver_health_finds_missing_trigger() -> None:
    audit = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write(root / "quiet/SKILL.md", "# Quiet\n\nNo routing language here.\n")
        findings = audit.resolver_health(root)
        assert any(item["issue"] == "missing discoverable trigger terms" for item in findings)


def test_resolver_health_finds_overlap() -> None:
    audit = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name in ("a", "b", "c"):
            write(root / name / "SKILL.md", f"# {name}\n\nUse when handling calendar scheduling workflow.\n\n## Verification\n\nRun tests.\n\n## Role\n\nOwns routing.\n")
        findings = audit.resolver_health(root)
        assert any("overlapping trigger term" in item["issue"] for item in findings)


def test_resolver_health_finds_missing_skill_md() -> None:
    audit = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "stale-folder").mkdir()
        findings = audit.resolver_health(root)
        assert any(item["issue"] == "skill folder missing SKILL.md" for item in findings)


def test_verification_warning_is_mutation_scoped() -> None:
    audit = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write(root / "read-only/SKILL.md", "# Read Only\n\nUse when reviewing notes.\n\n## Role\n\nOwns review.\n")
        write(root / "mutating/SKILL.md", "# Mutating\n\nUse when editing files.\n\n## Role\n\nOwns edits.\n")
        findings = audit.resolver_health(root)
        skills = [item["skill"] for item in findings if item["issue"] == "missing verification section"]
        assert "mutating" in skills
        assert "read-only" not in skills


if __name__ == "__main__":
    test_resolver_health_finds_missing_trigger()
    test_resolver_health_finds_overlap()
    test_resolver_health_finds_missing_skill_md()
    test_verification_warning_is_mutation_scoped()
    print("skill_repo_audit tests passed")
