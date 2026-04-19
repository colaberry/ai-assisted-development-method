"""Self-tests for reconcile.py.

Covers the symbol-presence upgrade in particular — the existing parser and
coverage logic also have spot-checks so future edits don't regress them.

Run with:  python3 tooling/tests/test_reconcile.py
"""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


def _load_reconcile():
    here = Path(__file__).resolve().parent
    script = here.parent / "scripts" / "reconcile.py"
    spec = importlib.util.spec_from_file_location("reconcile", script)
    module = importlib.util.module_from_spec(spec)
    sys.modules["reconcile"] = module
    spec.loader.exec_module(module)
    return module


r = _load_reconcile()


def _make_sprint(tmp: Path, prd: str, tasks: str) -> Path:
    sprint = tmp / "sprints" / "v1"
    sprint.mkdir(parents=True)
    (sprint / "PRD.md").write_text(prd, encoding="utf-8")
    (sprint / "TASKS.md").write_text(tasks, encoding="utf-8")
    return sprint


class IdentifierHeuristicTests(unittest.TestCase):
    def test_snake_case_identifier(self):
        self.assertTrue(r._looks_like_identifier("_routes_differ"))
        self.assertTrue(r._looks_like_identifier("load_ref"))

    def test_camel_and_pascal_case(self):
        self.assertTrue(r._looks_like_identifier("loadRef"))
        self.assertTrue(r._looks_like_identifier("RouteHandler"))

    def test_all_caps_constant(self):
        self.assertTrue(r._looks_like_identifier("HTTP"))
        self.assertTrue(r._looks_like_identifier("MAX_RETRIES"))

    def test_plain_english_is_excluded(self):
        self.assertFalse(r._looks_like_identifier("when"))
        self.assertFalse(r._looks_like_identifier("matches"))
        self.assertFalse(r._looks_like_identifier("routes"))  # plural English

    def test_too_short_is_excluded(self):
        self.assertFalse(r._looks_like_identifier("ab"))
        self.assertFalse(r._looks_like_identifier("x_"))


class ExtractCandidateSymbolsTests(unittest.TestCase):
    def _task(self, title="", acceptance=None) -> "r.Task":
        return r.Task(id="T001", title=title, status="complete",
                      line_number=1, acceptance=acceptance)

    def test_backticked_tokens_kept_verbatim(self):
        t = self._task(
            title="Wire `_routes_differ` into Check 1.7 load_ref path",
        )
        syms = r.extract_candidate_symbols(t)
        self.assertIn("_routes_differ", syms)
        self.assertIn("load_ref", syms)  # bare snake_case picked up too

    def test_acceptance_text_is_scanned(self):
        t = self._task(
            title="Add field",
            acceptance="When `loadRef` matches, set `routes_differ` to True.",
        )
        syms = r.extract_candidate_symbols(t)
        self.assertIn("loadRef", syms)
        self.assertIn("routes_differ", syms)

    def test_pure_english_returns_nothing(self):
        t = self._task(
            title="Improve docs",
            acceptance="When the docs are clearer, the team is happier.",
        )
        self.assertEqual(r.extract_candidate_symbols(t), [])

    def test_dedup_preserves_order(self):
        t = self._task(
            title="`load_ref` then `load_ref` again with load_ref",
        )
        syms = r.extract_candidate_symbols(t)
        self.assertEqual(syms, ["load_ref"])


class FindSymbolsInFilesTests(unittest.TestCase):
    def test_returns_matched_subset(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "src").mkdir()
            (repo / "src" / "a.py").write_text("def load_ref(): pass\n")
            self.assertEqual(
                r.find_symbols_in_files(
                    ["load_ref", "missing_thing"], ["src/a.py"], repo
                ),
                ["load_ref"],
            )

    def test_no_files_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                r.find_symbols_in_files(["load_ref"], [], Path(tmp)), []
            )

    def test_no_symbols_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                r.find_symbols_in_files([], ["src/a.py"], Path(tmp)), []
            )

    def test_unreadable_file_skipped_not_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            # File listed but doesn't exist on disk → existing_files would
            # have filtered it out, but verify the OSError path explicitly.
            self.assertEqual(
                r.find_symbols_in_files(
                    ["load_ref"], ["nope/missing.py"], repo
                ),
                [],
            )


PRD_FIXTURE = """\
# PRD v1

- [D1] Implement load_ref check
- [D2] Add routes-differ flag
- [D3] Out-of-scope (deferred)
"""

TASKS_REAL_IMPL = """\
- [x] T001: Wire `_routes_differ` into Check 1.7 `load_ref` path
  - Satisfies: D1, D2
  - Acceptance: When `load_ref` matches, set `_routes_differ` accordingly.
  - Files: src/threading.py
- [DEFERRED] T002: Out of scope
  - Satisfies: D3
  - Status: DEFERRED
  - Target: v2
"""

TASKS_STUB_IMPL = """\
- [x] T001: Wire `_routes_differ` into Check 1.7 `load_ref` path
  - Satisfies: D1, D2
  - Acceptance: When `load_ref` matches, set `_routes_differ` accordingly.
  - Files: src/threading.py
- [DEFERRED] T002: Out of scope
  - Satisfies: D3
  - Status: DEFERRED
  - Target: v2
"""


