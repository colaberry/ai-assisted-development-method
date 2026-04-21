#!/usr/bin/env python3
"""gap.py — initiative-boundary coverage analysis.

`reconcile.py` guarantees that every PRD requirement is claimed by a task.
It does not guarantee that every *initiative* requirement — the
`docs/<INITIATIVE>.md` stable IDs that the PRD is supposed to project —
ever makes it into a sprint PRD in the first place. A requirement can
be silently dropped across every sprint of an initiative and each sprint
still reconciles green. At client acceptance, the gap becomes visible.

`gap.py` closes that boundary. It diffs the requirement IDs in the
design document against the union of `Satisfies:` lines across every
sprint's `TASKS.md` (locked and active) and every `[DEFERRED]` entry,
then emits `docs/<INITIATIVE>_GAP_ANALYSIS.md` with four sections:

    Covered                 — requirement is Satisfies:-linked by an open
                              or completed task in some sprint.
    Deferred (with target)  — requirement has a [DEFERRED] entry naming a
                              future sprint and a reason.
    Orphaned                — requirement has no task and no deferral —
                              the silent-drop case. This is what makes
                              the check worth running.
    Conflicted              — more than one open task claims the same
                              requirement. Legitimate when tasks cover
                              different slices; a signal worth reviewing
                              otherwise.

Supersession (`SUPERSEDED-BY:` lines) is honored at a v1 level: a
requirement with a `SUPERSEDED-BY: §X, §Y` line is considered covered
when any of its successors is covered or deferred-with-target. Full
supersession-chain semantics (multi-hop, round-trip via reconcile) are
issue #29; gap.py v1 handles the single-hop case so a one-step
renegotiation doesn't spuriously show up as an orphan.

CLI:

    gap.py <initiative-md> <sprints-root> [--output PATH] [--ci]

Exit codes:
    0 — no orphans, no conflicts
    1 — conflicts only
    2 — orphans (with or without conflicts)

When `--ci` is not passed, gap.py always writes the analysis file and
exits 0 on success, non-zero only on argument errors, to keep
interactive runs from bleeding exit codes into shell chains.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple


# Mirror reconcile.py's stable-ID grammar so we share one notion of what
# counts as a requirement ID.
_REQ_ID_RE = re.compile(r"(?:SOW-)?(?:§\d+(?:\.\d+)*[a-z]?|[DQ]\d+)")

_INITIATIVE_REQ_LINE_RE = re.compile(
    r"(?:^\s*[-*]\s*\[?|^\s*#{1,6}\s*|^\s*\*\*)(" + _REQ_ID_RE.pattern + r")\]?"
)

_TASK_HEADER_RE = re.compile(
    r"^\s*[-*]\s*\[(?P<status>x|\s|DEFERRED)\]\s*(?P<id>T\d+):\s*(?P<title>.+?)\s*$",
    re.IGNORECASE,
)

_SATISFIES_RE = re.compile(
    r"^\s+(?:[-*]\s+)?Satisfies:\s*(?P<ids>.+?)\s*$", re.IGNORECASE
)

_TARGET_RE = re.compile(
    r"^\s+(?:[-*]\s+)?Target:\s*(?P<target>v\d+\S*)\s*$", re.IGNORECASE
)

_SUPERSEDED_BY_RE = re.compile(
    r"SUPERSEDED-BY:\s*(?P<ids>[^\n]+)", re.IGNORECASE
)

_SPRINT_DIR_RE = re.compile(r"^v(\d+)$")


@dataclass
class TaskRef:
    """A Satisfies: citation from some sprint's TASKS.md."""
    sprint: str            # "v2"
    task_id: str           # "T001"
    status: str            # "open" | "complete" | "deferred"
    target: Optional[str]  # for deferred tasks — the target sprint


@dataclass
class GapReport:
    initiative_path: Path
    initiative_ids: List[str]
    covered: Dict[str, List[TaskRef]] = field(default_factory=dict)
    deferred: Dict[str, List[TaskRef]] = field(default_factory=dict)
    orphaned: List[str] = field(default_factory=list)
    conflicted: Dict[str, List[TaskRef]] = field(default_factory=dict)
    supersedes: Dict[str, List[str]] = field(default_factory=dict)

    def has_orphans(self) -> bool:
        return bool(self.orphaned)

    def has_conflicts(self) -> bool:
        return bool(self.conflicted)


def _split_ids(raw: str) -> List[str]:
    ids: List[str] = []
    for token in re.split(r"[,\s]+", raw):
        token = token.strip().rstrip(".,;")
        if _REQ_ID_RE.fullmatch(token):
            ids.append(token)
    return ids


