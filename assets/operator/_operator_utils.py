#!/usr/bin/env python3
"""Shared helpers for Codex memory-operator dry-run scripts."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable


WIKILINK_RE = re.compile(r"(?<!!)\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def vault_root() -> Path:
    return Path(__file__).resolve().parents[2]


def rel(path: Path, root: Path | None = None) -> str:
    root = root or vault_root()
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def load_json(path: Path) -> dict:
    return json.loads(read_text(path)) if path.exists() else {}


def load_review_state(path: Path) -> dict[str, dict]:
    state: dict[str, dict] = {}
    if not path.exists():
        return state
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        item_id = item.get("id")
        if item_id:
            state[item_id] = item
    return state


def markdown_table(headers: list[str], rows: Iterable[Iterable[object]]) -> str:
    out = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        out.append("| " + " | ".join(_cell(value) for value in row) + " |")
    return "\n".join(out)


def _cell(value: object) -> str:
    text = "" if value is None else str(value)
    return text.replace("\n", "<br>").replace("|", "\\|")


def approval_packet(
    operation: str,
    files_to_read: list[str],
    files_to_write: list[str] | None = None,
    files_to_move: list[str] | None = None,
    risks: list[str] | None = None,
    verification: list[str] | None = None,
) -> str:
    lines = [
        "## Approval Packet",
        "",
        f"- Operation: `{operation}`",
        "- Mode: `dry-run -> apply`",
        f"- Files to read: {', '.join(f'`{p}`' for p in files_to_read) or 'none'}",
        f"- Files to write: {', '.join(f'`{p}`' for p in (files_to_write or [])) or 'none before approval'}",
        f"- Files to move: {', '.join(f'`{p}`' for p in (files_to_move or [])) or 'none before approval'}",
        "- Raw sources affected: read-only",
        "- Shared memory writes: none before approval",
        f"- Risks: {'; '.join(risks or ['classification can be wrong without reading full source'])}",
        f"- Rollback: inspect `git status --short` and revert only approved changes if apply mode is later used",
        f"- Verification: {'; '.join(verification or ['git status --short'])}",
    ]
    return "\n".join(lines)
