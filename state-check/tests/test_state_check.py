"""Self-tests for state-check.py.

Exercises each code path added or refactored for issue #1:
  - is_test_file (path-component match, no substring false positives)
  - find_active_initiative (tuple return)
  - check_multiple_initiatives (ambiguity warning)
  - check_claude_md_placeholders (P0 on unfilled <BRACKETED> markers)
  - check_failures_log_size (counts active rules, not files)
  - find_latest_lock_commit / git_recent_test_modifications (graceful no-git)

Run with:  python -m unittest state-check/tests/test_state_check.py
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


def _load_state_check():
    """Load state-check.py despite the hyphen in its filename.

    The module must be registered in sys.modules *before* exec_module so that
    dataclass annotation resolution can find it (required on Python 3.8).
    """
    here = Path(__file__).resolve().parent
    script = here.parent / "scripts" / "state-check.py"
    spec = importlib.util.spec_from_file_location("state_check", script)
    module = importlib.util.module_from_spec(spec)
    sys.modules["state_check"] = module
    spec.loader.exec_module(module)
    return module


sc = _load_state_check()


class IsTestFileTests(unittest.TestCase):
    def test_path_components_match(self):
        for path in [
            "tests/foo.py",
            "src/__tests__/Component.test.tsx",
            "spec/widget_spec.rb",
            "app/test/whatever.go",
        ]:
            self.assertTrue(sc.is_test_file(path), path)

    def test_filename_patterns_match(self):
        for path in [
            "src/foo_test.py",
            "src/test_foo.py",
            "src/Foo.test.ts",
            "src/Foo.spec.tsx",
        ]:
            self.assertTrue(sc.is_test_file(path), path)

    def test_substring_false_positives_rejected(self):
        for path in [
            "docs/latest.md",
            "src/contest_routes.py",
            "src/spectrum.py",
            "lib/protest.go",
        ]:
            self.assertFalse(sc.is_test_file(path), path)


class FindActiveInitiativeTests(unittest.TestCase):
    def test_returns_tuple_no_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            active, candidates = sc.find_active_initiative(Path(tmp))
            self.assertIsNone(active)
            self.assertEqual(candidates, [])

    def test_picks_latest_and_returns_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / "docs"
            docs.mkdir()
            (docs / "alpha.md").write_text("a", encoding="utf-8")
            beta = docs / "beta.md"
            beta.write_text("b", encoding="utf-8")
            # Bump beta's mtime slightly
            import os, time
            future = time.time() + 60
            os.utime(beta, (future, future))
            active, candidates = sc.find_active_initiative(Path(tmp))
            self.assertEqual(active, "beta")
            self.assertEqual(len(candidates), 2)


class MultipleInitiativesTests(unittest.TestCase):
    def test_no_warning_on_single(self):
        self.assertIsNone(sc.check_multiple_initiatives([Path("docs/only.md")]))

    def test_warning_on_multiple(self):
        flag = sc.check_multiple_initiatives(
            [Path("docs/alpha.md"), Path("docs/beta.md")]
        )
        self.assertIsNotNone(flag)
        self.assertEqual(flag.severity, "P1")
        self.assertIn("alpha", flag.message)
        self.assertIn("beta", flag.message)


class ClaudeMdPlaceholderTests(unittest.TestCase):
    def test_no_file_no_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(sc.check_claude_md_placeholders(Path(tmp)))

    def test_clean_file_no_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "CLAUDE.md").write_text(
                "# Project\nSome real content here.\n", encoding="utf-8"
            )
            self.assertIsNone(sc.check_claude_md_placeholders(Path(tmp)))

    def test_placeholders_flagged_p0(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "CLAUDE.md").write_text(
                "Project: <PROJECT_NAME>\nClient: <CLIENT NAME>\n",
                encoding="utf-8",
            )
            flag = sc.check_claude_md_placeholders(Path(tmp))
            self.assertIsNotNone(flag)
            self.assertEqual(flag.severity, "P0")
            self.assertIn("PROJECT_NAME", flag.message)

    def test_short_brackets_ignored(self):
        # <A> and <B> shouldn't trigger — they're below the length threshold.
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "CLAUDE.md").write_text(
                "Use <A> and <B> in formulas.", encoding="utf-8"
            )
            self.assertIsNone(sc.check_claude_md_placeholders(Path(tmp)))


class FailuresLogTests(unittest.TestCase):
    def _make_entry(self, dir: Path, name: str, status: str | None) -> None:
        body = f"# {name}\n\n"
        if status is not None:
            body += f"Status: {status}\n"
        body += "Body text.\n"
        (dir / f"{name}.md").write_text(body, encoding="utf-8")

    def test_no_dir_no_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(sc.check_failures_log_size(Path(tmp)))

    def test_retired_entries_dont_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "docs" / "failures"
            d.mkdir(parents=True)
            for i in range(60):
                self._make_entry(d, f"rule-{i:03d}", "Retired")
            for i in range(5):
                self._make_entry(d, f"active-{i:03d}", "Active prevention rule")
            # 60 retired + 5 active = 65 files but only 5 active → no flag
            self.assertIsNone(sc.check_failures_log_size(Path(tmp)))

    def test_active_threshold_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "docs" / "failures"
            d.mkdir(parents=True)
            for i in range(55):
                self._make_entry(d, f"rule-{i:03d}", "Active prevention rule")
            flag = sc.check_failures_log_size(Path(tmp))
            self.assertIsNotNone(flag)
            self.assertEqual(flag.severity, "P2")
            self.assertIn("55", flag.message)

    def test_unannotated_counted_as_active_and_called_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "docs" / "failures"
            d.mkdir(parents=True)
            for i in range(51):
                self._make_entry(d, f"rule-{i:03d}", None)
            flag = sc.check_failures_log_size(Path(tmp))
            self.assertIsNotNone(flag)
            self.assertIn("lack a Status:", flag.message)


class GitGracefulFallbackTests(unittest.TestCase):
    """find_latest_lock_commit and git_recent_test_modifications must not
    raise on non-git directories."""

    def test_non_git_returns_none_and_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(sc.find_latest_lock_commit(Path(tmp)))
            self.assertEqual(sc.git_recent_test_modifications(Path(tmp)), [])


class SecuritySuppressionsStalenessTests(unittest.TestCase):
    import datetime as _dt

    def _write(self, tmp: str, entries_md: str) -> Path:
        supp = Path(tmp) / "docs" / "security"
        supp.mkdir(parents=True)
        (supp / "suppressions.md").write_text(
            "# Security Suppressions\n\n" + entries_md, encoding="utf-8"
        )
        return Path(tmp)

    def test_no_file_no_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(sc.check_security_suppressions_staleness(Path(tmp)))

    def test_fresh_entry_no_flag(self):
        today = self._dt.date(2026, 4, 18)
        body = (
            "### S001: fresh\n\n"
            "- **Re-reviewed:** 2026-04-01 by @alice\n"
            "- **Justification:** test\n\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._write(tmp, body)
            self.assertIsNone(
                sc.check_security_suppressions_staleness(repo, today=today)
            )

    def test_stale_entry_flagged(self):
        today = self._dt.date(2026, 4, 18)
        body = (
            "### S001: ancient\n\n"
            "- **Re-reviewed:** 2025-10-01 by @alice\n"  # >90 days
            "- **Justification:** test\n\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._write(tmp, body)
            flag = sc.check_security_suppressions_staleness(repo, today=today)
            self.assertIsNotNone(flag)
            self.assertEqual(flag.severity, "P2")
            self.assertIn("S001", flag.message)

    def test_missing_date_flagged(self):
        body = (
            "### S002: no-date\n\n"
            "- **Justification:** someone forgot to add the Re-reviewed line\n\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._write(tmp, body)
            flag = sc.check_security_suppressions_staleness(repo)
            self.assertIsNotNone(flag)
            self.assertIn("S002", flag.message)

    def test_removed_entry_ignored(self):
        today = self._dt.date(2026, 4, 18)
        body = (
            "### S003: historical\n\n"
            "- **Re-reviewed:** 2024-01-01 by @alice\n"  # very old
            "- **Removed:** 2025-06-01 by @bob — fixed in #42\n\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._write(tmp, body)
            self.assertIsNone(
                sc.check_security_suppressions_staleness(repo, today=today)
            )

    def test_mixed_entries(self):
        today = self._dt.date(2026, 4, 18)
        body = (
            "### S001: stale\n\n"
            "- **Re-reviewed:** 2025-01-01 by @alice\n\n"
            "### S002: fresh\n\n"
            "- **Re-reviewed:** 2026-04-10 by @bob\n\n"
            "### S003: no-date\n\n"
            "- **Justification:** oops\n\n"
            "### S004: removed\n\n"
            "- **Re-reviewed:** 2024-01-01 by @bob\n"
            "- **Removed:** 2025-06-01\n\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._write(tmp, body)
            flag = sc.check_security_suppressions_staleness(repo, today=today)
            self.assertIsNotNone(flag)
            self.assertIn("S001", flag.message)
            self.assertIn("S003", flag.message)
            # Fresh and removed entries should NOT appear
            self.assertNotIn("S002", flag.message)
            self.assertNotIn("S004", flag.message)


class IncidentIsOpenTests(unittest.TestCase):
    def test_bold_resolved_with_real_date_is_closed(self):
        self.assertFalse(sc._incident_is_open("**Resolved:** 2026-04-18 14:32 PST"))

    def test_plain_resolved_with_date_is_closed(self):
        self.assertFalse(sc._incident_is_open("Resolved: 2026-04-18"))

    def test_empty_resolved_field_is_open(self):
        self.assertTrue(sc._incident_is_open("**Resolved:**\n"))

    def test_template_placeholder_is_open(self):
        self.assertTrue(sc._incident_is_open("**Resolved:** <YYYY-MM-DD HH:MM timezone>"))

    def test_bare_yyyy_mm_dd_token_is_open(self):
        self.assertTrue(sc._incident_is_open("**Resolved:** YYYY-MM-DD"))

    def test_missing_resolved_line_is_open(self):
        self.assertTrue(sc._incident_is_open("Some post-mortem with no Resolved field at all"))

    def test_multiple_resolved_lines_any_real_date_closes(self):
        body = (
            "**Resolved:** YYYY-MM-DD\n"
            "...\n"
            "**Resolved:** 2026-04-18 15:00 UTC\n"
        )
        self.assertFalse(sc._incident_is_open(body))


class CheckOpenIncidentsTests(unittest.TestCase):
    def _write_incident(self, repo: Path, name: str, body: str) -> None:
        incidents = repo / "docs" / "incidents"
        incidents.mkdir(parents=True, exist_ok=True)
        (incidents / name).write_text(body, encoding="utf-8")

    def test_no_directory_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(sc.check_open_incidents(Path(tmp)))

    def test_no_incidents_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "docs" / "incidents").mkdir(parents=True)
            self.assertIsNone(sc.check_open_incidents(repo))

    def test_all_resolved_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._write_incident(
                repo, "2026-04-10-auth.md", "**Resolved:** 2026-04-10 12:00 UTC\n"
            )
            self._write_incident(
                repo, "2026-04-12-payments.md", "Resolved: 2026-04-12 16:00 UTC\n"
            )
            self.assertIsNone(sc.check_open_incidents(repo))

    def test_open_incident_flagged_p1(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._write_incident(
                repo, "2026-04-15-webhook.md", "**Resolved:**\n"
            )
            flag = sc.check_open_incidents(repo)
            self.assertIsNotNone(flag)
            self.assertEqual(flag.severity, "P1")
            self.assertEqual(flag.category, "learning-loop")
            self.assertIn("2026-04-15-webhook.md", flag.message)

    def test_template_and_readme_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._write_incident(repo, "TEMPLATE.md", "**Resolved:** <YYYY-MM-DD>\n")
            self._write_incident(repo, "README.md", "header")
            self.assertIsNone(sc.check_open_incidents(repo))

    def test_multiple_open_incidents_truncated_in_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            for slug in ("a", "b", "c", "d", "e"):
                self._write_incident(
                    repo, f"2026-04-0{ord(slug)-96}-{slug}.md", "**Resolved:**\n"
                )
            flag = sc.check_open_incidents(repo)
            self.assertIsNotNone(flag)
            self.assertIn("(+2 more)", flag.message)

    def test_template_placeholder_treated_as_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._write_incident(
                repo, "2026-04-15-fresh.md",
                "**Resolved:** <YYYY-MM-DD HH:MM timezone>\n"
            )
            flag = sc.check_open_incidents(repo)
            self.assertIsNotNone(flag)
            self.assertIn("2026-04-15-fresh.md", flag.message)


if __name__ == "__main__":
    unittest.main()
