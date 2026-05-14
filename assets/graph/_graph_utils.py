"""Small dependency-free graph helpers for the public Obsidian Memory graph tools."""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Iterable


class NodeView:
    def __init__(self, graph: "SimpleGraph") -> None:
        self._graph = graph

    def __iter__(self):
        return iter(self._graph._nodes)

    def __contains__(self, node_id: str) -> bool:
        return node_id in self._graph._nodes

    def __getitem__(self, node_id: str) -> dict:
        return self._graph._nodes[node_id]

    def __call__(self, data: bool = False):
        if data:
            return self._graph._nodes.items()
        return self._graph._nodes.keys()


class EdgeView:
    def __init__(self, graph: "SimpleGraph") -> None:
        self._graph = graph

    def __call__(self, data: bool = False):
        if data:
            return [(u, v, attrs) for u, v, attrs in self._graph._edges]
        return [(u, v) for u, v, _attrs in self._graph._edges]


class SimpleGraph:
    """Minimal undirected multigraph API used by the bundled graph scripts."""

    def __init__(self) -> None:
        self._nodes: dict[str, dict] = {}
        self._edges: list[tuple[str, str, dict]] = []
        self.nodes = NodeView(self)
        self.edges = EdgeView(self)

    def add_node(self, node_id: str, **attrs) -> None:
        self._nodes.setdefault(node_id, {"id": node_id}).update(attrs)

    def add_edge(self, source: str, target: str, **attrs) -> None:
        if source not in self._nodes:
            self.add_node(source)
        if target not in self._nodes:
            self.add_node(target)
        self._edges.append((source, target, dict(attrs)))

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def degree(self, node_id: str) -> int:
        return sum(1 for source, target, _attrs in self._edges if source == node_id or target == node_id)

    def neighbors(self, node_id: str) -> set[str]:
        out: set[str] = set()
        for source, target, _attrs in self._edges:
            if source == node_id:
                out.add(target)
            elif target == node_id:
                out.add(source)
        return out

    def number_of_nodes(self) -> int:
        return len(self._nodes)

    def number_of_edges(self) -> int:
        return len(self._edges)


def validate_extraction(extraction: dict) -> list[str]:
    errors: list[str] = []
    node_ids: set[str] = set()
    for index, node in enumerate(extraction.get("nodes", [])):
        node_id = node.get("id")
        if not node_id:
            errors.append(f"node {index} has no id")
            continue
        if node_id in node_ids:
            errors.append(f"duplicate node id: {node_id}")
        node_ids.add(node_id)
    for index, edge in enumerate(extraction.get("edges", [])):
        source = edge.get("source")
        target = edge.get("target")
        if source not in node_ids:
            errors.append(f"edge {index} has unknown source: {source}")
        if target not in node_ids:
            errors.append(f"edge {index} has unknown target: {target}")
        if not edge.get("edge_id"):
            errors.append(f"edge {index} has no edge_id")
    return errors


def build_graph(extractions: Iterable[dict]) -> SimpleGraph:
    graph = SimpleGraph()
    for extraction in extractions:
        for node in extraction.get("nodes", []):
            attrs = dict(node)
            node_id = attrs.pop("id")
            graph.add_node(node_id, **attrs)
        for edge in extraction.get("edges", []):
            attrs = dict(edge)
            source = attrs.pop("source")
            target = attrs.pop("target")
            graph.add_edge(source, target, **attrs)
    return graph


def connected_communities(graph: SimpleGraph) -> dict[int, list[str]]:
    seen: set[str] = set()
    communities: dict[int, list[str]] = {}
    cid = 0
    for node_id in graph.nodes:
        if node_id in seen:
            continue
        stack = [node_id]
        members: list[str] = []
        seen.add(node_id)
        while stack:
            current = stack.pop()
            members.append(current)
            for neighbor in graph.neighbors(current):
                if neighbor in seen:
                    continue
                seen.add(neighbor)
                stack.append(neighbor)
        communities[cid] = sorted(members)
        cid += 1
    return communities


