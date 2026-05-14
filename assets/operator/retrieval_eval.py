#!/usr/bin/env python3
"""Phase 4 retrieval evaluation for the Codex memory core."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from _operator_utils import approval_packet, markdown_table, read_text, rel, vault_root


AGENT_ID = os.environ.get("OBSIDIAN_AGENT_ID", "codex")
PRIVATE_ROOT = Path(os.environ.get("OBSIDIAN_PRIVATE_ROOT", f"12-{AGENT_ID}"))
EVAL_DIR = PRIVATE_ROOT / "retrieval-eval"
MISS_LOG = EVAL_DIR / "missed-retrievals.jsonl"
SKIP_LOG = EVAL_DIR / "skipped-candidates.jsonl"
BASELINE_DIR = EVAL_DIR / "baselines"
REPLAY_DIR = EVAL_DIR / "replay-reports"
TOKEN_RE = re.compile(r"[A-Za-zА-Яа-я0-9_+-]{3,}")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
SEARCH_ROOTS = (
    f"{PRIVATE_ROOT.as_posix()}/lessons",
    f"{PRIVATE_ROOT.as_posix()}/memory_active.md",
    f"{PRIVATE_ROOT.as_posix()}/memory_corrections.md",
    f"{PRIVATE_ROOT.as_posix()}/memory_in_progress.md",
    f"{PRIVATE_ROOT.as_posix()}/memory_improvements_backlog.md",
    "12-shared/memory_decisions.md",
    "12-shared/memory_ops.md",
    "wiki/concepts",
    "wiki/synthesis",
    "wiki/domains",
)
STOPWORDS = {
    "and",
    "the",
    "for",
    "with",
    "from",
    "это",
    "как",
    "что",
    "или",
    "для",
    "при",
    "надо",
    "нужно",
    "если",
    "без",
    "где",
    "уже",
}


@dataclass
class Candidate:
    path: str
    kind: str
    confidence: str
    score: int
    reason: str
    matched_terms: list[str]
    heading: str
    snippet: str


def approval_present() -> bool:
    return os.environ.get("MEMORY_OPERATOR_APPROVED") == "1"


def tokens(text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for token in TOKEN_RE.findall(text.lower()):
        if token in STOPWORDS or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def candidate_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for item in SEARCH_ROOTS:
        path = root / item
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.md")))
    return sorted(set(files))


def parse_kind(path: Path, root: Path, text: str) -> str:
    relative = rel(path, root)
    private_rel = PRIVATE_ROOT.as_posix().rstrip("/") + "/"
    if relative.startswith(f"{private_rel}lessons/"):
        match = re.search(r"^type:\s*\"?([^\"\n]+)\"?", text, re.MULTILINE)
        return f"lesson:{match.group(1).strip()}" if match else "lesson"
    if relative == f"{private_rel}memory_corrections.md":
        return "correction"
    if relative.startswith(private_rel):
        return "codex-memory"
    if relative.startswith("12-shared/"):
        return "shared-memory"
    if relative.startswith("wiki/"):
        return "wiki-context"
    return "memory"


def first_heading(text: str) -> str:
    match = HEADING_RE.search(text)
    return match.group(2).strip() if match else "(no heading)"


def snippet_for(text: str, terms: list[str], max_len: int = 220) -> str:
    lower = text.lower()
    positions = [lower.find(term) for term in terms if lower.find(term) >= 0]
    start = max(0, min(positions) - 80) if positions else 0
    snippet = re.sub(r"\s+", " ", text[start : start + max_len]).strip()
    return snippet


def score_text(text: str, query_terms: list[str]) -> tuple[int, list[str]]:
    lower = text.lower()
    matched = [term for term in query_terms if term in lower]
    if not matched:
        return 0, []
    score = 0
    fm_match = FRONTMATTER_RE.match(text)
    frontmatter = fm_match.group(1).lower() if fm_match else ""
    headings = " ".join(match.group(2).lower() for match in HEADING_RE.finditer(text))
    for term in matched:
        score += lower.count(term)
        if term in headings:
            score += 4
        if term in frontmatter:
            score += 2
    return score, matched


def confidence_for(score: int, matched_count: int, query_count: int) -> str:
    coverage = matched_count / max(query_count, 1)
    if score >= 12 and coverage >= 0.5:
        return "high"
    if score >= 5 and coverage >= 0.25:
        return "medium"
    return "low"


def query(root: Path, query_text: str, limit: int) -> list[Candidate]:
    query_terms = tokens(query_text)
    candidates: list[Candidate] = []
    if not query_terms:
        return candidates
    for path in candidate_files(root):
        text = read_text(path)
        score, matched = score_text(text, query_terms)
        if score <= 0:
            continue
        kind = parse_kind(path, root, text)
        confidence = confidence_for(score, len(matched), len(query_terms))
        candidates.append(
            Candidate(
                path=rel(path, root),
                kind=kind,
                confidence=confidence,
                score=score,
                reason=f"matched {len(matched)}/{len(query_terms)} query terms in {kind}",
                matched_terms=matched,
                heading=first_heading(text),
                snippet=snippet_for(text, matched),
            )
        )
    return sorted(candidates, key=lambda item: (-item.score, item.path))[:limit]


def read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    out: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            out.append({"invalid_json": line})
    return out


def event_id(prefix: str, payload: dict[str, object]) -> str:
    seed = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{digest}"


def append_event(root: Path, relative_log: Path, payload: dict[str, object], apply: bool) -> int:
    target = root / relative_log
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    event = {"created": now, **payload}
    event["id"] = event_id(str(payload.get("kind", "retrieval")), event)
    print(json.dumps(event, ensure_ascii=False, indent=2))
    if not apply:
        print("\nDry-run only. Add --apply with MEMORY_OPERATOR_APPROVED=1 to append this event.")
        return 0
    if not approval_present():
        print("ERROR: apply mode requires MEMORY_OPERATOR_APPROVED=1", flush=True)
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"\nappended: {target}")
    return 0


def render_candidates(candidates: Iterable[Candidate]) -> str:
    items = list(candidates)
    if not items:
        return "_No candidates._"
    return markdown_table(
        ["confidence", "score", "kind", "path", "reason", "matched_terms", "heading", "snippet"],
        (
            [
                item.confidence,
                item.score,
                item.kind,
                item.path,
                item.reason,
                ", ".join(item.matched_terms),
                item.heading,
                item.snippet,
            ]
            for item in items
        ),
    )


def candidate_paths(candidates: Iterable[Candidate]) -> list[str]:
    return [candidate.path for candidate in candidates]


def jaccard(left: Iterable[str], right: Iterable[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set and not right_set:
        return 1.0
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)


def baseline_rows(root: Path, queries: list[str], limit: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for idx, query_text in enumerate(queries, start=1):
        started = time.perf_counter()
        candidates = query(root, query_text, limit)
        latency_ms = int((time.perf_counter() - started) * 1000)
        rows.append(
            {
                "schema_version": 1,
                "id": idx,
                "query": query_text,
                "limit": limit,
                "retrieved_paths": candidate_paths(candidates),
                "top_path": candidates[0].path if candidates else "",
                "latency_ms": latency_ms,
            }
        )
    return rows


def read_queries(path: Path) -> list[str]:
    queries: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        queries.append(line)
    return queries


def write_jsonl(path: Path, rows: Iterable[dict[str, object]], apply: bool) -> int:
    if not apply:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False, sort_keys=True))
        print("\nDry-run only. Add --apply with MEMORY_OPERATOR_APPROVED=1 to write the baseline/report.")
        return 0
    if not approval_present():
        print("ERROR: apply mode requires MEMORY_OPERATOR_APPROVED=1", flush=True)
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"wrote: {path}")
    return 0


def load_baseline(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def replay_rows(root: Path, baseline: list[dict[str, object]]) -> dict[str, object]:
    results: list[dict[str, object]] = []
    skipped = 0
    errored = 0
    for row in baseline:
        query_text = str(row.get("query", ""))
        if not query_text:
            skipped += 1
            continue
        limit = int(row.get("limit", 8) or 8)
        try:
            started = time.perf_counter()
            current = query(root, query_text, limit)
            latency_ms = int((time.perf_counter() - started) * 1000)
            captured_paths = [str(item) for item in row.get("retrieved_paths", []) if item]
            current_paths = candidate_paths(current)
            captured_top = str(row.get("top_path", ""))
            current_top = current_paths[0] if current_paths else ""
            captured_latency = int(row.get("latency_ms", 0) or 0)
            results.append(
                {
                    "id": row.get("id"),
                    "query": query_text,
                    "captured_paths": captured_paths,
                    "current_paths": current_paths,
                    "jaccard": round(jaccard(captured_paths, current_paths), 4),
                    "top1_match": captured_top == current_top,
                    "captured_top": captured_top,
                    "current_top": current_top,
                    "latency_delta_ms": latency_ms - captured_latency,
                }
            )
        except Exception as exc:  # replay should report row-level failures
            errored += 1
            results.append({"id": row.get("id"), "query": query_text, "error": str(exc)})
    replayed = [item for item in results if "error" not in item]
    mean_jaccard = sum(float(item["jaccard"]) for item in replayed) / len(replayed) if replayed else 0.0
    top1_rate = sum(1 for item in replayed if item.get("top1_match")) / len(replayed) if replayed else 0.0
    mean_latency_delta = sum(int(item["latency_delta_ms"]) for item in replayed) / len(replayed) if replayed else 0.0
    return {
        "schema_version": 1,
        "summary": {
            "rows_total": len(baseline),
            "rows_replayed": len(replayed),
            "rows_skipped": skipped,
            "rows_errored": errored,
            "mean_jaccard": round(mean_jaccard, 4),
            "top1_stability_rate": round(top1_rate, 4),
            "mean_latency_delta_ms": round(mean_latency_delta, 1),
        },
        "results": results,
    }


def render_report(root: Path) -> str:
    misses = read_jsonl(root / MISS_LOG)
    skips = read_jsonl(root / SKIP_LOG)
    active_misses = [item for item in misses if item.get("status", "active") != "resolved"]
    skipped_by_path: dict[str, int] = {}
    for item in skips:
        path = str(item.get("candidate_path", ""))
        if path:
            skipped_by_path[path] = skipped_by_path.get(path, 0) + 1
    lines = [
        "# RETRIEVAL_EVAL report",
        "",
        "Nothing changed. This is a measurement layer before any semantic/vector index decision.",
        "",
        "## Summary",
        markdown_table(
            ["metric", "count"],
            [
                ["missed_retrieval_records", len(misses)],
                ["active_missed_retrievals", len(active_misses)],
                ["skipped_candidate_records", len(skips)],
                ["baseline_files", len(list((root / BASELINE_DIR).glob("*.jsonl"))) if (root / BASELINE_DIR).exists() else 0],
                ["replay_reports", len(list((root / REPLAY_DIR).glob("*.json"))) if (root / REPLAY_DIR).exists() else 0],
                ["search_files", len(candidate_files(root))],
            ],
        ),
        "",
        "## Active Misses",
        markdown_table(
            ["id", "query", "expected_path", "reason", "status"],
            (
                [
                    item.get("id", ""),
                    item.get("query", ""),
                    item.get("expected_path", ""),
                    item.get("reason", ""),
                    item.get("status", "active"),
                ]
                for item in active_misses
            ),
        ) if active_misses else "_No active missed retrievals recorded._",
        "",
        "## Frequently Skipped Candidates",
        markdown_table(
            ["candidate_path", "skipped_count"],
            sorted(skipped_by_path.items(), key=lambda item: (-item[1], item[0])),
        ) if skipped_by_path else "_No skipped candidates recorded._",
        "",
        approval_packet(
            "RETRIEVAL_EVAL",
            [*SEARCH_ROOTS, str(MISS_LOG), str(SKIP_LOG)],
            files_to_write=[str(MISS_LOG), str(SKIP_LOG)],
            risks=[
                "keyword candidates can miss semantic matches",
                "false positives must be recorded as skipped rather than hidden",
                "semantic index remains deferred until missed retrieval evidence exists",
            ],
            verification=[
                "python3 assets/operator/retrieval_eval.py report",
                "python3 assets/operator/retrieval_eval.py export-baseline --queries-file /path/to/queries.txt",
                f"python3 assets/operator/retrieval_eval.py replay --against {EVAL_DIR.as_posix()}/baselines/example.jsonl",
                "python3 assets/operator/retrieval_eval.py query --query \"commit staging leak\"",
                "run your local release gate after reviewing findings",
            ],
        ),
    ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Read-only retrieval evaluation before semantic index activation")
    sub = ap.add_subparsers(dest="mode", required=True)
    q = sub.add_parser("query", help="Show candidate memory hits for a query")
    q.add_argument("--query", required=True)
    q.add_argument("--limit", type=int, default=8)
    q.add_argument("--json", action="store_true")
    sub.add_parser("report", help="Show Phase 4 retrieval evaluation report")
    export = sub.add_parser("export-baseline", help="Dry-run or write a retrieval baseline from a query file")
    export.add_argument("--queries-file", required=True)
    export.add_argument("--output", default=str(BASELINE_DIR / "baseline.jsonl"))
    export.add_argument("--limit", type=int, default=8)
    export.add_argument("--apply", action="store_true")
    replay = sub.add_parser("replay", help="Replay current retrieval against a baseline")
    replay.add_argument("--against", required=True)
    replay.add_argument("--output", default=str(REPLAY_DIR / "replay-report.json"))
    replay.add_argument("--json", action="store_true")
    replay.add_argument("--apply", action="store_true")
    miss = sub.add_parser("record-miss", help="Dry-run or append a missed retrieval case")
    miss.add_argument("--query", required=True)
    miss.add_argument("--expected-path", required=True)
    miss.add_argument("--reason", required=True)
    miss.add_argument("--status", default="active", choices=["active", "resolved"])
    miss.add_argument("--apply", action="store_true")
    skip = sub.add_parser("record-skip", help="Dry-run or append a skipped candidate case")
    skip.add_argument("--query", required=True)
    skip.add_argument("--candidate-path", required=True)
    skip.add_argument("--reason", required=True)
    skip.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    root = vault_root()
    if args.mode == "query":
        candidates = query(root, args.query, args.limit)
        if args.json:
            print(json.dumps({"mode": "dry-run", "query": args.query, "candidates": [asdict(item) for item in candidates]}, ensure_ascii=False, indent=2))
        else:
            print("# RETRIEVAL_EVAL query")
            print("")
            print("Nothing changed. Candidate lessons/context are advisory only.")
            print("")
            print(f"query: `{args.query}`")
            print("")
            print(render_candidates(candidates))
        return
    if args.mode == "report":
        print(render_report(root))
        return
    if args.mode == "export-baseline":
        rows = baseline_rows(root, read_queries(Path(args.queries_file)), args.limit)
        raise SystemExit(write_jsonl(root / args.output, rows, args.apply))
    if args.mode == "replay":
        report = replay_rows(root, load_baseline(root / args.against if not Path(args.against).is_absolute() else Path(args.against)))
        if args.json or not args.apply:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        if not args.apply:
            print("\nDry-run only. Add --apply with MEMORY_OPERATOR_APPROVED=1 to write the replay report.")
            return
        if not approval_present():
            print("ERROR: apply mode requires MEMORY_OPERATOR_APPROVED=1", flush=True)
            raise SystemExit(1)
        target = root / args.output
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote: {target}")
        return
    if args.mode == "record-miss":
        raise SystemExit(
            append_event(
                root,
                MISS_LOG,
                {
                    "kind": "missed-retrieval",
                    "query": args.query,
                    "expected_path": args.expected_path,
                    "reason": args.reason,
                    "status": args.status,
                },
                args.apply,
            )
        )
    if args.mode == "record-skip":
        raise SystemExit(
            append_event(
                root,
                SKIP_LOG,
                {
                    "kind": "skipped-candidate",
                    "query": args.query,
                    "candidate_path": args.candidate_path,
                    "reason": args.reason,
                },
                args.apply,
            )
        )


if __name__ == "__main__":
    main()
