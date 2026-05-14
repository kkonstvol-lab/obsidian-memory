#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "retrieval_eval.py"
SCRIPTS_DIR = SCRIPT.parent


def load_module():
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("retrieval_eval", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_query_returns_source_path_confidence_and_reason() -> None:
    retrieval = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write(
            root / "12-codex/memory_corrections.md",
            "# Corrections\n\n## Commit staging leak\n\nRule extracted: check staged index before grouped commit.\n",
        )
        candidates = retrieval.query(root, "staging commit leak", 5)
        assert candidates
        assert candidates[0].path == "12-codex/memory_corrections.md"
        assert candidates[0].confidence in {"low", "medium", "high"}
        assert "matched" in candidates[0].reason


def test_record_miss_is_dry_run_without_apply() -> None:
    retrieval = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        with redirect_stdout(StringIO()):
            code = retrieval.append_event(
                root,
                retrieval.MISS_LOG,
                {
                    "kind": "missed-retrieval",
                    "query": "raw cache pdf",
                    "expected_path": "12-shared/memory_decisions.md",
                    "reason": "fixture",
                    "status": "active",
                },
                apply=False,
            )
        assert code == 0
        assert not (root / retrieval.MISS_LOG).exists()


def test_apply_requires_approval_marker() -> None:
    retrieval = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        old = os.environ.pop("MEMORY_OPERATOR_APPROVED", None)
        try:
            with redirect_stdout(StringIO()):
                code = retrieval.append_event(
                    root,
                    retrieval.MISS_LOG,
                    {
                        "kind": "missed-retrieval",
                        "query": "raw cache pdf",
                        "expected_path": "12-shared/memory_decisions.md",
                        "reason": "fixture",
                        "status": "active",
                    },
                    apply=True,
                )
        finally:
            if old is not None:
                os.environ["MEMORY_OPERATOR_APPROVED"] = old
        assert code == 1
        assert not (root / retrieval.MISS_LOG).exists()


def test_replay_reports_stable_metrics() -> None:
    retrieval = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write(
            root / "12-codex/memory_corrections.md",
            "# Corrections\n\n## Commit staging leak\n\nRule extracted: check staged index before grouped commit.\n",
        )
        baseline = retrieval.baseline_rows(root, ["staging commit leak"], 5)
        report = retrieval.replay_rows(root, baseline)
        assert report["summary"]["rows_total"] == 1
        assert report["summary"]["rows_replayed"] == 1
        assert report["summary"]["mean_jaccard"] == 1.0
        assert report["summary"]["top1_stability_rate"] == 1.0


def test_export_baseline_dry_run_does_not_write() -> None:
    retrieval = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        rows = [{"schema_version": 1, "id": 1, "query": "x", "retrieved_paths": []}]
        with redirect_stdout(StringIO()):
            code = retrieval.write_jsonl(root / "12-codex/retrieval-eval/baselines/test.jsonl", rows, apply=False)
        assert code == 0
        assert not (root / "12-codex/retrieval-eval/baselines/test.jsonl").exists()


if __name__ == "__main__":
    test_query_returns_source_path_confidence_and_reason()
    test_record_miss_is_dry_run_without_apply()
    test_apply_requires_approval_marker()
    test_replay_reports_stable_metrics()
    test_export_baseline_dry_run_does_not_write()
    print("retrieval_eval tests passed")
