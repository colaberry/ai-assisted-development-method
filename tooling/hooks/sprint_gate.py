#!/usr/bin/env python3
"""sprint_gate.py — Claude Code PreToolUse hook for the AI-Assisted Development Method.

Blocks `Write`, `Edit`, `MultiEdit`, and `NotebookEdit` operations under
`sprints/vK/` when any earlier sprint `sprints/vJ/` (J < K) is missing a
`.lock` file. This makes the anti-skip discipline structural: you cannot
start writing into v2 while v1 is still open, no matter how confident you
are that "v1 is basically done."

It also enforces the active sprint's declared scope. When a prior sprint
lacks `.lock` (the skip condition), writes outside the active sprint's
TASKS.md `Files:` allowlist are blocked. Without this extension, a team
can ship an entire vN+1 feature by writing to `src/`, `tests/`, and
`migrations/` without ever touching `sprints/vN+1/` — and the hook would
fire zero times. Method rule 11 ("silent scope expansion is an anti-
pattern") becomes structural: add the file to TASKS.md `Files:` first,
or close the prior sprint, before writing it.

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

  Anti-skip (target under sprints/vK/):
  - If the target is sprints/vN/ but no earlier sprints exist, allow.
  - If the target is sprints/vK/ and every sprints/vJ/ (J < K) has .lock,
    allow.
  - Otherwise: block with a message naming the missing .lock files.

  Scope allowlist (target outside sprints/vN/):
  - If no active (unlocked) sprint exists, allow.
  - If no earlier sprint is unlocked (i.e., the skip condition is not in
    effect), allow. The allowlist is only enforced alongside an active
    anti-skip condition to keep v1 bootstrap and steady-state single-
    sprint work unblocked.
  - Otherwise, parse the active sprint's TASKS.md and build the union of
    `Files:` lines across open `[ ]` tasks. If the target is in that
    union, allow. If it isn't, block and append to
    `sprints/vN/.gate-blocks.log`.

Defensive defaults: any parse error or unexpected condition allows the
operation (and logs to stderr). The hook is a structural reminder, not
a security boundary — if it can't tell what's going on, it gets out of
the way rather than blocking real work. Missing or unparseable TASKS.md
therefore warns and allows.

Exit codes (per Claude Code hook protocol):
    0  allow
    2  block — Claude Code will surface the stderr message to the agent
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple


SPRINT_DIR_RE = re.compile(r"^v(\d+)$")
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}

# Matches a top-level task line in TASKS.md — open, completed, or a title case
# variant. DEFERRED tasks are intentionally excluded from the allowlist.
_TASK_LINE_RE = re.compile(r"^-\s*\[([ xX])\]\s+T\d+:")
_FILES_LINE_RE = re.compile(r"^\s+-\s+Files:\s*(.+)$")


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


def active_sprint(sprints: List[Tuple[int, Path]]) -> Optional[Tuple[int, Path]]:
    """Highest-numbered sprint missing .lock, or None if every sprint is locked."""
    for n, path in reversed(sprints):
        if not (path / ".lock").exists():
            return (n, path)
    return None


def parse_files_allowlist(tasks_md: Path) -> Optional[List[str]]:
    """Return the union of `Files:` entries across open `[ ]` tasks in TASKS.md.

    Returns `None` when TASKS.md cannot be read — the caller treats that as
    warn-only (defensive default). Completed `[x]` tasks and `[DEFERRED]`
    tasks do not contribute to the allowlist.
    """
    try:
        text = tasks_md.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    files: List[str] = []
    in_open_task = False
    for line in text.splitlines():
        task_match = _TASK_LINE_RE.match(line)
        if task_match:
            in_open_task = task_match.group(1) == " "
            continue
        if not in_open_task:
            continue
        files_match = _FILES_LINE_RE.match(line)
        if not files_match:
            continue
        for raw in files_match.group(1).split(","):
            candidate = raw.strip()
            if candidate:
                files.append(candidate)
    return files


def _normalize_allowlist(entries: Sequence[str]) -> List[str]:
    """Normalize separators and strip leading './' for comparison."""
    normalized: List[str] = []
    for entry in entries:
        cleaned = entry.replace("\\", "/").strip()
        if cleaned.startswith("./"):
            cleaned = cleaned[2:]
        if cleaned:
            normalized.append(cleaned)
    return normalized


def target_in_allowlist(rel_target: str, allowlist: Sequence[str]) -> bool:
    rel = rel_target.replace("\\", "/")
    for entry in _normalize_allowlist(allowlist):
        if rel == entry:
            return True
        # Directory entries ("src/auth/") match files beneath them.
        if entry.endswith("/") and rel.startswith(entry):
            return True
    return False


def append_gate_log(
    active_sprint_dir: Path,
    tool_name: str,
    rel_target: str,
    allowlist: Sequence[str],
) -> None:
    """Record the block so retros can review false positives."""
    try:
        log_path = active_sprint_dir / ".gate-blocks.log"
        timestamp = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        line = (
            f"{timestamp}\t{tool_name}\t{rel_target}\t"
            f"allowlist_size={len(allowlist)}\n"
        )
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(line)
    except OSError as exc:  # defensive: logging must never break the hook
        print(f"sprint_gate: could not append gate log ({exc})", file=sys.stderr)


def evaluate(tool_name: str, tool_input: dict, cwd: Path) -> Tuple[bool, Optional[str]]:
    """Decide whether to block. Returns (allow, message)."""
    raw_path = extract_target_path(tool_name, tool_input)
    if raw_path is None:
        return True, None

    target = Path(raw_path)
    if not target.is_absolute():
        target = (cwd / target).resolve()

    repo_root = find_repo_root(cwd)
    sprints = list_sprint_dirs(repo_root)

    sprint_n = sprint_index_for(target, repo_root)
    if sprint_n is not None:
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

    # Target is outside sprints/vN/. Enforce the active sprint's Files:
    # allowlist only when the anti-skip condition is already in effect —
    # i.e. some earlier sprint is unlocked. In steady-state single-sprint
    # work, the allowlist is not enforced (and v1 bootstrap is unaffected).
    active = active_sprint(sprints)
    if active is None:
        return True, None
    active_n, active_path = active
    if not unlocked_predecessors(active_n, sprints):
        return True, None

    tasks_md = active_path / "TASKS.md"
    allowlist = parse_files_allowlist(tasks_md)
    if allowlist is None:
        print(
            f"sprint_gate: could not read {tasks_md}; allowing (warn-only)",
            file=sys.stderr,
        )
        return True, None

    try:
        rel_target = target.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return True, None
    rel_str = str(rel_target).replace("\\", "/")

    if target_in_allowlist(rel_str, allowlist):
        return True, None

    append_gate_log(active_path, tool_name, rel_str, allowlist)
    pretty_missing = ", ".join(
        f"sprints/v{n}/.lock" for n in unlocked_predecessors(active_n, sprints)
    )
    message = (
        f"Sprint-gate: refusing {tool_name} on {rel_str}.\n"
        f"  Target is outside sprints/v{active_n}/TASKS.md Files: allowlist\n"
        f"  while prior sprint(s) remain unlocked: {pretty_missing}\n"
        f"  Either add this file to an open task's Files: line in\n"
        f"  sprints/v{active_n}/TASKS.md, or close the prior sprint(s) via\n"
        f"  sprint_close.py before expanding scope. Logged to\n"
        f"  sprints/v{active_n}/.gate-blocks.log."
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