def parse_initiative(initiative_path: Path) -> Tuple[List[str], Dict[str, List[str]]]:
    """Return (ordered unique requirement IDs, supersession map).

    The supersession map is `{requirement_id: [successor_ids...]}` for
    any requirement carrying a `SUPERSEDED-BY:` line. Only single-hop
    pairs are extracted; multi-hop chains are issue #29.
    """
    text = initiative_path.read_text(encoding="utf-8")
    ids: List[str] = []
    seen: Set[str] = set()
    current_req: Optional[str] = None
    supersedes: Dict[str, List[str]] = {}

    for raw_line in text.splitlines():
        line = raw_line
        match = _INITIATIVE_REQ_LINE_RE.search(line)
        if match:
            req_id = match.group(1)
            if req_id not in seen:
                seen.add(req_id)
                ids.append(req_id)
            current_req = req_id

        sup_match = _SUPERSEDED_BY_RE.search(line)
        if sup_match and current_req is not None:
            successors = _split_ids(sup_match.group("ids"))
            if successors:
                supersedes.setdefault(current_req, []).extend(successors)

    return ids, supersedes


def collect_satisfies(sprints_root: Path) -> Tuple[
    Dict[str, List[TaskRef]], Dict[str, List[TaskRef]]
]:
    """Walk sprints/v*/TASKS.md and return (active, deferred) citations.

    - active[req_id] = TaskRefs whose status is "open" or "complete"
    - deferred[req_id] = TaskRefs whose status is "deferred" and which
      carry a `Target:` line (bare [DEFERRED] without a target isn't a
      legitimate defer; it'll surface as orphaned-equivalent).
    """
    active: Dict[str, List[TaskRef]] = {}
    deferred: Dict[str, List[TaskRef]] = {}
    if not sprints_root.is_dir():
        return active, deferred

    for entry in sorted(sprints_root.iterdir()):
        if not entry.is_dir():
            continue
        match = _SPRINT_DIR_RE.match(entry.name)
        if not match:
            continue
        tasks_md = entry / "TASKS.md"
        if not tasks_md.is_file():
            continue
        _collect_from_tasks(entry.name, tasks_md, active, deferred)

    return active, deferred


def _collect_from_tasks(
    sprint_name: str,
    tasks_md: Path,
    active: Dict[str, List[TaskRef]],
    deferred: Dict[str, List[TaskRef]],
) -> None:
    current: Optional[Tuple[str, str]] = None  # (task_id, status)
    pending_target: Optional[str] = None
    # Each task's Satisfies: ids are collected; after we see the task's
    # sublines we assign them.
    task_satisfies: Dict[Tuple[str, str], List[str]] = {}
    task_targets: Dict[Tuple[str, str], Optional[str]] = {}

    for line in tasks_md.read_text(encoding="utf-8").splitlines():
        header = _TASK_HEADER_RE.match(line)
        if header:
            status_char = header.group("status")
            if status_char.lower() == "deferred":
                status = "deferred"
            elif status_char.lower() == "x":
                status = "complete"
            else:
                status = "open"
            current = (header.group("id"), status)
            task_satisfies.setdefault(current, [])
            task_targets.setdefault(current, None)
            continue
        if current is None:
            continue
        sat = _SATISFIES_RE.match(line)
        if sat:
            for req_id in _split_ids(sat.group("ids")):
                task_satisfies[current].append(req_id)
            continue
        tgt = _TARGET_RE.match(line)
        if tgt:
            task_targets[current] = tgt.group("target")

    for (task_id, status), req_ids in task_satisfies.items():
        target = task_targets.get((task_id, status))
        for req_id in req_ids:
            ref = TaskRef(
                sprint=sprint_name,
                task_id=task_id,
                status=status,
                target=target,
            )
            if status == "deferred":
                if target:
                    deferred.setdefault(req_id, []).append(ref)
                # else: deferred without a target — falls through to
                # orphaned because nothing records it as covered.
            else:
                active.setdefault(req_id, []).append(ref)


def analyze(
    initiative_path: Path,
    sprints_root: Path,
) -> GapReport:
    ids, supersedes = parse_initiative(initiative_path)
    active, deferred = collect_satisfies(sprints_root)

    report = GapReport(
        initiative_path=initiative_path,
        initiative_ids=ids,
        supersedes=supersedes,
    )

    def is_claimed(req_id: str, seen: Optional[Set[str]] = None) -> Tuple[bool, str]:
        """Return (claimed, kind) where kind is 'active' | 'deferred' | ''."""
        seen = seen or set()
        if req_id in seen:
            return False, ""
        seen.add(req_id)
        if req_id in active:
            return True, "active"
        if req_id in deferred:
            return True, "deferred"
        for successor in supersedes.get(req_id, []):
            claimed, kind = is_claimed(successor, seen)
            if claimed:
                return True, kind
        return False, ""

    for req_id in ids:
        if req_id in active:
            refs = active[req_id]
            open_claims = [r for r in refs if r.status == "open"]
            if len(open_claims) > 1:
                report.conflicted[req_id] = open_claims
            report.covered[req_id] = refs
            continue
        if req_id in deferred:
            report.deferred[req_id] = deferred[req_id]
            continue
        # Fall through to supersession: if a successor is covered/deferred,
        # treat this requirement as covered via supersession.
        if req_id in supersedes:
            claimed, kind = is_claimed(req_id)
            if claimed:
                if kind == "deferred":
                    # borrow successor's deferred refs
                    for succ in supersedes[req_id]:
                        if succ in deferred:
                            report.deferred.setdefault(req_id, []).extend(deferred[succ])
                else:
                    for succ in supersedes[req_id]:
                        if succ in active:
                            report.covered.setdefault(req_id, []).extend(active[succ])
                continue
        report.orphaned.append(req_id)

    return report


