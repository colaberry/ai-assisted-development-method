"""Tests for tooling/scripts/dev_session.py — the /dev-test ↔ /dev-impl split."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "dev_session.py"


def load_module():
    spec = importlib.util.spec_from_file_location("dev_session", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["dev_session"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


dev_session = load_module()


def init_repo(root: Path) -> Path:
    """Initialize a real git repo so test commits are verifiable."""
    subprocess.run(
        ["git", "init", "--quiet", "--initial-branch=main"],
        cwd=root,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=root, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=root, check=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=root, check=True,
    )
    # seed commit so HEAD exists
    (root / "README.md").write_text("# test repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "--quiet", "-m", "seed"],
        cwd=root, check=True,
    )
    return root


def make_commit(root: Path, path: str, body: str, message: str) -> str:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    subprocess.run(["git", "add", path], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "--quiet", "-m", message],
        cwd=root, check=True,
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root, check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


def make_sprint(root: Path, n: int) -> Path:
    sprint = root / "sprints" / f"v{n}"
    sprint.mkdir(parents=True)
    return sprint


class NormalizeTaskIdTests(unittest.TestCase):
    def test_accepts_tnnn(self):
        self.assertEqual(dev_session.normalize_task_id("T012"), "T012")

    def test_accepts_t_nnn(self):
        self.assertEqual(dev_session.normalize_task_id("T-012"), "T-012")

    def test_rejects_bare_number(self):
        with self.assertRaises(ValueError):
            dev_session.normalize_task_id("12")

    def test_rejects_bogus(self):
        with self.assertRaises(ValueError):
            dev_session.normalize_task_id("TASK-12")


class WriteAndParseMarkerTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            sprint = make_sprint(Path(tmp), 2)
            paths = dev_session.marker_paths(sprint, "T001")
            written = dev_session.write_marker(paths, "a" * 40)
            self.assertTrue(written.exists())
            commit, when = dev_session.parse_marker(written)
            self.assertEqual(commit, "a" * 40)
            self.assertIsNotNone(when)

    def test_write_marker_rejects_bad_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            sprint = make_sprint(Path(tmp), 2)
            paths = dev_session.marker_paths(sprint, "T001")
            with self.assertRaises(ValueError):
                dev_session.write_marker(paths, "not-a-sha")

    def test_parse_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            sprint = make_sprint(Path(tmp), 2)
            paths = dev_session.marker_paths(sprint, "T999")
            commit, when = dev_session.parse_marker(paths.test_done)
            self.assertIsNone(commit)
            self.assertIsNone(when)

    def test_parse_malformed_returns_missing_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            sprint = make_sprint(Path(tmp), 2)
            paths = dev_session.marker_paths(sprint, "T001")
            paths.marker_dir.mkdir(parents=True)
            paths.test_done.write_text("garbage\n", encoding="utf-8")
            commit, when = dev_session.parse_marker(paths.test_done)
            self.assertIsNone(commit)
            self.assertIsNone(when)


class CheckImplReadyTests(unittest.TestCase):
    def test_refuses_when_marker_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            init_repo(Path(tmp))
            sprint = make_sprint(Path(tmp), 2)
            ready, msg = dev_session.check_impl_ready(sprint, "T001")
            self.assertFalse(ready)
            self.assertIn("no test-done marker", msg)
            self.assertIn("Method rule 4", msg)

    def test_refuses_when_marker_malformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            init_repo(Path(tmp))
            sprint = make_sprint(Path(tmp), 2)
            paths = dev_session.marker_paths(sprint, "T001")
            paths.marker_dir.mkdir(parents=True)
            paths.test_done.write_text("no commit here\n", encoding="utf-8")
            ready, msg = dev_session.check_impl_ready(sprint, "T001")
            self.assertFalse(ready)
            self.assertIn("malformed", msg)

    def test_refuses_when_not_git_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            sprint = make_sprint(Path(tmp), 2)
            paths = dev_session.marker_paths(sprint, "T001")
            dev_session.write_marker(paths, "a" * 40)
            ready, msg = dev_session.check_impl_ready(sprint, "T001")
            self.assertFalse(ready)
            self.assertIn("no git repo", msg)

    def test_refuses_when_commit_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            init_repo(Path(tmp))
            sprint = make_sprint(Path(tmp), 2)
            paths = dev_session.marker_paths(sprint, "T001")
            # sha that isn't present in this repo
            dev_session.write_marker(paths, "0" * 40)
            ready, msg = dev_session.check_impl_ready(sprint, "T001")
            self.assertFalse(ready)
            self.assertIn("not on disk", msg)

    def test_ready_when_marker_and_commit_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = init_repo(Path(tmp))
            sprint = make_sprint(root, 2)
            sha = make_commit(root, "tests/test_x.py", "def test_fail():\n    assert False\n", "test(T001): seed failing test")
            paths = dev_session.marker_paths(sprint, "T001")
            dev_session.write_marker(paths, sha)
            ready, msg = dev_session.check_impl_ready(sprint, "T001")
            self.assertTrue(ready, msg)
            self.assertIn(sha, msg)


class MarkCompleteTests(unittest.TestCase):
    def test_moves_test_done_to_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            sprint = make_sprint(Path(tmp), 2)
            paths = dev_session.marker_paths(sprint, "T001")
            dev_session.write_marker(paths, "b" * 40)
            ok, _ = dev_session.mark_complete(sprint, "T001")
            self.assertTrue(ok)
            self.assertFalse(paths.test_done.exists())
            self.assertTrue(paths.complete.exists())
            # audit trail preserved
            self.assertIn("b" * 40, paths.complete.read_text())

    def test_refuses_when_nothing_to_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            sprint = make_sprint(Path(tmp), 2)
            ok, msg = dev_session.mark_complete(sprint, "T001")
            self.assertFalse(ok)
            self.assertIn("no test-done marker", msg)

    def test_idempotent_when_already_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            sprint = make_sprint(Path(tmp), 2)
            paths = dev_session.marker_paths(sprint, "T001")
            dev_session.write_marker(paths, "c" * 40)
            dev_session.mark_complete(sprint, "T001")
            ok, _ = dev_session.mark_complete(sprint, "T001")
            self.assertTrue(ok)


class CliTests(unittest.TestCase):
    def _run(self, args, cwd: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT_PATH), *args],
            cwd=cwd,
            capture_output=True,
            text=True,
        )

    def test_test_done_writes_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = init_repo(Path(tmp))
            sprint = make_sprint(root, 2)
            sha = make_commit(root, "tests/test_y.py", "def test_fail():\n    assert False\n", "test(T001)")
            rel_sprint = os.path.relpath(sprint, root)
            result = self._run(
                ["test-done", rel_sprint, "T001", "--commit-sha", sha],
                cwd=root,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(
                (sprint / ".in-progress" / "T001.test-session-done").exists()
            )

    def test_check_impl_ready_cli_returns_one_without_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = init_repo(Path(tmp))
            sprint = make_sprint(root, 2)
            rel_sprint = os.path.relpath(sprint, root)
            result = self._run(
                ["check-impl-ready", rel_sprint, "T001"],
                cwd=root,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("no test-done marker", result.stderr)

    def test_check_impl_ready_cli_returns_zero_when_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = init_repo(Path(tmp))
            sprint = make_sprint(root, 2)
            sha = make_commit(root, "tests/test_z.py", "def test_fail():\n    assert False\n", "test(T001)")
            paths = dev_session.marker_paths(sprint, "T001")
            dev_session.write_marker(paths, sha)
            rel_sprint = os.path.relpath(sprint, root)
            result = self._run(
                ["check-impl-ready", rel_sprint, "T001"],
                cwd=root,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_mark_complete_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = init_repo(Path(tmp))
            sprint = make_sprint(root, 2)
            paths = dev_session.marker_paths(sprint, "T001")
            dev_session.write_marker(paths, "d" * 40)
            rel_sprint = os.path.relpath(sprint, root)
            result = self._run(
                ["mark-complete", rel_sprint, "T001"],
                cwd=root,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(paths.complete.exists())

    def test_invalid_task_id_exits_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = init_repo(Path(tmp))
            sprint = make_sprint(root, 2)
            rel_sprint = os.path.relpath(sprint, root)
            result = self._run(
                ["check-impl-ready", rel_sprint, "bogus"],
                cwd=root,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("invalid task id", result.stderr)


if __name__ == "__main__":
    unittest.main()
