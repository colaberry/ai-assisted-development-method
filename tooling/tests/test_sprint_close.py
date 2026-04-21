"""Self-tests for sprint_close.py.

Run with:  python3 tooling/tests/test_sprint_close.py
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


def _load(module_name: str, relpath: str):
    here = Path(__file__).resolve().parent
    script = here.parent / relpath
    spec = importlib.util.spec_from_file_location(module_name, script)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


sc = _load("sprint_close", "scripts/sprint_close.py")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PRD_GOOD = textwrap.dedent("""\
    # PRD v1
    - [D1] Implement load_ref check
""")

TASKS_GOOD = textwrap.dedent("""\
    - [x] T001: Wire `_routes_differ` into the `load_ref` path
      - Satisfies: D1
      - Acceptance: When `load_ref` matches, set `_routes_differ`.
      - Files: src/threading.py
""")

# A RETRO that's clearly the unfilled template — every TEMPLATE_MARKERS
# pattern matches.
RETRO_TEMPLATE = textwrap.dedent("""\
    # Sprint vN — Retrospective

    **Sprint:** vN
    **Sprint dates:** YYYY-MM-DD to YYYY-MM-DD
    **Facilitator:** <name>

    ## 1. What went well this sprint?

    <Concrete, specific. ...>

    - <pattern 1>

    ## 2. What went poorly?

    - <recurrence 1>

    ## 7. Actions

    - [ ] <action 1>
""")

# A RETRO with real content in sections 1 and 2, no template markers.
RETRO_FILLED = textwrap.dedent("""\
    # Sprint v3 — Retrospective

    **Sprint:** v3
    **Sprint dates:** 2026-04-01 to 2026-04-15
    **Facilitator:** Jane Doe

    ## 1. What went well this sprint?

    The async webhook integration test pattern caught two real bugs before staging.
    Pairing on the Stripe migration was faster than estimated.

    ## 2. What went poorly?

    Underestimated the SAML attribute-mapping work because we did not account
    for the client's non-standard attribute names.

    ## 7. Actions

    - Capture the SAML attribute pattern in CLAUDE.md by 2026-04-22.
""")

SIGNOFF_GOOD = textwrap.dedent("""\
    # Sprint sign-off

    Reviewer: Jane Doe
    Date: 2026-04-19
""")

SIGNOFF_BAD = "no fields here\n"


# PRD fixtures with the scope-flag lines in several states.
PRD_SECURITY_REQUIRED = textwrap.dedent("""\
    # PRD v1
    - [D1] Implement load_ref check

    ## Performance and security budgets

    - **`/security-review` required:** Yes
    - **`/ui-qa` required:** No
""")

PRD_UI_REQUIRED = textwrap.dedent("""\
    # PRD v1
    - [D1] Implement load_ref check

    ## Performance and security budgets

    - **`/security-review` required:** No
    - **`/ui-qa` required:** Yes
""")

PRD_BOTH_REQUIRED = textwrap.dedent("""\
    # PRD v1
    - [D1] Implement load_ref check

    ## Performance and security budgets

    - **`/security-review` required:** Yes
    - **`/ui-qa` required:** Yes
""")

PRD_BOTH_NO = textwrap.dedent("""\
    # PRD v1
    - [D1] Implement load_ref check

    ## Performance and security budgets

    - **`/security-review` required:** No
    - **`/ui-qa` required:** No
""")

# The literal template value — unfilled. Parser should treat as unspecified.
PRD_UNFILLED_TEMPLATE = textwrap.dedent("""\
    # PRD v1
    - [D1] Implement load_ref check

    ## Performance and security budgets

    - **`/security-review` required:** Yes / No
    - **`/ui-qa` required:** Yes / No
""")


# Scope-artifact fixtures.
SECURITY_REVIEW_PASSED = textwrap.dedent("""\
    # Security review — Sprint v3

    **Sprint:** v3
    **Scope:** auth
    **Reviewer:** Jane Doe
    **Date:** 2026-04-19
    **Decision:** passed

    ## Findings

    - None identified.
""")

SECURITY_REVIEW_NA = textwrap.dedent("""\
    # Security review — Sprint v3

    **Reviewer:** Jane Doe
    **Date:** 2026-04-19
    **Decision:** n/a
