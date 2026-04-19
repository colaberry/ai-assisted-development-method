#!/usr/bin/env python3
"""
reconcile.py — Sprint coverage check for the AI-Assisted Development Method (AADM).

Parses sprints/vN/PRD.md for requirement IDs and sprints/vN/TASKS.md for
`Satisfies:` citations. For each requirement, verifies that either:

  1. A completed task satisfies it AND the code contains a matching symbol, or
  2. It has an explicit [DEFERRED] entry naming a target sprint.

Emits a human-readable coverage table and, with --json, machine-readable output.
Exit code 0 = all requirements covered; 1 = one or more gaps; 2 = usage error.

Designed to run in CI on every PR touching an active sprint directory.

Assumptions (tune for your team's conventions):

  - Requirement IDs match the pattern: §X.Y, §X.Y.Z, Dn, Qn, SOW-§X.Y.
  - PRD requirements are lines like "- [REQ-ID] description" or headers
    containing "REQ-ID:" — see parse_prd() for the patterns matched.
  - Tasks in TASKS.md use checkbox format:
        - [x] T001: title
          - Satisfies: D5, §7.3
          - Files: path/to/file.py
    Completed tasks have [x]; incomplete have [ ]; deferred tasks have
    [DEFERRED] as their status or a "Status: DEFERRED" subline with a
    "Target: vN" line.
  - The "Files:" subline lists comma-separated paths.
  - Symbol presence: candidate symbols are extracted from each task's title
    and Acceptance: line — backticked tokens like `_routes_differ` are the
    strongest signal; bare identifiers with underscores or inner casing
    (snake_case, camelCase, PascalCase, ALL_CAPS) are also picked up. The
    script then greps the task's listed files for those symbols. A "covered"
    task whose listed files exist but contain no extracted symbol is the
    "empty stub" pattern and is flagged in confidence + notes. With
    --strict-symbols, that pattern is downgraded to a missing requirement.

Usage:
    python reconcile.py sprints/v1
    python reconcile.py sprints/v1 --json
    python reconcile.py sprints/v1 --ci   (non-zero exit on failure, terse output)
    python reconcile.py sprints/v1 --ci --strict-symbols  (also fail on stubs)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


# Regex patterns. Intentionally liberal — tune for your team's style.

# Match IDs like §7.3, §7.3.1, D5, Q12, SOW-§4.2, SOW-§4.2.a
REQ_ID_RE = re.compile(r"(?:SOW-)?(?:§\d+(?:\.\d+)*[a-z]?|[DQ]\d+)")

# Match PRD requirement lines. Prefers lines starting with "- [ID]" or
# "- **ID**" or headers like "### ID:" but will also accept any line
# containing a recognizable ID.
PRD_REQ_LINE_RE = re.compile(
    r"(?:^\s*[-*]\s*\[?|^\s*#{1,6}\s*|^\s*\*\*)(" + REQ_ID_RE.pattern + r")\]?"
)

# Match a task header line:  - [x] T001: title  (or [ ], or [DEFERRED])
TASK_HEADER_RE = re.compile(
    r"^\s*[-*]\s*\[(?P<status>x|\s|DEFERRED)\]\s*(?P<id>T\d+):\s*(?P<title>.+?)\s*$",
    re.IGNORECASE,
)

# Subline patterns within a task block.
# Sublines may appear either as plain indented lines ("  Satisfies: ...")
# or as nested markdown list items ("  - Satisfies: ..."). Accept both.
SATISFIES_RE = re.compile(
    r"^\s+(?:[-*]\s+)?Satisfies:\s*(?P<ids>.+?)\s*$", re.IGNORECASE
)
FILES_RE = re.compile(
    r"^\s+(?:[-*]\s+)?Files:\s*(?P<files>.+?)\s*$", re.IGNORECASE
)
ACCEPTANCE_RE = re.compile(
    r"^\s+(?:[-*]\s+)?Acceptance:\s*(?P<text>.+?)\s*$", re.IGNORECASE
)
TARGET_RE = re.compile(
    r"^\s+(?:[-*]\s+)?Target:\s*(?P<target>v\d+\S*)\s*$", re.IGNORECASE
)
STATUS_DEFERRED_RE = re.compile(
    r"^\s+(?:[-*]\s+)?Status:\s*DEFERRED\s*$", re.IGNORECASE
)

# Symbol-extraction patterns.
#
# 1. Backticked tokens — the strongest signal. The author has explicitly
#    flagged this string as a code identifier. Accept anything inside
#    backticks that's not pure whitespace.
BACKTICKED_RE = re.compile(r"`([^`\n]+?)`")

# 2. Bare identifier shapes that are unambiguously code, not English:
#    - contains an underscore (snake_case, _private, ALL_CAPS, kebab-cased
#      isn't matched but isn't typical for Python/JS symbols)
#    - inner case change (camelCase, PascalCase) — at least one
#      lowercase-then-uppercase transition
#    - all-caps with at least 2 chars (HTTP, OWASP, CONST)
# Plain English words (no underscore, no inner case, mixed case) are
# excluded to keep the false-positive rate down.
SNAKE_OR_CAMEL_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")

# Min length for an extracted bare identifier to count.
MIN_SYMBOL_LEN = 3

# Acceptance sentences full of common English get scrubbed of these noise
# tokens before the identifier scan. Keeping the list short on purpose —
# the goal is to drop obvious false positives, not to filter every English
# word.
ENGLISH_NOISE = {
    "the", "and", "but", "for", "with", "from", "into", "onto", "this",
    "that", "these", "those", "have", "has", "are", "was", "were", "been",
    "being", "will", "must", "should", "shall", "may", "can", "any", "all",
    "not", "non", "yes", "true", "false", "none", "null", "when", "then",
    "what", "where", "which", "who", "why", "how", "via", "use", "used",
    "uses", "set", "get", "put", "run", "runs", "ran", "see", "shows",
    "show", "show", "row", "rows", "one", "two", "old", "new", "now",
    "next", "prev", "previous", "current", "active", "every", "each",
    "exists", "exist", "missing", "found", "input", "output", "value",
    "values", "field", "fields", "line", "lines",
}


@dataclass
class Requirement:
    id: str
    line_number: int
    source_file: str


@dataclass
class Task:
    id: str
    title: str
    status: str  # "complete" | "open" | "deferred"
    line_number: int
    satisfies: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    acceptance: Optional[str] = None
    target: Optional[str] = None  # for deferred tasks


@dataclass
class CoverageEntry:
    requirement_id: str
    status: str  # "covered" | "deferred" | "missing"
    task_id: Optional[str] = None
    file_citations: list[str] = field(default_factory=list)
    confidence: str = "unknown"  # "high" | "medium" | "low" | "unknown"
    notes: str = ""
    candidate_symbols: list[str] = field(default_factory=list)
    matched_symbols: list[str] = field(default_factory=list)


def parse_prd(prd_path: Path) -> list[Requirement]:
    """Extract requirement IDs from a PRD markdown file."""
    if not prd_path.is_file():
        sys.stderr.write(f"ERROR: PRD file not found: {prd_path}\n")
        sys.exit(2)

    requirements: list[Requirement] = []
    seen: set[str] = set()

    with prd_path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            # Look for lines with a requirement ID.
            m = PRD_REQ_LINE_RE.search(line)
            if m:
                req_id = m.group(1)
                if req_id not in seen:
                    seen.add(req_id)
                    requirements.append(
                        Requirement(
                            id=req_id,
                            line_number=lineno,
                            source_file=str(prd_path),
                        )
                    )

    if not requirements:
        sys.stderr.write(
            f"WARNING: no requirement IDs found in {prd_path}. "
            f"Check that IDs match the expected patterns (§X.Y, Dn, Qn, SOW-§X.Y).\n"
        )

    return requirements


def parse_tasks(tasks_path: Path) -> list[Task]:
    """Extract tasks and their Satisfies: citations from a TASKS markdown file."""
    if not tasks_path.is_file():
        sys.stderr.write(f"ERROR: TASKS file not found: {tasks_path}\n")
        sys.exit(2)

    tasks: list[Task] = []
    current: Optional[Task] = None

    with tasks_path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            header_match = TASK_HEADER_RE.match(line)
            if header_match:
                # Finalize previous task
                if current is not None:
                    tasks.append(current)
                status_char = header_match.group("status")
                if status_char.lower() == "deferred":
                    status = "deferred"
                elif status_char == "x":
                    status = "complete"
                else:
                    status = "open"
                current = Task(
                    id=header_match.group("id"),
                    title=header_match.group("title"),
                    status=status,
                    line_number=lineno,
                )
                continue

            if current is None:
                continue

            # Subline parsing
            sat_match = SATISFIES_RE.match(line)
            if sat_match:
                raw_ids = sat_match.group("ids")
                for token in re.split(r"[,\s]+", raw_ids):
                    token = token.strip().rstrip(".,;")
                    if token and REQ_ID_RE.fullmatch(token):
                        current.satisfies.append(token)
                continue

            files_match = FILES_RE.match(line)
            if files_match:
                raw_files = files_match.group("files")
                for p in re.split(r",\s*", raw_files):
                    p = p.strip()
                    if p:
                        current.files.append(p)
                continue

            acceptance_match = ACCEPTANCE_RE.match(line)
            if acceptance_match:
                # Acceptance can wrap onto subsequent indented lines, but
                # parsing the first line is enough for symbol extraction —
                # symbols repeat across the wrap in practice.
                current.acceptance = acceptance_match.group("text")
                continue

            target_match = TARGET_RE.match(line)
            if target_match:
                current.target = target_match.group("target")
                continue

            if STATUS_DEFERRED_RE.match(line):
                current.status = "deferred"

    if current is not None:
        tasks.append(current)

    return tasks


def verify_file_presence(files: list[str], repo_root: Path) -> list[str]:
    """For a task's listed files, return which ones actually exist in the repo."""
    found: list[str] = []
    for relpath in files:
        # Files can be listed with or without a leading slash; normalize
        candidate = repo_root / relpath.lstrip("/")
        if candidate.is_file():
            # Record as repo-relative for clean output
            found.append(str(candidate.relative_to(repo_root)))
    return found


