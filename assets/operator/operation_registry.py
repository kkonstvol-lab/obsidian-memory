#!/usr/bin/env python3
"""Declarative registry for memory-operator commands.

The registry is descriptive by design: scripts remain the implementation
source of truth, while this file makes safety posture and verification visible.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from _operator_utils import markdown_table, vault_root


@dataclass(frozen=True)
class Operation:
    name: str
    purpose: str
    mode: str
    approval_required: bool
    touched_areas: list[str]
    artifact_class: str
    verification: list[str]


OPERATIONS: tuple[Operation, ...] = (
    Operation("inbox_triage", "Classify local inbox items before ingest.", "read_only", False, ["00-inbox", "raw-sources"], "advisory_report", ["provide or wire a local inbox triage script"]),
    Operation("wiki_lint", "Check wiki schema, links, index visibility, and evidence hygiene.", "read_only", False, ["wiki"], "advisory_report", ["provide or wire a local wiki lint script"]),
    Operation("graph_review", "Prepare graph action review batches; apply only approved graph decisions.", "mutating", True, ["12-shared/graph", "wiki"], "review_state", ["review graph actions before editing wiki pages"]),
    Operation("compile_drawers", "Review drawer-to-wing compile candidates.", "mutating", True, ["wiki/drawers", "wiki/wings"], "canonical_git", ["review drawer drafts before writing canonical wing pages"]),
    Operation("skill_repo_audit", "Audit clean skill repos against installed skills.", "read_only", False, ["codex-skills", "agent-skills"], "advisory_report", ["python3 assets/operator/skill_repo_audit.py --repo-path /path/to/repo --installed /path/to/installed"]),
    Operation("operator_readiness", "Check operator prerequisites and routing readiness.", "read_only", False, ["12-shared", "12-{agent}"], "advisory_report", ["inspect required roots before mutating vault files"]),
    Operation("raw_inbox_import", "Import approved raw inbox files into canonical raw/articles/wiki paths.", "mutating", True, ["raw-sources", "wiki", "12-shared"], "canonical_git", ["plan first, then apply only after explicit approval"]),
    Operation("pdf_conversion_plan", "Plan PDF conversion backlog without converting files.", "read_only", False, ["raw-sources"], "advisory_report", ["generate a dry-run conversion plan"]),
    Operation("raw_provenance", "Verify RAW provenance manifest and source hashes.", "read_only", False, ["raw-sources/provenance"], "canonical_git", ["verify manifest rows against converted/wiki frontmatter"]),
    Operation("git_raw_guard", "Prevent tracked RAW binaries from entering Git history.", "read_only", False, ["raw-sources"], "release_gate", ["run a Git staged-file RAW guard before commit"]),
    Operation("lesson_lint", "Validate private agent lesson schema without activating lessons.", "read_only", False, ["12-{agent}/lessons"], "release_gate", ["lint lesson files before surfacing lesson candidates"]),
    Operation("memory_gates", "Run advisory memory-core release gates.", "read_only", False, ["12-{agent}", "12-shared", "wiki"], "release_gate", ["combine wiki/provenance/bridge checks before release"]),
    Operation("session_registry", "Report session diagnostics and draft continuity state.", "read_only", False, ["12-{agent}/session-registry"], "advisory_report", ["inspect session diagnostics without injecting context automatically"]),
    Operation("retrieval_eval", "Measure retrieval candidates, misses, baselines, and replay stability.", "read_only", False, ["12-{agent}/retrieval-eval", "wiki", "12-shared"], "derived_reports", ["python3 assets/operator/retrieval_eval.py report"]),
    Operation("bridge_health", "Report practical bridges between RAW, wiki, graph, lessons, and sessions.", "read_only", False, ["raw-sources", "wiki", "12-shared/graph", "12-{agent}"], "advisory_report", ["python3 assets/operator/bridge_health.py --json"]),
    Operation("next-best-tests", "Suggest next safety checks for the memory system.", "read_only", False, ["12-shared/scripts"], "advisory_report", ["derive next checks from current reports"]),
    Operation("script_auditor", "Audit memory scripts for maintenance risks.", "read_only", False, ["12-shared/scripts"], "advisory_report", ["review scripts without rewriting them"]),
    Operation("session-start", "Render local memory context fallback.", "read_only", False, ["12-{agent}", "12-shared", "wiki"], "advisory_report", ["python3 12-shared/scripts/memory_operator.py session-start"]),
    Operation("session-end", "Write a non-canonical session draft and hook marker.", "mutating", True, ["12-{agent}/session-drafts", "12-{agent}/hook-runs"], "derived_reports", ["python3 12-shared/scripts/memory_operator.py hooks-status"]),
    Operation("check-all", "Run release gates without mutating canonical memory.", "read_only", False, ["12-{agent}", "12-shared", "wiki", "raw-sources"], "release_gate", ["run local RAW/provenance/wiki/bridge checks before commit"]),
)


def operations_by_name() -> dict[str, Operation]:
    return {operation.name: operation for operation in OPERATIONS}


def registry_summary() -> dict[str, int]:
    summary = {"total": len(OPERATIONS), "read_only": 0, "mutating": 0, "approval_required": 0}
    for operation in OPERATIONS:
        summary[operation.mode] = summary.get(operation.mode, 0) + 1
        if operation.approval_required:
            summary["approval_required"] += 1
    return summary


def validate_registry() -> list[str]:
    issues: list[str] = []
    seen: set[str] = set()
    for operation in OPERATIONS:
        if operation.name in seen:
            issues.append(f"duplicate operation: {operation.name}")
        seen.add(operation.name)
        if operation.mode not in {"read_only", "mutating"}:
            issues.append(f"{operation.name}: invalid mode {operation.mode}")
        if operation.mode == "mutating" and not operation.approval_required:
            issues.append(f"{operation.name}: mutating operation must require approval")
        if operation.mode == "read_only" and operation.approval_required:
            issues.append(f"{operation.name}: read-only operation should not require approval")
        if not operation.verification:
            issues.append(f"{operation.name}: missing verification")
    return issues


def render_markdown() -> str:
    summary = registry_summary()
    issues = validate_registry()
    rows = [
        [
            operation.name,
            operation.mode,
            "yes" if operation.approval_required else "no",
            operation.artifact_class,
            ", ".join(operation.touched_areas),
            "; ".join(operation.verification),
        ]
        for operation in OPERATIONS
    ]
    return "\n".join(
        [
            "# MEMORY_OPERATION_REGISTRY",
            "",
            "Descriptive registry only. Scripts remain the implementation backend; this report does not mutate canonical memory.",
            "",
            "## Summary",
            markdown_table(["metric", "count"], sorted(summary.items())),
            "",
            "## Validation",
            "\n".join(f"- {issue}" for issue in issues) if issues else "_No registry validation issues._",
            "",
            "## Operations",
            markdown_table(["name", "mode", "approval", "artifact_class", "touched_areas", "verification"], rows),
        ]
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Render the memory operation registry")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    data = {
        "mode": "dry-run",
        "root": str(vault_root()),
        "summary": registry_summary(),
        "issues": validate_registry(),
        "operations": [asdict(operation) for operation in OPERATIONS],
    }
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(render_markdown())
    raise SystemExit(1 if data["issues"] else 0)


if __name__ == "__main__":
    main()
