#!/usr/bin/env python3
"""sprint_gate.py — Claude Code PreToolUse hook for the AI-Assisted Development Method.

Blocks `Write`, `Edit`, `MultiEdit`, and `NotebookEdit` operations under
`sprints/vK/` when any earlier sprint `sprints/vJ/` (J < K) is missing a
`.lock` file. This makes the anti-skip discipline structural: you cannot
start writing into v2 while v1 is still open, no matter how confident you
are that "v1 is basically done."

The complementary check — sprint_close.py refusing to write `.lock` when
gates fail — is what makes the .lock signal trustworthy. Together they
close the loop.

How to install in a client repo:

  1. Copy this file to <repo>/.claude/hooks/sprint_gate.py
  2. chmod +x <repo>/.claude/hooks/sprint_gate.py
  3. Add to <repo>/.claude/settings.json (or merge with existing):
     {
       "hooks": {
         "PreToolUse": [
           {
             "matcher": "Write|Edit|MultiEdit|NotebookEdit",
             "hooks": [
               {"type": "command", "command": ".claude/hooks/sprint_gate.py"}
             ]
           }
         ]
       }
     }

Behavior:

  - If the tool's target file is not under sprints/vN/, allow.
  - If the target is sprints/vN/ but no earlier sprints exist, allow.
  - If the target is sprints/vK/ and every sprints/vJ/ (J < K) has .lock,
    allow.
  - Otherwise: block with a message naming the missing .lock files.

Defensive defaults: any parse error or unexpected condition allows the
operation (and logs to stderr). The hook is a structural reminder, not
a security boundary — if it can't tell what's going on, it gets out of
the way rather than blocking real work.

Exit codes (per Claude Code hook protocol):
    0  allow
    2  block — Claude Code will surface the stderr message to the agent
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple


SPRINT_DIR_RE = re.compile(r"^v(\d+)$")
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}


def find_repo_root(start: Path) -> Path:
    """Walk up from `start` looking for a .git or sprints/ marker."""
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / "sprints").is_dir():
            return candidate
    return current


def extract_target_path(tool_name: str, tool_input: dict) -> Optional[str]:
    """Pull the file_path argument out of the tool input. Tools that don't
    write to a single file return None and the hook allows them."""
    if tool_name not in WRITE_TOOLS:
        return None
    path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not isinstance(path, str) or not path:
        return None
    return path


def sprint_index_for(target: Path, repo_root: Path) -> Optional[int]:
    """If `target` lives under <repo_root>/sprints/vK/..., return K. Else None."""
    try:
        rel = target.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) < 2 or parts[0] != "sprints":
        return None
    match = SPRINT_DIR_RE.match(parts[1])
    if not match:
        return None
    return int(match.group(1))


def list_sprint_dirs(repo_root: Path) -> List[Tuple[int, Path]]:
    """Return [(N, path), ...] sorted by N for every sprints/vN/ dir present."""
    sprints_dir = repo_root / "sprints"
    if not sprints_dir.is_dir():
        return []
    found: List[Tuple[int, Path]] = []
    for entry in sprints_dir.iterdir():
        if not entry.is_dir():
            continue
        match = SPRINT_DIR_RE.match(entry.name)
        if not match:
            continue
        found.append((int(match.group(1)), entry))
    found.sort(key=lambda pair: pair[0])
    return found


def unlocked_predecessors(target_n: int, sprints: List[Tuple[int, Path]]) -> List[int]:
    """Return sorted list of sprint numbers earlier than target_n that lack .lock."""
    return sorted(
        n for n, path in sprints if n < target_n and not (path / ".lock").exists()
    )


def evaluate(tool_name: str, tool_input: dict, cwd: Path) -> Tuple[bool, Optional[str]]:
    """Decide whether to block. Returns (allow, message)."""
    raw_path = extract_target_path(tool_name, tool_input)
    if raw_path is None:
        return True, None

    target = Path(raw_path)
    if not target.is_absolute():
        target = (cwd / target).resolve()

    repo_root = find_repo_root(cwd)
    sprint_n = sprint_index_for(target, repo_root)
    if sprint_n is None:
        return True, None

    sprints = list_sprint_dirs(repo_root)
    missing = unlocked_predecessors(sprint_n, sprints)
    if not missing:
        return True, None

    pretty_missing = ", ".join(f"sprints/v{n}/.lock" for n in missing)
    message = (
        f"Sprint-gate: refusing {tool_name} on {raw_path}.\n"
        f"  Target sprint: v{sprint_n}\n"
        f"  Missing .lock for prior sprint(s): {pretty_missing}\n"
        f"  Run sprint_close.py on the unlocked sprint(s) before writing into v{sprint_n}."
    )
    return False, message


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"sprint_gate: could not parse hook input ({exc}); allowing", file=sys.stderr)
        return 0

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}
    if not isinstance(tool_input, dict):
        return 0

    cwd_value = payload.get("cwd") or os.getcwd()
    try:
        cwd = Path(cwd_value)
    except TypeError:
        cwd = Path.cwd()

    try:
        allow, message = evaluate(tool_name, tool_input, cwd)
    except Exception as exc:  # defensive: never block on unexpected errors
        print(f"sprint_gate: unexpected error ({exc}); allowing", file=sys.stderr)
        return 0

    if allow:
        return 0

    print(message, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