def _looks_like_identifier(token: str) -> bool:
    """True if `token` looks like code, not English."""
    if len(token) < MIN_SYMBOL_LEN:
        return False
    if token.lower() in ENGLISH_NOISE:
        return False
    if "_" in token:
        return True
    # Inner case change → camelCase or PascalCase.
    for i in range(1, len(token)):
        if token[i].isupper() and token[i - 1].islower():
            return True
    # All-caps with at least 3 chars (HTTP, OWASP, CONST).
    if token.isupper() and any(c.isalpha() for c in token):
        return True
    return False


def extract_candidate_symbols(task: Task) -> list[str]:
    """Pull likely code-symbol tokens from a task's title and Acceptance text.

    Backticked tokens are kept verbatim (strongest signal). Bare tokens must
    look like an identifier (snake_case, camelCase/PascalCase, or ALL_CAPS).
    Plain English words are filtered out — the goal is high-precision hints,
    not exhaustive extraction.
    """
    sources: list[str] = []
    if task.title:
        sources.append(task.title)
    if task.acceptance:
        sources.append(task.acceptance)

    seen: set[str] = set()
    out: list[str] = []

    for text in sources:
        # Backticked first — these are explicit code refs.
        for bt in BACKTICKED_RE.findall(text):
            for piece in re.split(r"[,\s()]+", bt.strip()):
                piece = piece.strip("`.,;:")
                if piece and piece not in seen:
                    seen.add(piece)
                    out.append(piece)
        # Strip backticks before scanning bare identifiers, otherwise we'd
        # match the contents twice and apply the noise filter to them.
        scrubbed = BACKTICKED_RE.sub(" ", text)
        for tok in SNAKE_OR_CAMEL_RE.findall(scrubbed):
            if _looks_like_identifier(tok) and tok not in seen:
                seen.add(tok)
                out.append(tok)

    return out