""")

SECURITY_REVIEW_BLOCKED = textwrap.dedent("""\
    # Security review — Sprint v3

    **Reviewer:** Jane Doe
    **Date:** 2026-04-19
    **Decision:** blocked

    ## Findings

    - Unsuppressed semgrep `hardcoded-secret` on src/integrations/stripe.py:42.
""")

SECURITY_REVIEW_MISSING_DECISION = textwrap.dedent("""\
    # Security review — Sprint v3

    **Reviewer:** Jane Doe
    **Date:** 2026-04-19
""")

UI_QA_PASSED = textwrap.dedent("""\
    # UI QA — Sprint v3

    **Reviewer:** Jane Doe
    **Date:** 2026-04-19
    **Decision:** passed

    ## Findings

    - None identified.
""")

UI_QA_BLOCKED = textwrap.dedent("""\
    # UI QA — Sprint v3

    **Reviewer:** Jane Doe
    **Date:** 2026-04-19
    **Decision:** blocked

    ## Findings

    - Login button covers password field on mobile viewport.
""")


def _install_metrics(repo_root: Path) -> None:
    """Drop metrics/scripts/metrics.py into repo_root so find_metrics_script hits."""
    here = Path(__file__).resolve().parent
    src = here.parent.parent / "metrics" / "scripts" / "metrics.py"
    dest = repo_root / "metrics" / "scripts"
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dest / "metrics.py")


def _seed_session_event(repo_root: Path, sprint_name: str, n: int = 1) -> None:
    """Write `n` session events for `sprint_name` to docs/metrics/events.jsonl."""
    events_dir = repo_root / "docs" / "metrics"
    events_dir.mkdir(parents=True, exist_ok=True)
    with (events_dir / "events.jsonl").open("a", encoding="utf-8") as fp:
        for _ in range(n):
            fp.write(
                json.dumps({
                    "ts": "2026-04-19T00:00:00+00:00",
                    "event_type": "session",
                    "sprint": sprint_name,
                    "kind": "dev",
                }) + "\n"
            )


def _build_sprint(
    tmp: Path,
    *,
    retro: str = RETRO_FILLED,
    tasks: str = TASKS_GOOD,
    prd: str = PRD_GOOD,
    signoff: str | None = SIGNOFF_GOOD,
    code_real: bool = True,
) -> tuple[Path, Path]:
    """Create a sprint directory plus the supporting code/file layout.

    Returns (repo_root, sprint_dir).
    """
    repo_root = tmp
    sprint_dir = repo_root / "sprints" / "v3"
    sprint_dir.mkdir(parents=True)

    # Drop reconcile.py into scripts/ so sprint_close can find it.
    here = Path(__file__).resolve().parent
    src_reconcile = here.parent / "scripts" / "reconcile.py"
    (repo_root / "scripts").mkdir()
    shutil.copy(src_reconcile, repo_root / "scripts" / "reconcile.py")

    (sprint_dir / "PRD.md").write_text(prd, encoding="utf-8")
    (sprint_dir / "TASKS.md").write_text(tasks, encoding="utf-8")
    (sprint_dir / "RETRO.md").write_text(retro, encoding="utf-8")

    if signoff is not None:
        (sprint_dir / "SIGNOFF.md").write_text(signoff, encoding="utf-8")

    # Drop the file the task references; either with or without the symbols.
    (repo_root / "src").mkdir()
    if code_real:
        (repo_root / "src" / "threading.py").write_text(
            "def load_ref():\n    _routes_differ = True\n"
        )
    else:
        (repo_root / "src" / "threading.py").write_text("pass\n")

    return repo_root, sprint_dir


# ---------------------------------------------------------------------------
# Helpers tests
# ---------------------------------------------------------------------------

class HasRealContentTests(unittest.TestCase):
    def test_empty_bullets_are_not_real_content(self):
        body = "- <pattern 1>\n- <pattern 2>\n"
        self.assertFalse(sc._has_real_content(body))

    def test_blockquote_prose_is_not_real_content(self):
        body = "> Goal of this document: ...\n"
        self.assertFalse(sc._has_real_content(body))

    def test_real_paragraph_counts(self):
        body = "We shipped the SAML migration ahead of schedule.\n"
        self.assertTrue(sc._has_real_content(body))

    def test_real_bullet_with_text_counts(self):
        body = "- Pairing on the Stripe migration was faster than estimated.\n"
        self.assertTrue(sc._has_real_content(body))


class SectionBodyTests(unittest.TestCase):
    def test_extracts_section(self):
        body = sc._section_body(RETRO_FILLED, "What went well this sprint?")
        self.assertIsNotNone(body)
        self.assertIn("async webhook", body)

    def test_returns_none_when_missing(self):
        self.assertIsNone(sc._section_body(RETRO_FILLED, "Nonexistent heading"))


# ---------------------------------------------------------------------------
# Per-check tests
# ---------------------------------------------------------------------------

class RetroFilledCheckTests(unittest.TestCase):
    def test_template_stub_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            sprint = Path(tmp) / "v3"
            sprint.mkdir()
            (sprint / "RETRO.md").write_text(RETRO_TEMPLATE, encoding="utf-8")
            res = sc.check_retro_filled(sprint)
            self.assertFalse(res.passed)
            self.assertIn("template marker", res.detail)

    def test_filled_retro_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            sprint = Path(tmp) / "v3"
            sprint.mkdir()
            (sprint / "RETRO.md").write_text(RETRO_FILLED, encoding="utf-8")
            res = sc.check_retro_filled(sprint)
            self.assertTrue(res.passed)

    def test_missing_retro_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            sprint = Path(tmp) / "v3"
            sprint.mkdir()
            res = sc.check_retro_filled(sprint)
            self.assertFalse(res.passed)
            self.assertIn("missing", res.detail)


class SignoffCheckTests(unittest.TestCase):
    def test_valid_signoff_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            sprint = Path(tmp) / "v3"
            sprint.mkdir()
            (sprint / "SIGNOFF.md").write_text(SIGNOFF_GOOD, encoding="utf-8")
            res, reviewer = sc.check_signoff(sprint, reviewer_arg=None)
            self.assertTrue(res.passed)
            self.assertEqual(reviewer, "Jane Doe")

    def test_missing_signoff_fails_when_no_reviewer(self):
        with tempfile.TemporaryDirectory() as tmp:
            sprint = Path(tmp) / "v3"
            sprint.mkdir()
            res, reviewer = sc.check_signoff(sprint, reviewer_arg=None)
            self.assertFalse(res.passed)
            self.assertIsNone(reviewer)

    def test_reviewer_arg_creates_signoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            sprint = Path(tmp) / "v3"
            sprint.mkdir()
            res, reviewer = sc.check_signoff(sprint, reviewer_arg="Alex")
            self.assertTrue(res.passed)
            self.assertEqual(reviewer, "Alex")
            self.assertTrue((sprint / "SIGNOFF.md").is_file())

    def test_malformed_signoff_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            sprint = Path(tmp) / "v3"
            sprint.mkdir()
            (sprint / "SIGNOFF.md").write_text(SIGNOFF_BAD, encoding="utf-8")
            res, reviewer = sc.check_signoff(sprint, reviewer_arg=None)
            self.assertFalse(res.passed)


# ---------------------------------------------------------------------------
# Scope-artifact parsing and checks
# ---------------------------------------------------------------------------

class ParsePrdScopeFlagTests(unittest.TestCase):
    def test_yes_returns_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            prd = Path(tmp) / "PRD.md"
            prd.write_text(PRD_SECURITY_REQUIRED, encoding="utf-8")
            self.assertIs(sc._parse_prd_scope_flag(prd, "security-review"), True)
            self.assertIs(sc._parse_prd_scope_flag(prd, "ui-qa"), False)

    def test_no_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            prd = Path(tmp) / "PRD.md"
            prd.write_text(PRD_BOTH_NO, encoding="utf-8")
            self.assertIs(sc._parse_prd_scope_flag(prd, "security-review"), False)
            self.assertIs(sc._parse_prd_scope_flag(prd, "ui-qa"), False)

    def test_unfilled_template_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            prd = Path(tmp) / "PRD.md"
            prd.write_text(PRD_UNFILLED_TEMPLATE, encoding="utf-8")
            self.assertIsNone(sc._parse_prd_scope_flag(prd, "security-review"))
            self.assertIsNone(sc._parse_prd_scope_flag(prd, "ui-qa"))

    def test_missing_line_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            prd = Path(tmp) / "PRD.md"
            prd.write_text(PRD_GOOD, encoding="utf-8")
            self.assertIsNone(sc._parse_prd_scope_flag(prd, "security-review"))

    def test_missing_file_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            prd = Path(tmp) / "PRD.md"
            self.assertIsNone(sc._parse_prd_scope_flag(prd, "security-review"))


class ParseScopeArtifactTests(unittest.TestCase):
    def test_full_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "SECURITY-REVIEW.md"
            art.write_text(SECURITY_REVIEW_PASSED, encoding="utf-8")
            reviewer, date, decision = sc._parse_scope_artifact(art)
            self.assertEqual(reviewer, "Jane Doe")
            self.assertEqual(date, "2026-04-19")
            self.assertEqual(decision, "passed")

    def test_na_normalized(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "SECURITY-REVIEW.md"
            art.write_text(SECURITY_REVIEW_NA, encoding="utf-8")
            _, _, decision = sc._parse_scope_artifact(art)
            self.assertEqual(decision, "n/a")

    def test_missing_decision_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "SECURITY-REVIEW.md"
            art.write_text(SECURITY_REVIEW_MISSING_DECISION, encoding="utf-8")
            reviewer, date, decision = sc._parse_scope_artifact(art)
            self.assertEqual(reviewer, "Jane Doe")
            self.assertEqual(date, "2026-04-19")
            self.assertIsNone(decision)

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "SECURITY-REVIEW.md"
            self.assertEqual(sc._parse_scope_artifact(art), (None, None, None))


class ScopeArtifactCheckTests(unittest.TestCase):
    def _make_sprint(self, tmp: Path, prd: str) -> Path:
        sprint = tmp / "v3"
        sprint.mkdir()
        (sprint / "PRD.md").write_text(prd, encoding="utf-8")
        return sprint

    def test_flag_unspecified_passes_without_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            sprint = self._make_sprint(Path(tmp), PRD_UNFILLED_TEMPLATE)
            res = sc.check_scope_artifact(
                sprint, flag_name="security-review",
                artifact_filename="SECURITY-REVIEW.md",
                check_name="security_review",
            )
            self.assertTrue(res.passed)
            self.assertIn("unspecified", res.detail)

    def test_flag_no_passes_without_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            sprint = self._make_sprint(Path(tmp), PRD_BOTH_NO)
            res = sc.check_scope_artifact(
                sprint, flag_name="security-review",
                artifact_filename="SECURITY-REVIEW.md",
                check_name="security_review",
            )
            self.assertTrue(res.passed)

    def test_flag_yes_without_artifact_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            sprint = self._make_sprint(Path(tmp), PRD_SECURITY_REQUIRED)
            res = sc.check_scope_artifact(
                sprint, flag_name="security-review",
                artifact_filename="SECURITY-REVIEW.md",
                check_name="security_review",
            )
            self.assertFalse(res.passed)
            self.assertIn("SECURITY-REVIEW.md is missing", res.detail)

    def test_flag_yes_with_passed_artifact_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            sprint = self._make_sprint(Path(tmp), PRD_SECURITY_REQUIRED)
            (sprint / "SECURITY-REVIEW.md").write_text(SECURITY_REVIEW_PASSED, encoding="utf-8")
            res = sc.check_scope_artifact(
                sprint, flag_name="security-review",
                artifact_filename="SECURITY-REVIEW.md",
                check_name="security_review",
            )
            self.assertTrue(res.passed)
            self.assertIn("passed", res.detail)

    def test_flag_yes_with_na_artifact_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            sprint = self._make_sprint(Path(tmp), PRD_SECURITY_REQUIRED)
            (sprint / "SECURITY-REVIEW.md").write_text(SECURITY_REVIEW_NA, encoding="utf-8")
            res = sc.check_scope_artifact(
                sprint, flag_name="security-review",
                artifact_filename="SECURITY-REVIEW.md",
                check_name="security_review",
            )
            self.assertTrue(res.passed)
            self.assertIn("n/a", res.detail)

    def test_flag_yes_with_blocked_artifact_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            sprint = self._make_sprint(Path(tmp), PRD_SECURITY_REQUIRED)
            (sprint / "SECURITY-REVIEW.md").write_text(SECURITY_REVIEW_BLOCKED, encoding="utf-8")
            res = sc.check_scope_artifact(
                sprint, flag_name="security-review",
                artifact_filename="SECURITY-REVIEW.md",
                check_name="security_review",
            )
            self.assertFalse(res.passed)
            self.assertIn("blocked", res.detail)

    def test_flag_yes_with_missing_decision_field_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            sprint = self._make_sprint(Path(tmp), PRD_SECURITY_REQUIRED)
            (sprint / "SECURITY-REVIEW.md").write_text(
                SECURITY_REVIEW_MISSING_DECISION, encoding="utf-8"
            )
            res = sc.check_scope_artifact(
                sprint, flag_name="security-review",
                artifact_filename="SECURITY-REVIEW.md",
                check_name="security_review",
            )
            self.assertFalse(res.passed)
            self.assertIn("Decision", res.detail)


# ---------------------------------------------------------------------------
# End-to-end orchestration
# ---------------------------------------------------------------------------

class RunCloseTests(unittest.TestCase):
    def test_happy_path_writes_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp))
            report = sc.run_close(
                sprint_dir=sprint, repo_root=repo,
                reviewer_arg=None, strict_symbols=False, dry_run=False,
            )
            self.assertTrue(report.locked, msg=[c for c in report.checks if not c.passed])
            self.assertEqual(report.reviewer, "Jane Doe")
            self.assertTrue((sprint / ".lock").is_file())
            content = (sprint / ".lock").read_text()
            self.assertIn("locked_at:", content)
            self.assertIn("reviewer: Jane Doe", content)

    def test_dry_run_does_not_write_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp))
            report = sc.run_close(
                sprint_dir=sprint, repo_root=repo,
                reviewer_arg=None, strict_symbols=False, dry_run=True,
            )
            self.assertFalse(report.locked)
            self.assertFalse((sprint / ".lock").exists())
            self.assertTrue(all(c.passed for c in report.checks))

    def test_unfilled_retro_blocks_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp), retro=RETRO_TEMPLATE)
            report = sc.run_close(
                sprint_dir=sprint, repo_root=repo,
                reviewer_arg=None, strict_symbols=False, dry_run=False,
            )
            self.assertFalse(report.locked)
            self.assertFalse((sprint / ".lock").exists())
            failing = {c.name for c in report.checks if not c.passed}
            self.assertIn("retro_filled", failing)

    def test_missing_signoff_blocks_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp), signoff=None)
            report = sc.run_close(
                sprint_dir=sprint, repo_root=repo,
                reviewer_arg=None, strict_symbols=False, dry_run=False,
            )
            self.assertFalse(report.locked)
            failing = {c.name for c in report.checks if not c.passed}
            self.assertIn("signoff", failing)

    def test_reviewer_arg_satisfies_signoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp), signoff=None)
            report = sc.run_close(
                sprint_dir=sprint, repo_root=repo,
                reviewer_arg="Alex", strict_symbols=False, dry_run=False,
            )
            self.assertTrue(report.locked, msg=[c for c in report.checks if not c.passed])
            self.assertEqual(report.reviewer, "Alex")
            self.assertTrue((sprint / "SIGNOFF.md").is_file())

    def test_strict_symbols_blocks_on_stub(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp), code_real=False)
            report = sc.run_close(
                sprint_dir=sprint, repo_root=repo,
                reviewer_arg=None, strict_symbols=True, dry_run=False,
            )
            self.assertFalse(report.locked)
            failing = {c.name for c in report.checks if not c.passed}
            self.assertIn("reconcile", failing)

    def test_metrics_not_installed_does_not_block(self):
        # Existing installs without the metrics module must keep working —
        # minimum-viable adoption is CLAUDE.md + stable IDs + reconcile.py.
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp))
            report = sc.run_close(
                sprint_dir=sprint, repo_root=repo,
                reviewer_arg=None, strict_symbols=False, dry_run=False,
            )
            self.assertTrue(report.locked, msg=[c for c in report.checks if not c.passed])
            sessions = next(c for c in report.checks if c.name == "sessions_logged")
            self.assertTrue(sessions.passed)
            self.assertIn("metrics/ not installed", sessions.detail)

    def test_metrics_installed_zero_sessions_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp))
            _install_metrics(repo)
            report = sc.run_close(
                sprint_dir=sprint, repo_root=repo,
                reviewer_arg=None, strict_symbols=False, dry_run=False,
            )
            self.assertFalse(report.locked)
            self.assertFalse((sprint / ".lock").exists())
            failing = {c.name for c in report.checks if not c.passed}
            self.assertIn("sessions_logged", failing)
            sessions = next(c for c in report.checks if c.name == "sessions_logged")
            self.assertIn("no session events logged for v3", sessions.detail)

    def test_metrics_installed_with_session_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp))
            _install_metrics(repo)
            _seed_session_event(repo, "v3", n=2)
            report = sc.run_close(
                sprint_dir=sprint, repo_root=repo,
                reviewer_arg=None, strict_symbols=False, dry_run=False,
            )
            self.assertTrue(report.locked, msg=[c for c in report.checks if not c.passed])
            sessions = next(c for c in report.checks if c.name == "sessions_logged")
            self.assertIn("2 session event(s) logged for v3", sessions.detail)

    def test_session_events_for_other_sprint_do_not_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp))
            _install_metrics(repo)
            _seed_session_event(repo, "v2", n=5)  # wrong sprint
            report = sc.run_close(
                sprint_dir=sprint, repo_root=repo,
                reviewer_arg=None, strict_symbols=False, dry_run=False,
            )
            self.assertFalse(report.locked)
            sessions = next(c for c in report.checks if c.name == "sessions_logged")
            self.assertFalse(sessions.passed)

    def test_scope_flag_yes_blocks_close_without_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp), prd=PRD_SECURITY_REQUIRED)
            report = sc.run_close(
                sprint_dir=sprint, repo_root=repo,
                reviewer_arg=None, strict_symbols=False, dry_run=False,
            )
            self.assertFalse(report.locked)
            self.assertFalse((sprint / ".lock").exists())
            failing = {c.name for c in report.checks if not c.passed}
            self.assertIn("security_review", failing)

    def test_scope_flag_yes_with_passed_artifact_locks(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp), prd=PRD_SECURITY_REQUIRED)
            (sprint / "SECURITY-REVIEW.md").write_text(
                SECURITY_REVIEW_PASSED, encoding="utf-8"
            )
            report = sc.run_close(
                sprint_dir=sprint, repo_root=repo,
                reviewer_arg=None, strict_symbols=False, dry_run=False,
            )
            self.assertTrue(
                report.locked,
                msg=[c for c in report.checks if not c.passed],
            )

    def test_scope_flag_yes_with_blocked_artifact_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp), prd=PRD_SECURITY_REQUIRED)
            (sprint / "SECURITY-REVIEW.md").write_text(
                SECURITY_REVIEW_BLOCKED, encoding="utf-8"
            )
            report = sc.run_close(
                sprint_dir=sprint, repo_root=repo,
                reviewer_arg=None, strict_symbols=False, dry_run=False,
            )
            self.assertFalse(report.locked)
            failing = {c.name for c in report.checks if not c.passed}
            self.assertIn("security_review", failing)

    def test_ui_qa_flag_yes_blocks_without_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp), prd=PRD_UI_REQUIRED)
            report = sc.run_close(
                sprint_dir=sprint, repo_root=repo,
                reviewer_arg=None, strict_symbols=False, dry_run=False,
            )
            self.assertFalse(report.locked)
            failing = {c.name for c in report.checks if not c.passed}
            self.assertIn("ui_qa", failing)

    def test_ui_qa_flag_yes_with_blocked_artifact_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp), prd=PRD_UI_REQUIRED)
            (sprint / "UI-QA.md").write_text(UI_QA_BLOCKED, encoding="utf-8")
            report = sc.run_close(
                sprint_dir=sprint, repo_root=repo,
                reviewer_arg=None, strict_symbols=False, dry_run=False,
            )
            self.assertFalse(report.locked)
            failing = {c.name for c in report.checks if not c.passed}
            self.assertIn("ui_qa", failing)

    def test_both_scopes_required_both_artifacts_needed(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp), prd=PRD_BOTH_REQUIRED)
            # Only security artifact — UI QA still missing.
            (sprint / "SECURITY-REVIEW.md").write_text(
                SECURITY_REVIEW_PASSED, encoding="utf-8"
            )
            report = sc.run_close(
                sprint_dir=sprint, repo_root=repo,
                reviewer_arg=None, strict_symbols=False, dry_run=False,
            )
            self.assertFalse(report.locked)
            failing = {c.name for c in report.checks if not c.passed}
            self.assertIn("ui_qa", failing)
            self.assertNotIn("security_review", failing)

    def test_both_scopes_required_both_passed_locks(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp), prd=PRD_BOTH_REQUIRED)
            (sprint / "SECURITY-REVIEW.md").write_text(
                SECURITY_REVIEW_PASSED, encoding="utf-8"
            )
            (sprint / "UI-QA.md").write_text(UI_QA_PASSED, encoding="utf-8")
            report = sc.run_close(
                sprint_dir=sprint, repo_root=repo,
                reviewer_arg=None, strict_symbols=False, dry_run=False,
            )
            self.assertTrue(
                report.locked,
                msg=[c for c in report.checks if not c.passed],
            )

    def test_scope_flag_unfilled_template_does_not_block(self):
        # The PRD template literally reads "Yes / No" until filled in.
        # That state is "unspecified" — do not refuse to lock on a missing
        # artifact, since minimum-viable adoption uses the template verbatim.
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp), prd=PRD_UNFILLED_TEMPLATE)
            report = sc.run_close(
                sprint_dir=sprint, repo_root=repo,
                reviewer_arg=None, strict_symbols=False, dry_run=False,
            )
            self.assertTrue(
                report.locked,
                msg=[c for c in report.checks if not c.passed],
            )

    def test_already_locked_short_circuits(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp))
            (sprint / ".lock").write_text("locked_at: earlier\n")
            report = sc.run_close(
                sprint_dir=sprint, repo_root=repo,
                reviewer_arg=None, strict_symbols=False, dry_run=False,
            )
            self.assertFalse(report.locked)
            failing = {c.name for c in report.checks if not c.passed}
            self.assertIn("not_already_locked", failing)
            # Reconcile and downstream checks should not have run.
            self.assertEqual(
                {c.name for c in report.checks},
                {"sprint_layout", "not_already_locked"},
            )


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------

class CLITests(unittest.TestCase):
    def test_cli_happy_path_exit_zero(self):
        script = Path(__file__).resolve().parent.parent / "scripts" / "sprint_close.py"
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp))
            res = subprocess.run(
                [sys.executable, str(script), str(sprint), "--repo-root", str(repo)],
                capture_output=True, text=True,
            )
            self.assertEqual(res.returncode, 0, msg=res.stdout + res.stderr)
            self.assertTrue((sprint / ".lock").is_file())

    def test_cli_failure_exit_one(self):
        script = Path(__file__).resolve().parent.parent / "scripts" / "sprint_close.py"
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp), retro=RETRO_TEMPLATE)
            res = subprocess.run(
                [sys.executable, str(script), str(sprint), "--repo-root", str(repo)],
                capture_output=True, text=True,
            )
            self.assertEqual(res.returncode, 1)
            self.assertFalse((sprint / ".lock").exists())

    def test_cli_json_output(self):
        script = Path(__file__).resolve().parent.parent / "scripts" / "sprint_close.py"
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp))
            res = subprocess.run(
                [sys.executable, str(script), str(sprint),
                 "--repo-root", str(repo), "--json"],
                capture_output=True, text=True,
            )
            self.assertEqual(res.returncode, 0, msg=res.stdout + res.stderr)
            payload = json.loads(res.stdout)
            self.assertTrue(payload["locked"])
            self.assertEqual(payload["reviewer"], "Jane Doe")


GAP_ANALYSIS_CLEAN = """\
# Gap analysis — AUTH

