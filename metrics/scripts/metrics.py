#!/usr/bin/env python3
"""metrics.py — Development metrics logger for AADM (Phase 1: gate events only).

Phase 1 ships a single event type: `gate`. Whenever a structural gate runs
(reconcile, security, gap, ui_qa, sprint_close), `log-gate` records pass/fail
plus optional findings count to an append-only JSONL file at
docs/metrics/events.jsonl. Designed to be called from CI on every gate run, so
no engineer discipline is required.

Session and rework events (log-session, log-rework, retro rollups) are
deferred to Phase 2 — see issue #13. The schema is intentionally narrow until
real engagement data validates the threshold ranges.

Commands:
    metrics.py log-gate      Log a gate event (pass/fail) — typically from CI
    metrics.py list-events   Print the raw event log (or a filtered slice)

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


def metrics_dir(repo: Path) -> Path:
    d = repo / "docs" / "metrics"
    d.mkdir(parents=True, exist_ok=True)
    return d


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


def cmd_list_events(args: argparse.Namespace, repo: Path) -> int:
    events = load_events(repo)
    if args.sprint:
        events = [e for e in events if e.get("sprint") == args.sprint]
    if args.gate:
        events = [e for e in events if e.get("gate") == args.gate]
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

    ple = subparsers.add_parser("list-events", help="Print events (optionally filtered)")
    ple.add_argument("--sprint", help="Filter by sprint")
    ple.add_argument("--gate", help="Filter by gate name")
    ple.add_argument("--json", action="store_true", help="Emit as a JSON array")

    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()

    handlers = {
        "log-gate": cmd_log_gate,
        "list-events": cmd_list_events,
    }
    return handlers[args.command](args, repo)


if __name__ == "__main__":
    sys.exit(main())
