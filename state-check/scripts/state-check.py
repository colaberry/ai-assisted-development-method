#!/usr/bin/env python3
"""
state-check.py — Repo state detector for the AI-Assisted Development Method.

Detects which mode the repo is in (client delivery v3.2.1 or Internal Product
Mode), which stage/phase is active, and flags anything that requires attention.
This is a heads-up display, not an autopilot: judgment calls are surfaced for
humans, never decided by the tool.

Usage:
    python state-check.py                     # human-readable report
    python state-check.py --json              # machine-readable JSON
    python state-check.py --repo-root /path   # inspect different repo

Exit codes:
    0   — state detected successfully, no P0 flags
    1   — P0 flags present (blocking issue)
    2   — usage error or repo is not set up for the method
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


# =====================================================================
# Data classes
# =====================================================================

@dataclass
class Flag:
    """An item that requires attention. Severity drives exit code and presentation."""
    severity: str  # "P0" | "P1" | "P2"
    category: str  # short category tag, e.g. "coverage", "memory", "sprint"
    message: str
    suggested_action: str = ""


@dataclass
class ModeState:
    """Overall detected state of the repo."""
    mode: str  # "client-delivery" | "internal-product" | "unknown"
    stage: Optional[str] = None  # For internal: "exploration" | "validation" | "commercialization"
    phase: Optional[str] = None  # For client: "intake" | "design" | "sprint" | "between-sprints"
    active_initiative: Optional[str] = None
    active_sprint: Optional[str] = None
    active_sprint_locked: bool = False
    open_tasks: int = 0
    completed_tasks: int = 0
    deferred_tasks: int = 0
    flags: list[Flag] = field(default_factory=list)
    recommended_next: Optional[str] = None
    judgment_calls: list[str] = field(default_factory=list)


# =====================================================================
# Mode detection
# =====================================================================

def detect_mode(repo: Path) -> tuple[str, Optional[str]]:
    """
    Detect which mode the repo is in and, for internal mode, which stage.
    Returns (mode, stage).
    """
    intake_dir = repo / "docs" / "intake"
    contract_sow = repo / "docs" / "contract" / "SOW.md"
    hypothesis = repo / "docs" / "hypothesis.md"
    gate_1_2 = repo / "docs" / "gate-1-to-2-decision.md"
    gate_2_3 = repo / "docs" / "gate-2-to-3-decision.md"

    # Internal Product Mode indicators (check first — if hypothesis.md exists,
    # that's a stronger signal than SOW, which could be leftover scaffolding).
    if hypothesis.exists():
        if gate_2_3.exists():
            return ("internal-product", "commercialization")
        if gate_1_2.exists():
            return ("internal-product", "validation")
        return ("internal-product", "exploration")

    # Client delivery indicators.
    if contract_sow.exists() or (intake_dir.exists() and any(intake_dir.iterdir())):
        return ("client-delivery", None)

    return ("unknown", None)


# =====================================================================
# Sprint detection
# =====================================================================

def find_sprint_dirs(repo: Path) -> list[Path]:
    """Return sorted list of sprint directories (sprints/v1/, sprints/v2/, ...)."""
    sprints_dir = repo / "sprints"
    if not sprints_dir.is_dir():
        return []
    sprint_dirs = [p for p in sprints_dir.iterdir() if p.is_dir() and re.match(r"v\d+", p.name)]
    # Sort by the integer in the name
    sprint_dirs.sort(key=lambda p: int(re.match(r"v(\d+)", p.name).group(1)))
    return sprint_dirs


def find_active_sprint(sprint_dirs: list[Path]) -> Optional[Path]:
    """
    Active sprint = highest-numbered sprint without a .lock file.
    If all sprints are locked, no sprint is active (between-sprints state).
    """
    for sprint in reversed(sprint_dirs):
        if not (sprint / ".lock").exists():
            return sprint
    return None


def count_tasks(tasks_file: Path) -> tuple[int, int, int]:
    """Count open, completed, and deferred tasks in a TASKS.md file."""
    if not tasks_file.is_file():
        return (0, 0, 0)
    open_count = 0
    complete_count = 0
    deferred_count = 0
    task_pattern = re.compile(
        r"^\s*[-*]\s*\[(?P<status>x|\s|DEFERRED)\]\s*T\d+:",
        re.IGNORECASE,
    )
    with tasks_file.open("r", encoding="utf-8") as f:
        for line in f:
            m = task_pattern.match(line)
            if m:
                s = m.group("status").lower()
                if s == "x":
                    complete_count += 1
                elif s == "deferred":
                    deferred_count += 1
                else:
                    open_count += 1
    return (open_count, complete_count, deferred_count)


def find_active_initiative(repo: Path) -> Optional[str]:
    """Find the most recently modified design doc under docs/, excluding known subfolders."""
    docs_dir = repo / "docs"
    if not docs_dir.is_dir():
        return None
    excluded_dirs = {"intake", "contract", "decisions", "failures", "client-facing"}
    candidates = [
        p for p in docs_dir.iterdir()
        if p.is_file() and p.suffix == ".md" and p.stem != "hypothesis"
    ]
    if not candidates:
        return None
    # Use most recently modified as a heuristic for "active"
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return latest.stem


# =====================================================================
# Git inspection (optional — works if repo is a git repo, silent if not)
# =====================================================================

def git_file_exists_in_history(repo: Path, path: str) -> bool:
    """True if the file is tracked by git. False on error."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "--error-unmatch", path],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def git_recent_test_modifications(repo: Path, since: str = "2.days") -> list[str]:
    """
    Return list of test files modified in recent commits. A heuristic for the
    "tests modified to match code" anti-pattern. Empty list on error.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "log", f"--since={since}", "--name-only", "--pretty=format:"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return []
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        # Heuristic: any file with "test" in the path
        return sorted(set(l for l in lines if "test" in l.lower()))
    except (subprocess.SubprocessError, FileNotFoundError):
        return []


# =====================================================================
# Flag checks
# =====================================================================

def check_claude_md_size(repo: Path) -> Optional[Flag]:
    claude_md = repo / "CLAUDE.md"
    if not claude_md.is_file():
        return Flag(
            severity="P0",
            category="setup",
            message="CLAUDE.md is missing at repo root.",
            suggested_action="Copy from tooling/templates/CLAUDE.md and fill in the bracketed placeholders.",
        )
    try:
        line_count = sum(1 for _ in claude_md.open("r", encoding="utf-8"))
    except Exception:
        return None
    if line_count > 500:
        return Flag(
            severity="P1",
            category="memory",
            message=f"CLAUDE.md is {line_count} lines (threshold: 500). LLMs skip content in longer files.",
            suggested_action="Push detail into linked docs; keep CLAUDE.md as the index.",
        )
    return None


def check_failures_log_size(repo: Path) -> Optional[Flag]:
    failures_dir = repo / "docs" / "failures"
    if not failures_dir.is_dir():
        return None
    entries = [p for p in failures_dir.iterdir() if p.is_file() and p.suffix == ".md" and p.stem not in ("README", "TEMPLATE")]
    count = len(entries)
    if count > 100:
        return Flag(
            severity="P2",
            category="memory",
            message=f"Failures log has {count} entries (guideline: prune beyond 20–50 active rules).",
            suggested_action="Run a consolidation pass: merge entries producing the same prevention rule; retire rules unused in 12 months.",
        )
    return None


def check_sprint_state(sprint: Path, mode: str) -> list[Flag]:
    """Check the active sprint for common issues."""
    flags: list[Flag] = []
    prd = sprint / "PRD.md"
    tasks = sprint / "TASKS.md"
    retro = sprint / "RETRO.md"

    if not prd.is_file():
        flags.append(Flag(
            severity="P0",
            category="sprint",
            message=f"Sprint {sprint.name} has no PRD.md.",
            suggested_action="Run /prd to produce a sprint PRD from the design doc.",
        ))
    if not tasks.is_file():
        flags.append(Flag(
            severity="P0",
            category="sprint",
            message=f"Sprint {sprint.name} has no TASKS.md.",
            suggested_action="Run /prd to produce a task breakdown with Satisfies: lines.",
        ))

    # Check for Satisfies: coverage if TASKS.md exists
    if tasks.is_file():
        has_tasks_without_satisfies = False
        with tasks.open("r", encoding="utf-8") as f:
            in_task = False
            task_had_satisfies = False
            current_task_id = None
            task_header_re = re.compile(r"^\s*[-*]\s*\[(?P<s>x|\s|DEFERRED)\]\s*(?P<id>T\d+):", re.IGNORECASE)
            satisfies_re = re.compile(r"^\s+(?:[-*]\s+)?Satisfies:", re.IGNORECASE)
            for line in f:
                m = task_header_re.match(line)
                if m:
                    # finalize previous task
                    if in_task and not task_had_satisfies:
                        has_tasks_without_satisfies = True
                    in_task = True
                    task_had_satisfies = False
                    current_task_id = m.group("id")
                    continue
                if in_task and satisfies_re.match(line):
                    task_had_satisfies = True
            # finalize last task
            if in_task and not task_had_satisfies:
                has_tasks_without_satisfies = True
        if has_tasks_without_satisfies:
            flags.append(Flag(
                severity="P0",
                category="traceability",
                message=f"Sprint {sprint.name} has one or more tasks without a Satisfies: line.",
                suggested_action="Add Satisfies: <IDs> to each task, or explicitly defer the task.",
            ))

    # Retro check for non-first sprints
    if not retro.is_file() and sprint.name != "v1":
        flags.append(Flag(
            severity="P2",
            category="retro",
            message=f"Sprint {sprint.name} has no RETRO.md yet.",
            suggested_action="Run /retro at end of sprint; feeds failures log from within-sprint experience.",
        ))

    return flags


def check_test_modifications(repo: Path) -> Optional[Flag]:
    modified = git_recent_test_modifications(repo)
    if modified:
        return Flag(
            severity="P1",
            category="anti-pattern",
            message=f"Test files modified in recent commits: {', '.join(modified[:3])}{' ...' if len(modified) > 3 else ''}",
            suggested_action="Verify tests weren't modified to match code. If a test was wrong, fix and note it; do not silently adjust to pass.",
        )
    return None


def check_mode_specific(mode: str, stage: Optional[str], repo: Path) -> list[Flag]:
    """Mode- and stage-specific checks."""
    flags: list[Flag] = []

    if mode == "client-delivery":
        # SOW presence
        sow = repo / "docs" / "contract" / "SOW.md"
        if not sow.is_file():
            flags.append(Flag(
                severity="P1",
                category="contract",
                message="No docs/contract/SOW.md found.",
                suggested_action="Place the client SOW at docs/contract/SOW.md and assign SOW-§X.Y IDs to each acceptance criterion.",
            ))

    if mode == "internal-product":
        hypothesis = repo / "docs" / "hypothesis.md"
        if stage == "exploration" and not hypothesis.is_file():
            flags.append(Flag(
                severity="P0",
                category="setup",
                message="Internal Product Mode Stage 1 requires docs/hypothesis.md.",
                suggested_action="Write the product hypothesis document with problem, hypothesis, test, kill signal, and timeline.",
            ))

    return flags


# =====================================================================
# Judgment-call questions (surfaced for humans, not answered by tool)
# =====================================================================

def compose_judgment_calls(mode: str, stage: Optional[str], state: ModeState) -> list[str]:
    calls: list[str] = []

    if mode == "internal-product":
        gate_1_2 = Path("docs") / "gate-1-to-2-decision.md"
        gate_2_3 = Path("docs") / "gate-2-to-3-decision.md"
        if stage == "exploration":
            calls.append(
                "Has the kill signal fired? If yes, the gate says: pivot or kill, not continue. "
                "Revisit the hypothesis doc."
            )
            calls.append(
                "Is there evidence of real user value from non-team users? "
                f"If yes, draft {gate_1_2} to graduate to Stage 2. "
                "If no, next sprint should test the next hypothesis, not add features."
            )
        if stage == "validation":
            calls.append(
                "Are behavior metrics moving in the right direction? "
                "If a recently shipped feature didn't move any metric, investigate before building on it."
            )
            calls.append(
                f"Is commercialization imminent? If yes, draft {gate_2_3} and budget hardening work."
            )

    if state.active_sprint_locked and state.phase == "between-sprints":
        calls.append(
            "Are you ready to start the next sprint? The last one is locked. "
            "If yes, run /prd for sprint vN+1. If no, that's fine — sprints are demand-driven."
        )

    return calls


# =====================================================================
# Recommendation
# =====================================================================

def compose_recommendation(mode: str, stage: Optional[str], state: ModeState, sprint_dirs: list[Path]) -> str:
    # P0 flags dominate
    p0 = [f for f in state.flags if f.severity == "P0"]
    if p0:
        return f"Resolve P0 flag first: {p0[0].message}"

    if mode == "unknown":
        return (
            "This repo is not set up for the method. If this is a client engagement, "
            "run Phase 0 (see docs/intake/TEMPLATE.md or the method document). "
            "If this is an internal product, write docs/hypothesis.md first."
        )

    if not sprint_dirs:
        if mode == "client-delivery":
            return (
                "No sprint directories yet. If Phase 0 is done (design doc + SOW mapping complete), "
                "create sprints/v1/ and run /prd."
            )
        else:
            return "No sprint directories yet. Create sprints/v1/ and run /prd against docs/hypothesis.md."

    if state.active_sprint_locked:
        return (
            "All sprints are locked (between-sprints state). "
            "Start sprint vN+1 by running /prd when ready."
        )

    if state.open_tasks > 0:
        return f"{state.open_tasks} open task(s) in {state.active_sprint}. Pick the next one and run /dev."
    if state.open_tasks == 0 and state.completed_tasks > 0:
        return f"{state.active_sprint} has no open tasks. If sprint is done, run /sprint-close."

    return "Sprint has no tasks defined. Run /prd to break the design doc into tasks."


# =====================================================================
# Main orchestration
# =====================================================================

def run_state_check(repo: Path) -> ModeState:
    state = ModeState(mode="unknown")

    mode, stage = detect_mode(repo)
    state.mode = mode
    state.stage = stage

    sprint_dirs = find_sprint_dirs(repo)
    active_sprint = find_active_sprint(sprint_dirs)

    if active_sprint is not None:
        state.active_sprint = str(active_sprint.relative_to(repo))
        state.active_sprint_locked = False
        open_c, complete_c, deferred_c = count_tasks(active_sprint / "TASKS.md")
        state.open_tasks = open_c
        state.completed_tasks = complete_c
        state.deferred_tasks = deferred_c
        state.phase = "sprint"
        state.flags.extend(check_sprint_state(active_sprint, mode))
    elif sprint_dirs:
        # All sprints locked
        state.active_sprint_locked = True
        state.phase = "between-sprints"
        state.active_sprint = str(sprint_dirs[-1].relative_to(repo)) + " (locked)"

    state.active_initiative = find_active_initiative(repo)

    # Repo-wide checks
    for check in (check_claude_md_size, check_failures_log_size, check_test_modifications):
        flag = check(repo)
        if flag:
            state.flags.append(flag)

    state.flags.extend(check_mode_specific(mode, stage, repo))

    state.recommended_next = compose_recommendation(mode, stage, state, sprint_dirs)
    state.judgment_calls = compose_judgment_calls(mode, stage, state)

    return state


# =====================================================================
# Presentation
# =====================================================================

def print_human_report(state: ModeState) -> None:
    print()
    print("=" * 72)
    print("Repository state check")
    print("=" * 72)
    print()

    mode_label = {
        "client-delivery": "Client delivery (v3.2.1)",
        "internal-product": f"Internal Product Mode — Stage: {state.stage}" if state.stage else "Internal Product Mode",
        "unknown": "Unknown (method not yet set up)",
    }.get(state.mode, state.mode)
    print(f"Mode:               {mode_label}")
    if state.active_initiative:
        print(f"Active initiative:  {state.active_initiative}")
    if state.active_sprint:
        print(f"Active sprint:      {state.active_sprint}")
    if state.phase:
        print(f"Phase:              {state.phase}")
    if state.active_sprint and not state.active_sprint_locked:
        print(f"Tasks:              {state.open_tasks} open, {state.completed_tasks} complete, {state.deferred_tasks} deferred")
    print()

    if state.flags:
        print("Flags (require attention):")
        for f in state.flags:
            marker = {"P0": "✗", "P1": "⚠", "P2": "·"}.get(f.severity, "-")
            print(f"  {marker} [{f.severity}] {f.message}")
            if f.suggested_action:
                print(f"     → {f.suggested_action}")
        print()
    else:
        print("Flags:              None")
        print()

    if state.recommended_next:
        print(f"Recommended next:   {state.recommended_next}")
        print()

    if state.judgment_calls:
        print("Judgment calls (for humans, not automated):")
        for i, call in enumerate(state.judgment_calls, 1):
            print(f"  {i}. {call}")
        print()

    print("=" * 72)
    print()


# =====================================================================
# CLI entry
# =====================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect current state of a repo using the AI-Assisted Development Method."
    )
    parser.add_argument("--repo-root", default=".", help="Repository root (default: cwd).")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve()
    if not repo.is_dir():
        sys.stderr.write(f"ERROR: repo root not found: {repo}\n")
        return 2

    state = run_state_check(repo)

    if args.json:
        print(json.dumps(asdict(state), indent=2))
    else:
        print_human_report(state)

    p0_count = sum(1 for f in state.flags if f.severity == "P0")
    return 1 if p0_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
