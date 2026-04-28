"""
Lightweight hybrid retrieval candidate report for Obsidian memory.

This is a derived report over graph.json. It never edits wiki/ or raw-sources/.

Run:
    python hybrid_retrieval.py "project alpha status"
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


GRAPH_DIR = Path(__file__).resolve().parent
OUT_DIR = Path(os.environ.get("GRAPHIFY_OUT", GRAPH_DIR / "graphify-out")).resolve()
GRAPH = Path(os.environ.get("GRAPHIFY_GRAPH", OUT_DIR / "graph.json")).resolve()
OUT = OUT_DIR / "retrieval_candidates.jsonl"


def tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-zа-я0-9]+", text.lower()) if len(t) > 2}


def parse_date(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:16] if "T" in fmt else value[:10], fmt)
        except ValueError:
            continue
    return None


def recency_score(node: dict) -> float:
    dt = parse_date(str(node.get("updated") or node.get("valid_from") or ""))
    if not dt:
        return 0.0
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    age_days = max((now - dt).days, 0)
    return max(0.0, 1.0 - min(age_days, 365) / 365)


def source_quality(node: dict) -> float:
    node_type = node.get("node_type")
    source_file = str(node.get("source_file", ""))
    if node_type == "raw_source" or source_file.startswith("raw-sources/"):
        return 1.0
    if node_type == "drawer" or source_file.startswith("wiki/drawers/"):
        return 0.95
    if node.get("has_evidence"):
        return 0.75
    if node_type in {"summary", "synthesis", "wing"}:
        return 0.45
    return 0.35


def score_node(node: dict, query_terms: set[str]) -> dict:
    haystack = " ".join(
        str(node.get(k, ""))
        for k in ("label", "source_file", "node_type", "claim_id", "claim_value", "source")
    )
    terms = tokenize(haystack)
    overlap = len(query_terms & terms)
    exact = overlap / max(len(query_terms), 1)
    person_project_boost = 0.2 if node.get("node_type") == "wing" or "person-" in haystack or "project-" in haystack else 0.0
    recency = recency_score(node)
    quality = source_quality(node)
    total = round((exact * 0.55) + (person_project_boost * 0.15) + (recency * 0.10) + (quality * 0.20), 4)
    return {
        "id": node.get("id"),
        "label": node.get("label"),
        "source_file": node.get("source_file"),
        "node_type": node.get("node_type"),
        "score": total,
        "score_parts": {
            "exact_keyword_overlap": round(exact, 4),
            "person_project_boost": person_project_boost,
            "recency": round(recency, 4),
            "source_quality": quality,
        },
    }


def main() -> None:
    query = " ".join(sys.argv[1:]).strip() or os.environ.get("GRAPHIFY_QUERY", "")
    query_terms = tokenize(query)
    data = json.loads(GRAPH.read_text(encoding="utf-8"))
    candidates = [score_node(node, query_terms) for node in data.get("nodes", [])]
    candidates = [c for c in candidates if c["score"] > 0]
    candidates.sort(key=lambda c: c["score"], reverse=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in candidates[:100]), encoding="utf-8")
    print(f"wrote {OUT} ({len(candidates[:100])} candidates)")


if __name__ == "__main__":
    main()