def find_symbols_in_files(
    symbols: list[str], existing_files: list[str], repo_root: Path
) -> list[str]:
    """Return the subset of `symbols` that appear (substring match) in any of
    the given existing files. Case-sensitive — code symbols are.
    """
    if not symbols or not existing_files:
        return []
    matched: set[str] = set()
    remaining = set(symbols)
    for relpath in existing_files:
        if not remaining:
            break
        path = repo_root / relpath
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for sym in list(remaining):
            if sym in content:
                matched.add(sym)
                remaining.discard(sym)
    # Preserve the original symbol order for deterministic output.
    return [s for s in symbols if s in matched]


def determine_confidence(
    task: Task,
    existing_files: list[str],
    candidate_symbols: list[str],
    matched_symbols: list[str],
) -> str:
    """
    Heuristic for confidence:
      HIGH   — task complete, all files exist, AND (no candidate symbols to
               check OR ≥1 candidate symbol present in those files)
      MEDIUM — task complete, all files exist, candidates extracted, but
               none matched (likely-empty stub) — OR — task complete with
               some files missing
      LOW    — task complete but no files listed, or no files exist
    """
    if task.status != "complete":
        return "unknown"
    if not task.files:
        return "low"
    if len(existing_files) == 0:
        return "low"
    if len(existing_files) < len(task.files):
        return "medium"
    # All files exist — promote/demote on symbol match.
    if not candidate_symbols:
        return "high"
    return "high" if matched_symbols else "medium"


