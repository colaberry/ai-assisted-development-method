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


if __name__ == "__main__":
    unittest.main()
