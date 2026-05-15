#!/usr/bin/env python3
"""Read-only decision capture review board for memory operators."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from _operator_utils import markdown_table, read_text, rel, vault_root


SCHEMA_VERSION = "decision-review-board.v1"
DEFAULT_CANDIDATE_CAP = 30
DEFAULT_MARKDOWN_LINE_CAP = 180
TEXT_CAP = 240
ARTIFACTS = {
    "memory_decision",
    "agent_lesson",
    "wiki_synthesis",
    "runbook_update",
    "public_surface_note",
    "no_durable_write",
}
SOURCE_TYPES = {"git_commit", "memory_in_progress", "memory_correction", "wiki_log", "session_draft"}
REVIEW_STATUSES = {"accepted", "skipped", "duplicate", "deferred", "needs_user_decision"}
RESOLVED_STATUSES = {"accepted", "skipped", "duplicate"}
DECISION_KEYWORDS = {
    "decision",
    "policy",
    "rule",
    "invariant",
    "release",
    "target",
    "archive",
    "surface",
    "never",
    "must",
    "fix",
    "deferred",
    "rejected",
    "public",
    "readme",
    "license",
    "attribution",
    "install",
    "runbook",
    "maintenance",
    "workflow",
    "gate",
    "approval",
    "routing",
    "ошибка",
    "правило",
    "решение",
    "релиз",
    "архив",
}
NOISE_COMMIT_RE = re.compile(r"^(vault backup:|wip\b|typo\b|format\b)", re.IGNORECASE)
COMMIT_ACTION_RE = re.compile(r"^(Add|Clarify|Record|Archive|Resolve|Evaluate|Update|Fix)\b")
TOKEN_RE = re.compile(r"[a-zа-я0-9]{3,}", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str


@dataclass
class Candidate:
    id: str
    source_type: str
    source_ref: str
    text: str
    recommended_artifact: str
    confidence: str
    reason: str
    risk_if_not_captured: str
    duplicate_hint: str | None = None
    review_status: str = "open"
    review_note: str | None = None
    reviewed_at_utc: str | None = None
    reviewer: str | None = None


@dataclass(frozen=True)
class ReviewRecord:
    candidate_id: str
    status: str
    reviewed_at_utc: str
    reviewer: str
    note: str
    source_ref: str | None = None
    recommended_artifact: str | None = None


def agent_dir(agent: str) -> str:
    return f"12-{agent}"


def default_state_path(agent: str) -> Path:
    return Path(agent_dir(agent)) / "decision-review" / "review-state.jsonl"


def run_git(root: Path, args: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(["git", "-C", str(root), *args], check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.returncode, result.stdout.rstrip("\n"), result.stderr.strip()


def truncate(text: str, limit: int = TEXT_CAP) -> str:
    text = " ".join(text.replace("\r\n", "\n").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def normalize(text: str) -> str:
    return " ".join(TOKEN_RE.findall(text.lower()))


def tokens(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.lower()))


def stable_id(source_type: str, source_ref: str, text: str) -> str:
    stable_ref = re.sub(r":\d+$", "", source_ref)
    seed = f"{source_type}|{stable_ref}|{normalize(text)}"
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def has_keyword(text: str, keywords: Iterable[str] = DECISION_KEYWORDS) -> bool:
    lower = text.lower()
    return any(keyword in lower for keyword in keywords)


def route(text: str, source_type: str) -> tuple[str, str, str]:
    lower = text.lower()
    if source_type == "memory_correction":
        return ("agent_lesson", "high", "correction section is a direct process-learning signal")
    if any(word in lower for word in ("public", "readme", "license", "attribution", "install", "github repo", "skill repo")):
        return ("public_surface_note", "medium" if source_type == "git_commit" else "high", "candidate affects public release surface or public documentation")
    if any(word in lower for word in ("runbook", "sop", "procedure", "maintenance", "workflow", "command", "operator")):
        return ("runbook_update", "medium", "candidate describes a repeatable operator workflow")
    if any(word in lower for word in ("policy", "rule", "invariant", "never", "must", "release", "target", "approval", "routing")):
        return ("memory_decision", "medium", "candidate looks like a durable operating rule")
    if source_type == "wiki_log":
        return ("wiki_synthesis", "high", "wiki log entry records a durable knowledge operation")
    if source_type == "session_draft":
        return ("memory_decision", "low", "session draft contains decision-like language but needs review")
    return ("wiki_synthesis", "medium", "commit or memory entry looks durable enough for review")


def risk_for(artifact: str) -> str:
    risks = {
        "memory_decision": "future agents may miss a durable operating rule",
        "agent_lesson": "the agent may repeat the same process failure",
        "wiki_synthesis": "architecture or knowledge context may be recoverable only from chat/git history",
        "runbook_update": "repeatable workflow may remain manual or inconsistently executed",
        "public_surface_note": "public release surface may drift from actual capability or policy",
        "no_durable_write": "low durable-memory risk",
    }
    return risks[artifact]


def make_candidate(source_type: str, source_ref: str, text: str, artifact: str | None = None, confidence: str | None = None, reason: str | None = None) -> Candidate:
    routed_artifact, routed_confidence, routed_reason = route(text, source_type)
    selected_artifact = artifact or routed_artifact
    selected_confidence = confidence or routed_confidence
    selected_reason = reason or routed_reason
    short = truncate(text)
    return Candidate(
        id=stable_id(source_type, source_ref, short),
        source_type=source_type,
        source_ref=source_ref,
        text=short,
        recommended_artifact=selected_artifact,
        confidence=selected_confidence,
        reason=selected_reason,
        risk_if_not_captured=risk_for(selected_artifact),
    )


def split_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_title = ""
    current_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current_title or current_lines:
                sections.append((current_title, "\n".join(current_lines)))
            current_title = line[3:].strip()
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_title or current_lines:
        sections.append((current_title, "\n".join(current_lines)))
    return sections


def memory_in_progress_candidates(root: Path, agent: str, findings: list[Finding]) -> list[Candidate]:
    path = root / agent_dir(agent) / "memory_in_progress.md"
    if not path.exists():
        findings.append(Finding("warn", "missing_memory_in_progress", f"{rel(path, root)} is missing"))
        return []
    candidates: list[Candidate] = []
    for idx, line in enumerate(read_text(path).splitlines(), 1):
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        body = stripped[2:].strip()
        if has_keyword(body):
            candidates.append(make_candidate("memory_in_progress", f"{rel(path, root)}:{idx}", body))
    return candidates


def memory_correction_candidates(root: Path, agent: str, findings: list[Finding]) -> list[Candidate]:
    path = root / agent_dir(agent) / "memory_corrections.md"
    if not path.exists():
        findings.append(Finding("warn", "missing_memory_corrections", f"{rel(path, root)} is missing"))
        return []
    candidates: list[Candidate] = []
    for title, body in split_sections(read_text(path)):
        if not title:
            continue
        excerpt_lines = [title]
        for line in body.splitlines():
            if any(marker in line.lower() for marker in ("**error:**", "**fix:**", "**rule extracted:**", "ошибка", "правило")):
                excerpt_lines.append(line)
        candidates.append(make_candidate("memory_correction", f"{rel(path, root)}#{title}", " ".join(excerpt_lines[:4]), "agent_lesson", "high", "correction section is a direct process-learning signal"))
    return candidates


def wiki_log_candidates(root: Path, findings: list[Finding]) -> list[Candidate]:
    path = root / "wiki" / "log.md"
    if not path.exists():
        findings.append(Finding("warn", "missing_wiki_log", "wiki/log.md is missing; wiki-log candidates skipped"))
        return []
    candidates: list[Candidate] = []
    for title, body in split_sections(read_text(path)):
        if not title:
            continue
        lines = [line.strip("- ").strip() for line in body.splitlines() if line.strip().startswith(("- Operation:", "- Notes:", "- Created:", "- Updated:"))]
        if lines:
            candidates.append(make_candidate("wiki_log", f"{rel(path, root)}#{title}", f"{title}. {' '.join(lines[:3])}"))
    return candidates


def git_commit_candidates(root: Path, findings: list[Finding]) -> list[Candidate]:
    code, out, err = run_git(root, ["log", "--format=%h%x09%s", "-30"])
    if code != 0:
        findings.append(Finding("blocker", "git_log_failed", err or "cannot read git log"))
        return []
    candidates: list[Candidate] = []
    for line in out.splitlines():
        if "\t" not in line:
            continue
        sha, subject = line.split("\t", 1)
        if subject.lower().startswith("vault backup:"):
            candidates.append(make_candidate("git_commit", sha, subject, "no_durable_write", "low", "backup commit is low durable-memory value"))
            continue
        if NOISE_COMMIT_RE.search(subject) and not has_keyword(subject):
            candidates.append(make_candidate("git_commit", sha, subject, "no_durable_write", "low", "technical/noise commit without decision keywords"))
            continue
        if COMMIT_ACTION_RE.search(subject) or has_keyword(subject):
            candidates.append(make_candidate("git_commit", sha, subject))
    return candidates


def session_draft_candidates(root: Path, agent: str, findings: list[Finding]) -> list[Candidate]:
    base = root / agent_dir(agent) / "session-drafts"
    if not base.exists():
        findings.append(Finding("warn", "missing_session_drafts", f"{rel(base, root)} is missing; diagnostic candidates skipped"))
        return []
    candidates: list[Candidate] = []
    for path in sorted(base.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:10]:
        for idx, line in enumerate(read_text(path).splitlines(), 1):
            stripped = line.strip("- >").strip()
            if stripped and has_keyword(stripped) and not re.fullmatch(r"#+\s*important decisions", stripped, flags=re.IGNORECASE):
                candidates.append(make_candidate("session_draft", f"{rel(path, root)}:{idx}", stripped))
    return candidates


def dedupe_docs(root: Path, agent: str) -> list[tuple[str, str]]:
    docs: list[tuple[str, str]] = []
    for path in (root / "12-shared" / "memory_decisions.md", root / "12-shared" / "memory_ops.md", root / "wiki" / "log.md"):
        if path.exists():
            docs.append((rel(path, root), read_text(path)))
    lessons = root / agent_dir(agent) / "lessons"
    if lessons.exists():
        for path in sorted(lessons.glob("*.md")):
            if path.name.lower() != "readme.md":
                docs.append((rel(path, root), read_text(path)))
    return docs


def duplicate_hint(candidate: Candidate, docs: list[tuple[str, str]]) -> str | None:
    candidate_norm = normalize(candidate.text)
    candidate_tokens = tokens(candidate.text)
    if not candidate_norm or not candidate_tokens:
        return None
    source_path = candidate.source_ref.split("#", 1)[0].split(":", 1)[0]
    for doc_ref, text in docs:
        if doc_ref == source_path:
            continue
        if candidate_norm and candidate_norm in normalize(text):
            return f"possible duplicate in {doc_ref}"
        doc_tokens = tokens(text)
        overlap = len(candidate_tokens & doc_tokens) / max(len(candidate_tokens), 1)
        if len(candidate_tokens) >= 6 and overlap >= 0.7:
            return f"possible token-overlap duplicate in {doc_ref}"
    return None


def validate_candidate(candidate: Candidate) -> Finding | None:
    if candidate.source_type not in SOURCE_TYPES:
        return Finding("blocker", "invalid_source_type", f"{candidate.id}: invalid source_type {candidate.source_type}")
    if candidate.recommended_artifact not in ARTIFACTS:
        return Finding("blocker", "invalid_artifact", f"{candidate.id}: invalid artifact {candidate.recommended_artifact}")
    if candidate.confidence not in {"low", "medium", "high"}:
        return Finding("blocker", "invalid_confidence", f"{candidate.id}: invalid confidence {candidate.confidence}")
    if len(candidate.text) > TEXT_CAP:
        return Finding("blocker", "text_cap_violation", f"{candidate.id}: text exceeds {TEXT_CAP} chars")
    return None


def state_path(root: Path, agent: str, override: str | None = None) -> Path:
    if override:
        path = Path(override)
        return path if path.is_absolute() else root / path
    return root / default_state_path(agent)


def load_review_state(path: Path, findings: list[Finding]) -> dict[str, ReviewRecord]:
    if not path.exists():
        return {}
    latest: dict[str, ReviewRecord] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            findings.append(Finding("blocker", "malformed_decision_review_state", f"{path}:{line_no} is not valid JSONL"))
            continue
        candidate_id = str(raw.get("candidate_id", "")).strip()
        status = str(raw.get("status", "")).strip()
        if not candidate_id or status not in REVIEW_STATUSES:
            findings.append(Finding("blocker", "invalid_decision_review_state", f"{path}:{line_no} has invalid candidate_id/status"))
            continue
        latest[candidate_id] = ReviewRecord(
            candidate_id=candidate_id,
            status=status,
            reviewed_at_utc=str(raw.get("reviewed_at_utc", "")),
            reviewer=str(raw.get("reviewer", "")),
            note=str(raw.get("note", "")),
            source_ref=raw.get("source_ref"),
            recommended_artifact=raw.get("recommended_artifact"),
        )
    return latest


def apply_review_state(candidates: list[Candidate], records: dict[str, ReviewRecord]) -> None:
    for candidate in candidates:
        record = records.get(candidate.id)
        if not record:
            continue
        candidate.review_status = record.status
        candidate.review_note = record.note
        candidate.reviewed_at_utc = record.reviewed_at_utc
        candidate.reviewer = record.reviewer


def select_candidates(candidates: list[Candidate], verbose: bool, include_reviewed: bool) -> list[Candidate]:
    selected = candidates if verbose else [candidate for candidate in candidates if candidate.recommended_artifact != "no_durable_write"]
    if not include_reviewed:
        selected = [candidate for candidate in selected if candidate.review_status not in RESOLVED_STATUSES]
    return selected if verbose else selected[:DEFAULT_CANDIDATE_CAP]


def summary(candidates: list[Candidate], shown: list[Candidate]) -> dict[str, int]:
    out = {
        "total_candidates": len(candidates),
        "shown_candidates": len(shown),
        "open_candidates": sum(1 for candidate in candidates if candidate.review_status == "open"),
        "reviewed_candidates": sum(1 for candidate in candidates if candidate.review_status != "open"),
        "memory_decision": 0,
        "agent_lesson": 0,
        "wiki_synthesis": 0,
        "runbook_update": 0,
        "public_surface_note": 0,
        "no_durable_write": 0,
        "accepted": 0,
        "skipped": 0,
        "duplicate": 0,
        "deferred": 0,
        "needs_user_decision": 0,
    }
    for candidate in candidates:
        out[candidate.recommended_artifact] += 1
        if candidate.review_status in REVIEW_STATUSES:
            out[candidate.review_status] += 1
    return out


def collect(root: Path, agent: str = "agent", verbose: bool = False, include_reviewed: bool = False, review_state_path: str | None = None) -> dict[str, object]:
    findings: list[Finding] = []
    code, _out, err = run_git(root, ["rev-parse", "--show-toplevel"])
    if code != 0:
        findings.append(Finding("blocker", "not_git_repo", err or f"{root} is not a git repo"))
    candidates: list[Candidate] = []
    candidates.extend(memory_in_progress_candidates(root, agent, findings))
    candidates.extend(memory_correction_candidates(root, agent, findings))
    candidates.extend(wiki_log_candidates(root, findings))
    candidates.extend(git_commit_candidates(root, findings))
    candidates.extend(session_draft_candidates(root, agent, findings))
    docs = dedupe_docs(root, agent)
    for candidate in candidates:
        candidate.duplicate_hint = duplicate_hint(candidate, docs)
        validation = validate_candidate(candidate)
        if validation:
            findings.append(validation)
    resolved_state_path = state_path(root, agent, review_state_path)
    apply_review_state(candidates, load_review_state(resolved_state_path, findings))
    shown = select_candidates(candidates, verbose, include_reviewed)
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "dry-run",
        "agent": agent,
        "generated_at_utc": utc_now(),
        "review_state_path": rel(resolved_state_path, root) if resolved_state_path.is_relative_to(root) else str(resolved_state_path),
        "summary": summary(candidates, shown),
        "candidates": [asdict(item) for item in shown],
        "findings": [asdict(item) for item in findings],
    }


def append_review_record(root: Path, args: argparse.Namespace) -> dict[str, object]:
    if os.environ.get("MEMORY_OPERATOR_APPROVED") != "1":
        raise SystemExit("decision-review --mark requires MEMORY_OPERATOR_APPROVED=1")
    if args.status not in REVIEW_STATUSES:
        raise SystemExit(f"invalid --status {args.status}; expected one of {', '.join(sorted(REVIEW_STATUSES))}")
    if not args.note.strip():
        raise SystemExit("decision-review --mark requires --note")
    report = collect(root, args.agent, verbose=True, include_reviewed=True, review_state_path=args.review_state_path)
    candidates = {str(item["id"]): item for item in report["candidates"]}  # type: ignore[index]
    candidate = candidates.get(args.mark)
    if not candidate:
        raise SystemExit(f"candidate id not found in current decision-review report: {args.mark}")
    path = state_path(root, args.agent, args.review_state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": "decision-review-state.v1",
        "candidate_id": args.mark,
        "status": args.status,
        "reviewed_at_utc": utc_now(),
        "reviewer": args.reviewer,
        "note": args.note.strip(),
        "source_ref": candidate["source_ref"],
        "recommended_artifact": candidate["recommended_artifact"],
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return {
        "schema_version": "decision-review-mark.v1",
        "mode": "apply",
        "review_state_path": rel(path, root) if path.is_relative_to(root) else str(path),
        "record": record,
    }


def render_markdown(report: dict[str, object], verbose: bool) -> str:
    candidates = report["candidates"]
    findings = report["findings"]
    assert isinstance(candidates, list)
    assert isinstance(findings, list)
    lines = [
        "# DECISION_REVIEW dry-run",
        "",
        "Nothing changed. This board shows candidates for durable routing into memory, wiki, lessons, runbooks, or public surfaces.",
        "",
        "## Summary",
        markdown_table(["metric", "count"], sorted(report["summary"].items())),  # type: ignore[union-attr]
        "",
        "## Candidates",
        markdown_table(
            ["status", "artifact", "confidence", "source", "text", "duplicate"],
            ([item["review_status"], item["recommended_artifact"], item["confidence"], item["source_ref"], item["text"], item["duplicate_hint"] or ""] for item in candidates),
        ) if candidates else "_No candidates shown._",
        "",
        "## Findings",
        markdown_table(["severity", "code", "message"], ([item["severity"], item["code"], item["message"]] for item in findings)) if findings else "_No findings._",
    ]
    return "\n".join(lines if verbose else lines[:DEFAULT_MARKDOWN_LINE_CAP])


def main() -> None:
    ap = argparse.ArgumentParser(description="Render a read-only decision review board")
    fmt = ap.add_mutually_exclusive_group()
    fmt.add_argument("--md", action="store_true")
    fmt.add_argument("--json", action="store_true")
    ap.add_argument("--root", "--vault", dest="root", default=str(vault_root()))
    ap.add_argument("--agent", default="agent")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--include-reviewed", action="store_true", help="include accepted/skipped/duplicate candidates in output")
    ap.add_argument("--review-state-path", default=None, help="override review-state JSONL path")
    ap.add_argument("--mark", help="append a review-state record for the candidate id")
    ap.add_argument("--status", choices=sorted(REVIEW_STATUSES))
    ap.add_argument("--note", default="")
    ap.add_argument("--reviewer", default="agent")
    args = ap.parse_args()

    try:
        root = Path(args.root).resolve()
        if args.mark:
            report = append_review_record(root, args)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            raise SystemExit(0)
        report = collect(root, args.agent, verbose=args.verbose, include_reviewed=args.include_reviewed, review_state_path=args.review_state_path)
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(render_markdown(report, args.verbose))
        raise SystemExit(2 if any(item["severity"] == "blocker" for item in report["findings"]) else 0)  # type: ignore[index]
    except SystemExit:
        raise
    except Exception as exc:
        print(f"decision-review failed: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