class SymbolPresenceCoverageTests(unittest.TestCase):
    def test_real_implementation_is_high_confidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            sprint = _make_sprint(repo, PRD_FIXTURE, TASKS_REAL_IMPL)
            (repo / "src").mkdir()
            (repo / "src" / "threading.py").write_text(
                "def load_ref():\n    _routes_differ = True\n"
            )
            reqs = r.parse_prd(sprint / "PRD.md")
            tasks = r.parse_tasks(sprint / "TASKS.md")
            entries = r.build_coverage(reqs, tasks, repo)
            covered = [e for e in entries if e.status == "covered"]
            self.assertEqual(len(covered), 2)
            for e in covered:
                self.assertEqual(e.confidence, "high")
                self.assertIn("_routes_differ", e.matched_symbols)

    def test_empty_stub_is_demoted_to_medium_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            sprint = _make_sprint(repo, PRD_FIXTURE, TASKS_STUB_IMPL)
            # File exists but contains nothing matching — the stub case.
            (repo / "src").mkdir()
            (repo / "src" / "threading.py").write_text(
                "# TODO: implement\npass\n"
            )
            reqs = r.parse_prd(sprint / "PRD.md")
            tasks = r.parse_tasks(sprint / "TASKS.md")
            entries = r.build_coverage(reqs, tasks, repo)
            covered = [e for e in entries if e.status == "covered"]
            self.assertEqual(len(covered), 2)
            for e in covered:
                self.assertEqual(e.confidence, "medium")
                self.assertIn("STUB-WARNING", e.notes)
                self.assertEqual(e.matched_symbols, [])
                self.assertGreater(len(e.candidate_symbols), 0)

    def test_strict_symbols_promotes_stub_to_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            sprint = _make_sprint(repo, PRD_FIXTURE, TASKS_STUB_IMPL)
            (repo / "src").mkdir()
            (repo / "src" / "threading.py").write_text("pass\n")
            reqs = r.parse_prd(sprint / "PRD.md")
            tasks = r.parse_tasks(sprint / "TASKS.md")
            entries = r.build_coverage(
                reqs, tasks, repo, strict_symbols=True
            )
            statuses = {e.requirement_id: e.status for e in entries}
            # D1 and D2 share the same stub task → both flip to missing.
            self.assertEqual(statuses["D1"], "missing")
            self.assertEqual(statuses["D2"], "missing")
            self.assertEqual(statuses["D3"], "deferred")

    def test_no_extractable_symbols_does_not_punish(self):
        # Task title and acceptance both vague-English. Should still be
        # high-confidence covered if files exist (the heuristic must not
        # downgrade things it can't analyze).
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            tasks_md = """\
- [x] T001: improve docs
  - Satisfies: D1
  - Acceptance: when the docs are clearer the team is happier
  - Files: docs/readme.md
"""
            prd_md = "- [D1] Improve docs\n"
            sprint = _make_sprint(repo, prd_md, tasks_md)
            (repo / "docs").mkdir()
            (repo / "docs" / "readme.md").write_text("# README\n")
            reqs = r.parse_prd(sprint / "PRD.md")
            tasks = r.parse_tasks(sprint / "TASKS.md")
            entries = r.build_coverage(
                reqs, tasks, repo, strict_symbols=True
            )
            self.assertEqual(entries[0].status, "covered")
            self.assertEqual(entries[0].confidence, "high")
            self.assertEqual(entries[0].candidate_symbols, [])

    def test_acceptance_subline_is_parsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            tasks_md = """\
- [x] T001: do the thing
  - Satisfies: D1
  - Acceptance: When `target_symbol` is set, return early.
  - Files: src/x.py
"""
            sprint = _make_sprint(repo, "- [D1] Thing\n", tasks_md)
            tasks = r.parse_tasks(sprint / "TASKS.md")
            self.assertEqual(
                tasks[0].acceptance,
                "When `target_symbol` is set, return early.",
            )


