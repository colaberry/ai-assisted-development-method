"""Tests for tooling/hooks/sprint_gate.py — the PreToolUse anti-skip hook."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Tuple


HOOK_PATH = Path(__file__).resolve().parents[1] / "hooks" / "sprint_gate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sprint_gate", HOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["sprint_gate"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


sprint_gate = load_module()


def make_repo(tmp: Path) -> Path:
    """Return an empty 'repo' (with a .git marker so find_repo_root finds it)."""
    (tmp / ".git").mkdir()
    return tmp


def make_sprint(repo: Path, n: int, locked: bool) -> Path:
    sprint = repo / "sprints" / f"v{n}"
    sprint.mkdir(parents=True)
    if locked:
        (sprint / ".lock").write_text("locked_at: 2026-01-01T00:00:00Z\n")
    return sprint


def write_tasks(sprint: Path, body: str) -> Path:
    tasks = sprint / "TASKS.md"
    tasks.write_text(body, encoding="utf-8")
    return tasks


TASKS_SINGLE_OPEN = """\
# Sprint v2 — Tasks

- [ ] T001: Add endpoint
  - Satisfies: §1.2
  - Acceptance: returns 200
  - Files: src/api/foo.py, tests/api/test_foo.py
  - Tests required: A, B
"""


TASKS_MIXED = """\
# Sprint v2 — Tasks

- [ ] T001: Open task
  - Satisfies: §1.1
  - Files: src/api/open.py
- [x] T002: Completed
  - Satisfies: §1.2
  - Files: src/api/done.py
  - Completed: 2026-04-20
- [DEFERRED] T003: Deferred
  - Status: DEFERRED
  - Target: v3
  - Reason: blocked on vendor
  - Files: src/api/deferred.py
"""


TASKS_DIR_ENTRY = """\
# Sprint v2 — Tasks

- [ ] T001: Refactor auth module
  - Satisfies: §2.1
  - Files: src/auth/
