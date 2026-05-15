#!/usr/bin/env python3
"""Dry-run lint for private agent operational lessons."""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from _operator_utils import approval_packet, markdown_table, rel, vault_root

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
LESSON_TYPES = {"case", "pattern", "principle"}
STATUSES = {"draft", "active", "weakened", "deprecated"}
REQUIRED_FIELDS = {
    "id",
    "type",
    "status",
    "created",
    "updated",
    "source",
    "confidence_1_5",
    "impact_1_5",
    "confirmed_count",
    "contradicted_count",
    "anchors",
    "summary",
    "rule",
    "evidence",
}
REQUIRED_ANCHORS = {
    "domain",
    "situation",
    "trigger",
    "stakes",
    "actors",
    "environment",
    "circumstances",
    "purpose",
    "method",
}


@dataclass
class Finding:
    severity: str
    file: str
    issue: str
    suggested_fix: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"", "null", "None"}:
        return ""
    if value == "[]":
        return []
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        return value


def parse_simple_mapping(lines: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for line in lines:
        stripped = line.strip()
        if ":" not in stripped or stripped.startswith("- "):
            continue
        key, value = stripped.split(":", 1)
        out[key.strip()] = parse_scalar(value)
    return out


def parse_simple_list(lines: list[str]) -> list[Any]:
    items: list[Any] = []
    current: dict[str, Any] | None = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- "):
            if current is not None:
                items.append(current)
                current = None
            rest = stripped[2:].strip()
            if ":" in rest:
                key, value = rest.split(":", 1)
                current = {key.strip(): parse_scalar(value)}
            else:
                items.append(parse_scalar(rest))
            continue
        if current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key.strip()] = parse_scalar(value)
    if current is not None:
        items.append(current)
    return items