class CLIIntegrationTests(unittest.TestCase):
    def test_strict_symbols_flag_returns_nonzero_on_stub(self):
        script = Path(__file__).resolve().parent.parent / "scripts" / "reconcile.py"
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            sprint = _make_sprint(repo, PRD_FIXTURE, TASKS_STUB_IMPL)
            (repo / "src").mkdir()
            (repo / "src" / "threading.py").write_text("pass\n")
            res = subprocess.run(
                ["python3", str(script), str(sprint),
                 "--ci", "--strict-symbols", "--repo-root", str(repo)],
                capture_output=True, text=True,
            )
            self.assertEqual(res.returncode, 1)
            self.assertIn("FAIL", res.stderr)

    def test_default_does_not_block_on_stub(self):
        # Without --strict-symbols, a stub does not flip the exit code —
        # only confidence + notes change. Existing CI keeps passing.
        script = Path(__file__).resolve().parent.parent / "scripts" / "reconcile.py"
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            sprint = _make_sprint(repo, PRD_FIXTURE, TASKS_STUB_IMPL)
            (repo / "src").mkdir()
            (repo / "src" / "threading.py").write_text("pass\n")
            res = subprocess.run(
                ["python3", str(script), str(sprint),
                 "--ci", "--repo-root", str(repo)],
                capture_output=True, text=True,
            )
            self.assertEqual(res.returncode, 0)

    def test_json_output_includes_symbol_fields(self):
        script = Path(__file__).resolve().parent.parent / "scripts" / "reconcile.py"
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            sprint = _make_sprint(repo, PRD_FIXTURE, TASKS_REAL_IMPL)
            (repo / "src").mkdir()
            (repo / "src" / "threading.py").write_text(
                "def load_ref(): _routes_differ = True\n"
            )
            res = subprocess.run(
                ["python3", str(script), str(sprint),
                 "--json", "--repo-root", str(repo)],
                capture_output=True, text=True, check=True,
            )
            payload = json.loads(res.stdout)
            entry = next(e for e in payload["entries"]
                         if e["requirement_id"] == "D1")
            self.assertIn("candidate_symbols", entry)
            self.assertIn("matched_symbols", entry)
            self.assertIn("_routes_differ", entry["matched_symbols"])


class AutonomyAnnotationTests(unittest.TestCase):
    """Parsing and validation of the optional `Autonomy:` subline."""

    def _parse(self, tasks_md: str):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_file = Path(tmp) / "TASKS.md"
            tasks_file.write_text(tasks_md, encoding="utf-8")
            return r.parse_tasks(tasks_file)

    def test_direct_level_parsed(self):
        tasks = self._parse(
            "- [ ] T001: title\n"
            "  - Satisfies: §1.1\n"
            "  - Autonomy: direct\n"
        )
        self.assertEqual(tasks[0].autonomy, "direct")
        self.assertTrue(tasks[0].autonomy_valid)

    def test_checkpoint_level_parsed(self):
        tasks = self._parse(
            "- [ ] T001: title\n"
            "  - Satisfies: §1.1\n"
            "  - Autonomy: checkpoint\n"
        )
        self.assertEqual(tasks[0].autonomy, "checkpoint")
        self.assertTrue(tasks[0].autonomy_valid)

    def test_review_only_level_parsed(self):
        tasks = self._parse(
            "- [ ] T001: title\n"
            "  - Satisfies: §1.1\n"
            "  - Autonomy: review-only\n"
        )
        self.assertEqual(tasks[0].autonomy, "review-only")
        self.assertTrue(tasks[0].autonomy_valid)

    def test_uppercase_normalized(self):
        tasks = self._parse(
            "- [ ] T001: title\n"
            "  - Autonomy: DIRECT\n"
        )
        self.assertEqual(tasks[0].autonomy, "direct")
        self.assertTrue(tasks[0].autonomy_valid)

    def test_unknown_level_marked_invalid(self):
        tasks = self._parse(
            "- [ ] T001: title\n"
            "  - Autonomy: yolo\n"
        )
        self.assertEqual(tasks[0].autonomy, "yolo")
        self.assertFalse(tasks[0].autonomy_valid)

    def test_missing_annotation_is_none(self):
        tasks = self._parse(
            "- [ ] T001: title\n"
            "  - Satisfies: §1.1\n"
        )
        self.assertIsNone(tasks[0].autonomy)
        self.assertTrue(tasks[0].autonomy_valid)  # absent is fine

    def test_subline_does_not_break_other_parsing(self):
        tasks = self._parse(
            "- [ ] T001: title\n"
            "  - Autonomy: checkpoint\n"
            "  - Satisfies: §1.1, §1.2\n"
            "  - Files: src/a.py\n"
        )
        self.assertEqual(tasks[0].satisfies, ["§1.1", "§1.2"])
        self.assertEqual(tasks[0].files, ["src/a.py"])
        self.assertEqual(tasks[0].autonomy, "checkpoint")

    def test_invalid_value_warns_to_stderr_via_cli(self):
        script = Path(__file__).resolve().parent.parent / "scripts" / "reconcile.py"
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            tasks_md = (
                "## Tasks\n\n"
                "- [x] T001: Wire `_routes_differ` into `load_ref`\n"
                "  - Satisfies: D1, D2\n"
                "  - Acceptance: `_routes_differ` is set when `load_ref` matches.\n"
                "  - Files: src/threading.py\n"
                "  - Autonomy: typo-here\n"
                "- [DEFERRED] T002: Out of scope\n"
                "  - Satisfies: D3\n"
                "  - Status: DEFERRED\n"
                "  - Target: v2\n"
            )
            sprint = _make_sprint(repo, PRD_FIXTURE, tasks_md)
            (repo / "src").mkdir()
            (repo / "src" / "threading.py").write_text(
                "def load_ref(): _routes_differ = True\n"
            )
            res = subprocess.run(
                ["python3", str(script), str(sprint),
                 "--ci", "--repo-root", str(repo)],
                capture_output=True, text=True,
            )
            self.assertIn("WARNING", res.stderr)
            self.assertIn("typo-here", res.stderr)
            self.assertIn("T001", res.stderr)
            # Invalid autonomy must NOT fail the gate.
            self.assertEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main()
