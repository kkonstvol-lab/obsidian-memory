#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bridge_health.py"
SCRIPTS_DIR = SCRIPT.parent


def load_module():
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("bridge_health", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_converted_without_summary_is_warn() -> None:
    bridge = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write(root / "raw-sources/converted/source.md", "---\ntitle: Source\n---\n# Source\n")
        findings = bridge.bridge_converted_to_summary(root)
        assert any(item.bridge == "converted_to_summary" and item.severity == "warn" for item in findings)


def test_lesson_lint_missing_from_check_all_is_blocker() -> None:
    bridge = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write(root / "12-shared/scripts/memory_operator.py", "def run_check_all(): pass\n")
        findings = bridge.bridge_lesson_to_gate(root)
        assert any(item.bridge == "lesson_to_gate" and item.severity == "blocker" for item in findings)


def test_graph_action_without_review_state_is_unreviewed() -> None:
    bridge = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write(root / "12-shared/graph/graphify-out/GRAPH_READY.md", "- [ ] `gq-abc123` **Check**\n")
        write(root / "12-shared/graph/review-state.jsonl", "")
        findings = bridge.bridge_graph_action_to_review_state(root)
        assert any(item.bridge == "graph_action_to_review_state" and item.status == "unreviewed" for item in findings)


def test_articles_are_not_forced_through_raw_conversion_bridge() -> None:
    bridge = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write(
            root / "raw-sources/provenance/raw-local-manifest.jsonl",
            '{"local_cache_path":"raw-sources/articles/direct-source.md","converted_path":""}\n',
        )
        findings = bridge.bridge_raw_to_converted(root)
        assert findings == []


def test_status_report_buckets_known_backlog_separately() -> None:
    bridge = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write(root / "12-shared/graph/graphify-out/GRAPH_READY.md", "- [ ] `gq-abc123` **Check**\n")
        findings = bridge.bridge_graph_action_to_review_state(root)
        report = bridge.status_report(root, findings)
        assert report["buckets"]["known_backlog"] == 1
        assert report["buckets"]["blocker"] == 0
        assert "derived_reports" in report["artifact_classes"]


if __name__ == "__main__":
    test_converted_without_summary_is_warn()
    test_lesson_lint_missing_from_check_all_is_blocker()
    test_graph_action_without_review_state_is_unreviewed()
    test_articles_are_not_forced_through_raw_conversion_bridge()
    test_status_report_buckets_known_backlog_separately()
    print("bridge_health tests passed")
