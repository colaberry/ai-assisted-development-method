#!/usr/bin/env python3
"""sprint_close.py — Atomic sprint-closure for the AI-Assisted Development Method.

Promotes the manual /sprint-close checklist to a script. Runs reconcile in
CI mode, verifies the closure artifacts (RETRO.md is not a template stub,
reviewer sign-off exists), and writes `.lock` only when every check passes.
The `.lock` file is the structural signal that downstream tooling (and the
PreToolUse hook) uses to allow work on sprint vN+1.

What this script will refuse to lock:

  - A sprint whose reconcile.py --ci fails (missing requirements with no
    [DEFERRED] entry).
  - A sprint whose RETRO.md is still recognizably the template (unfilled
    `<placeholder>` brackets, literal `vN`, literal `YYYY-MM-DD`, or empty
    bullet lists for the "What went well / poorly" sections).
  - A sprint whose PRD.md declares `/security-review required: Yes` but
    has no `SECURITY-REVIEW.md` artifact (same for `/ui-qa` and UI-QA.md).
    The artifact must contain `Reviewer:`, `Date:`, and `Decision:` fields;
    `Decision: blocked` is a refusal.
  - A sprint without a sign-off (either `sprints/vN/SIGNOFF.md` containing
    `Reviewer:` + `Date:` lines, or `--reviewer NAME` passed on the CLI to
    create one).

Usage:
    sprint_close.py sprints/v3
    sprint_close.py sprints/v3 --reviewer "Jane Doe"
    sprint_close.py sprints/v3 --strict-symbols     # pass-through to reconcile
    sprint_close.py sprints/v3 --dry-run            # report only, never write
    sprint_close.py sprints/v3 --json               # machine-readable result

Exit codes:
    0  all checks passed (and `.lock` was written, unless --dry-run)
    1  one or more checks failed (no `.lock` written)
    2  usage / environment error
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# Heuristics for recognizing template stubs in RETRO.md. Any single match
# is enough to flag the file as unfilled.
TEMPLATE_MARKERS = (
    re.compile(r"<[A-Za-z][^>\n]*>"),     # <placeholder>, <name>, <slug>...
    re.compile(r"\bYYYY-MM-DD\b"),
    re.compile(r"\bvN\b"),
)

# A "non-trivial" RETRO needs at least these two sections to contain actual
# answers, not just the prompt prose. We detect by counting non-prompt
# bullet lines under the headings — any bullet that isn't the literal
# template placeholder prose counts.
REQUIRED_SECTION_HEADINGS = (
    "What went well this sprint?",
    "What went poorly?",
)


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class CloseReport:
    sprint_dir: str
    locked: bool
    dry_run: bool
    reviewer: Optional[str]
    checks: list[CheckResult] = field(default_factory=list)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def find_repo_root(sprint_dir: Path) -> Path:
    """Walk upward from sprint_dir until we find a directory containing a
    `scripts/` directory or a `.git/` directory. Falls back to cwd."""
    cur = sprint_dir.resolve()
    for parent in (cur, *cur.parents):
        if (parent / ".git").is_dir() or (parent / "scripts").is_dir():
            return parent
    return Path.cwd().resolve()


def find_reconcile_script(repo_root: Path) -> Optional[Path]:
    """Look for reconcile.py in the conventional location."""
    candidate = repo_root / "scripts" / "reconcile.py"
    if candidate.is_file():
        return candidate
    # Some teams keep tooling in tooling/scripts/ inside the AADM repo
    # itself — accept that for self-tests.
    candidate = repo_root / "tooling" / "scripts" / "reconcile.py"
    if candidate.is_file():
        return candidate
    return None


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_sprint_layout(sprint_dir: Path) -> CheckResult:
    if not sprint_dir.is_dir():
        return CheckResult("sprint_layout", False, f"not a directory: {sprint_dir}")
    missing = [
        name for name in ("PRD.md", "TASKS.md")
        if not (sprint_dir / name).is_file()
    ]
    if missing:
        return CheckResult(
            "sprint_layout", False, f"missing required file(s): {', '.join(missing)}"
        )
    return CheckResult("sprint_layout", True, "PRD.md and TASKS.md present")


def check_not_already_locked(sprint_dir: Path) -> CheckResult:
    lock = sprint_dir / ".lock"
    if lock.exists():
        return CheckResult(
            "not_already_locked",
            False,
            f"{lock} already exists — sprint is already closed",
        )
    return CheckResult("not_already_locked", True, "")


def check_reconcile(
    sprint_dir: Path,
    repo_root: Path,
    strict_symbols: bool,
) -> CheckResult:
    script = find_reconcile_script(repo_root)
    if script is None:
        return CheckResult(
            "reconcile",
            False,
            "could not find scripts/reconcile.py — is the tooling installed?",
        )
    cmd = [
        sys.executable, str(script), str(sprint_dir),
        "--ci", "--repo-root", str(repo_root),
    ]
    if strict_symbols:
        cmd.append("--strict-symbols")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        return CheckResult("reconcile", True, "all requirements covered or deferred")
    detail = (proc.stderr or proc.stdout or "").strip().splitlines()
    summary = detail[-1] if detail else f"exit {proc.returncode}"
    return CheckResult("reconcile", False, summary)


def check_retro_filled(sprint_dir: Path) -> CheckResult:
    retro = sprint_dir / "RETRO.md"
    if not retro.is_file():
        return CheckResult("retro_filled", False, "RETRO.md missing")
    text = retro.read_text(encoding="utf-8")

    # 1. No template-marker leftovers.
    for marker in TEMPLATE_MARKERS:
        m = marker.search(text)
        if m:
            return CheckResult(
                "retro_filled",
                False,
                f"RETRO.md still contains template marker: {m.group(0)!r}",
            )

    # 2. The two key sections must have non-template content.
    missing_sections: list[str] = []
    for heading in REQUIRED_SECTION_HEADINGS:
        body = _section_body(text, heading)
        if body is None:
            missing_sections.append(heading)
            continue
        # Strip blank lines and the prompt prose (italicized blockquotes
        # don't count). A genuine answer is either a non-bullet paragraph
        # or a bullet whose content isn't just whitespace.
        if not _has_real_content(body):
            missing_sections.append(heading)
    if missing_sections:
        return CheckResult(
            "retro_filled",
            False,
            "RETRO.md sections appear empty: " + ", ".join(missing_sections),
        )
    return CheckResult("retro_filled", True, "RETRO.md has filled sections 1 and 2")


def _section_body(text: str, heading_text: str) -> Optional[str]:
    """Return the body of an `## N. <heading_text>`-style section."""
    # Match `## 1. What went well this sprint?` or similar.
    pattern = re.compile(
        rf"^##\s+\d+\.\s+{re.escape(heading_text)}\s*$",
        re.MULTILINE,
    )
    m = pattern.search(text)
    if not m:
        return None
    body_start = m.end()
    next_heading = re.search(r"^---\s*$|^##\s+\d+\.\s+", text[body_start:], re.MULTILINE)
    body_end = body_start + next_heading.start() if next_heading else len(text)
    return text[body_start:body_end]


def _has_real_content(body: str) -> bool:
    """True if `body` contains any line that looks like a genuine answer."""
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        # Skip prompt prose (italicized in the template via `*...*` or `>` blockquote).
        if line.startswith(">"):
            continue
        # Skip empty bullets like "- " or "- <pattern 1>".
        if line.startswith(("-", "*")):
            content = line.lstrip("-* \t")
            # Empty, or a placeholder of the form `<text>` (template stub).
            if not content:
                continue
            if content.startswith("<") and content.endswith(">"):
                continue
            return True
        # Plain prose paragraph that isn't a heading.
        if not line.startswith("#"):
            return True
    return False


def find_metrics_script(repo_root: Path) -> Optional[Path]:
    """Look for metrics.py in the conventional locations."""
    for rel in ("metrics/scripts/metrics.py", "scripts/metrics.py"):
        candidate = repo_root / rel
        if candidate.is_file():
            return candidate
    return None


def _count_session_events(events_file: Path, sprint: str) -> int:
    if not events_file.is_file():
        return 0
    count = 0
    try:
        with events_file.open("r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if evt.get("event_type") == "session" and evt.get("sprint") == sprint:
                    count += 1
    except OSError:
        return 0
    return count


def check_sessions_logged(
    sprint_dir: Path,
    repo_root: Path,
) -> CheckResult:
    """Refuse to lock a sprint with zero logged session events.

    Structural, not cultural: without this check a team can drift into
    sprint-closing without ever logging a session, and the retro metrics
    section has nothing to feed on. If no metrics module is installed at
    all, the check passes with a note — metrics/ is optional for the
    minimum-viable adoption path.
    """
    metrics_script = find_metrics_script(repo_root)
    if metrics_script is None:
        return CheckResult(
            "sessions_logged",
            True,
            "metrics/ not installed; session logging is optional for this repo",
        )
    events_file = repo_root / "docs" / "metrics" / "events.jsonl"
    n = _count_session_events(events_file, sprint_dir.name)
    if n == 0:
        return CheckResult(
            "sessions_logged",
            False,
            (
                f"no session events logged for {sprint_dir.name} — run "
                f"`python3 {metrics_script.relative_to(repo_root)} log-session "
                f"--kind dev` at session end, at least once per sprint"
            ),
        )
    return CheckResult(
        "sessions_logged",
        True,
        f"{n} session event(s) logged for {sprint_dir.name}",
    )


# Valid `Decision:` values in a scope artifact (SECURITY-REVIEW.md / UI-QA.md).
_SCOPE_DECISIONS = ("passed", "n/a", "blocked")


def _parse_prd_scope_flag(prd_path: Path, flag_name: str) -> Optional[bool]:
    """Parse whether `/security-review` or `/ui-qa` is required for this sprint.

    Looks for a line like ``- **`/security-review` required:** Yes`` in
    ``PRD.md``. Returns True/False if the flag is decisively set, or None
    if the line is missing or still the unfilled template (``Yes / No``).
    None means "treat as unspecified" — the close does not refuse on a
    missing artifact in that case, but the check result makes the ambiguity
    visible in the report.
    """
    if not prd_path.is_file():
        return None
    text = prd_path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"^\s*[-*]\s*\*\*`/{re.escape(flag_name)}`\s+required:\*\*\s*(.+?)\s*$",
        re.MULTILINE,
    )
    m = pattern.search(text)
    if not m:
        return None
    value = m.group(1).strip().lower()
    # Unfilled template literally reads "yes / no" — treat as unspecified.
    if re.fullmatch(r"yes\s*/\s*no", value):
        return None
    if value in ("yes", "y", "true", "required"):
        return True
    if value in ("no", "n", "false", "not required", "n/a"):
        return False
    return None


def _parse_scope_artifact(artifact_path: Path) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Return (reviewer, date, decision) from a SECURITY-REVIEW.md / UI-QA.md.

    Any field that isn't present or doesn't match the expected shape comes
    back as None. The caller decides how to treat partial parses.
    """
    if not artifact_path.is_file():
        return (None, None, None)
    text = artifact_path.read_text(encoding="utf-8")
    rev_match = re.search(r"^\s*\*{0,2}Reviewer:\*{0,2}\s*(.+?)\s*$", text, re.MULTILINE)
    date_match = re.search(
        r"^\s*\*{0,2}Date:\*{0,2}\s*(\d{4}-\d{2}-\d{2})\s*$",
        text,
        re.MULTILINE,
    )
    decision_match = re.search(
        r"^\s*\*{0,2}Decision:\*{0,2}\s*(passed|n/?a|blocked)\s*$",
        text,
        re.MULTILINE | re.IGNORECASE,
    )
    reviewer = rev_match.group(1).strip() if rev_match else None
    date = date_match.group(1) if date_match else None
    decision = decision_match.group(1).strip().lower().replace("n/a", "n/a") if decision_match else None
    if decision == "na":
        decision = "n/a"
    return (reviewer, date, decision)