def render_markdown(report: GapReport) -> str:
    lines: List[str] = []
    initiative_name = report.initiative_path.stem
    lines.append(f"# Gap analysis — {initiative_name}")
    lines.append("")
    lines.append(
        f"> Generated by `tooling/scripts/gap.py`. Diffs the requirement "
        f"IDs in `{report.initiative_path}` against the union of "
        f"`Satisfies:` citations in every sprint's TASKS.md."
    )
    lines.append("")
    lines.append(
        f"**Initiative requirements:** {len(report.initiative_ids)}  "
        f"| covered: {len(report.covered)}  "
        f"| deferred: {len(report.deferred)}  "
        f"| orphaned: {len(report.orphaned)}  "
        f"| conflicted: {len(report.conflicted)}"
    )
    lines.append("")

    lines.append("## Covered")
    lines.append("")
    if not report.covered:
        lines.append("- None.")
    else:
        for req_id, refs in sorted(report.covered.items()):
            cite = ", ".join(
                f"{r.sprint}/{r.task_id} ({r.status})" for r in refs
            )
            lines.append(f"- **{req_id}** — {cite}")
    lines.append("")

    lines.append("## Deferred (with target)")
    lines.append("")
    if not report.deferred:
        lines.append("- None.")
    else:
        for req_id, refs in sorted(report.deferred.items()):
            cite = ", ".join(
                f"{r.sprint}/{r.task_id} → {r.target}" for r in refs
            )
            lines.append(f"- **{req_id}** — deferred to {cite}")
    lines.append("")

    lines.append("## Orphaned")
    lines.append("")
    if not report.orphaned:
        lines.append(
            "- None identified. Every initiative requirement has either "
            "an active task or a `[DEFERRED]` entry with a target."
        )
    else:
        lines.append(
            "> Each entry below is a requirement in the design document "
            "that no sprint has picked up and no task has formally "
            "deferred. This is the silent-drop case. Either add a task "
            "via `/prd`, or add a `[DEFERRED]` entry with `Target:` and "
            "`Reason:` in an active sprint's TASKS.md before `/sprint-close`."
        )
        lines.append("")
        for req_id in report.orphaned:
            lines.append(f"- **{req_id}**")
    lines.append("")

    lines.append("## Conflicted")
    lines.append("")
    if not report.conflicted:
        lines.append("- None.")
    else:
        lines.append(
            "> More than one open task claims the same requirement. "
            "Legitimate when the tasks cover different slices of the "
            "same ID; worth reviewing otherwise."
        )
        lines.append("")
        for req_id, refs in sorted(report.conflicted.items()):
            cite = ", ".join(f"{r.sprint}/{r.task_id}" for r in refs)
            lines.append(f"- **{req_id}** — {cite}")
    lines.append("")

    if report.supersedes:
        lines.append("## Supersession map (v1, single-hop)")
        lines.append("")
        for req_id, successors in sorted(report.supersedes.items()):
            lines.append(f"- **{req_id}** SUPERSEDED-BY: {', '.join(successors)}")
        lines.append("")

    return "\n".join(lines) + "\n"


def default_output_path(initiative_path: Path) -> Path:
    return initiative_path.with_name(f"{initiative_path.stem}_GAP_ANALYSIS.md")


def _run_cli(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gap.py",
        description=(
            "Initiative-boundary coverage analysis: diffs design-doc "
            "requirement IDs against Satisfies: citations across all sprints."
        ),
    )
    parser.add_argument("initiative", help="Path to docs/<INITIATIVE>.md")
    parser.add_argument(
        "sprints_root",
        nargs="?",
        default="sprints",
        help="Directory containing sprints/v*/ (default: ./sprints)",
    )
    parser.add_argument(
        "--output",
        help="Output path for the analysis (default: docs/<INITIATIVE>_GAP_ANALYSIS.md)",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help=(
            "Exit non-zero on orphans (2) or conflicts (1); without --ci "
            "the command always exits 0 on success and writes the file."
        ),
    )
    args = parser.parse_args(argv)

    initiative_path = Path(args.initiative)
    if not initiative_path.is_file():
        print(f"gap.py: initiative file not found: {initiative_path}", file=sys.stderr)
        return 2

    sprints_root = Path(args.sprints_root)
    report = analyze(initiative_path, sprints_root)

    output_path = Path(args.output) if args.output else default_output_path(initiative_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown(report), encoding="utf-8")
    print(f"wrote {output_path}")

    if args.ci:
        if report.has_orphans():
            print(
                "gap.py: ORPHANED requirements detected: "
                + ", ".join(report.orphaned),
                file=sys.stderr,
            )
            return 2
        if report.has_conflicts():
            print(
                "gap.py: CONFLICTED requirements detected: "
                + ", ".join(sorted(report.conflicted)),
                file=sys.stderr,
            )
            return 1
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    return _run_cli(argv)


if __name__ == "__main__":
    sys.exit(main())
