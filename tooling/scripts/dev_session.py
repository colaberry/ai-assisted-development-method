#!/usr/bin/env python3
"""dev_session.py — structural enforcement for the /dev-test → /dev-impl split.

Method rule 4 says test writing and implementation must be in separate
Claude Code sessions. The original `/dev` skill ran them in the same
session, which left the rule enforced only by convention. This script
turns the split into a filesystem signal that `/dev-impl` must observe
before it can write a line of implementation code.

The signal lives at `sprints/vN/.in-progress/T-NNN.test-session-done`.
It is a tiny YAML-ish file containing the git SHA of the commit that
introduced the failing tests for the task, plus a UTC timestamp. The
`/dev-test` skill writes it after committing the test matrix. The
`/dev-impl` skill reads it via `check-impl-ready`, which:

  1. Refuses if the marker is missing.
  2. Refuses if the recorded commit SHA is not resolvable with
     `git cat-file -e <sha>`.
  3. Refuses if the repo is not a git repo (so the signal is
     verifiable; a weaker fallback is deliberately avoided).

When the task is marked `[x]`, `/dev-impl` calls `mark-complete`, which
moves the marker to `T-NNN.complete` so the next `/dev-test` session for
a different task starts with a clean slate and the audit trail persists.

Subcommands:

    test-done      <sprint-dir> <task-id> --commit-sha <SHA>
    check-impl-ready <sprint-dir> <task-id>
    mark-complete  <sprint-dir> <task-id>

Exit codes:
    0  — success / ready
    1  — refusal (message on stderr)
    2  — argument / usage error
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


MARKER_DIR_NAME = ".in-progress"
TEST_DONE_SUFFIX = ".test-session-done"
COMPLETE_SUFFIX = ".complete"

_TASK_ID_RE = re.compile(r"^T[-_]?\d+$", re.IGNORECASE)
_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


@dataclass
class MarkerPaths:
    sprint_dir: Path
    marker_dir: Path
    test_done: Path
    complete: Path


def normalize_task_id(raw: str) -> str:
    """Return the canonical task id, e.g. "T-012". Hyphen is preserved as-is
    if already present; otherwise we keep exactly what the user gave us, so
    the marker matches the form used in TASKS.md."""
    if not _TASK_ID_RE.match(raw):
        raise ValueError(f"invalid task id: {raw!r} (expected TNNN or T-NNN)")
    return raw


def marker_paths(sprint_dir: Path, task_id: str) -> MarkerPaths:
    marker_dir = sprint_dir / MARKER_DIR_NAME
    return MarkerPaths(
        sprint_dir=sprint_dir,
        marker_dir=marker_dir,
        test_done=marker_dir / f"{task_id}{TEST_DONE_SUFFIX}",
        complete=marker_dir / f"{task_id}{COMPLETE_SUFFIX}",
    )


def write_marker(paths: MarkerPaths, commit_sha: str) -> Path:
    if not _SHA_RE.match(commit_sha):
        raise ValueError(
            f"invalid commit sha {commit_sha!r}; expected 7–40 hex chars"
        )
    paths.marker_dir.mkdir(parents=True, exist_ok=True)
    timestamp = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    body = (
        f"test_commit: {commit_sha}\n"
        f"written_at: {timestamp}\n"
    )
    paths.test_done.write_text(body, encoding="utf-8")
    return paths.test_done


def parse_marker(marker_path: Path) -> Tuple[Optional[str], Optional[str]]:
    """Return (commit_sha, written_at). Either may be None if missing/malformed."""
    try:
        text = marker_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None, None
    commit: Optional[str] = None
    when: Optional[str] = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("test_commit:"):
            commit = line.split(":", 1)[1].strip()
        elif line.startswith("written_at:"):
            when = line.split(":", 1)[1].strip()
    return commit, when


def commit_exists(commit_sha: str, repo_root: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "cat-file", "-e", commit_sha],
            cwd=repo_root,
            check=False,
            capture_output=True,
        )
    except (FileNotFoundError, OSError):
        return False
    return result.returncode == 0


def repo_root_for(sprint_dir: Path) -> Path:
    """Walk up from sprint_dir to find a .git marker. Falls back to parent of
    sprints/ if no .git is found (defensive; caller treats this as 'no git')."""
    current = sprint_dir.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    # fallback: the grandparent of sprints/vN (i.e., the notional repo root)
    parts = current.parts
    if "sprints" in parts:
        idx = parts.index("sprints")
        return Path(*parts[:idx]) if idx > 0 else current
    return current


def check_impl_ready(sprint_dir: Path, task_id: str) -> Tuple[bool, str]:
    """Decide whether /dev-impl may proceed. Returns (ready, message)."""
    paths = marker_paths(sprint_dir, task_id)
    if not paths.test_done.exists():
        return False, (
            f"/dev-impl refusing: no test-done marker for {task_id}.\n"
            f"  Expected: {paths.test_done}\n"
            f"  Run /dev-test in a separate Claude Code session first: it writes\n"
            f"  the failing test matrix, commits it, and drops this marker with\n"
            f"  the test commit SHA. Method rule 4 requires the split."
        )
    commit_sha, _ = parse_marker(paths.test_done)
    if not commit_sha:
        return False, (
            f"/dev-impl refusing: marker {paths.test_done} is malformed\n"
            f"  (missing `test_commit:` line). Delete it and re-run /dev-test\n"
            f"  so the marker records a real commit SHA."
        )
    repo_root = repo_root_for(sprint_dir)
    if not (repo_root / ".git").exists():
        return False, (
            f"/dev-impl refusing: no git repo rooted at {repo_root}.\n"
            f"  The test commit recorded in the marker ({commit_sha}) cannot be\n"
            f"  verified. /dev-test must run in a real git repo so its commit\n"
            f"  is auditable."
        )
    if not commit_exists(commit_sha, repo_root):
        return False, (
            f"/dev-impl refusing: test commit {commit_sha} named in\n"
            f"  {paths.test_done} is not on disk in this repo.\n"
            f"  The marker is stale — re-run /dev-test to regenerate it against\n"
            f"  the current HEAD."
        )
    return True, f"/dev-impl ready for {task_id} — test commit {commit_sha} verified."


def mark_complete(sprint_dir: Path, task_id: str) -> Tuple[bool, str]:
    """Move T-NNN.test-session-done to T-NNN.complete. Idempotent."""
    paths = marker_paths(sprint_dir, task_id)
    if paths.complete.exists():
        return True, f"{task_id} already marked complete at {paths.complete}"
    if not paths.test_done.exists():
        return False, (
            f"mark-complete refusing: no test-done marker for {task_id}.\n"
            f"  Expected: {paths.test_done}"
        )
    paths.test_done.replace(paths.complete)
    return True, f"{task_id} marker moved to {paths.complete}"


def _cmd_test_done(args: argparse.Namespace) -> int:
    try:
        task_id = normalize_task_id(args.task_id)
    except ValueError as exc:
        print(f"dev_session: {exc}", file=sys.stderr)
        return 2
    paths = marker_paths(Path(args.sprint_dir), task_id)
    try:
        written = write_marker(paths, args.commit_sha)
    except ValueError as exc:
        print(f"dev_session: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {written}")
    return 0


def _cmd_check_impl_ready(args: argparse.Namespace) -> int:
    try:
        task_id = normalize_task_id(args.task_id)
    except ValueError as exc:
        print(f"dev_session: {exc}", file=sys.stderr)
        return 2
    ready, message = check_impl_ready(Path(args.sprint_dir), task_id)
    if ready:
        print(message)
        return 0
    print(message, file=sys.stderr)
    return 1


def _cmd_mark_complete(args: argparse.Namespace) -> int:
    try:
        task_id = normalize_task_id(args.task_id)
    except ValueError as exc:
        print(f"dev_session: {exc}", file=sys.stderr)
        return 2
    ok, message = mark_complete(Path(args.sprint_dir), task_id)
    if ok:
        print(message)
        return 0
    print(message, file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dev_session.py",
        description="Enforce the /dev-test → /dev-impl session split via marker files.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    td = sub.add_parser("test-done", help="Write the test-session-done marker.")
    td.add_argument("sprint_dir")
    td.add_argument("task_id")
    td.add_argument("--commit-sha", required=True)
    td.set_defaults(func=_cmd_test_done)

    ci = sub.add_parser(
        "check-impl-ready",
        help="Check whether /dev-impl may proceed for the task.",
    )
    ci.add_argument("sprint_dir")
    ci.add_argument("task_id")
    ci.set_defaults(func=_cmd_check_impl_ready)

    mc = sub.add_parser(
        "mark-complete",
        help="Move the test-done marker to .complete when the task is [x].",
    )
    mc.add_argument("sprint_dir")
    mc.add_argument("task_id")
    mc.set_defaults(func=_cmd_mark_complete)

    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