def score_communities(graph: SimpleGraph, communities: dict[int, list[str]]) -> dict[int, float]:
    scores: dict[int, float] = {}
    edge_pairs = {frozenset((source, target)) for source, target, _attrs in graph.edges(data=True)}
    for cid, members in communities.items():
        if len(members) < 2:
            scores[cid] = 0.0
            continue
        possible = len(members) * (len(members) - 1) / 2
        internal = sum(1 for a, b in combinations(members, 2) if frozenset((a, b)) in edge_pairs)
        scores[cid] = round(internal / possible, 3)
    return scores


def god_nodes(graph: SimpleGraph, top_n: int = 10) -> list[dict]:
    return [
        {"id": node_id, "label": graph.nodes[node_id].get("label", node_id), "degree": graph.degree(node_id)}
        for node_id in sorted(graph.nodes, key=lambda nid: graph.degree(nid), reverse=True)[:top_n]
    ]


def surprising_connections(graph: SimpleGraph, communities: dict[int, list[str]], top_n: int = 7) -> list[dict]:
    community_by_node = {
        node_id: cid
        for cid, members in communities.items()
        for node_id in members
    }
    items: list[dict] = []
    for source, target, attrs in graph.edges(data=True):
        if community_by_node.get(source) == community_by_node.get(target):
            continue
        items.append({
            "source": graph.nodes[source].get("label", source),
            "target": graph.nodes[target].get("label", target),
            "relation": attrs.get("relation", "links_to"),
        })
    return items[:top_n]


def suggest_questions(graph: SimpleGraph, communities: dict[int, list[str]], top_n: int = 7) -> list[str]:
    questions: list[str] = []
    for cid, members in sorted(communities.items(), key=lambda item: -len(item[1])):
        labels = [graph.nodes[nid].get("label", nid) for nid in members[:3]]
        if labels:
            questions.append(f"What connects {', '.join(labels)} in community-{cid}?")
        if len(questions) >= top_n:
            break
    return questions


def node_link_data(graph: SimpleGraph) -> dict:
    return {
        "directed": False,
        "multigraph": True,
        "graph": {},
        "nodes": [{"id": node_id, **attrs} for node_id, attrs in graph.nodes(data=True)],
        "links": [{"source": source, "target": target, **attrs} for source, target, attrs in graph.edges(data=True)],
    }


def node_link_graph(data: dict) -> SimpleGraph:
    graph = SimpleGraph()
    for node in data.get("nodes", []):
        attrs = dict(node)
        node_id = attrs.pop("id")
        graph.add_node(node_id, **attrs)
    for edge in data.get("links", data.get("edges", [])):
        attrs = dict(edge)
        source = attrs.pop("source")
        target = attrs.pop("target")
        graph.add_edge(source, target, **attrs)
    return graph


def generate_report(
    graph: SimpleGraph,
    *,
    communities: dict[int, list[str]],
    cohesion_scores: dict[int, float],
    god_node_list: list[dict],
    surprise_list: list[dict],
    detection_result: dict,
    root: str,
    suggested_questions: list[str],
) -> str:
    lines = [
        "# GRAPH_REPORT",
        "",
        "Derived graph report for Obsidian Memory. This file is rebuildable and does not mutate the vault.",
        "",
        f"- root: `{root}`",
        f"- files: {detection_result.get('total_files', 0)}",
        f"- words: {detection_result.get('total_words', 0)}",
        f"- nodes: {graph.number_of_nodes()}",
        f"- edges: {graph.number_of_edges()}",
        f"- communities: {len(communities)}",
        "",
        "## Communities",
        "",
    ]
    for cid, members in sorted(communities.items()):
        labels = [graph.nodes[nid].get("label", nid) for nid in members[:8]]
        lines.append(f"- community-{cid}: cohesion={cohesion_scores.get(cid, 0.0)}; {', '.join(labels)}")
    lines.extend(["", "## High-Degree Nodes", ""])
    for node in god_node_list:
        lines.append(f"- {node['label']} (`{node['id']}`): degree={node['degree']}")
    lines.extend(["", "## Cross-Community Connections", ""])
    if surprise_list:
        for item in surprise_list:
            lines.append(f"- {item['source']} -> {item['target']} (`{item['relation']}`)")
    else:
        lines.append("- None detected.")
    lines.extend(["", "## Suggested Questions", ""])
    if suggested_questions:
        for question in suggested_questions:
            lines.append(f"- {question}")
    else:
        lines.append("- None generated.")
    return "\n".join(lines) + "\n"
