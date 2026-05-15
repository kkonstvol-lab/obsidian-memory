#!/usr/bin/env python3
"""Read-only branch close and handoff report for memory operators."""
from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from _operator_utils import FRONTMATTER_RE, markdown_table, read_text, rel, vault_root


SCHEMA_VERSION = "branch-close-pack.v1"
DEFAULT_CAP = 25
DEFAULT_MD_LINES = 180


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str


def agent_dir(agent: str) -> str:
    return f"12-{agent}"


def run_git(root: Path, args: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(["git", "-C", str(root), *args], check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.returncode, result.stdout.rstrip("\n"), result.stderr.strip()


def git(root: Path, args: list[str]) -> str:
    code, out, _err = run_git(root, args)
    return out if code == 0 else ""


def short_head(root: Path) -> str:
    return git(root, ["rev-parse", "--short", "HEAD"])


def parse_ahead_behind(root: Path, upstream: str) -> tuple[int | None, int | None]:
    if not upstream:
        return None, None
    counts = git(root, ["rev-list", "--left-right", "--count", f"HEAD...{upstream}"])
    if not counts:
        return None, None
    left, right = (counts.split() + ["0", "0"])[:2]
    try:
        return int(left), int(right)
    except ValueError:
        return None, None


def parse_status_porcelain(text: str) -> dict[str, Any]:
    staged: list[dict[str, str]] = []
    unstaged: list[dict[str, str]] = []
    untracked: list[str] = []
    for line in text.splitlines():
        if not line:
            continue
        code = line[:2]
        path = line[3:] if len(line) > 3 else line[2:].strip()
        if code == "??":
            untracked.append(path)
            continue
        if code[0] != " ":
            staged.append({"status": code[0], "path": path})
        if code[1] != " ":
            unstaged.append({"status": code[1], "path": path})
    return {"staged": staged, "unstaged": unstaged, "untracked": untracked, "clean": not staged and not unstaged and not untracked}


def cap(items: list[Any], verbose: bool) -> list[Any]:
    return items if verbose else items[:DEFAULT_CAP]


def collect_repo(root: Path) -> dict[str, Any]:
    upstream = git(root, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    ahead, behind = parse_ahead_behind(root, upstream)
    return {
        "root": str(root),
        "branch": git(root, ["branch", "--show-current"]),
        "upstream": upstream or None,
        "head": short_head(root),
        "remote_origin": git(root, ["remote", "get-url", "origin"]) or None,
        "ahead": ahead,
        "behind": behind,
    }


def collect_recent_commits(root: Path, verbose: bool) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in git(root, ["log", "--oneline", "-50" if verbose else "-25"]).splitlines():
        if not line.strip():
            continue
        sha, _, subject = line.partition(" ")
        rows.append({"sha": sha, "subject": subject})
    return rows


def markdown_bullets_from_sections(path: Path, max_items: int) -> list[str]:
    text = read_text(path)
    items: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") and len(stripped) > 2:
            items.append(stripped[2:])
        elif stripped.startswith("## "):
            items.append(stripped[3:])
        if len(items) >= max_items:
            break
    return items


def recent_corrections(root: Path, agent: str, max_items: int) -> list[str]:
    path = root / agent_dir(agent) / "memory_corrections.md"
    text = read_text(path)
    return [line[3:].strip() for line in text.splitlines() if line.startswith("## ")][:max_items]


def collect_memory(root: Path, agent: str, verbose: bool) -> dict[str, list[str]]:
    limit = 25 if verbose else 8
    base = root / agent_dir(agent)
    return {
        "recent_done": markdown_bullets_from_sections(base / "memory_in_progress.md", limit),
        "active_debt": markdown_bullets_from_sections(base / "memory_active.md", limit),
        "recent_corrections": recent_corrections(root, agent, limit),
    }


def parse_lesson_frontmatter(path: Path) -> dict[str, Any]:
    match = FRONTMATTER_RE.match(read_text(path))
    if not match:
        return {}
    out: dict[str, Any] = {}
    for line in match.group(1).splitlines():
        if ":" not in line or line.startswith(" "):
            continue
        key, value = line.split(":", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def lesson_summary(root: Path, agent: str) -> dict[str, int]:
    out = {"draft": 0, "active": 0, "needs_review": 0}
    base = root / agent_dir(agent) / "lessons"
    for path in sorted(base.glob("*.md")) if base.exists() else []:
        if path.name.lower() == "readme.md":
            continue
        fm = parse_lesson_frontmatter(path)
        status = str(fm.get("status", ""))
        if status in out:
            out[status] += 1
        if str(fm.get("human_reviewed", "false")).lower() != "true":
            out["needs_review"] += 1
    return out


def graph_summary(root: Path) -> dict[str, int]:
    ready_path = root / "12-shared" / "graph" / "graphify-out" / "GRAPH_READY.md"
    state_path = root / "12-shared" / "graph" / "review-state.jsonl"
    ready = read_text(ready_path)
    state_count = 0
    if state_path.exists():
        state_count = len([line for line in state_path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()])
    return {"ready": ready.count("`gq-"), "historical": state_count, "open_without_review_state": 0}


def bridge_summary(root: Path, agent: str) -> dict[str, int]:
    previous = os.environ.get("OBSIDIAN_AGENT_ID")
    try:
        os.environ["OBSIDIAN_AGENT_ID"] = agent
        import bridge_health

        bridge_health = importlib.reload(bridge_health)
        bridge_collect = bridge_health.collect

        findings = bridge_collect(root)
        counts: dict[str, int] = {}
        for item in findings:
            status = getattr(item, "status", "info")
            counts[status] = counts.get(status, 0) + 1
        return {
            "broken": int(counts.get("broken", 0)),
            "stale": int(counts.get("stale", 0)),
            "unreviewed": int(counts.get("unreviewed", 0)),
            "healthy": int(counts.get("healthy", 0)),
        }
    except Exception:
        return {"broken": 0, "stale": 0, "unreviewed": 0, "healthy": 0}
    finally:
        if previous is None:
            os.environ.pop("OBSIDIAN_AGENT_ID", None)
        else:
            os.environ["OBSIDIAN_AGENT_ID"] = previous


def lesson_lint_blockers(root: Path, agent: str) -> int:
    try:
        from lesson_lint import lint

        return len([item for item in lint(root, agent) if item.severity == "blocker"])
    except Exception:
        return 0


def findings(repo: dict[str, Any], working_tree: dict[str, Any], backlog: dict[str, Any], root: Path, agent: str) -> list[Finding]:
    out: list[Finding] = []
    if working_tree["staged"]:
        out.append(Finding("blocker", "staged_scope_present", "Staged files are present; review scope before closing the branch."))
    if working_tree["unstaged"] or working_tree["untracked"]:
        out.append(Finding("blocker", "dirty_worktree", "Working tree is not clean; handoff can be incomplete."))
    if not repo.get("upstream"):
        out.append(Finding("blocker", "missing_upstream", "Branch has no upstream; sync target is unclear."))
    if repo.get("behind"):
        out.append(Finding("blocker", "branch_behind_upstream", "Local branch is behind upstream."))
    if lesson_lint_blockers(root, agent):
        out.append(Finding("blocker", "lesson_lint_blockers", "lesson_lint reports blocker findings."))
    if int(backlog["bridges"].get("broken", 0)) > 0:
        out.append(Finding("blocker", "bridge_broken", "bridge_health reports broken bridges."))
    return out


def collect(root: Path, agent: str, verbose: bool) -> dict[str, Any]:
    repo = collect_repo(root)
    working_tree = parse_status_porcelain(git(root, ["status", "--porcelain"]))
    memory = collect_memory(root, agent, verbose)
    backlog = {"lessons": lesson_summary(root, agent), "graph": graph_summary(root), "bridges": bridge_summary(root, agent)}
    result = {
        "schema_version": SCHEMA_VERSION,
        "mode": "dry-run",
        "agent": agent,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "repo": repo,
        "working_tree": {
            "staged": cap(working_tree["staged"], verbose),
            "unstaged": cap(working_tree["unstaged"], verbose),
            "untracked": cap(working_tree["untracked"], verbose),
            "clean": working_tree["clean"],
        },
        "recent_commits": cap(collect_recent_commits(root, verbose), verbose),
        "memory": memory,
        "backlog": backlog,
        "handoff": {
            "done_candidates": memory["recent_done"][:8],
            "remaining_candidates": memory["active_debt"][:8],
            "risks": [],
            "next_branch_recommendation": "Create a short branch from the current upstream after handoff review.",
        },
        "verification_commands": [
            "git status --short --branch",
            "python3 assets/operator/lesson_review_board.py --md",
            "python3 assets/operator/release_surface_check.py --profile public-skill --md",
            "run the repo's release gates",
        ],
        "findings": [],
    }
    result["findings"] = [asdict(item) for item in findings(repo, working_tree, backlog, root, agent)]
    result["handoff"]["risks"] = [item["message"] for item in result["findings"] if item["severity"] != "info"]
    return result


def render_markdown(report: dict[str, Any], verbose: bool) -> str:
    repo = report["repo"]
    wt = report["working_tree"]
    lines = [
        "# BRANCH_CLOSE dry-run",
        "",
        "Nothing changed. This report only gathers branch-close context.",
        "",
        "## Repo",
        markdown_table(
            ["field", "value"],
            [["root", repo["root"]], ["branch", repo["branch"]], ["upstream", repo["upstream"]], ["head", repo["head"]], ["ahead/behind", f"{repo['ahead']}/{repo['behind']}"]],
        ),
        "",
        "## Working Tree",
        markdown_table(["kind", "count"], [["staged", len(wt["staged"])], ["unstaged", len(wt["unstaged"])], ["untracked", len(wt["untracked"])], ["clean", wt["clean"]]]),
        "",
        "## Backlog",
        markdown_table(["area", "summary"], [["lessons", report["backlog"]["lessons"]], ["graph", report["backlog"]["graph"]], ["bridges", report["backlog"]["bridges"]]]),
        "",
        "## Findings",
        markdown_table(["severity", "code", "message"], ([f["severity"], f["code"], f["message"]] for f in report["findings"])) if report["findings"] else "_No findings._",
        "",
        "## Recent Commits",
        "\n".join(f"- `{c['sha']}` {c['subject']}" for c in report["recent_commits"]) or "_No commits._",
        "",
        "## Handoff Skeleton",
        "### Done Candidates",
        "\n".join(f"- {item}" for item in report["handoff"]["done_candidates"]) or "- review required",
        "",
        "### Remaining Candidates",
        "\n".join(f"- {item}" for item in report["handoff"]["remaining_candidates"]) or "- review required",
        "",
        "### Risks",
        "\n".join(f"- {item}" for item in report["handoff"]["risks"]) or "- none detected",
        "",
        "### Next Branch",
        f"- {report['handoff']['next_branch_recommendation']}",
        "",
        "## Verification",
        "\n".join(f"- `{cmd}`" for cmd in report["verification_commands"]),
    ]
    return "\n".join(lines if verbose else lines[:DEFAULT_MD_LINES])


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a read-only branch close pack")
    fmt = ap.add_mutually_exclusive_group()
    fmt.add_argument("--md", action="store_true")
    fmt.add_argument("--json", action="store_true")
    ap.add_argument("--root", default=str(vault_root()))
    ap.add_argument("--agent", default="agent")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    report = collect(root, args.agent, args.verbose)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report, args.verbose))
    raise SystemExit(2 if any(item["severity"] == "blocker" for item in report["findings"]) else 0)


if __name__ == "__main__":
    main()