def build_coverage(
    requirements: list[Requirement],
    tasks: list[Task],
    repo_root: Path,
    strict_symbols: bool = False,
) -> list[CoverageEntry]:
    """Map each requirement to its covering task (or lack thereof).

    When `strict_symbols` is True, a completed task whose listed files exist
    but contain none of the symbols extracted from its title/Acceptance is
    treated as a missing requirement (the "empty stub" pattern).
    """
    # Build lookup: requirement_id -> list of tasks claiming to satisfy it
    req_to_tasks: dict[str, list[Task]] = {}
    for task in tasks:
        for req_id in task.satisfies:
            req_to_tasks.setdefault(req_id, []).append(task)

    entries: list[CoverageEntry] = []
    for req in requirements:
        claiming = req_to_tasks.get(req.id, [])
        completed = [t for t in claiming if t.status == "complete"]
        deferred = [t for t in claiming if t.status == "deferred"]

        if completed:
            # Pick the first completed task; record its file evidence.
            task = completed[0]
            existing = verify_file_presence(task.files, repo_root)
            candidates = extract_candidate_symbols(task)
            matched = find_symbols_in_files(candidates, existing, repo_root)
            confidence = determine_confidence(task, existing, candidates, matched)

            # Build a notes string that reads cleanly in the table.
            note_parts: list[str] = []
            if task.files:
                note_parts.append(
                    f"Listed {len(task.files)} file(s); {len(existing)} found"
                )
            else:
                note_parts.append("No files listed on task")
            if candidates:
                if matched:
                    note_parts.append(
                        f"matched {len(matched)}/{len(candidates)} symbol(s)"
                    )
                elif existing:
                    note_parts.append(
                        f"STUB-WARNING: 0/{len(candidates)} symbols found in listed files"
                    )

            stub_pattern = (
                bool(existing)
                and bool(candidates)
                and not matched
            )
            if strict_symbols and stub_pattern:
                entries.append(
                    CoverageEntry(
                        requirement_id=req.id,
                        status="missing",
                        task_id=task.id,
                        file_citations=existing,
                        confidence="high",
                        notes=(
                            f"STUB: task complete and files exist but none of "
                            f"{candidates[:5]}... appear in {existing}"
                        ),
                        candidate_symbols=candidates,
                        matched_symbols=matched,
                    )
                )
            else:
                entries.append(
                    CoverageEntry(
                        requirement_id=req.id,
                        status="covered",
                        task_id=task.id,
                        file_citations=existing,
                        confidence=confidence,
                        notes="; ".join(note_parts),
                        candidate_symbols=candidates,
                        matched_symbols=matched,
                    )
                )
        elif deferred:
            task = deferred[0]
            target = task.target or "UNSPECIFIED"
            entries.append(
                CoverageEntry(
                    requirement_id=req.id,
                    status="deferred",
                    task_id=task.id,
                    confidence="high" if task.target else "low",
                    notes=f"Deferred to {target}",
                )
            )
        else:
            # No task claims to satisfy this requirement.
            entries.append(
                CoverageEntry(
                    requirement_id=req.id,
                    status="missing",
                    confidence="high",
                    notes="No task cites this requirement ID",
                )
            )

    return entries


