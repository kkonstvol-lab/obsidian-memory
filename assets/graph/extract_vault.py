"""
Obsidian vault -> graphify knowledge graph with Beads-inspired metadata.

Corpus: wiki/ + raw-sources/ (markdown only; PDFs/audio deferred).
Output: graphify-out/GRAPH_REPORT.md + graph.json + wikilink suggestions.

Environment overrides for tests:
    GRAPHIFY_VAULT=C:/path/to/vault
    GRAPHIFY_OUT=C:/path/to/output
    GRAPHIFY_REVIEW_STATE=C:/path/to/review-state.jsonl

Run:
    python extract_vault.py
"""

import hashlib
import json
import os
import re
from pathlib import Path

from graphify import analyze, build, cluster, report

GRAPH_DIR = Path(__file__).resolve().parent
VAULT = Path(os.environ.get("GRAPHIFY_VAULT", GRAPH_DIR.parent.parent)).resolve()
CORPUS_ROOTS = [
    VAULT / "wiki",
    VAULT / "raw-sources",
]
SKIP_FILES = {"CLAUDE.md", "index.md", "log.md"}
OUT = Path(os.environ.get("GRAPHIFY_OUT", GRAPH_DIR / "graphify-out")).resolve()
OUT.mkdir(parents=True, exist_ok=True)
REVIEW_STATE = Path(os.environ.get("GRAPHIFY_REVIEW_STATE", GRAPH_DIR / "review-state.jsonl")).resolve()
REVIEW_STATE.touch(exist_ok=True)

WIKILINK_RE = re.compile(r"\[\[([^\]\|#]+)(?:#[^\]\|]+)?(?:\|[^\]]+)?\]\]")
H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
TAG_RE = re.compile(r"(?:^|\s)#([a-z][a-z0-9/_-]+)", re.IGNORECASE)
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*", re.DOTALL)
EVIDENCE_LINK_RE = re.compile(r"(?:←\s*)?\[\[([^\]\|#]+)(?:#[^\]\|]+)?(?:\|[^\]]+)?\]\]")

FOLDER_TYPE = {
    "entities": "document",
    "domains": "document",
    "concepts": "document",
    "summaries": "document",
    "synthesis": "document",
    "drawers": "document",
    "wings": "document",
    "books": "paper",
    "articles": "paper",
    "converted": "document",
    "pdfs": "paper",
}

WIKI_NODE_TYPES = {
    "entities": "entity",
    "domains": "domain",
    "concepts": "concept",
    "summaries": "summary",
    "synthesis": "synthesis",
    "drawers": "drawer",
    "wings": "wing",
}


def stable_id(prefix: str, *parts: object, length: int = 10) -> str:
    payload = "\u241f".join(str(p) for p in parts)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:length]
    return f"{prefix}-{digest}"


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def collect_md(roots: list[Path]) -> list[Path]:
    files = []
    for root in roots:
        if not root.exists():
            continue
        for f in sorted(root.rglob("*.md")):
            if f.name in SKIP_FILES:
                continue
            files.append(f)
    return files


def label_of(f: Path, text: str) -> str:
    m = H1_RE.search(text)
    return m.group(1).strip() if m else f.stem


def parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    values: dict[str, str] = {}
    for raw_line in match.group(1).splitlines():
        if ":" not in raw_line or raw_line.startswith(" "):
            continue
        key, value = raw_line.split(":", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def rel(f: Path) -> str:
    try:
        return str(f.relative_to(VAULT)).replace("\\", "/")
    except ValueError:
        return f.name


def node_type_of(f: Path | None, folder: str) -> str:
    if folder == "__missing__":
        return "missing"
    if f is None:
        return "wiki"
    path = rel(f)
    if path.startswith("raw-sources/"):
        return "raw_source"
    if path.startswith("wiki/"):
        return WIKI_NODE_TYPES.get(folder, "wiki")
    return "document"


def load_review_state(path: Path) -> dict[str, dict]:
    state: dict[str, dict] = {}
    if not path.exists():
        return state
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError:
            print(f"warning: ignored invalid review-state line {line_no}: {stripped[:80]}")
            continue
        record_id = record.get("id") or record.get("action_id") or record.get("edge_id")
        if record_id:
            state[str(record_id)] = record
    return state


def status_for(review_state: dict[str, dict], item_id: str, default: str) -> str:
    status = review_state.get(item_id, {}).get("status")
    return status if status in {"open", "accepted", "skipped", "obsolete"} else default


def make_edge(source: str, target: str, relation: str, confidence: str, source_file: str, review_state: dict[str, dict]) -> dict:
    edge_id = stable_id("ge", source, target, relation, source_file)
    default_status = "accepted" if confidence == "EXTRACTED" else "open"
    if nodes.get(target, {}).get("folder") == "__missing__":
        default_status = "open"
    return {
        "source": source,
        "target": target,
        "relation": relation,
        "confidence": confidence,
        "source_file": source_file,
        "edge_id": edge_id,
        "stable_id": edge_id,
        "review_status": status_for(review_state, edge_id, default_status),
    }


def ensure_derived_node(node_id: str, label: str, node_type: str, source_file: str = "") -> None:
    if node_id in nodes:
        return
    nodes[node_id] = {
        "id": node_id,
        "label": label,
        "file_type": "document",
        "source_file": source_file,
        "source_path": source_file,
        "folder": f"__{node_type}__",
        "node_type": node_type,
        "stable_id": stable_id("gn", node_type, label),
    }


review_state = load_review_state(REVIEW_STATE)

files = collect_md(CORPUS_ROOTS)
total_words = 0

nodes: dict[str, dict] = {}
stem_to_id: dict[str, str] = {}
id_to_text: dict[str, str] = {}

for f in files:
    text = f.read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(text)
    total_words += len(text.split())
    folder = f.parent.name
    node_id = slugify(f.stem)
    lbl = label_of(f, text)
    ftype = FOLDER_TYPE.get(folder, "document")
    source_path = rel(f)
    node = {
        "id": node_id,
        "label": lbl,
        "file_type": ftype,
        "source_file": source_path,
        "source_path": source_path,
        "folder": folder,
        "node_type": node_type_of(f, folder),
        "stable_id": stable_id("gn", source_path),
        "updated": fm.get("updated", ""),
        "valid_from": fm.get("valid_from", ""),
        "valid_to": fm.get("valid_to", ""),
        "supersedes": fm.get("supersedes", ""),
        "superseded_by": fm.get("superseded_by", ""),
        "claim_id": fm.get("claim_id", ""),
        "claim_value": fm.get("claim_value", ""),
        "source": fm.get("source") or fm.get("source_file", ""),
        "has_evidence": bool(
            fm.get("source")
            or fm.get("source_file")
            or "## Source Evidence" in text
            or "## Evidence" in text
            or "← [[" in text
            or "raw-sources/" in text
            or "wiki/drawers/" in text
        ),
    }
    nodes[node_id] = node
    stem_to_id[f.stem.lower()] = node_id
    stem_to_id[lbl.lower()] = node_id
    id_to_text[node_id] = text

edges: list[dict] = []
tag_to_nodes: dict[str, set] = {}

for node_id, text in id_to_text.items():
    src_file = nodes[node_id]["source_file"]
    node = nodes[node_id]

    for m in WIKILINK_RE.finditer(text):
        target_name = m.group(1).strip()
        tgt_id = stem_to_id.get(target_name.lower()) or slugify(target_name)
        if tgt_id == node_id:
            continue
        if tgt_id not in nodes:
            nodes[tgt_id] = {
                "id": tgt_id,
                "label": target_name,
                "file_type": "document",
                "source_file": src_file,
                "source_path": src_file,
                "folder": "__missing__",
                "node_type": "missing",
                "stable_id": stable_id("gn", "missing", target_name),
            }
        edges.append(make_edge(node_id, tgt_id, "links_to", "EXTRACTED", src_file, review_state))

        target_file = nodes.get(tgt_id, {}).get("source_file", "")
        if target_file.startswith("raw-sources/") or target_file.startswith("wiki/drawers/") or "raw-sources/" in target_name or "drawer-" in target_name:
            edges.append(make_edge(node_id, tgt_id, "derived_from", "EXTRACTED", src_file, review_state))

    for tm in TAG_RE.finditer(text):
        tag = tm.group(1).lower()
        if tag in ("md", "markdown", "obsidian"):
            continue
        tag_to_nodes.setdefault(tag, set()).add(node_id)

vault_ids = {n["id"] for n in nodes.values() if n.get("folder") != "__missing__"}
for tag, ids in tag_to_nodes.items():
    ids = sorted(ids & vault_ids)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            relation = f"shares_tag:{tag}"
            edges.append(make_edge(ids[i], ids[j], relation, "INFERRED", "__tag_index__", review_state))

for node_id, node in list(nodes.items()):
    supersedes = node.get("supersedes", "")
    if supersedes:
        target_name = supersedes.strip("[]")
        target_id = stem_to_id.get(target_name.lower()) or slugify(target_name)
        if target_id not in nodes:
            ensure_derived_node(target_id, target_name, "missing", node.get("source_file", ""))
        edges.append(make_edge(node_id, target_id, "supersedes", "EXTRACTED", node.get("source_file", ""), review_state))

    valid_from = node.get("valid_from", "")
    valid_to = node.get("valid_to", "")
    if valid_from or valid_to:
        label = f"{valid_from or 'unknown'}..{valid_to or 'open'}"
        temporal_id = stable_id("time", label)
        ensure_derived_node(temporal_id, label, "temporal_period")
        edges.append(make_edge(node_id, temporal_id, "valid_during", "EXTRACTED", node.get("source_file", ""), review_state))

extraction = {"nodes": list(nodes.values()), "edges": edges}
errors = build.validate_extraction(extraction)
if errors:
    print(f"Validation errors ({len(errors)}):")
    for e in errors[:5]:
        print(" ", e)
    raise SystemExit(1)

print(f"corpus: {len(files)} files · {total_words:,} words")
print(f"graph:  {len(nodes)} nodes · {len(edges)} edges")

G = build.build([extraction], directed=False)
communities = cluster.cluster(G)
cohesion = cluster.score_all(G, communities)
community_labels = {cid: f"community-{cid}" for cid in communities}
gods = analyze.god_nodes(G, top_n=10)
surprises = analyze.surprising_connections(G, communities, top_n=7)
questions = analyze.suggest_questions(G, communities, community_labels, top_n=7)

print(f"result: {G.number_of_nodes()} nodes · {G.number_of_edges()} edges · {len(communities)} communities")

for cid, nids in communities.items():
    for nid in nids:
        if G.has_node(nid):
            G.nodes[nid]["community"] = cid

md = report.generate(
    G,
    communities=communities,
    cohesion_scores=cohesion,
    community_labels=community_labels,
    god_node_list=gods,
    surprise_list=surprises,
    detection_result={"total_files": len(files), "total_words": total_words},
    token_cost={"total_usd": 0.0, "notes": "phase-1: no LLM"},
    root=str(VAULT),
    suggested_questions=questions,
)
(OUT / "GRAPH_REPORT.md").write_text(md, encoding="utf-8")
print(f"wrote {OUT}/GRAPH_REPORT.md")

import networkx as nx

data = nx.node_link_data(G, edges="links")
(OUT / "graph.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"wrote {OUT}/graph.json")

missing = {n["id"]: n["label"] for n in nodes.values() if n.get("folder") == "__missing__"}
if missing:
    lines = [
        "# Wikilink Suggestions - missing targets",
        "",
        "These wikilinks point to pages that do not exist yet. Review and create the page or fix spelling.",
        "",
    ]
    for nid, lbl in sorted(missing.items()):
        sources = sorted({e["source_file"] for e in edges if e["target"] == nid})
        lines.append(f"## [[{lbl}]]")
        lines.append(f"- action_id: `{stable_id('gq', 'create_missing_page', nid, lbl)}`")
        for s in sources[:5]:
            lines.append(f"- source: `{s}`")
        lines.append("")
    (OUT / "wikilink-suggestions.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}/wikilink-suggestions.md  ({len(missing)} missing targets)")
