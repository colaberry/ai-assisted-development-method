"""Tests for tooling/scripts/gap.py — initiative-boundary coverage analysis."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "gap.py"


def load_module():
    spec = importlib.util.spec_from_file_location("gap", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["gap"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


gap = load_module()


# ---------- fixtures --------------------------------------------------------

INITIATIVE_THREE_IDS = """\
# Auth initiative

## §1.1 Login
Users can log in with email + password.

## §1.2 Session expiry
Sessions expire after 24h.

## §1.3 Password reset
Users can reset via email.
"""


INITIATIVE_WITH_SUPERSEDE = """\
# Auth initiative

## §3.2 Old session handling
Renegotiated during SOW amendment.
SUPERSEDED-BY: §3.7, §3.8

## §3.7 Auth flow
Post-amendment auth.

## §3.8 Session expiry
Post-amendment expiry.
"""


TASKS_COVERS_ONE = """\
# Sprint v1

- [x] T001: Login
  - Satisfies: §1.1
  - Files: src/auth/login.py
"""


TASKS_COVERS_ONE_DEFERS_ONE = """\
# Sprint v1

- [x] T001: Login
  - Satisfies: §1.1
  - Files: src/auth/login.py
- [DEFERRED] T002: Session expiry
  - Satisfies: §1.2
  - Status: DEFERRED
  - Target: v2
  - Reason: blocked on vendor clock
"""


TASKS_COVERS_SUCCESSORS = """\
# Sprint v1

- [x] T001: Post-amendment auth
  - Satisfies: §3.7
  - Files: src/auth/flow.py
- [x] T002: Post-amendment expiry
  - Satisfies: §3.8
  - Files: src/auth/expiry.py
"""


TASKS_CONFLICT = """\
# Sprint v1

- [ ] T001: Login path A
  - Satisfies: §1.1
  - Files: src/auth/a.py
- [ ] T002: Login path B
  - Satisfies: §1.1
  - Files: src/auth/b.py
"""


TASKS_DEFERRED_WITHOUT_TARGET = """\
# Sprint v1

- [DEFERRED] T001: Login
  - Satisfies: §1.1
  - Status: DEFERRED
  - Reason: no target filed
"""


# ---------- helpers ---------------------------------------------------------

def make_layout(root: Path, initiative_body: str, sprint_tasks: dict) -> Path:
    (root / "docs").mkdir()
    initiative = root / "docs" / "AUTH.md"
    initiative.write_text(initiative_body, encoding="utf-8")

    sprints_root = root / "sprints"
    sprints_root.mkdir()
    for sprint_name, body in sprint_tasks.items():
        sprint = sprints_root / sprint_name
        sprint.mkdir()
        (sprint / "TASKS.md").write_text(body, encoding="utf-8")
    return initiative


# ---------- tests -----------------------------------------------------------

class ParseInitiativeTests(unittest.TestCase):
    def test_extracts_three_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initiative = make_layout(root, INITIATIVE_THREE_IDS, {})
            ids, supersedes = gap.parse_initiative(initiative)
            self.assertEqual(ids, ["§1.1", "§1.2", "§1.3"])
            self.assertEqual(supersedes, {})

    def test_extracts_superseded_by(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initiative = make_layout(root, INITIATIVE_WITH_SUPERSEDE, {})
            ids, supersedes = gap.parse_initiative(initiative)
            self.assertEqual(ids, ["§3.2", "§3.7", "§3.8"])
            self.assertEqual(supersedes, {"§3.2": ["§3.7", "§3.8"]})

    def test_dedupes_repeated_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = "## §1.1\nfoo\n\nMentioned again: §1.1\n"
            initiative = make_layout(root, body, {})
            ids, _ = gap.parse_initiative(initiative)
            self.assertEqual(ids, ["§1.1"])


class CollectSatisfiesTests(unittest.TestCase):
    def test_collects_active_and_deferred(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_layout(root, INITIATIVE_THREE_IDS, {"v1": TASKS_COVERS_ONE_DEFERS_ONE})
            active, deferred = gap.collect_satisfies(root / "sprints")
            self.assertIn("§1.1", active)
            self.assertEqual(active["§1.1"][0].status, "complete")
            self.assertIn("§1.2", deferred)
            self.assertEqual(deferred["§1.2"][0].target, "v2")

    def test_deferred_without_target_is_neither(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_layout(root, INITIATIVE_THREE_IDS, {"v1": TASKS_DEFERRED_WITHOUT_TARGET})
            active, deferred = gap.collect_satisfies(root / "sprints")
            self.assertNotIn("§1.1", active)
            self.assertNotIn("§1.1", deferred)


class AnalyzeTests(unittest.TestCase):
    def test_clean_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initiative = make_layout(
                root,
                INITIATIVE_THREE_IDS,
                {
                    "v1": """\
# v1
- [x] T001: Login
  - Satisfies: §1.1
- [ ] T002: Session expiry
  - Satisfies: §1.2
- [ ] T003: Reset
  - Satisfies: §1.3
