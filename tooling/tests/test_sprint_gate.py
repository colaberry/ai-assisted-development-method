"""Tests for tooling/hooks/sprint_gate.py — the PreToolUse anti-skip hook."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


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
