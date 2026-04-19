#!/usr/bin/env python3
"""metrics.py — Development metrics logger for AADM.

Two event types land in `docs/metrics/events.jsonl`:

  - `gate` (Phase 1): whenever a structural gate runs (reconcile, security,
    gap, ui_qa, sprint_close), `log-gate` records pass/fail plus optional
    findings count. Called from CI on every gate run, so no engineer
    discipline is required.

  - `session` (Phase 2 partial — #13): whenever a work session wraps up,
    `log-session` records a sprint-tagged session with no per-engineer
    attribution. `sprint_close.py` structurally requires at least one logged
    session before it will write `.lock`, which makes session logging a hard
    discipline rather than a cultural one.

Threshold ranges (sessions/sprint, rework rate, tokens/session) that would
*interpret* session data are intentionally NOT shipped here — calibration
against real engagement data comes in a follow-up (see #13). Shipping ranges
against simulated numbers is how metrics systems become noise machines.

Commands:
    metrics.py log-gate        Log a gate event (pass/fail) — typically from CI
    metrics.py log-session     Log a work-session event — typically at session end
    metrics.py count-sessions  Count session events (optionally filtered by sprint)
    metrics.py list-events     Print the raw event log (or a filtered slice)

See metrics/docs/METRICS.md for the schema and interpretation guide.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

GATE_CHOICES = ("reconcile", "security", "gap", "ui_qa", "sprint_close")
RESULT_CHOICES = ("pass", "fail")

# Session categories are deliberately coarse. Finer-grained categories
# (e.g. "refactor", "investigate", "test-author") can be added when there
# is real data showing the distinction earns the extra field.
SESSION_KIND_CHOICES = ("dev", "tests", "review", "other")


def metrics_dir(repo: Path) -> Path:
    return repo / "docs" / "metrics"


def events_file(repo: Path) -> Path:
    return metrics_dir(repo) / "events.jsonl"


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def detect_active_sprint(repo: Path) -> Optional[str]:
    """Highest-numbered sprints/vN/ without a .lock file. None if no match."""
    sprints = repo / "sprints"
    if not sprints.is_dir():
        return None
    sprint_dirs = [
        p for p in sprints.iterdir()
        if p.is_dir() and re.match(r"v\d+$", p.name)
    ]
    sprint_dirs.sort(key=lambda p: int(p.name[1:]))
    for d in reversed(sprint_dirs):
        if not (d / ".lock").exists():
            return d.name
    # All locked — return the most recent so events still get attributed.
    return sprint_dirs[-1].name if sprint_dirs else None


def append_event(repo: Path, event: dict) -> None:
    f = events_file(repo)
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(event, separators=(",", ":")) + "\n")


def load_events(repo: Path) -> list[dict]:
    f = events_file(repo)
    if not f.is_file():
        return []
    events: list[dict] = []
    with f.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as e:
                sys.stderr.write(
                    f"WARNING: malformed event line skipped: {line[:80]}... ({e})\n"
                )
    return events


def cmd_log_gate(args: argparse.Namespace, repo: Path) -> int:
    event = {
        "ts": iso_now(),
        "event_type": "gate",
        "sprint": args.sprint or detect_active_sprint(repo),
        "gate": args.gate,
        "result": args.result,
    }
    if args.findings is not None:
        event["findings_count"] = args.findings
    append_event(repo, event)
    suffix = f" ({args.findings} findings)" if args.findings is not None else ""
    print(f"Logged gate {args.gate}: {args.result}{suffix}")
    return 0


def cmd_log_session(args: argparse.Namespace, repo: Path) -> int:
    event = {
        "ts": iso_now(),
        "event_type": "session",
        "sprint": args.sprint or detect_active_sprint(repo),
        "kind": args.kind,
    }
    if args.task:
        event["task"] = args.task
    if args.rework:
        event["rework"] = True
    append_event(repo, event)
    task_suffix = f" task={args.task}" if args.task else ""
    rework_suffix = " [rework]" if args.rework else ""
    print(f"Logged session kind={args.kind}{task_suffix}{rework_suffix}")
    return 0


def count_sessions(repo: Path, sprint: Optional[str]) -> int:
    events = load_events(repo)
    if sprint:
        events = [e for e in events if e.get("sprint") == sprint]
    return sum(1 for e in events if e.get("event_type") == "session")


def cmd_count_sessions(args: argparse.Namespace, repo: Path) -> int:
    sprint = args.sprint or detect_active_sprint(repo)
    n = count_sessions(repo, sprint)
    if args.json:
        print(json.dumps({"sprint": sprint, "session_count": n}))
    else:
        scope = f"sprint={sprint}" if sprint else "all sprints"
        print(f"{n} session event(s) for {scope}")
    return 0


def cmd_list_events(args: argparse.Namespace, repo: Path) -> int:
    events = load_events(repo)
    if args.sprint:
        events = [e for e in events if e.get("sprint") == args.sprint]
    if args.gate:
        events = [e for e in events if e.get("gate") == args.gate]
    if getattr(args, "event_type", None):
        events = [e for e in events if e.get("event_type") == args.event_type]
    if args.json:
        print(json.dumps(events, indent=2))
    else:
        for e in events:
            print(json.dumps(e, separators=(",", ":")))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Log and query AADM gate metrics (Phase 1: gate events only).",
    )
    parser.add_argument("--repo-root", default=".", help="Repo root (default: cwd)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    pg = subparsers.add_parser("log-gate", help="Log a gate event (typically called from CI)")
    pg.add_argument("--gate", required=True, choices=GATE_CHOICES,
                    help="Which structural gate fired")
    pg.add_argument("--result", required=True, choices=RESULT_CHOICES,
                    help="Gate result")
    pg.add_argument("--sprint", help="Sprint name (e.g. v3); defaults to detected active sprint")
    pg.add_argument("--findings", type=int,
                    help="Number of findings (relevant for gap, security with non-zero counts)")

    ps = subparsers.add_parser("log-session", help="Log a work-session event")
    ps.add_argument("--kind", required=True, choices=SESSION_KIND_CHOICES,
                    help="Session category (dev, tests, review, other)")
    ps.add_argument("--sprint", help="Sprint name (default: detected active sprint)")
    ps.add_argument("--task", help="Optional task ID (e.g., T007) the session worked on")
    ps.add_argument("--rework", action="store_true",
                    help="Mark this session as rework on already-closed work")

    pcs = subparsers.add_parser("count-sessions", help="Count logged session events")
    pcs.add_argument("--sprint", help="Sprint name (default: detected active sprint)")
    pcs.add_argument("--json", action="store_true", help="Emit as JSON")

    ple = subparsers.add_parser("list-events", help="Print events (optionally filtered)")
    ple.add_argument("--sprint", help="Filter by sprint")
    ple.add_argument("--gate", help="Filter by gate name")
    ple.add_argument("--event-type", dest="event_type", choices=("gate", "session"),
                    help="Filter by event type")
    ple.add_argument("--json", action="store_true", help="Emit as a JSON array")

    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()

    handlers = {
        "log-gate": cmd_log_gate,
        "log-session": cmd_log_session,
        "count-sessions": cmd_count_sessions,
        "list-events": cmd_list_events,
    }
    return handlers[args.command](args, repo)


if __name__ == "__main__":
    sys.exit(main())