"""


class ExtractTargetPathTests(unittest.TestCase):
    def test_returns_file_path_for_write(self):
        path = sprint_gate.extract_target_path("Write", {"file_path": "a.py"})
        self.assertEqual(path, "a.py")

    def test_returns_none_for_non_write_tool(self):
        self.assertIsNone(sprint_gate.extract_target_path("Read", {"file_path": "a.py"}))

    def test_notebook_path_used_for_notebook_edit(self):
        path = sprint_gate.extract_target_path("NotebookEdit", {"notebook_path": "n.ipynb"})
        self.assertEqual(path, "n.ipynb")

    def test_missing_file_path_returns_none(self):
        self.assertIsNone(sprint_gate.extract_target_path("Edit", {}))

    def test_non_string_file_path_returns_none(self):
        self.assertIsNone(sprint_gate.extract_target_path("Edit", {"file_path": 42}))


class SprintIndexForTests(unittest.TestCase):
    def test_returns_index_for_sprint_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            sprint = make_sprint(repo, 3, locked=False)
            target = sprint / "TASKS.md"
            self.assertEqual(sprint_gate.sprint_index_for(target, repo), 3)

    def test_returns_none_for_non_sprint_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            target = repo / "src" / "foo.py"
            self.assertIsNone(sprint_gate.sprint_index_for(target, repo))

    def test_returns_none_for_path_outside_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            self.assertIsNone(sprint_gate.sprint_index_for(Path("/etc/hosts"), repo))

    def test_returns_none_for_unparseable_sprint_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            (repo / "sprints" / "v_not_a_number").mkdir(parents=True)
            target = repo / "sprints" / "v_not_a_number" / "TASKS.md"
            self.assertIsNone(sprint_gate.sprint_index_for(target, repo))


class ListSprintDirsTests(unittest.TestCase):
    def test_lists_sprints_sorted(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            make_sprint(repo, 2, locked=True)
            make_sprint(repo, 1, locked=True)
            make_sprint(repo, 10, locked=False)
            ns = [n for n, _ in sprint_gate.list_sprint_dirs(repo)]
            self.assertEqual(ns, [1, 2, 10])

    def test_skips_non_sprint_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            make_sprint(repo, 1, locked=True)
            (repo / "sprints" / "archive").mkdir()
            (repo / "sprints" / "v_x").mkdir()
            ns = [n for n, _ in sprint_gate.list_sprint_dirs(repo)]
            self.assertEqual(ns, [1])

    def test_returns_empty_when_no_sprints_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            self.assertEqual(sprint_gate.list_sprint_dirs(repo), [])


class UnlockedPredecessorsTests(unittest.TestCase):
    def test_returns_unlocked_earlier_sprints(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            make_sprint(repo, 1, locked=True)
            make_sprint(repo, 2, locked=False)
            make_sprint(repo, 3, locked=False)
            sprints = sprint_gate.list_sprint_dirs(repo)
            self.assertEqual(sprint_gate.unlocked_predecessors(3, sprints), [2])

    def test_empty_when_all_predecessors_locked(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            make_sprint(repo, 1, locked=True)
            make_sprint(repo, 2, locked=True)
            sprints = sprint_gate.list_sprint_dirs(repo)
            self.assertEqual(sprint_gate.unlocked_predecessors(2, sprints), [])

    def test_v1_has_no_predecessors(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            make_sprint(repo, 1, locked=False)
            sprints = sprint_gate.list_sprint_dirs(repo)
            self.assertEqual(sprint_gate.unlocked_predecessors(1, sprints), [])


class EvaluateTests(unittest.TestCase):
    def test_allows_non_sprint_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            allow, msg = sprint_gate.evaluate(
                "Write", {"file_path": str(repo / "src" / "foo.py")}, repo
            )
            self.assertTrue(allow)
            self.assertIsNone(msg)

    def test_allows_sprint_writes_when_predecessors_locked(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            make_sprint(repo, 1, locked=True)
            sprint2 = make_sprint(repo, 2, locked=False)
            allow, _ = sprint_gate.evaluate(
                "Edit", {"file_path": str(sprint2 / "TASKS.md")}, repo
            )
            self.assertTrue(allow)

    def test_blocks_sprint_writes_when_predecessor_unlocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            make_sprint(repo, 1, locked=False)
            sprint2 = make_sprint(repo, 2, locked=False)
            allow, msg = sprint_gate.evaluate(
                "Write", {"file_path": str(sprint2 / "PRD.md")}, repo
            )
            self.assertFalse(allow)
            self.assertIn("sprints/v1/.lock", msg)
            self.assertIn("v2", msg)

    def test_lists_all_missing_locks_when_multiple_predecessors_unlocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            make_sprint(repo, 1, locked=False)
            make_sprint(repo, 2, locked=False)
            sprint3 = make_sprint(repo, 3, locked=False)
            allow, msg = sprint_gate.evaluate(
                "Write", {"file_path": str(sprint3 / "TASKS.md")}, repo
            )
            self.assertFalse(allow)
            self.assertIn("sprints/v1/.lock", msg)
            self.assertIn("sprints/v2/.lock", msg)

    def test_allows_writing_to_v1_with_no_other_sprints(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            sprint1 = make_sprint(repo, 1, locked=False)
            allow, _ = sprint_gate.evaluate(
                "Write", {"file_path": str(sprint1 / "PRD.md")}, repo
            )
            self.assertTrue(allow)

    def test_allows_writing_to_unlocked_sprint_when_only_later_sprint_locked(self):
        # Edge case: v1 unlocked, v2 locked. Writing to v1 should be allowed
        # (no earlier sprint exists). The hook only enforces forward-skip.
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            sprint1 = make_sprint(repo, 1, locked=False)
            make_sprint(repo, 2, locked=True)
            allow, _ = sprint_gate.evaluate(
                "Edit", {"file_path": str(sprint1 / "RETRO.md")}, repo
            )
            self.assertTrue(allow)

    def test_allows_read_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            make_sprint(repo, 1, locked=False)
            sprint2 = make_sprint(repo, 2, locked=False)
            allow, _ = sprint_gate.evaluate(
                "Read", {"file_path": str(sprint2 / "PRD.md")}, repo
            )
            self.assertTrue(allow)

    def test_relative_path_resolved_against_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            make_sprint(repo, 1, locked=False)
            make_sprint(repo, 2, locked=False)
            allow, msg = sprint_gate.evaluate(
                "Write", {"file_path": "sprints/v2/PRD.md"}, repo
            )
            self.assertFalse(allow)
            self.assertIn("sprints/v1/.lock", msg)


class ActiveSprintTests(unittest.TestCase):
    def test_returns_highest_unlocked_sprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            make_sprint(repo, 1, locked=True)
            s2 = make_sprint(repo, 2, locked=False)
            sprints = sprint_gate.list_sprint_dirs(repo)
            active = sprint_gate.active_sprint(sprints)
            self.assertIsNotNone(active)
            self.assertEqual(active[0], 2)
            self.assertEqual(active[1], s2)

    def test_returns_none_when_all_locked(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            make_sprint(repo, 1, locked=True)
            make_sprint(repo, 2, locked=True)
            sprints = sprint_gate.list_sprint_dirs(repo)
            self.assertIsNone(sprint_gate.active_sprint(sprints))

    def test_returns_none_when_no_sprints(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            self.assertIsNone(sprint_gate.active_sprint([]))


class ParseFilesAllowlistTests(unittest.TestCase):
    def test_returns_files_from_open_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            sprint = make_sprint(repo, 2, locked=False)
            tasks = write_tasks(sprint, TASKS_SINGLE_OPEN)
            allow = sprint_gate.parse_files_allowlist(tasks)
            self.assertEqual(
                allow, ["src/api/foo.py", "tests/api/test_foo.py"]
            )

    def test_skips_completed_and_deferred_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            sprint = make_sprint(repo, 2, locked=False)
            tasks = write_tasks(sprint, TASKS_MIXED)
            allow = sprint_gate.parse_files_allowlist(tasks)
            self.assertEqual(allow, ["src/api/open.py"])

    def test_returns_none_when_tasks_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            sprint = make_sprint(repo, 2, locked=False)
            self.assertIsNone(
                sprint_gate.parse_files_allowlist(sprint / "TASKS.md")
            )

    def test_returns_empty_when_no_open_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            sprint = make_sprint(repo, 2, locked=False)
            tasks = write_tasks(
                sprint,
                "# Sprint v2\n\n- [x] T001: Done\n  - Files: src/done.py\n",
            )
            self.assertEqual(sprint_gate.parse_files_allowlist(tasks), [])


class TargetInAllowlistTests(unittest.TestCase):
    def test_exact_match(self):
        self.assertTrue(
            sprint_gate.target_in_allowlist("src/api/foo.py", ["src/api/foo.py"])
        )

    def test_miss(self):
        self.assertFalse(
            sprint_gate.target_in_allowlist("src/api/bar.py", ["src/api/foo.py"])
        )

    def test_directory_entry_matches_descendant(self):
        self.assertTrue(
            sprint_gate.target_in_allowlist("src/auth/session.py", ["src/auth/"])
        )

    def test_directory_entry_does_not_match_sibling(self):
        self.assertFalse(
            sprint_gate.target_in_allowlist("src/api/foo.py", ["src/auth/"])
        )

    def test_leading_dot_slash_tolerated(self):
        self.assertTrue(
            sprint_gate.target_in_allowlist("src/api/foo.py", ["./src/api/foo.py"])
        )


class EvaluateScopeAllowlistTests(unittest.TestCase):
    def _setup_skip_condition(self, tmp: Path) -> Tuple[Path, Path]:
        """Set up v1 unlocked + v2 active (unlocked) — the trigger for scope checks."""
        repo = make_repo(tmp)
        make_sprint(repo, 1, locked=False)
        sprint2 = make_sprint(repo, 2, locked=False)
        write_tasks(sprint2, TASKS_SINGLE_OPEN)
        (repo / "src" / "api").mkdir(parents=True)
        (repo / "tests" / "api").mkdir(parents=True)
        return repo, sprint2

    def test_declared_file_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = self._setup_skip_condition(Path(tmp))
            allow, msg = sprint_gate.evaluate(
                "Write",
                {"file_path": str(repo / "src" / "api" / "foo.py")},
                repo,
            )
            self.assertTrue(allow, msg)

    def test_undeclared_file_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint2 = self._setup_skip_condition(Path(tmp))
            allow, msg = sprint_gate.evaluate(
                "Write",
                {"file_path": str(repo / "src" / "api" / "undeclared.py")},
                repo,
            )
            self.assertFalse(allow)
            self.assertIn("src/api/undeclared.py", msg)
            self.assertIn("v2/TASKS.md Files: allowlist", msg)
            self.assertIn("sprints/v1/.lock", msg)
            log = (sprint2 / ".gate-blocks.log").read_text(encoding="utf-8")
            self.assertIn("src/api/undeclared.py", log)
            self.assertIn("Write", log)

    def test_no_enforcement_when_no_skip_condition(self):
        # v1 locked, v2 open, no prior unlocked sprint => scope allowlist
        # is NOT enforced. Writes to undeclared files are allowed.
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            make_sprint(repo, 1, locked=True)
            sprint2 = make_sprint(repo, 2, locked=False)
            write_tasks(sprint2, TASKS_SINGLE_OPEN)
            allow, _ = sprint_gate.evaluate(
                "Write",
                {"file_path": str(repo / "src" / "other.py")},
                repo,
            )
            self.assertTrue(allow)

    def test_no_enforcement_on_v1_bootstrap(self):
        # v1 alone, unlocked, no TASKS.md => no prior unlocked sprint so
        # allowlist is not enforced. v1 bootstrap must not be bricked.
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            make_sprint(repo, 1, locked=False)
            allow, _ = sprint_gate.evaluate(
                "Write",
                {"file_path": str(repo / "src" / "new.py")},
                repo,
            )
            self.assertTrue(allow)

    def test_missing_tasks_md_is_warn_only(self):
        # v1 unlocked + v2 active, but v2 has no TASKS.md -> defensive allow.
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            make_sprint(repo, 1, locked=False)
            make_sprint(repo, 2, locked=False)  # no TASKS.md written
            allow, _ = sprint_gate.evaluate(
                "Write",
                {"file_path": str(repo / "src" / "whatever.py")},
                repo,
            )
            self.assertTrue(allow)

    def test_completed_task_file_is_blocked(self):
        # Completed tasks shouldn't keep expanding scope.
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            make_sprint(repo, 1, locked=False)
            sprint2 = make_sprint(repo, 2, locked=False)
            write_tasks(sprint2, TASKS_MIXED)
            allow, msg = sprint_gate.evaluate(
                "Edit",
                {"file_path": str(repo / "src" / "api" / "done.py")},
                repo,
            )
            self.assertFalse(allow)
            self.assertIn("src/api/done.py", msg)

    def test_deferred_task_file_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            make_sprint(repo, 1, locked=False)
            sprint2 = make_sprint(repo, 2, locked=False)
            write_tasks(sprint2, TASKS_MIXED)
            allow, _ = sprint_gate.evaluate(
                "Write",
                {"file_path": str(repo / "src" / "api" / "deferred.py")},
                repo,
            )
            self.assertFalse(allow)

    def test_directory_entry_in_files_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            make_sprint(repo, 1, locked=False)
            sprint2 = make_sprint(repo, 2, locked=False)
            write_tasks(sprint2, TASKS_DIR_ENTRY)
            allow, _ = sprint_gate.evaluate(
                "Edit",
                {"file_path": str(repo / "src" / "auth" / "session.py")},
                repo,
            )
            self.assertTrue(allow)

    def test_sprint_path_uses_anti_skip_not_allowlist(self):
        # Writes under sprints/vK/ keep going through the old anti-skip path —
        # they are not subject to the Files: allowlist.
        with tempfile.TemporaryDirectory() as tmp:
            repo, sprint2 = self._setup_skip_condition(Path(tmp))
            allow, msg = sprint_gate.evaluate(
                "Edit",
                {"file_path": str(sprint2 / "PRD.md")},
                repo,
            )
            self.assertFalse(allow)
            self.assertIn("sprints/v1/.lock", msg)
            self.assertIn("Run sprint_close.py", msg)


class MainEntryPointTests(unittest.TestCase):
    """End-to-end: invoke the script via stdin like Claude Code does."""

    def _run(self, payload: dict) -> tuple[int, str]:
        import subprocess
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
        )
        return result.returncode, result.stderr

    def test_blocks_on_unlocked_predecessor_via_stdin(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            make_sprint(repo, 1, locked=False)
            sprint2 = make_sprint(repo, 2, locked=False)
            payload = {
                "tool_name": "Write",
                "tool_input": {"file_path": str(sprint2 / "PRD.md"), "content": "x"},
                "cwd": str(repo),
            }
            code, stderr = self._run(payload)
            self.assertEqual(code, 2)
            self.assertIn("sprints/v1/.lock", stderr)

    def test_allows_when_all_predecessors_locked(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            make_sprint(repo, 1, locked=True)
            sprint2 = make_sprint(repo, 2, locked=False)
            payload = {
                "tool_name": "Edit",
                "tool_input": {"file_path": str(sprint2 / "TASKS.md")},
                "cwd": str(repo),
            }
            code, _ = self._run(payload)
            self.assertEqual(code, 0)

    def test_allows_on_malformed_json(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input="this is not json",
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("could not parse", result.stderr)

    def test_allows_when_tool_input_not_dict(self):
        code, _ = self._run({"tool_name": "Write", "tool_input": "oops"})
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
