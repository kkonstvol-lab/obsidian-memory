#!/usr/bin/env python3
"""Read-only release/push preflight for memory-related repos."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from _operator_utils import markdown_table


INTENTS = {"generic", "vault-memory", "public-obsidian-memory", "agent-skills"}
RAW_BINARY_SUFFIXES = {".pdf", ".docx", ".zip"}
LOCAL_RAW_PREFIXES = ("raw-sources/pdfs/", "raw-sources/00 RAW INBOX/")


@dataclass(frozen=True)
class Risk:
    severity: str
    code: str
    message: str


def run_git(repo: Path, args: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.returncode, result.stdout.rstrip("\n"), result.stderr.strip()


def git_or_empty(repo: Path, args: list[str]) -> str:
    code, out, _err = run_git(repo, args)
    return out if code == 0 else ""


def find_git_root(path: Path) -> Path:
    code, out, err = run_git(path, ["rev-parse", "--show-toplevel"])
    if code != 0 or not out:
        raise RuntimeError(err or f"{path} is not inside a git repository")
    return Path(out)


def split_status(status: str) -> dict[str, list[str]]:
    staged: list[str] = []
    unstaged: list[str] = []
    untracked: list[str] = []
    for line in status.splitlines():
        if not line:
            continue
        code = line[:2]
        path = line[2:].lstrip() if len(line) > 2 else ""
        if code == "??":
            untracked.append(path)
            continue
        if code[0] != " ":
            staged.append(path)
        if code[1] != " ":
            unstaged.append(path)
    return {"staged": staged, "unstaged": unstaged, "untracked": untracked}


def changed_paths(working_tree: dict[str, object]) -> list[str]:
    paths: list[str] = []
    for key in ("staged", "unstaged", "untracked"):
        paths.extend(str(item) for item in working_tree.get(key, []))
    return sorted(dict.fromkeys(paths))


def remote_url(root: Path, remote_name: str) -> str:
    if not remote_name:
        return ""
    return git_or_empty(root, ["remote", "get-url", remote_name])


def collect_repo(root: Path) -> dict[str, object]:
    branch = git_or_empty(root, ["branch", "--show-current"])
    origin_url = remote_url(root, "origin")
    upstream = git_or_empty(root, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    upstream_remote = upstream.split("/", 1)[0] if "/" in upstream else ""
    upstream_url = remote_url(root, upstream_remote)
    ahead = 0
    behind = 0
    if upstream:
        counts = git_or_empty(root, ["rev-list", "--left-right", "--count", f"HEAD...{upstream}"])
        if counts:
            left, right = (counts.split() + ["0", "0"])[:2]
            ahead = int(left)
            behind = int(right)
    return {
        "root": str(root),
        "branch": branch,
        "origin_url": origin_url,
        "upstream": upstream,
        "upstream_remote": upstream_remote,
        "upstream_url": upstream_url,
        "ahead": ahead,
        "behind": behind,
        "last_commit": git_or_empty(root, ["log", "--oneline", "-1"]),
    }


def collect_working_tree(root: Path) -> dict[str, object]:
    status = git_or_empty(root, ["status", "--short"])
    parts = split_status(status)
    data: dict[str, object] = {
        "status_short": status.splitlines(),
        "staged": parts["staged"],
        "unstaged": parts["unstaged"],
        "untracked": parts["untracked"],
        "staged_with_status": git_or_empty(root, ["diff", "--cached", "--name-status"]).splitlines(),
    }
    data["is_clean"] = not data["status_short"]
    return data


def detect_surface(root: Path, repo: dict[str, object], paths: list[str]) -> dict[str, object]:
    remote = f"{repo.get('origin_url', '')} {repo.get('upstream_url', '')}".lower()
    repo_name = root.name.lower()
    reasons: list[str] = []
    surface = "unknown"

    if repo_name == "obsidian-vault" or "obsidian-vault" in remote:
        surface = "obsidian-vault"
        reasons.append("repo name or remote matches obsidian-vault")
    elif repo_name == "obsidian-memory" or remote.rstrip("/").endswith("/obsidian-memory.git"):
        surface = "standalone-obsidian-memory"
        reasons.append("repo name or remote matches standalone obsidian-memory")
    elif "agents" in repo_name and (
        any(path.startswith("agent-skills/obsidian-memory/") for path in paths)
        or (root / "agent-skills/obsidian-memory").exists()
    ):
        surface = "agents-monorepo-obsidian-memory"
        reasons.append("agents-style repo contains obsidian-memory skill copy")
    elif any(path.startswith("agent-skills/") or path.startswith("codex-skills/") for path in paths):
        surface = "agent-skills"
        reasons.append("changed paths include agent skill directories")

    return {
        "type": surface,
        "confidence": "high" if surface != "unknown" else "low",
        "reasons": reasons or ["no known surface rule matched"],
    }


def expected_remote_matches(expected: str, repo: dict[str, object]) -> bool:
    if not expected:
        return True
    candidates = {
        str(repo.get("upstream_remote", "")),
        str(repo.get("upstream_url", "")),
        str(repo.get("origin_url", "")),
        "origin" if repo.get("origin_url") else "",
    }
    return expected in candidates


def recommended_commands(intent: str) -> list[str]:
    base = ["git status --short --branch", "git diff --check"]
    if intent == "vault-memory":
        return [
            "python3 12-shared/scripts/wiki_lint.py --json",
            "python3 12-shared/scripts/bridge_health.py --status --json",
            *base,
        ]
    if intent == "public-obsidian-memory":
        return [
            "git status --short --branch",
            "git diff --check",
            "python3 -m py_compile assets/operator/*.py",
            "verify standalone and monorepo skill copy if both are in scope",
            "ensure public commits include: Co-authored-by: Codex <noreply@openai.com>",
        ]
    if intent == "agent-skills":
        return ["git status --short --branch", "git remote -v", "run the repo's skill tests", *base]
    return base


def collect_risks(
    *,
    repo: dict[str, object],
    working_tree: dict[str, object],
    surface: dict[str, object],
    intent: str,
    strict: bool,
    expected_branch: str,
    expected_remote: str,
) -> list[Risk]:
    risks: list[Risk] = []
    branch = str(repo.get("branch", ""))
    if not repo.get("upstream"):
        risks.append(Risk("warn", "no_upstream", "No upstream branch is configured; default push target is unclear."))
    if expected_branch and branch != expected_branch:
        risks.append(
            Risk(
                "blocker" if strict else "warn",
                "expected_branch_mismatch",
                f"Current branch `{branch or '(detached)'}` does not match expected branch `{expected_branch}`.",
            )
        )
    if expected_remote and not expected_remote_matches(expected_remote, repo):
        risks.append(
            Risk(
                "blocker" if strict else "warn",
                "expected_remote_mismatch",
                f"Configured remote/upstream does not match expected remote `{expected_remote}`.",
            )
        )
    if working_tree["unstaged"] or working_tree["untracked"]:
        risks.append(Risk("warn", "dirty_worktree", "Working tree has unstaged or untracked files."))
    if working_tree["staged"]:
        risks.append(Risk("warn", "staged_changes", "There are staged changes; confirm the release packet before commit/push."))
    staged_raw = [
        path
        for path in working_tree["staged"]
        if Path(path).suffix.lower() in RAW_BINARY_SUFFIXES
        and (path.startswith(LOCAL_RAW_PREFIXES) or path.startswith("raw-sources/"))
    ]
    if staged_raw:
        risks.append(Risk("blocker", "staged_raw_binary", f"Staged RAW binary paths detected: {', '.join(staged_raw)}."))

    surface_type = str(surface.get("type", "unknown"))
    if surface_type == "unknown" and intent != "generic":
        risks.append(Risk("warn", "unknown_surface", "Release surface could not be identified from path, remote, or changed files."))
    if intent == "public-obsidian-memory":
        risks.append(Risk("info", "codex_attribution", "Public Codex-attributed commits should include `Co-authored-by: Codex <noreply@openai.com>`."))
        if surface_type == "agents-monorepo-obsidian-memory":
            risks.append(Risk("blocker", "standalone_verification_required", "Verify/update standalone obsidian-memory before claiming a monorepo sync release."))
    if intent == "vault-memory" and surface_type != "obsidian-vault":
        risks.append(Risk("blocker" if strict else "warn", "vault_surface_mismatch", f"Intent is vault-memory but detected surface is `{surface_type}`."))
    return risks


def verdict_from_risks(risks: list[Risk]) -> str:
    if any(risk.severity == "blocker" for risk in risks):
        return "blocked"
    if any(risk.severity == "warn" for risk in risks):
        return "needs_review"
    return "ready"


def post_push_obligations(intent: str, surface: dict[str, object]) -> list[str]:
    if intent == "vault-memory" or surface.get("type") == "obsidian-vault":
        return ["After successful push, update the relevant agent memory/handoff note if task state changed."]
    return []


def collect(args: argparse.Namespace) -> dict[str, object]:
    root = find_git_root(Path(args.repo).expanduser().resolve())
    repo = collect_repo(root)
    working_tree = collect_working_tree(root)
    surface = detect_surface(root, repo, changed_paths(working_tree))
    push_target = repo["upstream"] or f"{repo['upstream_remote'] or 'origin'}/{repo['branch'] or 'HEAD'}"
    push_boundary = {
        "push_target": push_target,
        "has_upstream": bool(repo["upstream"]),
        "expected_branch": args.expected_branch or "",
        "expected_branch_matches": not args.expected_branch or repo["branch"] == args.expected_branch,
        "expected_remote": args.expected_remote or "",
        "expected_remote_matches": expected_remote_matches(args.expected_remote or "", repo),
    }
    risks = collect_risks(
        repo=repo,
        working_tree=working_tree,
        surface=surface,
        intent=args.intent,
        strict=args.strict,
        expected_branch=args.expected_branch or "",
        expected_remote=args.expected_remote or "",
    )
    obligations = post_push_obligations(args.intent, surface)
    for obligation in obligations:
        risks.append(Risk("info", "post_push_memory_obligation", obligation))
    verdict = verdict_from_risks(risks)
    return {
        "mode": "dry-run",
        "verdict": verdict,
        "repo": repo,
        "push_boundary": push_boundary,
        "working_tree": working_tree,
        "surface": surface,
        "risks": [asdict(risk) for risk in risks],
        "release_packet": {
            "verdict": verdict,
            "repo_root": repo.get("root", ""),
            "branch": repo.get("branch", ""),
            "upstream": repo.get("upstream", ""),
            "push_target": push_boundary.get("push_target", ""),
            "surface": surface.get("type", "unknown"),
            "staged_files": working_tree.get("staged", []),
            "unstaged_files": working_tree.get("unstaged", []),
            "untracked_files": working_tree.get("untracked", []),
        },
        "recommended_commands": recommended_commands(args.intent),
        "post_push_obligations": obligations,
    }


def render_markdown(report: dict[str, object]) -> str:
    repo = report["repo"]
    push = report["push_boundary"]
    tree = report["working_tree"]
    surface = report["surface"]
    packet = report["release_packet"]
    risk_rows = [[risk["severity"], risk["code"], risk["message"]] for risk in report["risks"]] or [["info", "none", "No release risks detected."]]
    packet_rows = [[key, value if not isinstance(value, list) else ", ".join(value) or "(none)"] for key, value in packet.items()]
    return "\n".join(
        [
            "# RELEASE_STATUS",
            "",
            "Read-only release/push preflight. This command does not stage, commit, push, write memory, or mutate tracked files.",
            "",
            f"## Verdict\n\n`{report['verdict']}`",
            "",
            "## Repo Identity",
            markdown_table(
                ["field", "value"],
                [
                    ["root", repo["root"]],
                    ["branch", repo["branch"] or "(detached)"],
                    ["origin_url", repo["origin_url"] or "(none)"],
                    ["upstream", repo["upstream"] or "(none)"],
                    ["upstream_url", repo["upstream_url"] or "(none)"],
                    ["ahead/behind", f"{repo['ahead']}/{repo['behind']}"],
                    ["last_commit", repo["last_commit"] or "(none)"],
                ],
            ),
            "",
            "## Push Boundary",
            markdown_table(
                ["field", "value"],
                [
                    ["push_target", push["push_target"] or "(unknown)"],
                    ["has_upstream", "yes" if push["has_upstream"] else "no"],
                    ["expected_branch", push["expected_branch"] or "(not provided)"],
                    ["expected_branch_matches", "yes" if push["expected_branch_matches"] else "no"],
                    ["expected_remote", push["expected_remote"] or "(not provided)"],
                    ["expected_remote_matches", "yes" if push["expected_remote_matches"] else "no"],
                ],
            ),
            "",
            "## Working Tree",
            markdown_table(
                ["field", "value"],
                [
                    ["staged", ", ".join(tree["staged"]) or "(none)"],
                    ["unstaged", ", ".join(tree["unstaged"]) or "(none)"],
                    ["untracked", ", ".join(tree["untracked"]) or "(none)"],
                ],
            ),
            "",
            "## Detected Surface",
            markdown_table(
                ["field", "value"],
                [["type", surface["type"]], ["confidence", surface["confidence"]], ["reasons", "; ".join(surface["reasons"])]],
            ),
            "",
            "## Risks",
            markdown_table(["severity", "code", "message"], risk_rows),
            "",
            "## Release Packet",
            markdown_table(["field", "value"], packet_rows),
            "",
            "## Recommended Checks",
            "\n".join(f"- `{cmd}`" for cmd in report["recommended_commands"]),
            "",
            "## Post-Push Obligations",
            "\n".join(f"- {item}" for item in report["post_push_obligations"]) if report["post_push_obligations"] else "_No post-push obligations detected._",
        ]
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Read-only release/push status packet")
    ap.add_argument("--repo", default=".", help="Repo or path inside repo to inspect")
    ap.add_argument("--intent", choices=sorted(INTENTS), default="generic")
    ap.add_argument("--expected-branch", default="")
    ap.add_argument("--expected-remote", default="")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = collect(args)
    except RuntimeError as exc:
        print(f"release-status error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report))
    return 1 if report["verdict"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
