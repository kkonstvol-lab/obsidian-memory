#!/usr/bin/env python3
"""Read-only release surface guardrail for memory-related repos."""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from _operator_utils import markdown_table, read_text, vault_root


SCHEMA_VERSION = "release-surface-check.v1"


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str


def run_git(path: Path, args: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(["git", "-C", str(path), *args], check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.returncode, result.stdout.rstrip("\n"), result.stderr.strip()


def git(path: Path, args: list[str]) -> str:
    code, out, _err = run_git(path, args)
    return out if code == 0 else ""


def repo_root(path: Path) -> Path | None:
    code, out, _err = run_git(path, ["rev-parse", "--show-toplevel"])
    return Path(out) if code == 0 and out else None


def add_check(checks: list[dict[str, str]], code: str, status: str, message: str) -> None:
    checks.append({"code": code, "status": status, "message": message})


def repo_info(path: Path) -> dict[str, Any]:
    root = repo_root(path) if path.exists() else None
    if root is None:
        return {"branch": None, "remote_origin": None, "head": None, "dirty": False}
    status = git(root, ["status", "--porcelain"])
    return {
        "branch": git(root, ["branch", "--show-current"]) or None,
        "remote_origin": git(root, ["remote", "get-url", "origin"]) or None,
        "head": git(root, ["rev-parse", "--short", "HEAD"]) or None,
        "dirty": bool(status.strip()),
    }


def surface(name: str, path: Path, checks: list[dict[str, str]]) -> dict[str, Any]:
    return {"name": name, "path": str(path), "exists": path.exists(), "repo": repo_info(path), "checks": checks}


def status_to_finding(surface_name: str, check: dict[str, str]) -> Finding | None:
    if check["status"] not in {"warn", "blocker"}:
        return None
    return Finding(check["status"], check["code"], f"{surface_name}: {check['message']}")


def check_remote(checks: list[dict[str, str]], repo: dict[str, Any], expected: str) -> None:
    remote = str(repo.get("remote_origin") or "")
    if not expected:
        add_check(checks, "expected_remote", "not_applicable", "no expected remote configured")
    elif expected in remote:
        add_check(checks, "expected_remote", "pass", f"remote contains `{expected}`")
    else:
        add_check(checks, "expected_remote", "blocker", f"remote does not contain `{expected}`")


def check_dirty(checks: list[dict[str, str]], repo: dict[str, Any]) -> None:
    if repo.get("dirty"):
        add_check(checks, "dirty_release_surface", "blocker", "release surface has dirty/staged files")
    else:
        add_check(checks, "dirty_release_surface", "pass", "release surface is clean")


def vault_surface(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, str]] = []
    for marker in ("wiki/CLAUDE.md", "12-shared/"):
        add_check(checks, f"marker_{marker}", "pass" if (root / marker).exists() else "blocker", f"required marker `{marker}`")
    info = repo_info(root)
    check_dirty(checks, info)
    plugin_status = git(root, ["status", "--short", "--", ".obsidian/plugins"])
    add_check(checks, "obsidian_plugins_drift", "warn" if plugin_status.strip() else "pass", ".obsidian/plugins drift is warn-only")
    return [surface("vault", root, checks)], ["git status --short --branch", "run local wiki/provenance/bridge checks"]


def readme_has(text: str, needles: list[str]) -> bool:
    lower = text.lower()
    return any(needle.lower() in lower for needle in needles)


def public_skill_surface(standalone: Path, monorepo: Path | None) -> tuple[list[dict[str, Any]], list[str]]:
    surfaces: list[dict[str, Any]] = []
    for name, path, expected in (("standalone", standalone, "obsidian-memory"), ("monorepo", monorepo, "agents")):
        checks: list[dict[str, str]] = []
        if path is None or not path.exists():
            add_check(checks, "surface_exists", "not_applicable", "surface path does not exist")
            surfaces.append(surface(name, path or Path("(not configured)"), checks))
            continue
        info = repo_info(path)
        add_check(checks, "surface_exists", "pass", "surface path exists")
        check_remote(checks, info, expected)
        check_dirty(checks, info)
        readme = read_text(path / "README.md")
        first = "\n".join(readme.splitlines()[:160])
        has_core = readme_has(first, ["memory", "obsidian"])
        has_hooks = "hook" in first.lower()
        has_graph = readme_has(first, ["graph", "bridge"])
        has_control_tower = readme_has(first, ["control tower", "workflow discipline", "release status"])
        has_quick_start = readme_has(first, ["quick start", "smoke start", "install", "установка"])
        has_license = (path / "LICENSE").exists()
        has_agents = (path / "AGENTS.md").exists()
        add_check(checks, "readme_core_system", "pass" if has_core else "blocker", "README first 160 lines mention core system" if has_core else "README first 160 lines do not mention core system")
        add_check(checks, "readme_hooks", "pass" if has_hooks else "warn", "README mentions hooks" if has_hooks else "README does not mention hooks")
        add_check(checks, "readme_graph_bridge", "pass" if has_graph else "warn", "README mentions graph/bridge" if has_graph else "README does not mention graph/bridge")
        add_check(checks, "readme_control_tower", "pass" if has_control_tower else "warn", "README mentions Control Tower/workflow discipline" if has_control_tower else "README does not mention Control Tower/workflow discipline")
        add_check(checks, "readme_quick_start", "pass" if has_quick_start else "blocker", "README has install/quick start" if has_quick_start else "README lacks install/quick start")
        add_check(checks, "license", "pass" if has_license else "blocker", "LICENSE exists" if has_license else "LICENSE is missing")
        add_check(checks, "agents_md", "pass" if has_agents else "warn", "AGENTS.md exists" if has_agents else "AGENTS.md is missing")
        log = git(path, ["log", "-10", "--format=%B"])
        has_codex_attribution = "Co-authored-by: Codex <noreply@openai.com>" in log
        add_check(checks, "codex_attribution", "pass" if has_codex_attribution else "warn", "recent commits include Codex co-author trailer" if has_codex_attribution else "recent commits do not include Codex co-author trailer")
        surfaces.append(surface(name, path, checks))
    if standalone.exists() and monorepo and monorepo.exists():
        skill_root = monorepo / "agent-skills" / "obsidian-memory"
        if skill_root.exists() and read_text(standalone / "README.md") != read_text(skill_root / "README.md"):
            surfaces[0]["checks"].append({"code": "standalone_monorepo_sync", "status": "warn", "message": "standalone and monorepo README differ"})
    return surfaces, ["git status --short --branch", "diff standalone and monorepo skill copy when both are in scope"]


def collect(args: argparse.Namespace) -> dict[str, Any]:
    if args.profile == "vault":
        surfaces, next_checks = vault_surface(Path(args.root).resolve())
    else:
        monorepo = Path(args.monorepo).resolve() if args.monorepo else None
        surfaces, next_checks = public_skill_surface(Path(args.standalone).resolve(), monorepo)
    findings: list[Finding] = []
    for item in surfaces:
        for check in item["checks"]:
            finding = status_to_finding(item["name"], check)
            if finding:
                findings.append(finding)
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "dry-run",
        "profile": args.profile,
        "surfaces": surfaces,
        "required_next_checks": next_checks,
        "findings": [asdict(item) for item in findings],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = ["# RELEASE_SURFACE_CHECK dry-run", "", "Nothing changed. This checks only the selected release surface.", ""]
    for item in report["surfaces"]:
        lines.extend(
            [
                f"## {item['name']}",
                markdown_table(
                    ["field", "value"],
                    [["path", item["path"]], ["exists", item["exists"]], ["branch", item["repo"]["branch"]], ["remote", item["repo"]["remote_origin"]], ["dirty", item["repo"]["dirty"]]],
                ),
                "",
                markdown_table(["code", "status", "message"], ([c["code"], c["status"], c["message"]] for c in item["checks"])),
                "",
            ]
        )
    lines.extend(
        [
            "## Findings",
            markdown_table(["severity", "code", "message"], ([f["severity"], f["code"], f["message"]] for f in report["findings"])) if report["findings"] else "_No findings._",
            "",
            "## Required Next Checks",
            "\n".join(f"- `{cmd}`" for cmd in report["required_next_checks"]) or "_None._",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Read-only release surface guardrail")
    ap.add_argument("--profile", choices=["vault", "public-skill"], required=True)
    fmt = ap.add_mutually_exclusive_group()
    fmt.add_argument("--md", action="store_true")
    fmt.add_argument("--json", action="store_true")
    ap.add_argument("--root", default=str(vault_root()))
    ap.add_argument("--standalone", default=".")
    ap.add_argument("--monorepo", default="")
    args = ap.parse_args()

    report = collect(args)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report))
    raise SystemExit(2 if any(item["severity"] == "blocker" for item in report["findings"]) else 0)


if __name__ == "__main__":
    main()