**Initiative requirements:** 3  | covered: 3 | deferred: 0 | orphaned: 0 | conflicted: 0

## Covered

- **§1.1** — v3/T001 (complete)

## Deferred (with target)

- None.

## Orphaned

- None identified. Every initiative requirement has either an active task or a `[DEFERRED]` entry with a target.

## Conflicted

- None.
"""


GAP_ANALYSIS_WITH_ORPHANS = """\
# Gap analysis — AUTH

**Initiative requirements:** 3  | covered: 1 | deferred: 0 | orphaned: 2 | conflicted: 0

## Covered

- **§1.1** — v3/T001 (complete)

## Orphaned

> Each entry below is a requirement in the design document that no sprint has picked up.

- **§1.2**
- **§1.3**

## Conflicted

- None.
"""


class GapOrphansCheckTests(unittest.TestCase):
    def _write_analysis(self, repo: Path, name: str, body: str) -> Path:
        (repo / "docs").mkdir(exist_ok=True)
        analysis = repo / "docs" / name
        analysis.write_text(body, encoding="utf-8")
        return analysis

    def test_no_docs_dir_is_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = sc.check_gap_orphans(Path(tmp))
            self.assertTrue(result.passed)
            self.assertIn("no docs/", result.detail)

    def test_no_analyses_is_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "docs").mkdir()
            result = sc.check_gap_orphans(Path(tmp))
            self.assertTrue(result.passed)
            self.assertIn("no *_GAP_ANALYSIS.md", result.detail)

    def test_clean_analysis_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._write_analysis(repo, "AUTH_GAP_ANALYSIS.md", GAP_ANALYSIS_CLEAN)
            result = sc.check_gap_orphans(repo)
            self.assertTrue(result.passed, result.detail)

    def test_orphan_analysis_fails_and_names_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._write_analysis(
                repo, "AUTH_GAP_ANALYSIS.md", GAP_ANALYSIS_WITH_ORPHANS
            )
            result = sc.check_gap_orphans(repo)
            self.assertFalse(result.passed)
            self.assertIn("§1.2", result.detail)
            self.assertIn("§1.3", result.detail)
            self.assertIn("AUTH_GAP_ANALYSIS.md", result.detail)

    def test_multiple_analyses_any_orphan_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._write_analysis(repo, "AUTH_GAP_ANALYSIS.md", GAP_ANALYSIS_CLEAN)
            self._write_analysis(
                repo, "BILLING_GAP_ANALYSIS.md", GAP_ANALYSIS_WITH_ORPHANS
            )
            result = sc.check_gap_orphans(repo)
            self.assertFalse(result.passed)
            self.assertIn("BILLING_GAP_ANALYSIS.md", result.detail)


class RunCloseGapIntegrationTests(unittest.TestCase):
    def test_gap_orphan_blocks_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp))
            (repo / "docs").mkdir()
            (repo / "docs" / "AUTH_GAP_ANALYSIS.md").write_text(
                GAP_ANALYSIS_WITH_ORPHANS, encoding="utf-8"
            )
            report = sc.run_close(
                sprint_dir=sprint, repo_root=repo,
                reviewer_arg=None, strict_symbols=False, dry_run=False,
            )
            self.assertFalse(report.locked)
            failing = {c.name for c in report.checks if not c.passed}
            self.assertIn("gap_orphans", failing)
            self.assertFalse((sprint / ".lock").exists())

    def test_clean_gap_analysis_allows_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp))
            (repo / "docs").mkdir()
            (repo / "docs" / "AUTH_GAP_ANALYSIS.md").write_text(
                GAP_ANALYSIS_CLEAN, encoding="utf-8"
            )
            report = sc.run_close(
                sprint_dir=sprint, repo_root=repo,
                reviewer_arg=None, strict_symbols=False, dry_run=False,
            )
            self.assertTrue(report.locked, msg=[c for c in report.checks if not c.passed])

    def test_missing_gap_analysis_does_not_block(self):
        # Absent analyses must not block lock (warn-only; state-check surfaces
        # the absence as P1).
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint = _build_sprint(Path(tmp))
            report = sc.run_close(
                sprint_dir=sprint, repo_root=repo,
                reviewer_arg=None, strict_symbols=False, dry_run=False,
            )
            self.assertTrue(report.locked, msg=[c for c in report.checks if not c.passed])


if __name__ == "__main__":
    unittest.main()
