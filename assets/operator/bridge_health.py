#!/usr/bin/env python3
"""Phase 5 practical bridge-health report for the memory core."""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from _operator_utils import FRONTMATTER_RE, approval_packet, markdown_table, read_text, rel, vault_root


MANIFEST = Path("raw-sources/provenance/raw-local-manifest.jsonl")
GRAPH_READY = Path("12-shared/graph/graphify-out/GRAPH_READY.md")
GRAPH_REPORT = Path("12-shared/graph/graphify-out/GRAPH_REPORT.md")
AGENT_ID = os.environ.get("OBSIDIAN_AGENT_ID", "codex")
PRIVATE_ROOT = Path(os.environ.get("OBSIDIAN_PRIVATE_ROOT", f"12-{AGENT_ID}"))
GRAPH_REVIEW_STATE = Path("12-shared/graph/review-state.jsonl")
LESSON_LINT = Path("12-shared/scripts/lesson_lint.py")
MEMORY_OPERATOR = Path("12-shared/scripts/memory_operator.py")
SESSION_DRAFTS = PRIVATE_ROOT / "session-drafts"
MEMORY_ACTIVE = PRIVATE_ROOT / "memory_active.md"
MEMORY_CORRECTIONS = PRIVATE_ROOT / "memory_corrections.md"
LESSONS_DIR = PRIVATE_ROOT / "lessons"


@dataclass
class BridgeFinding:
    bridge: str
    status: str
    severity: str
    file: str
    issue: str
    next_step: str


ARTIFACT_CLASSES = {
    "canonical_git": [
        "wiki/",
        "12-shared/",
        "raw-sources/converted/",
        "raw-sources/provenance/",
    ],
    "local_raw_cache": [
        "raw-sources/pdfs/",
        "raw-sources/00 RAW INBOX/",
    ],
    "derived_reports": [
        "12-shared/graph/graphify-out/",
        "12-{agent}/retrieval-eval/",
        "output/memory-operator/",
    ],
    "review_state": [
        "12-shared/graph/review-state.jsonl",
        "12-{agent}/session-drafts/",
    ],
}


KNOWN_BACKLOG_BRIDGES = {
    "raw_to_converted",
    "converted_to_summary",
    "graph_action_to_review_state",
    "session_draft_to_memory_active",
}


def parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    out: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line or line.startswith(" "):
            continue
        key, value = line.split(":", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def load_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    records: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            records.append({"_invalid": line})
    return records


def md_files(path: Path) -> list[Path]:
    return sorted(path.glob("*.md")) if path.exists() else []


def normalized_source(value: str) -> str:
    value = value.strip()
    match = re.search(r"\[\[([^|\]#]+)", value)
    if match:
        value = match.group(1)
    return value.removesuffix(".md")


def existing_rel(root: Path, value: str) -> bool:
    if not value:
        return False
    rel_path = normalized_source(value)
    candidates = [root / rel_path, root / f"{rel_path}.md"]
    return any(path.exists() for path in candidates)


def bridge_raw_to_converted(root: Path) -> list[BridgeFinding]:
    findings: list[BridgeFinding] = []
    for record in load_jsonl(root / MANIFEST):
        source = str(record.get("local_cache_path", ""))
        if source.startswith("raw-sources/articles/"):
            continue
        converted = str(record.get("converted_path", ""))
        archive_status = str(record.get("archive_status", ""))
        if archive_status == "blocked_zero_byte":
            findings.append(
                BridgeFinding("raw_to_converted", "broken", "warn", source or rel(root / MANIFEST, root), "RAW source is blocked zero-byte", "replace the bad RAW source before conversion")
            )
        elif converted and not existing_rel(root, converted):
            findings.append(
                BridgeFinding("raw_to_converted", "broken", "warn", converted, "manifest converted_path does not exist", "regenerate provenance or restore converted markdown")
            )
        elif not converted:
            findings.append(
                BridgeFinding("raw_to_converted", "unreviewed", "info", source or rel(root / MANIFEST, root), "RAW source has no converted markdown yet", "leave as backlog or schedule conversion pilot")
            )
    return findings


def converted_summary_map(root: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for path in md_files(root / "wiki/summaries"):
        fm = parse_frontmatter(read_text(path))
        source = normalized_source(fm.get("source_file", ""))
        if source.startswith("raw-sources/converted/"):
            mapping[source] = rel(path, root)
    return mapping


def bridge_converted_to_summary(root: Path) -> list[BridgeFinding]:
    findings: list[BridgeFinding] = []
    summaries = converted_summary_map(root)
    for path in md_files(root / "raw-sources/converted"):
        fm = parse_frontmatter(read_text(path))
        if fm.get("conversion_status", "").startswith("blocked"):
            continue
        key = rel(path, root).removesuffix(".md")
        if key not in summaries:
            findings.append(
                BridgeFinding("converted_to_summary", "unreviewed", "warn", rel(path, root), "converted source has no summary bridge", "create/link a wiki summary or mark as intentionally parked")
            )
    return findings


def bridge_summary_to_domain(root: Path) -> list[BridgeFinding]:
    findings: list[BridgeFinding] = []
    domain_text = "\n".join(read_text(path) for path in md_files(root / "wiki/domains"))
    index_text = read_text(root / "wiki/index.md")
    combined = f"{domain_text}\n{index_text}"
    for path in md_files(root / "wiki/summaries"):
        stem = path.stem
        path_rel = rel(path, root)
        if stem not in combined and path_rel not in combined:
            findings.append(
                BridgeFinding("summary_to_domain", "stale", "warn", path_rel, "summary is not visible from domain MOCs or index", "link from a relevant domain page or wiki/index.md")
            )
    return findings


def bridge_wiki_to_graph(root: Path) -> list[BridgeFinding]:
    findings: list[BridgeFinding] = []
    ready = root / GRAPH_READY
    report = root / GRAPH_REPORT
    if not ready.exists() or not report.exists():
        return [
            BridgeFinding("wiki_to_graph", "broken", "warn", rel(ready, root), "graph reports are missing", "regenerate graph reports before graph review")
        ]
    ready_text = read_text(ready)
    if "type: `create_missing_page`; status: `open`" in ready_text:
        findings.append(
            BridgeFinding("wiki_to_graph", "stale", "warn", rel(ready, root), "graph queue still contains missing-page actions", "rerun graph extraction/review after the Phase 3.5 wiki-lint cleanup")
        )
    return findings


def open_graph_ids(text: str) -> set[str]:
    return set(re.findall(r"`(gq-[a-f0-9]+)`", text))


def reviewed_graph_ids(records: Iterable[dict[str, object]]) -> set[str]:
    ids: set[str] = set()
    for record in records:
        value = record.get("id") or record.get("action_id") or record.get("graph_action_id")
        if isinstance(value, str) and value.startswith("gq-"):
            ids.add(value)
    return ids


def bridge_graph_action_to_review_state(root: Path) -> list[BridgeFinding]:
    ready = root / GRAPH_READY
    if not ready.exists():
        return []
    open_ids = open_graph_ids(read_text(ready))
    reviewed = reviewed_graph_ids(load_jsonl(root / GRAPH_REVIEW_STATE))
    missing = sorted(open_ids - reviewed)
    if not missing:
        return []
    sample = ", ".join(missing[:8])
    if len(missing) > 8:
        sample += f", ... (+{len(missing) - 8} more)"
    return [
        BridgeFinding(
            "graph_action_to_review_state",
            "unreviewed",
            "warn",
            rel(ready, root),
            f"{len(missing)} open graph action(s) have no review-state record: {sample}",
            "run graph_review dry-run and accept/skip/obsolete stale actions",
        )
    ]


def correction_sections(root: Path) -> int:
    text = read_text(root / MEMORY_CORRECTIONS)
    return len(re.findall(r"^##\s+\d{4}-\d{2}-\d{2}\b", text, flags=re.MULTILINE))


def lesson_count(root: Path) -> int:
    return len([path for path in (root / LESSONS_DIR).glob("*.md") if path.name != "README.md"]) if (root / LESSONS_DIR).exists() else 0


def bridge_correction_to_lesson(root: Path) -> list[BridgeFinding]:
    corrections = correction_sections(root)
    lessons = lesson_count(root)
    if corrections and lessons == 0:
        return [
            BridgeFinding(
                "correction_to_lesson",
                "unreviewed",
                "warn",
                rel(root / MEMORY_CORRECTIONS, root),
                f"{corrections} correction section(s), but no operational lesson files yet",
                "create reviewed lesson candidates for repeated/high-impact corrections, starting as draft cases",
            )
        ]
    return []


def bridge_lesson_to_gate(root: Path) -> list[BridgeFinding]:
    operator_text = read_text(root / MEMORY_OPERATOR)
    if not (root / LESSON_LINT).exists() or "lesson_lint.py" not in operator_text or "check-all" not in operator_text:
        return [
            BridgeFinding("lesson_to_gate", "broken", "blocker", rel(root / MEMORY_OPERATOR, root), "lesson lint is not wired into check-all", "wire lesson_lint into memory_operator.py check-all")
        ]
    return []


def bridge_session_draft_to_memory_active(root: Path) -> list[BridgeFinding]:
    drafts = md_files(root / SESSION_DRAFTS)
    if not drafts:
        return []
    active = root / MEMORY_ACTIVE
    active_mtime = active.stat().st_mtime if active.exists() else 0
    newer = [path for path in drafts if path.stat().st_mtime > active_mtime]
    if newer:
        latest = rel(newer[-1], root)
        return [
            BridgeFinding(
                "session_draft_to_memory_active",
                "unreviewed",
                "info",
                latest,
                f"{len(newer)} session draft(s) are newer than memory_active.md",
                "review drafts during session closeout; copy only durable facts into canonical memory",
            )
        ]
    return []


def collect(root: Path) -> list[BridgeFinding]:
    findings: list[BridgeFinding] = []
    for bridge in (
        bridge_raw_to_converted,
        bridge_converted_to_summary,
        bridge_summary_to_domain,
        bridge_wiki_to_graph,
        bridge_graph_action_to_review_state,
        bridge_correction_to_lesson,
        bridge_lesson_to_gate,
        bridge_session_draft_to_memory_active,
    ):
        findings.extend(bridge(root))
    return findings


def render_markdown(root: Path, findings: list[BridgeFinding]) -> str:
    counts: dict[str, int] = {}
    for item in findings:
        counts[item.status] = counts.get(item.status, 0) + 1
    bridge_names = [
        "raw_to_converted",
        "converted_to_summary",
        "summary_to_domain",
        "wiki_to_graph",
        "graph_action_to_review_state",
        "correction_to_lesson",
        "lesson_to_gate",
        "session_draft_to_memory_active",
    ]
    unhealthy = {item.bridge for item in findings}
    healthy = [name for name in bridge_names if name not in unhealthy]
    lines = [
        "# BRIDGE_HEALTH practical bridge report",
        "",
        "Nothing changed. This is a practical bridge report: broken/stale/unreviewed/healthy plus the next script-checkable step.",
        "",
        "## Summary",
        markdown_table(
            ["status", "count"],
            [
                ["broken", counts.get("broken", 0)],
                ["stale", counts.get("stale", 0)],
                ["unreviewed", counts.get("unreviewed", 0)],
                ["healthy", len(healthy)],
            ],
        ),
        "",
        "## Healthy Bridges",
        ", ".join(healthy) if healthy else "_None._",
        "",
        "## Findings",
        markdown_table(
            ["bridge", "status", "severity", "file", "issue", "next_step"],
            ([f.bridge, f.status, f.severity, f.file, f.issue, f.next_step] for f in findings[:200]),
        ) if findings else "_No findings._",
        "",
        approval_packet(
            "BRIDGE_HEALTH",
            [
                str(MANIFEST),
                "raw-sources/converted/",
                "wiki/summaries/",
                "wiki/domains/",
                str(GRAPH_READY),
                str(GRAPH_REVIEW_STATE),
                f"{PRIVATE_ROOT.as_posix()}/lessons/",
                f"{PRIVATE_ROOT.as_posix()}/session-drafts/",
            ],
            files_to_write=[],
            risks=["reports can surface stale derived graph queues that need regeneration, not manual wiki edits"],
            verification=["python3 assets/operator/bridge_health.py --vault /path/to/vault", "run your local release gate after reviewing findings"],
        ),
    ]
    if len(findings) > 200:
        lines.insert(-2, f"\n_Showing first 200 findings of {len(findings)}._\n")
    return "\n".join(lines)


def finding_bucket(item: BridgeFinding) -> str:
    if item.severity == "blocker":
        return "blocker"
    if item.bridge in KNOWN_BACKLOG_BRIDGES and item.status in {"unreviewed", "stale"}:
        return "known_backlog"
    if item.severity == "warn":
        return "warn"
    return "info"


def status_report(root: Path, findings: list[BridgeFinding]) -> dict[str, object]:
    buckets = {"blocker": 0, "warn": 0, "known_backlog": 0, "info": 0}
    by_bridge: dict[str, dict[str, object]] = {}
    for item in findings:
        bucket = finding_bucket(item)
        buckets[bucket] += 1
        entry = by_bridge.setdefault(item.bridge, {"count": 0, "bucket": bucket, "severity": item.severity, "sample": item.file, "next_step": item.next_step})
        entry["count"] = int(entry["count"]) + 1
        if bucket == "blocker":
            entry["bucket"] = "blocker"
            entry["severity"] = item.severity
    return {
        "mode": "dry-run",
        "root": str(root),
        "artifact_classes": ARTIFACT_CLASSES,
        "buckets": buckets,
        "by_bridge": by_bridge,
        "findings": [asdict(item) | {"bucket": finding_bucket(item)} for item in findings],
    }


def render_status(root: Path, findings: list[BridgeFinding]) -> str:
    report = status_report(root, findings)
    by_bridge = report["by_bridge"]
    assert isinstance(by_bridge, dict)
    rows = [
        [bridge, data["count"], data["bucket"], data["severity"], data["sample"], data["next_step"]]
        for bridge, data in sorted(by_bridge.items())
    ]
    class_rows = [[name, ", ".join(paths)] for name, paths in ARTIFACT_CLASSES.items()]
    return "\n".join(
        [
            "# MEMORY_STORAGE_STATUS",
            "",
            "Read-only dashboard. Known backlog is visible here without becoming a release blocker.",
            "",
            "## Artifact Classes",
            markdown_table(["class", "paths"], class_rows),
            "",
            "## Buckets",
            markdown_table(["bucket", "count"], sorted(report["buckets"].items())),  # type: ignore[index]
            "",
            "## Bridge Summary",
            markdown_table(["bridge", "count", "bucket", "severity", "sample", "next_step"], rows) if rows else "_No findings._",
        ]
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Read-only Phase 5 bridge-health report")
    ap.add_argument("--vault", default=str(vault_root()))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--status", action="store_true", help="Render storage/bridge status dashboard")
    args = ap.parse_args()

    root = Path(args.vault).resolve()
    findings = collect(root)
    if args.json:
        if args.status:
            print(json.dumps(status_report(root, findings), ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"mode": "dry-run", "findings": [asdict(item) for item in findings]}, ensure_ascii=False, indent=2))
    elif args.status:
        print(render_status(root, findings))
    else:
        print(render_markdown(root, findings))
    raise SystemExit(1 if any(item.severity == "blocker" for item in findings) else 0)


if __name__ == "__main__":
    main()