def parse_simple_yaml(raw: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.startswith(" "):
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            out[key] = parse_scalar(value)
            i += 1
            continue

        block: list[str] = []
        i += 1
        while i < len(lines) and (lines[i].startswith("  ") or not lines[i].strip()):
            if lines[i].strip():
                block.append(lines[i])
            i += 1
        if not block:
            out[key] = ""
        elif block[0].lstrip().startswith("- "):
            out[key] = parse_simple_list(block)
        else:
            out[key] = parse_simple_mapping(block)
    return out


def parse_frontmatter(text: str) -> dict[str, Any]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    raw = match.group(1)
    if yaml is not None:
        loaded = yaml.safe_load(raw) or {}
        return loaded if isinstance(loaded, dict) else {}
    return parse_simple_yaml(raw)


def lessons_dir(root: Path, agent: str) -> Path:
    return root / f"12-{agent}" / "lessons"


def lesson_files(root: Path, agent: str = "agent") -> list[Path]:
    base = lessons_dir(root, agent)
    if not base.exists():
        return []
    return [path for path in sorted(base.rglob("*.md")) if path.is_file() and path.name.lower() != "readme.md"]


def is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def validate_lesson(path: Path, root: Path) -> list[Finding]:
    path_rel = rel(path, root)
    fm = parse_frontmatter(read_text(path))
    findings: list[Finding] = []
    if not fm:
        return [Finding("blocker", path_rel, "missing or invalid YAML frontmatter", "add the required lesson schema frontmatter")]

    missing = sorted(field for field in REQUIRED_FIELDS if field not in fm)
    if missing:
        findings.append(Finding("blocker", path_rel, f"missing required fields: {', '.join(missing)}", "fill all required lesson fields before activation or promotion"))

    lesson_id = str(fm.get("id", "")).strip()
    if lesson_id and not re.fullmatch(r"(case|pattern|principle)-[a-z0-9][a-z0-9-]*", lesson_id):
        findings.append(Finding("warn", path_rel, f"id has non-standard format: {lesson_id}", "use case-*, pattern-*, or principle-* slug identifiers"))
    if lesson_id and path.stem != lesson_id:
        findings.append(Finding("warn", path_rel, f"filename does not match id: {lesson_id}", "rename file or update id so stable references are unambiguous"))

    lesson_type = str(fm.get("type", "")).strip()
    if lesson_type and lesson_type not in LESSON_TYPES:
        findings.append(Finding("blocker", path_rel, f"invalid type: {lesson_type}", f"use one of: {', '.join(sorted(LESSON_TYPES))}"))
    status = str(fm.get("status", "")).strip()
    if status and status not in STATUSES:
        findings.append(Finding("blocker", path_rel, f"invalid status: {status}", f"use one of: {', '.join(sorted(STATUSES))}"))

    for field in ("confidence_1_5", "impact_1_5"):
        value = as_int(fm.get(field))
        if value is None or value < 1 or value > 5:
            findings.append(Finding("blocker", path_rel, f"{field} must be integer 1..5", "set a calibrated 1..5 score"))
    for field in ("confirmed_count", "contradicted_count"):
        value = as_int(fm.get(field))
        if value is None or value < 0:
            findings.append(Finding("blocker", path_rel, f"{field} must be a non-negative integer", "set 0 or a positive count"))
    for field in ("source", "summary", "rule", "evidence"):
        if field in fm and is_blank(fm.get(field)):
            findings.append(Finding("blocker", path_rel, f"{field} must not be empty", "record the source/evidence before trusting this lesson"))

    anchors = fm.get("anchors")
    if not isinstance(anchors, dict):
        findings.append(Finding("blocker", path_rel, "anchors must be a mapping", "add the required context anchors under anchors:"))
    else:
        missing_anchors = sorted(anchor for anchor in REQUIRED_ANCHORS if is_blank(anchors.get(anchor)))
        if missing_anchors:
            findings.append(Finding("blocker", path_rel, f"anchors missing values: {', '.join(missing_anchors)}", "fill every required context anchor"))

    contradictions = fm.get("contradictions", [])
    if contradictions is None:
        contradictions = []
    if not isinstance(contradictions, list):
        findings.append(Finding("blocker", path_rel, "contradictions must be a list", "use contradictions: [] or a list of records"))

    human_reviewed = bool(fm.get("human_reviewed", False))
    if lesson_type == "pattern" and status in {"active", "weakened", "deprecated"}:
        if len(as_list(fm.get("source_cases"))) < 2:
            findings.append(Finding("blocker", path_rel, "active pattern needs at least 2 source_cases", "keep as draft or link 2+ reviewed cases"))
        if not human_reviewed:
            findings.append(Finding("blocker", path_rel, "active pattern needs human_reviewed: true", "promote only after explicit human review"))
    if lesson_type == "principle" and status in {"active", "weakened", "deprecated"}:
        source_patterns = as_list(fm.get("source_patterns"))
        domains = as_list((anchors or {}).get("domain")) if isinstance(anchors, dict) else []
        if len(source_patterns) < 2 and len(domains) < 2:
            findings.append(Finding("blocker", path_rel, "active principle needs 2+ source_patterns or 2+ domains", "keep as draft until cross-pattern or cross-domain evidence exists"))
        if not human_reviewed:
            findings.append(Finding("blocker", path_rel, "active principle needs human_reviewed: true", "promote only after explicit human review"))
    return findings


def lint(root: Path, agent: str = "agent") -> list[Finding]:
    findings: list[Finding] = []
    base = lessons_dir(root, agent)
    readme = base / "README.md"
    if not base.exists():
        return [Finding("warn", rel(base, root), "lessons directory is missing", f"create 12-{agent}/lessons/README.md before adding operational lessons")]
    if not readme.exists():
        findings.append(Finding("warn", rel(readme, root), "lessons README is missing", "document the operational lessons schema and rollback policy"))
    for path in lesson_files(root, agent):
        findings.extend(validate_lesson(path, root))
    return findings


def render_markdown(findings: list[Finding], agent: str) -> str:
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    return "\n".join(
        [
            "# LESSON_LINT dry-run",
            "",
            f"Ничего не изменено. Проверяется только private operational lessons слой `12-{agent}/lessons`.",
            "",
            "## Summary",
            markdown_table(["severity", "count"], ([key, counts[key]] for key in ("blocker", "warn", "info") if key in counts)) if counts else "_No findings._",
            "",
            "## Findings",
            markdown_table(["severity", "file", "issue", "suggested_fix"], ([f.severity, f.file, f.issue, f.suggested_fix] for f in findings)) if findings else "_No findings._",
            "",
            approval_packet(
                "LESSON_LINT",
                [f"12-{agent}/lessons/"],
                files_to_write=[],
                risks=["invalid lessons can cause future false activation if promoted without review"],
                verification=["python3 assets/operator/lesson_lint.py", "git status --short"],
            ),
        ]
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Dry-run lint for private agent operational lessons")
    ap.add_argument("--vault", "--root", dest="vault", default=str(vault_root()))
    ap.add_argument("--agent", default="agent")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = Path(args.vault).resolve()
    findings = lint(root, args.agent)
    if args.json:
        print(json.dumps({"mode": "dry-run", "agent": args.agent, "findings": [asdict(item) for item in findings]}, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(findings, args.agent))
    raise SystemExit(1 if any(item.severity == "blocker" for item in findings) else 0)


if __name__ == "__main__":
    main()