def check_scope_artifact(
    sprint_dir: Path,
    *,
    flag_name: str,
    artifact_filename: str,
    check_name: str,
) -> CheckResult:
    """Verify a scope artifact (SECURITY-REVIEW.md / UI-QA.md) matches the PRD flag.

    Behavior:
    - PRD flag unspecified (missing or literal ``Yes / No`` stub): pass with
      a note; the engineer is responsible for setting the flag, but we do
      not refuse to lock on an unfilled template.
    - PRD flag ``No``: pass (scope not required).
    - PRD flag ``Yes`` and artifact missing: refuse.
    - PRD flag ``Yes`` and artifact missing ``Reviewer:`` / ``Date:`` /
      ``Decision:`` fields: refuse with the specific missing field named.
    - PRD flag ``Yes`` and ``Decision: blocked``: refuse with the blocker.
    - PRD flag ``Yes`` and ``Decision: passed`` or ``Decision: n/a``: pass.
    """
    prd_path = sprint_dir / "PRD.md"
    required = _parse_prd_scope_flag(prd_path, flag_name)
    artifact_path = sprint_dir / artifact_filename

    if required is None:
        return CheckResult(
            check_name,
            True,
            f"PRD `/{flag_name}` flag unspecified; artifact check skipped",
        )
    if required is False:
        return CheckResult(
            check_name,
            True,
            f"PRD declares /{flag_name} not required for this sprint",
        )

    # required is True — artifact must exist and pass.
    if not artifact_path.is_file():
        return CheckResult(
            check_name,
            False,
            (
                f"PRD requires /{flag_name} but {artifact_filename} is missing — "
                f"run /{flag_name} and commit the artifact"
            ),
        )
    reviewer, date, decision = _parse_scope_artifact(artifact_path)
    missing_fields = [
        name for name, value in
        (("Reviewer", reviewer), ("Date", date), ("Decision", decision))
        if not value
    ]
    if missing_fields:
        return CheckResult(
            check_name,
            False,
            (
                f"{artifact_filename} missing field(s): {', '.join(missing_fields)} "
                f"(expected Reviewer / Date / Decision)"
            ),
        )
    if decision not in _SCOPE_DECISIONS:
        return CheckResult(
            check_name,
            False,
            (
                f"{artifact_filename} has Decision: {decision!r} — must be one of "
                f"{', '.join(_SCOPE_DECISIONS)}"
            ),
        )
    if decision == "blocked":
        return CheckResult(
            check_name,
            False,
            (
                f"{artifact_filename} Decision: blocked — resolve the blocker and "
                f"re-run /{flag_name} before closing"
            ),
        )
    return CheckResult(
        check_name,
        True,
        f"{artifact_filename} Decision: {decision} (reviewer={reviewer!r}, date={date})",
    )


