"""
Standalone fixture checks for Beads-inspired graphify behavior.

Run from 12-shared/graph:
    python tests/test_graphify_beads.py
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "minimal-vault"
EXTRACT = ROOT / "extract_vault.py"
SUGGEST = ROOT / "suggest_wikilinks.py"
RAW_SOURCE = FIXTURE / "raw-sources" / "articles" / "raw-source.md"


def run_script(script: Path, out_dir: Path, review_state: Path) -> None:
    env = os.environ.copy()
    env["GRAPHIFY_VAULT"] = str(FIXTURE)
    env["GRAPHIFY_OUT"] = str(out_dir)
    env["GRAPHIFY_REVIEW_STATE"] = str(review_state)
    subprocess.run([sys.executable, str(script)], cwd=str(ROOT), env=env, check=True)


def graph_ids(out_dir: Path) -> tuple[set[str], set[str], dict]:
    data = json.loads((out_dir / "graph.json").read_text(encoding="utf-8"))
    node_ids = {n["stable_id"] for n in data["nodes"]}
    edge_ids = {e["edge_id"] for e in data["links"]}
    return node_ids, edge_ids, data


def main() -> None:
    original_raw = RAW_SOURCE.read_text(encoding="utf-8")
    tmp = Path(tempfile.mkdtemp(prefix="graphify-beads-"))
    try:
        review_state = tmp / "review-state.jsonl"
        out1 = tmp / "out1"
        out2 = tmp / "out2"
        out1.mkdir()
        out2.mkdir()
        review_state.write_text("", encoding="utf-8")

        run_script(EXTRACT, out1, review_state)
        run_script(SUGGEST, out1, review_state)
        nodes1, edges1, data1 = graph_ids(out1)

        run_script(EXTRACT, out2, review_state)
        run_script(SUGGEST, out2, review_state)
        nodes2, edges2, _ = graph_ids(out2)

        assert nodes1 == nodes2, "node stable IDs changed between runs"
        assert edges1 == edges2, "edge stable IDs changed between runs"
        assert all("node_type" in n and "source_path" in n and "stable_id" in n for n in data1["nodes"])
        assert all("edge_id" in e and "review_status" in e and "source_file" in e for e in data1["links"])

        ready_text = (out1 / "GRAPH_READY.md").read_text(encoding="utf-8")
        assert "Готово к ревью" in ready_text
        assert "Заблокировано" in ready_text
        assert "Требует решения" in ready_text
        assert "Принято/отклонено ранее" in ready_text
        assert "create_missing_page" in ready_text

        match = re.search(r"`(gq-[0-9a-f]+)` \*\*Создать или исправить missing page", ready_text)
        assert match, "missing-page action ID not found"
        skipped_id = match.group(1)
        review_state.write_text(
            json.dumps({"id": skipped_id, "status": "skipped", "reason": "fixture"}) + "\n",
            encoding="utf-8",
        )

        out3 = tmp / "out3"
        out3.mkdir()
        run_script(EXTRACT, out3, review_state)
        run_script(SUGGEST, out3, review_state)
        ready3 = (out3 / "GRAPH_READY.md").read_text(encoding="utf-8")
        ready_section = ready3.split("## Заблокировано", 1)[0]
        history_section = ready3.split("## Принято/отклонено ранее", 1)[1]
        assert skipped_id not in ready_section, "skipped action returned as ready"
        assert skipped_id in history_section, "skipped action missing from history"
        assert RAW_SOURCE.read_text(encoding="utf-8") == original_raw, "raw source was modified"

        print("fixture checks passed")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
