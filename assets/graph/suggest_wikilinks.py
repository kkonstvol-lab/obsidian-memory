"""
Beads-inspired graph action queue for Obsidian graphify.

Reads graph.json and review-state.jsonl, then writes:
- graphify-out/missing-links.md
- graphify-out/GRAPH_READY.md

The script never edits wiki/ or raw-sources/.
"""

import hashlib
import json
import os
from itertools import combinations
from pathlib import Path

from networkx.readwrite import json_graph

GRAPH_DIR = Path(__file__).resolve().parent
OUT_DIR = Path(os.environ.get("GRAPHIFY_OUT", GRAPH_DIR / "graphify-out")).resolve()
GRAPH = Path(os.environ.get("GRAPHIFY_GRAPH", OUT_DIR / "graph.json")).resolve()
OUT = OUT_DIR / "missing-links.md"
READY_OUT = OUT_DIR / "GRAPH_READY.md"
REVIEW_STATE = Path(os.environ.get("GRAPHIFY_REVIEW_STATE", GRAPH_DIR / "review-state.jsonl")).resolve()

MIN_COMMUNITY_SIZE = 3
MAX_SUGGESTIONS_PER_COMMUNITY = 8
MAX_TOTAL_SUGGESTIONS = 60
HISTORY_STATUSES = {"accepted", "skipped", "obsolete"}


def stable_id(prefix: str, *parts: object, length: int = 10) -> str:
    payload = "\u241f".join(str(p) for p in parts)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:length]
    return f"{prefix}-{digest}"


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


def status_for(action_id: str) -> str:
    status = review_state.get(action_id, {}).get("status")
    return status if status in {"open", "accepted", "skipped", "obsolete"} else "open"


def add_action(
    actions: list[dict],
    action_type: str,
    title: str,
    files: list[str],
    *,
    key_parts: tuple,
    reason: str,
    blocked_by: list[str] | None = None,
    meta: dict | None = None,
) -> dict:
    action_id = stable_id("gq", action_type, *key_parts)
    action = {
        "id": action_id,
        "type": action_type,
        "title": title,
        "files": files,
        "reason": reason,
        "status": status_for(action_id),
        "blocked_by": blocked_by or [],
        "meta": meta or {},
    }
    actions.append(action)
    return action


def node_label(node_id: str) -> str:
    return G.nodes[node_id].get("label", node_id)


def node_file(node_id: str) -> str:
    return G.nodes[node_id].get("source_file", "")


def is_missing(node_id: str) -> bool:
    return G.nodes[node_id].get("node_type") == "missing" or G.nodes[node_id].get("folder") == "__missing__"


def active(actions: list[dict]) -> list[dict]:
    return [a for a in actions if a["status"] == "open"]


def historical(actions: list[dict]) -> list[dict]:
    return [a for a in actions if a["status"] in HISTORY_STATUSES]


def ready(actions: list[dict]) -> list[dict]:
    return [a for a in active(actions) if not a["blocked_by"]]


def blocked(actions: list[dict]) -> list[dict]:
    return [a for a in active(actions) if a["blocked_by"]]


def render_action(action: dict) -> list[str]:
    lines = [f"- [ ] `{action['id']}` **{action['title']}**"]
    lines.append(f"  - type: `{action['type']}`; status: `{action['status']}`")
    lines.append(f"  - reason: {action['reason']}")
    if action["blocked_by"]:
        lines.append(f"  - blocked_by: {', '.join(f'`{b}`' for b in action['blocked_by'])}")
    for file in action["files"][:4]:
        lines.append(f"  - `{file}`")
    return lines


def render_section(title: str, items: list[dict], empty: str) -> list[str]:
    lines = [f"## {title}", ""]
    if not items:
        lines.append(empty)
        lines.append("")
        return lines
    for action in items:
        lines.extend(render_action(action))
    lines.append("")
    return lines


review_state = load_review_state(REVIEW_STATE)
data = json.loads(GRAPH.read_text(encoding="utf-8"))
try:
    G = json_graph.node_link_graph(data, edges="links")
except TypeError:
    G = json_graph.node_link_graph(data)

communities: dict[int, list[str]] = {}
for nid, d in G.nodes(data=True):
    cid = d.get("community")
    if cid is not None:
        communities.setdefault(int(cid), []).append(nid)

vault_nodes = {nid for nid in G.nodes if not is_missing(nid)}
extracted_pairs: set[frozenset] = {
    frozenset((u, v))
    for u, v, d in G.edges(data=True)
    if d.get("confidence") == "EXTRACTED" and not is_missing(u) and not is_missing(v)
}

actions: list[dict] = []

for nid, _d in sorted(G.nodes(data=True)):
    if not is_missing(nid):
        continue
    sources = sorted({edata.get("source_file", "") for _, target, edata in G.edges(data=True) if target == nid})
    add_action(
        actions,
        "create_missing_page",
        f"Создать или исправить missing page: [[{node_label(nid)}]]",
        sources,
        key_parts=(nid, node_label(nid)),
        reason="В vault есть wikilink на страницу, которой нет в корпусе.",
    )