def check_signoff(
    sprint_dir: Path,
    reviewer_arg: Optional[str],
) -> tuple[CheckResult, Optional[str]]:
    """Verify a sign-off exists, or create one if --reviewer was passed."""
    signoff = sprint_dir / "SIGNOFF.md"
    if reviewer_arg:
        signoff.write_text(
            f"# Sprint sign-off\n\n"
            f"Reviewer: {reviewer_arg}\n"
            f"Date: {_today_iso()}\n",
            encoding="utf-8",
        )
        return (
            CheckResult("signoff", True, f"wrote SIGNOFF.md (reviewer: {reviewer_arg})"),
            reviewer_arg,
        )

    if not signoff.is_file():
        return (
            CheckResult(
                "signoff",
                False,
                "SIGNOFF.md missing — create one or pass --reviewer NAME",
            ),
            None,
        )
    text = signoff.read_text(encoding="utf-8")
    rev_match = re.search(r"^Reviewer:\s*(.+?)\s*$", text, re.MULTILINE)
    date_match = re.search(r"^Date:\s*(\d{4}-\d{2}-\d{2})\s*$", text, re.MULTILINE)
    if not rev_match or not date_match:
        return (
            CheckResult(
                "signoff",
                False,
                "SIGNOFF.md must contain `Reviewer:` and `Date: YYYY-MM-DD` lines",
            ),
            None,
        )
    return (
        CheckResult(
            "signoff",
            True,
            f"reviewer={rev_match.group(1)!r} date={date_match.group(1)}",
        ),
        rev_match.group(1),
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_close(
    sprint_dir: Path,
    repo_root: Path,
    reviewer_arg: Optional[str],
    strict_symbols: bool,
    dry_run: bool,
) -> CloseReport:
    report = CloseReport(
        sprint_dir=str(sprint_dir),
        locked=False,
        dry_run=dry_run,
        reviewer=None,
    )

    layout = check_sprint_layout(sprint_dir)
    report.checks.append(layout)
    if not layout.passed:
        return report

    not_locked = check_not_already_locked(sprint_dir)
    report.checks.append(not_locked)
    if not not_locked.passed:
        return report

    report.checks.append(check_reconcile(sprint_dir, repo_root, strict_symbols))
    report.checks.append(check_retro_filled(sprint_dir))
    report.checks.append(check_sessions_logged(sprint_dir, repo_root))
    report.checks.append(check_scope_artifact(
        sprint_dir,
        flag_name="security-review",
        artifact_filename="SECURITY-REVIEW.md",
        check_name="security_review",
    ))
    report.checks.append(check_scope_artifact(
        sprint_dir,
        flag_name="ui-qa",
        artifact_filename="UI-QA.md",
        check_name="ui_qa",
    ))

    signoff_result, reviewer = check_signoff(sprint_dir, reviewer_arg)
    report.checks.append(signoff_result)
    report.reviewer = reviewer

    if not all(c.passed for c in report.checks):
        return report

    # All checks passed — write .lock unless dry-run.
    if not dry_run:
        lock_path = sprint_dir / ".lock"
        lock_path.write_text(
            f"locked_at: {_iso_now()}\n"
            f"reviewer: {reviewer or 'unknown'}\n"
            f"reconcile_status: pass\n",
            encoding="utf-8",
        )
        report.locked = True
    return report


def print_human(report: CloseReport) -> None:
    print(f"\n=== Sprint close: {report.sprint_dir} ===\n")
    width = max(len(c.name) for c in report.checks) if report.checks else 0
    for c in report.checks:
        marker = "PASS" if c.passed else "FAIL"
        print(f"  [{marker}] {c.name:<{width}}  {c.detail}")
    print()
    if report.locked:
        print(f"OK: .lock written. Reviewer: {report.reviewer}.")
    elif report.dry_run and all(c.passed for c in report.checks):
        print("DRY RUN: all checks passed; .lock would be written.")
    else:
        failing = [c.name for c in report.checks if not c.passed]
        print(
            "FAIL: sprint not locked. Failing check(s): "
            + ", ".join(failing or ["unknown"])
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Atomically close a sprint: run reconcile --ci, verify RETRO and "
            "sign-off, then write .lock. No partial closures."
        )
    )
    parser.add_argument("sprint_dir", help="Path to the sprint directory (e.g., sprints/v3)")
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repo root (default: auto-detected from sprint_dir)",
    )
    parser.add_argument(
        "--reviewer",
        default=None,
        help="Reviewer name. If passed, creates/overwrites SIGNOFF.md with today's date.",
    )
    parser.add_argument(
        "--strict-symbols",
        action="store_true",
        help="Pass --strict-symbols to reconcile (fail on empty stubs).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run all checks but never write .lock or SIGNOFF.md.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of the human-readable table.",
    )
    args = parser.parse_args()

    sprint_dir = Path(args.sprint_dir).resolve()
    repo_root = (
        Path(args.repo_root).resolve()
        if args.repo_root
        else find_repo_root(sprint_dir)
    )

    # Dry-run never writes SIGNOFF.md, even with --reviewer.
    reviewer_arg = None if args.dry_run else args.reviewer

    report = run_close(
        sprint_dir=sprint_dir,
        repo_root=repo_root,
        reviewer_arg=reviewer_arg,
        strict_symbols=args.strict_symbols,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps({
            "sprint_dir": report.sprint_dir,
            "locked": report.locked,
            "dry_run": report.dry_run,
            "reviewer": report.reviewer,
            "checks": [asdict(c) for c in report.checks],
        }, indent=2))
    else:
        print_human(report)

    return 0 if all(c.passed for c in report.checks) else 1


if __name__ == "__main__":
    sys.exit(main())
