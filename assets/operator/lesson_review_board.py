#!/usr/bin/env python3
"""Read-only review board for private agent operational lessons."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from _operator_utils import markdown_table, rel, vault_root
from lesson_lint import as_int, lint, lesson_files, parse_frontmatter, read_text


SCHEMA_VERSION = "lesson-review-board.v1"


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def anchor_value(anchors: Any, key: str) -> str:
    if not isinstance(anchors, dict):
        return ""
    value = anchors.get(key, "")
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    return str(value)


def lesson_record(path: Path, root: Path, blocked_paths: set[str]) -> dict[str, Any]:
    fm = parse_frontmatter(read_text(path))
    anchors = fm.get("anchors", {})
    lesson_type = str(fm.get("type", ""))
    status = str(fm.get("status", ""))
    human_reviewed = bool_value(fm.get("human_reviewed", False))
    confirmed = as_int(fm.get("confirmed_count")) or 0
    contradicted = as_int(fm.get("contradicted_count")) or 0
    path_rel = rel(path, root)

    if path_rel in blocked_paths:
        classification = "blocked"
        action = "resolve_blocker"
        reason = "lesson_lint contains a blocker finding"
    elif contradicted > confirmed or status == "weakened":
        classification = "deprecated_candidate"
        action = "consider_deprecate"
        reason = "contradictions outweigh confirmations or lesson is weakened"
    elif lesson_type == "case" and status == "draft":
        classification = "draft_case"
        action = "human_review" if not human_reviewed else "keep_draft"
        reason = "draft case needs review before promotion"
    elif lesson_type == "case" and status == "active":
        classification = "active_case"
        action = "human_review" if not human_reviewed else "keep_draft"
        reason = "active case is not promoted automatically"
    else:
        classification = "blocked" if not human_reviewed and lesson_type in {"pattern", "principle"} and status == "active" else "draft_case"
        action = "human_review" if not human_reviewed else "keep_draft"
        reason = "review is required before further use"

    return {
        "id": str(fm.get("id", path.stem)),
        "path": path_rel,
        "type": lesson_type,
        "status": status,
        "human_reviewed": human_reviewed,
        "confidence_1_5": as_int(fm.get("confidence_1_5")),
        "impact_1_5": as_int(fm.get("impact_1_5")),
        "confirmed_count": confirmed,
        "contradicted_count": contradicted,
        "anchors": {
            "domain": anchor_value(anchors, "domain"),
            "purpose": anchor_value(anchors, "purpose"),
            "method": anchor_value(anchors, "method"),
        },
        "classification": classification,
        "recommended_action": action,
        "reason": reason,
    }


def promotion_groups(lessons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for lesson in lessons:
        if lesson["type"] != "case":
            continue
        anchors = lesson.get("anchors", {})
        key = "|".join([anchors.get("domain", ""), anchors.get("purpose", ""), anchors.get("method", "")])
        if key == "||":
            continue
        groups.setdefault(key, []).append(lesson)

    out: list[dict[str, Any]] = []
    for key, cases in sorted(groups.items()):
        if len(cases) < 2:
            continue
        eligible = all(int(case.get("confirmed_count") or 0) >= 1 and case.get("classification") != "blocked" for case in cases)
        out.append(
            {
                "group_key": key,
                "case_ids": [case["id"] for case in cases],
                "eligible_for_pattern_review": eligible,
                "reason": "2+ cases share domain/purpose/method" if eligible else "group has 2+ cases but at least one case is not confirmed or is blocked",
            }
        )
    return out


def collect(root: Path, agent: str = "agent") -> dict[str, Any]:
    lint_findings = lint(root, agent)
    blocked_paths = {item.file for item in lint_findings if item.severity == "blocker"}
    lessons = [lesson_record(path, root, blocked_paths) for path in lesson_files(root, agent)]
    groups = promotion_groups(lessons)
    group_ids = {lesson_id for group in groups if group["eligible_for_pattern_review"] for lesson_id in group["case_ids"]}
    for lesson in lessons:
        if lesson["id"] in group_ids and lesson["classification"] != "blocked":
            lesson["classification"] = "promotion_candidate"
            lesson["recommended_action"] = "consider_pattern"
            lesson["reason"] = "2+ similar confirmed cases are ready for human pattern review"

    summary = {
        "total": len(lessons),
        "draft": sum(1 for item in lessons if item["status"] == "draft"),
        "active": sum(1 for item in lessons if item["status"] == "active"),
        "weakened": sum(1 for item in lessons if item["status"] == "weakened"),
        "deprecated": sum(1 for item in lessons if item["status"] == "deprecated"),
        "human_reviewed_false": sum(1 for item in lessons if not item["human_reviewed"]),
        "lint_blockers": len(blocked_paths),
    }
    findings: list[Finding] = []
    for item in lint_findings:
        if item.severity == "blocker":
            findings.append(Finding("blocker", "lesson_lint_blocker", f"{item.file}: {item.issue}"))
    for lesson in lessons:
        if lesson["type"] in {"pattern", "principle"} and lesson["status"] == "active" and not lesson["human_reviewed"]:
            findings.append(Finding("blocker", "active_unreviewed_lesson", f"{lesson['id']} active without human_reviewed:true"))
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "dry-run",
        "agent": agent,
        "summary": summary,
        "lessons": lessons,
        "promotion_groups": groups,
        "findings": [asdict(item) for item in findings],
    }


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# LESSON_REVIEW dry-run",
            "",
            "Nothing changed. This board shows the review queue for procedural memory.",
            "",
            "## Summary",
            markdown_table(["metric", "count"], sorted(report["summary"].items())),
            "",
            "## Lessons",
            markdown_table(
                ["id", "type", "status", "reviewed", "classification", "action", "reason"],
                ([item["id"], item["type"], item["status"], item["human_reviewed"], item["classification"], item["recommended_action"], item["reason"]] for item in report["lessons"]),
            ) if report["lessons"] else "_No lessons._",
            "",
            "## Promotion Groups",
            markdown_table(
                ["group_key", "case_ids", "eligible", "reason"],
                ([item["group_key"], ", ".join(item["case_ids"]), item["eligible_for_pattern_review"], item["reason"]] for item in report["promotion_groups"]),
            ) if report["promotion_groups"] else "_No promotion groups._",
            "",
            "## Findings",
            markdown_table(["severity", "code", "message"], ([f["severity"], f["code"], f["message"]] for f in report["findings"])) if report["findings"] else "_No findings._",
        ]
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Render a read-only lesson review board")
    fmt = ap.add_mutually_exclusive_group()
    fmt.add_argument("--md", action="store_true")
    fmt.add_argument("--json", action="store_true")
    ap.add_argument("--root", "--vault", dest="root", default=str(vault_root()))
    ap.add_argument("--agent", default="agent")
    args = ap.parse_args()

    report = collect(Path(args.root).resolve(), args.agent)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report))
    raise SystemExit(2 if any(item["severity"] == "blocker" for item in report["findings"]) else 0)


if __name__ == "__main__":
    main()