def print_human_table(entries: list[CoverageEntry]) -> None:
    """Print a plaintext coverage table suitable for terminal or PR comment."""
    print("\n=== Sprint Coverage Report ===\n")
    header = f"{'Requirement':<20} {'Status':<10} {'Task':<8} {'Confidence':<10}  {'Notes'}"
    print(header)
    print("-" * len(header))
    for e in entries:
        task = e.task_id or "—"
        print(
            f"{e.requirement_id:<20} {e.status:<10} {task:<8} {e.confidence:<10}  {e.notes}"
        )
        for cite in e.file_citations:
            print(f"  {'':<20} {'':<10} {'':<8} {'':<10}  ↳ {cite}")
    print()


def print_summary(entries: list[CoverageEntry]) -> tuple[int, int, int]:
    """Print a summary line and return counts."""
    covered = sum(1 for e in entries if e.status == "covered")
    deferred = sum(1 for e in entries if e.status == "deferred")
    missing = sum(1 for e in entries if e.status == "missing")
    total = len(entries)
    print(f"Covered: {covered}  Deferred: {deferred}  Missing: {missing}  Total: {total}")
    return covered, deferred, missing


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sprint coverage check — reconciles PRD requirements against TASKS and code."
    )
    parser.add_argument(
        "sprint_dir",
        help="Path to the sprint directory (e.g., sprints/v1/). "
        "Must contain PRD.md and TASKS.md.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of human-readable table.",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="CI mode: terser output, non-zero exit on any missing requirement.",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for file-existence checks (default: current directory).",
    )
    parser.add_argument(
        "--strict-symbols",
        action="store_true",
        help="Treat 'all listed files exist but no extracted symbol is "
        "present' as a missing requirement (the 'empty stub' pattern). "
        "Off by default — opt in once your team has validated the symbol "
        "extraction against a real sprint.",
    )
    args = parser.parse_args()

    sprint_dir = Path(args.sprint_dir).resolve()
    prd_path = sprint_dir / "PRD.md"
    tasks_path = sprint_dir / "TASKS.md"
    repo_root = Path(args.repo_root).resolve()

    if not sprint_dir.is_dir():
        sys.stderr.write(f"ERROR: sprint directory not found: {sprint_dir}\n")
        return 2

    requirements = parse_prd(prd_path)
    tasks = parse_tasks(tasks_path)
    entries = build_coverage(
        requirements, tasks, repo_root, strict_symbols=args.strict_symbols
    )

    if args.json:
        print(
            json.dumps(
                {
                    "sprint_dir": str(sprint_dir),
                    "total_requirements": len(entries),
                    "entries": [asdict(e) for e in entries],
                },
                indent=2,
            )
        )
    else:
        if not args.ci:
            print_human_table(entries)
        _, _, missing = print_summary(entries)
        if missing > 0 and args.ci:
            print("\nFAIL: requirements are missing without explicit [DEFERRED] entries.", file=sys.stderr)

    missing = sum(1 for e in entries if e.status == "missing")
    return 1 if missing > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