""",
                },
            )
            report = gap.analyze(initiative, root / "sprints")
            self.assertEqual(report.orphaned, [])
            self.assertEqual(set(report.covered), {"§1.1", "§1.2", "§1.3"})
            self.assertFalse(report.has_conflicts())

    def test_orphan_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initiative = make_layout(
                root, INITIATIVE_THREE_IDS, {"v1": TASKS_COVERS_ONE}
            )
            report = gap.analyze(initiative, root / "sprints")
            self.assertEqual(sorted(report.orphaned), ["§1.2", "§1.3"])
            self.assertEqual(set(report.covered), {"§1.1"})

    def test_deferred_with_target_is_not_orphan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initiative = make_layout(
                root,
                INITIATIVE_THREE_IDS,
                {"v1": TASKS_COVERS_ONE_DEFERS_ONE},
            )
            report = gap.analyze(initiative, root / "sprints")
            self.assertEqual(report.orphaned, ["§1.3"])
            self.assertIn("§1.2", report.deferred)

    def test_conflict_flagged_on_multiple_open_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = "## §1.1\nLogin.\n"
            initiative = make_layout(root, body, {"v1": TASKS_CONFLICT})
            report = gap.analyze(initiative, root / "sprints")
            self.assertIn("§1.1", report.conflicted)
            self.assertEqual(len(report.conflicted["§1.1"]), 2)

    def test_superseded_by_covered_successor_is_not_orphan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initiative = make_layout(
                root, INITIATIVE_WITH_SUPERSEDE, {"v1": TASKS_COVERS_SUCCESSORS}
            )
            report = gap.analyze(initiative, root / "sprints")
            self.assertEqual(report.orphaned, [])
            # §3.2 should be treated as covered via supersession
            self.assertIn("§3.2", report.covered)

    def test_superseded_by_uncovered_successor_still_orphan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initiative = make_layout(
                root,
                INITIATIVE_WITH_SUPERSEDE,
                {
                    "v1": """\
# v1
- [x] T001: Only §3.7
  - Satisfies: §3.7
""",
                },
            )
            report = gap.analyze(initiative, root / "sprints")
            # §3.2 is superseded by §3.7 (covered) and §3.8 (not covered).
            # The "any successor covered" v1 rule counts §3.2 as covered.
            self.assertNotIn("§3.2", report.orphaned)
            self.assertIn("§3.8", report.orphaned)


class RenderMarkdownTests(unittest.TestCase):
    def test_orphan_section_names_each_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initiative = make_layout(
                root, INITIATIVE_THREE_IDS, {"v1": TASKS_COVERS_ONE}
            )
            report = gap.analyze(initiative, root / "sprints")
            md = gap.render_markdown(report)
            self.assertIn("## Orphaned", md)
            self.assertIn("**§1.2**", md)
            self.assertIn("**§1.3**", md)
            self.assertIn("silent-drop", md)

    def test_clean_report_says_none_identified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initiative = make_layout(
                root,
                INITIATIVE_THREE_IDS,
                {
                    "v1": """\
# v1
- [ ] T001: §1.1
  - Satisfies: §1.1
- [ ] T002: §1.2
  - Satisfies: §1.2
- [ ] T003: §1.3
  - Satisfies: §1.3
""",
                },
            )
            report = gap.analyze(initiative, root / "sprints")
            md = gap.render_markdown(report)
            self.assertIn("None identified", md)

    def test_supersession_block_appears(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initiative = make_layout(
                root, INITIATIVE_WITH_SUPERSEDE, {"v1": TASKS_COVERS_SUCCESSORS}
            )
            report = gap.analyze(initiative, root / "sprints")
            md = gap.render_markdown(report)
            self.assertIn("Supersession map", md)
            self.assertIn("§3.2", md)


class CliTests(unittest.TestCase):
    def _run(self, args, cwd: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT_PATH), *args],
            cwd=cwd,
            capture_output=True,
            text=True,
        )

    def test_clean_run_exit_zero_ci(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initiative = make_layout(
                root,
                INITIATIVE_THREE_IDS,
                {
                    "v1": """\
# v1
- [ ] T001: §1.1
  - Satisfies: §1.1
- [ ] T002: §1.2
  - Satisfies: §1.2
- [ ] T003: §1.3
  - Satisfies: §1.3
""",
                },
            )
            result = self._run(
                [
                    str(initiative.relative_to(root)),
                    "sprints",
                    "--ci",
                ],
                cwd=root,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(
                (root / "docs" / "AUTH_GAP_ANALYSIS.md").exists()
            )

    def test_orphan_ci_exit_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initiative = make_layout(
                root, INITIATIVE_THREE_IDS, {"v1": TASKS_COVERS_ONE}
            )
            result = self._run(
                [str(initiative.relative_to(root)), "sprints", "--ci"],
                cwd=root,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("ORPHANED", result.stderr)
            self.assertIn("§1.2", result.stderr)
            self.assertIn("§1.3", result.stderr)

    def test_conflict_ci_exit_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = "## §1.1\nLogin.\n"
            initiative = make_layout(root, body, {"v1": TASKS_CONFLICT})
            result = self._run(
                [str(initiative.relative_to(root)), "sprints", "--ci"],
                cwd=root,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("CONFLICTED", result.stderr)

    def test_non_ci_always_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initiative = make_layout(
                root, INITIATIVE_THREE_IDS, {"v1": TASKS_COVERS_ONE}
            )
            result = self._run(
                [str(initiative.relative_to(root)), "sprints"],
                cwd=root,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            # analysis still written
            self.assertTrue((root / "docs" / "AUTH_GAP_ANALYSIS.md").exists())

    def test_missing_initiative_exits_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self._run(
                ["docs/nope.md", "sprints", "--ci"],
                cwd=root,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("not found", result.stderr)

    def test_custom_output_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initiative = make_layout(
                root, INITIATIVE_THREE_IDS, {"v1": TASKS_COVERS_ONE}
            )
            out = root / "reports" / "gap.md"
            result = self._run(
                [
                    str(initiative.relative_to(root)),
                    "sprints",
                    "--output",
                    str(out.relative_to(root)),
                ],
                cwd=root,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