community_suggestions = 0
for cid, members in sorted(communities.items(), key=lambda x: -len(x[1])):
    vault_members = [m for m in members if m in vault_nodes]
    if len(vault_members) < MIN_COMMUNITY_SIZE:
        continue
    ranked = sorted(vault_members, key=lambda n: G.degree(n), reverse=True)
    count = 0
    for a, b in combinations(ranked, 2):
        if count >= MAX_SUGGESTIONS_PER_COMMUNITY or community_suggestions >= MAX_TOTAL_SUGGESTIONS:
            break
        if frozenset((a, b)) in extracted_pairs:
            continue
        add_action(
            actions,
            "add_wikilink",
            f"Проверить wikilink: {node_label(a)} ↔ {node_label(b)}",
            [node_file(a), node_file(b)],
            key_parts=(cid, a, b),
            reason=f"Обе страницы в community-{cid}, но между ними нет прямой wikilink-связи.",
            meta={"community": cid, "degree_a": G.degree(a), "degree_b": G.degree(b)},
        )
        count += 1
        community_suggestions += 1

for u, v, d in G.edges(data=True):
    if d.get("confidence") != "INFERRED":
        continue
    if u not in vault_nodes or v not in vault_nodes:
        continue
    if frozenset((u, v)) in extracted_pairs:
        continue
    relation = d.get("relation", "")
    add_action(
        actions,
        "review_inferred_edge",
        f"Проверить inferred edge: {node_label(u)} ↔ {node_label(v)}",
        [node_file(u), node_file(v)],
        key_parts=(u, v, relation),
        reason=f"Связь найдена по `{relation}` и требует человеческого решения перед promotion в wikilink.",
        meta={"relation": relation},
    )

for nid in sorted(vault_nodes):
    if G.degree(nid) <= 1:
        add_action(
            actions,
            "attach_orphan",
            f"Разобрать слабосвязанный узел: {node_label(nid)}",
            [node_file(nid)],
            key_parts=(nid, G.degree(nid)),
            reason="Узел имеет не больше одной связи; возможно, ему нужны wikilinks или MOC.",
            meta={"degree": G.degree(nid)},
        )

for cid, members in sorted(communities.items()):
    vault_members = [m for m in members if m in vault_nodes]
    if len(vault_members) < 5:
        continue
    has_domain = any(G.nodes[m].get("node_type") == "domain" for m in vault_members)
    if has_domain:
        continue
    top = sorted(vault_members, key=lambda n: G.degree(n), reverse=True)[:5]
    add_action(
        actions,
        "create_moc_candidate",
        f"Проверить MOC-кандидат для community-{cid}",
        [node_file(n) for n in top],
        key_parts=(cid, len(vault_members), tuple(top)),
        reason="В community 5+ vault-страниц и нет domain/MOC-узла.",
        meta={"community": cid, "size": len(vault_members)},
    )

ready_actions = ready(actions)
blocked_actions = blocked(actions)
historical_actions = historical(actions)
needs_decision = [a for a in ready_actions if a["type"] in {"review_inferred_edge", "add_wikilink", "create_moc_candidate"}]

missing_lines = [
    "# Missing Links - Graph Review Queue",
    "",
    f"Generated from graph.json: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, {len(communities)} communities.",
    "",
    "Этот файл не меняет vault автоматически. Используй action_id в review-state.jsonl, чтобы принять или отклонить предложение.",
    "",
]
missing_lines.extend(render_section("Готово к ревью", ready_actions[:MAX_TOTAL_SUGGESTIONS], "Нет готовых действий."))
missing_lines.extend(render_section("Заблокировано", blocked_actions, "Нет заблокированных действий."))
missing_lines.extend(render_section("Требует решения", needs_decision[:MAX_TOTAL_SUGGESTIONS], "Нет отдельных решений."))
missing_lines.extend(render_section("Принято/отклонено ранее", historical_actions[:MAX_TOTAL_SUGGESTIONS], "Нет сохранённых решений."))
missing_lines.append(f"_Итого: ready={len(ready_actions)}, blocked={len(blocked_actions)}, historical={len(historical_actions)}_")
OUT.write_text("\n".join(missing_lines), encoding="utf-8")

ready_lines = [
    "# GRAPH_READY - Beads-style queue",
    "",
    "Очередь действий по графу. Это производный отчёт: он не является источником истины и не правит wiki/raw-sources.",
    "",
    f"- graph: `{GRAPH}`",
    f"- review_state: `{REVIEW_STATE}`",
    f"- nodes: {G.number_of_nodes()}",
    f"- edges: {G.number_of_edges()}",
    f"- communities: {len(communities)}",
    "",
]
ready_lines.extend(render_section("Готово к ревью", ready_actions, "Нет готовых действий."))
ready_lines.extend(render_section("Заблокировано", blocked_actions, "Нет заблокированных действий."))
ready_lines.extend(render_section("Требует решения", needs_decision, "Нет отдельных решений."))
ready_lines.extend(render_section("Принято/отклонено ранее", historical_actions, "Нет сохранённых решений."))
ready_lines.append(f"_Итого: ready={len(ready_actions)}, blocked={len(blocked_actions)}, needs_decision={len(needs_decision)}, historical={len(historical_actions)}_")
READY_OUT.write_text("\n".join(ready_lines), encoding="utf-8")

print(f"wrote {OUT}")
print(f"wrote {READY_OUT}")
print(f"  ready: {len(ready_actions)}")
print(f"  blocked: {len(blocked_actions)}")
print(f"  historical: {len(historical_actions)}")
