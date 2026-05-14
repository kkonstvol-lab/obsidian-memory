#!/usr/bin/env python3
"""Dry-run audit for local skill repositories.

The script compares public skill repos against installed skill folders and
prints drift, git status, file counts, and redacted secret-scan findings.
It never copies, edits, stages, commits, or pushes anything.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from _operator_utils import markdown_table, rel


DEFAULT_REPOS = {
    "example-agents": {
        "repo": "{YOUR_REPO_PATH}",
        "skills_dir": "agent-skills",
        "installed": "{YOUR_AGENT_SKILLS_DIR}",
        "remote": "{YOUR_REMOTE_URL}",
    },
}

SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", "dist", "build", ".next"}
TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".js",
    ".ts",
    ".py",
    ".sh",
    ".env",
}
SECRET_PATTERNS = [
    ("openai_key", re.compile(r"(?i)\bOPENAI_API_KEY\s*=\s*['\"]?([^'\"\s]+)")),
    ("generic_sk_key", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{20,}")),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]


@dataclass
class RepoAudit:
    name: str
    repo: str
    installed: str
    status: str
    git_status: str
    remote_ok: bool
    repo_skill_count: int
    installed_skill_count: int
    missing_skill_files: list[str]
    missing_in_repo: list[str]
    extra_in_repo: list[str]
    repo_file_count: int
    installed_file_count: int
    secret_findings: list[str]
    resolver_findings: list[dict[str, str]]
    resolver_summary: dict[str, int]


TRIGGER_RE = re.compile(r"(?i)(description:|use when|trigger|triggers|when to use|когда использовать|используй)")
TRIGGER_STOP_TERMS = {
    "about",
    "after",
    "almost",
    "analysis",
    "before",
    "being",
    "changes",
    "clearly",
    "coding",
    "command",
    "commands",
    "context",
    "create",
    "creating",
    "current",
    "default",
    "description",
    "direction",
    "especially",
    "existing",
    "explicit",
    "explicitly",
    "files",
    "generate",
    "handling",
    "include",
    "including",
    "implementation",
    "local",
    "mentions",
    "needs",
    "other",
    "prefer",
    "project",
    "quality",
    "report",
    "requests",
    "reviewing",
    "skill",
    "tasks",
    "terms",
    "using",
    "visual",
    "wants",
    "whenever",
    "workflow",
    "workflows",
    "working",
    "write",
    "использовать",
    "используй",
    "запускай",
    "когда",
    "команды",
    "перед",
    "только",
}
OVERLAP_WARN_TERMS = {
    "agent",
    "audit",
    "automation",
    "browser",
    "content",
    "design",
    "figma",
    "frontend",
    "google",
    "markdown",
    "memory",
    "notebooklm",
    "obsidian",
    "openclaw",
    "pdf",
    "research",
    "security",
    "seo",
    "vault",
}


def git(repo: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(["git", "-C", str(repo), *args], check=False, text=True, capture_output=True)
    except FileNotFoundError:
        return "git-not-found"
    return (result.stdout or result.stderr).strip()


def skill_names(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {p.parent.name for p in path.glob("*/SKILL.md") if p.is_file()}


def skill_dirs_missing_skill_md(path: Path) -> list[str]:
    if not path.exists():
        return []
    missing: list[str] = []
    for item in sorted(path.iterdir()):
        if not item.is_dir() or item.name in SKIP_DIRS:
            continue
        if not (item / "SKILL.md").is_file():
            missing.append(item.name)
    return missing


def count_files(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for item in path.rglob("*"):
        if item.is_dir() and item.name in SKIP_DIRS:
            continue
        if item.is_file() and not any(part in SKIP_DIRS for part in item.parts):
            total += 1
    return total


def secret_scan(path: Path, limit: int = 50) -> list[str]:
    findings: list[str] = []
    if not path.exists():
        return findings
    for item in sorted(path.rglob("*")):
        if len(findings) >= limit:
            break
        if not item.is_file() or any(part in SKIP_DIRS for part in item.parts):
            continue
        if item.suffix not in TEXT_SUFFIXES and item.name != ".env":
            continue
        try:
            if item.stat().st_size > 1_000_000:
                continue
            text = item.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line in text.splitlines():
            for label, pattern in SECRET_PATTERNS:
                match = pattern.search(line)
                if not match:
                    continue
                if is_placeholder_secret(label, match):
                    continue
                findings.append(f"{rel(item, path)}:{label}:redacted")
                break
            if findings and findings[-1].startswith(rel(item, path) + ":"):
                break
    return findings


def is_placeholder_secret(label: str, match: re.Match) -> bool:
    if label == "openai_key":
        value = match.group(1).strip().strip('"').strip("'")
        return value in {"...", "sk-...", "<key>", "<your-key>", "YOUR_OPENAI_API_KEY"} or "your" in value.lower()
    value = match.group(0)
    return "..." in value or "<" in value or "YOUR_" in value


def read_skill(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def trigger_terms(text: str) -> set[str]:
    terms: set[str] = set()
    for line in text.splitlines():
        if not TRIGGER_RE.search(line):
            continue
        for term in re.findall(r"[A-Za-zА-Яа-я0-9][A-Za-zА-Яа-я0-9_-]{4,}", line.lower()):
            if term not in TRIGGER_STOP_TERMS and term not in {"trigger", "triggers"}:
                terms.add(term)
    return terms


def resolver_health(skills_dir: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    skill_paths = sorted(skills_dir.glob("*/SKILL.md")) if skills_dir.exists() else []
    trigger_index: dict[str, list[str]] = {}
    for name in skill_dirs_missing_skill_md(skills_dir):
        findings.append({"severity": "warn", "skill": name, "issue": "skill folder missing SKILL.md", "action": "either add SKILL.md or move the folder outside the skill root"})
    for skill_path in skill_paths:
        name = skill_path.parent.name
        text = read_skill(skill_path)
        lower = text.lower()
        mutating = any(term in lower for term in ("write", "edit", "create", "update", "delete", "install", "deploy", "commit", "push", "modify", "rewrite"))
        if mutating and "verification" not in lower and "verify" not in lower and "test" not in lower:
            findings.append({"severity": "info", "skill": name, "issue": "missing verification section", "action": "add explicit verification expectations when the skill mutates files or external state"})
        if "owner" not in lower and "owns:" not in lower and "role" not in lower:
            findings.append({"severity": "info", "skill": name, "issue": "unclear ownership", "action": "state what this skill owns and does not own"})
        if "always" in lower and "do not auto" not in lower and "explicit" not in lower and "mandatory" not in lower:
            findings.append({"severity": "warn", "skill": name, "issue": "possible auto-trigger risk", "action": "confirm whether always-on language is intentional and bounded"})
        terms = trigger_terms(text)
        if not terms:
            findings.append({"severity": "warn", "skill": name, "issue": "missing discoverable trigger terms", "action": "add clear trigger phrases to SKILL.md frontmatter or When to Use section"})
        for term in terms:
            trigger_index.setdefault(term, []).append(name)
    for term, names in sorted(trigger_index.items()):
        unique = sorted(set(names))
        if len(unique) >= 3:
            severity = "warn" if term in OVERLAP_WARN_TERMS else "info"
            findings.append({"severity": severity, "skill": ", ".join(unique[:6]), "issue": f"overlapping trigger term: {term}", "action": "review routing specificity or add disambiguation rules"})
    return sorted(findings, key=finding_sort_key)[:100]


def finding_sort_key(item: dict[str, str]) -> tuple[int, str, str]:
    rank = {"error": 0, "warn": 1, "info": 2}
    return (rank.get(item.get("severity", "info"), 3), item.get("skill", ""), item.get("issue", ""))


def summarize_findings(findings: list[dict[str, str]]) -> dict[str, int]:
    summary = {"error": 0, "warn": 0, "info": 0, "total": len(findings)}
    for item in findings:
        severity = item.get("severity", "info")
        summary[severity] = summary.get(severity, 0) + 1
    return summary


def audit_status(repo_exists: bool, remote_ok: bool, secret_hits: int, resolver_summary: dict[str, int]) -> str:
    if not repo_exists or not remote_ok or secret_hits:
        return "error"
    if resolver_summary.get("warn", 0):
        return "warn"
    return "ok"


def audit_one(name: str, spec: dict) -> RepoAudit:
    repo = Path(spec["repo"]).resolve()
    installed = Path(spec["installed"]).resolve()
    repo_skills_dir = repo / spec["skills_dir"]
    repo_skills = skill_names(repo_skills_dir)
    installed_skills = skill_names(installed)
    status = git(repo, ["status", "--short", "--branch"]) if repo.exists() else "repo-missing"
    remote = git(repo, ["remote", "get-url", "origin"]) if repo.exists() else ""
    expected_remote = spec.get("remote", "")
    remote_ok = True if expected_remote in {"", "{YOUR_REMOTE_URL}"} else remote == expected_remote
    resolver_findings = resolver_health(repo_skills_dir)
    resolver_summary = summarize_findings(resolver_findings)
    secret_findings = secret_scan(repo)
    return RepoAudit(
        name=name,
        repo=str(repo),
        installed=str(installed),
        status=audit_status(repo.exists(), remote == spec["remote"], len(secret_findings), resolver_summary),
        git_status=status,
        remote_ok=remote_ok,
        repo_skill_count=len(repo_skills),
        installed_skill_count=len(installed_skills),
        missing_skill_files=skill_dirs_missing_skill_md(repo_skills_dir),
        missing_in_repo=sorted(installed_skills - repo_skills),
        extra_in_repo=sorted(repo_skills - installed_skills),
        repo_file_count=count_files(repo_skills_dir),
        installed_file_count=count_files(installed),
        secret_findings=secret_findings,
        resolver_findings=resolver_findings,
        resolver_summary=resolver_summary,
    )


def render_markdown(audits: list[RepoAudit]) -> str:
    rows = (
        [
            a.name,
            a.status,
            a.repo_skill_count,
            a.installed_skill_count,
            len(a.missing_skill_files),
            len(a.missing_in_repo),
            len(a.extra_in_repo),
            "yes" if a.remote_ok else "no",
            len(a.secret_findings),
            f"{a.resolver_summary.get('warn', 0)} warn / {a.resolver_summary.get('info', 0)} info",
        ]
        for a in audits
    )
    lines = [
        "# SKILL_REPO_AUDIT dry-run",
        "",
        "Ничего не скопировано, не изменено, не закоммичено и не запушено.",
        "",
        markdown_table(["repo", "status", "repo_skills", "installed_skills", "missing_skill_md", "missing", "extra", "remote_ok", "secret_hits", "resolver_findings"], rows),
        "",
    ]
    for audit in audits:
        lines.extend(
            [
                f"## {audit.name}",
                "",
                f"- Repo: `{audit.repo}`",
                f"- Installed: `{audit.installed}`",
                f"- Git status: `{audit.git_status.replace(chr(10), ' | ')}`",
                f"- Status: `{audit.status}`",
                f"- Missing SKILL.md folders: {', '.join(audit.missing_skill_files) or 'none'}",
                f"- Missing in repo: {', '.join(audit.missing_in_repo) or 'none'}",
                f"- Extra in repo: {', '.join(audit.extra_in_repo) or 'none'}",
                f"- Secret findings: {', '.join(audit.secret_findings) or 'none'}",
                f"- Resolver summary: {audit.resolver_summary.get('warn', 0)} warn, {audit.resolver_summary.get('info', 0)} info",
                "",
                "### Resolver Health",
                markdown_table(
                    ["severity", "skill", "issue", "action"],
                    ([item["severity"], item["skill"], item["issue"], item["action"]] for item in audit.resolver_findings[:20]),
                ) if audit.resolver_findings else "_No advisory resolver findings._",
                "",
            ]
        )
    lines.extend(
        [
            "## Approval Packet",
            "",
            "- Operation: `SKILL_REPO_SYNC`",
            "- Mode: `dry-run -> apply`",
            "- Files to read: local skill repos and installed skill folders",
            "- Files to write: none before approval",
            "- Files to move/copy: none before approval",
            "- Risks: copying installed skills may publish private or machine-local artifacts",
            "- Verification: rerun this audit, inspect git status, run repo-specific tests if present",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Dry-run audit for codex/agents skill repos")
    ap.add_argument("--repo", choices=sorted(DEFAULT_REPOS), action="append", help="Named repo from the built-in example defaults; repeatable")
    ap.add_argument("--repo-path", help="Path to a public skill repository checkout")
    ap.add_argument("--skills-dir", default="agent-skills", help="Skill directory inside --repo-path")
    ap.add_argument("--installed", help="Installed/runtime skill directory to compare against")
    ap.add_argument("--remote", default="", help="Expected origin URL; omit to skip strict remote check")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.repo_path:
        audits = [
            audit_one(
                "custom",
                {
                    "repo": args.repo_path,
                    "skills_dir": args.skills_dir,
                    "installed": args.installed or args.repo_path,
                    "remote": args.remote,
                },
            )
        ]
    else:
        names = args.repo or list(DEFAULT_REPOS)
        audits = [audit_one(name, DEFAULT_REPOS[name]) for name in names]
    if args.json:
        print(json.dumps({"mode": "dry-run", "audits": [asdict(a) for a in audits]}, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(audits))


if __name__ == "__main__":
    main()
