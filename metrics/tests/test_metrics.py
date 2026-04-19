"""Self-tests for metrics.py (Phase 1: gate events only).

Run with:  python3 metrics/tests/test_metrics.py
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


@contextlib.contextmanager
def _silence_stdout():
    """Suppress cmd_log_gate's confirmation print during tests."""
    saved = sys.stdout
    sys.stdout = io.StringIO()
    try:
        yield
    finally:
        sys.stdout = saved


def _load_metrics():
    here = Path(__file__).resolve().parent
    script = here.parent / "scripts" / "metrics.py"
    spec = importlib.util.spec_from_file_location("metrics", script)
    module = importlib.util.module_from_spec(spec)
    sys.modules["metrics"] = module
    spec.loader.exec_module(module)
    return module


m = _load_metrics()


def _ns(**kwargs) -> argparse.Namespace:
    """Build an argparse.Namespace with sensible Phase 1 defaults."""
    defaults = {
        "sprint": None,
        "gate": None,
        "result": None,
        "findings": None,
        "json": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class HelpersTests(unittest.TestCase):
    def test_metrics_dir_returns_path_without_creating(self):
        # Read-path callers (load_events, list-events) must not materialize
        # docs/metrics/ — only append_event creates it.
        with tempfile.TemporaryDirectory() as tmp:
            d = m.metrics_dir(Path(tmp))
            self.assertEqual(d, Path(tmp) / "docs" / "metrics")
            self.assertFalse(d.exists())

    def test_load_events_does_not_create_metrics_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(m.load_events(Path(tmp)), [])
            self.assertFalse((Path(tmp) / "docs" / "metrics").exists())

    def test_append_event_creates_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            m.append_event(repo, {"event_type": "gate", "gate": "reconcile", "result": "pass"})
            self.assertTrue((repo / "docs" / "metrics" / "events.jsonl").is_file())

    def test_iso_now_is_parseable_utc(self):
        from datetime import datetime
        ts = m.iso_now()
        # Should round-trip through fromisoformat without raising.
        parsed = datetime.fromisoformat(ts)
        self.assertIsNotNone(parsed.tzinfo)


class DetectActiveSprintTests(unittest.TestCase):
    def test_no_sprints_dir_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(m.detect_active_sprint(Path(tmp)))

    def test_empty_sprints_dir_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "sprints").mkdir()
            self.assertIsNone(m.detect_active_sprint(Path(tmp)))

    def test_picks_highest_unlocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            for n in (1, 2, 3):
                (Path(tmp) / "sprints" / f"v{n}").mkdir(parents=True)
            (Path(tmp) / "sprints" / "v1" / ".lock").touch()
            (Path(tmp) / "sprints" / "v2" / ".lock").touch()
            # v3 unlocked → active
            self.assertEqual(m.detect_active_sprint(Path(tmp)), "v3")

    def test_skips_locked_returns_lower_unlocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            for n in (1, 2, 3):
                (Path(tmp) / "sprints" / f"v{n}").mkdir(parents=True)
            (Path(tmp) / "sprints" / "v3" / ".lock").touch()
            self.assertEqual(m.detect_active_sprint(Path(tmp)), "v2")

    def test_all_locked_returns_most_recent(self):
        with tempfile.TemporaryDirectory() as tmp:
            for n in (1, 2):
                d = Path(tmp) / "sprints" / f"v{n}"
                d.mkdir(parents=True)
                (d / ".lock").touch()
            self.assertEqual(m.detect_active_sprint(Path(tmp)), "v2")

    def test_ignores_non_vN_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "sprints" / "v1").mkdir(parents=True)
            (Path(tmp) / "sprints" / "scratch").mkdir(parents=True)
            (Path(tmp) / "sprints" / "v1-archived").mkdir(parents=True)
            self.assertEqual(m.detect_active_sprint(Path(tmp)), "v1")


class LogGateTests(unittest.TestCase):
    def test_writes_event_with_required_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            args = _ns(gate="reconcile", result="pass", sprint="v3")
            with _silence_stdout():
                self.assertEqual(m.cmd_log_gate(args, repo), 0)
            events = m.load_events(repo)
            self.assertEqual(len(events), 1)
            e = events[0]
            self.assertEqual(e["event_type"], "gate")
            self.assertEqual(e["gate"], "reconcile")
            self.assertEqual(e["result"], "pass")
            self.assertEqual(e["sprint"], "v3")
            self.assertIn("ts", e)
            self.assertNotIn("findings_count", e)

    def test_findings_field_only_when_provided(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            with _silence_stdout():
                m.cmd_log_gate(_ns(gate="gap", result="pass", findings=7), repo)
                m.cmd_log_gate(_ns(gate="security", result="fail"), repo)
            events = m.load_events(repo)
            self.assertEqual(events[0]["findings_count"], 7)
            self.assertNotIn("findings_count", events[1])

    def test_findings_zero_is_recorded(self):
        # 0 findings is a meaningful signal (clean security run); must not be
        # confused with "no count provided" by the `is not None` check.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            with _silence_stdout():
                m.cmd_log_gate(_ns(gate="gap", result="pass", findings=0), repo)
            self.assertEqual(m.load_events(repo)[0]["findings_count"], 0)

    def test_appends_does_not_truncate(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            with _silence_stdout():
                for i in range(5):
                    m.cmd_log_gate(_ns(gate="reconcile", result="pass", sprint=f"v{i}"), repo)
            events = m.load_events(repo)
            self.assertEqual(len(events), 5)
            self.assertEqual([e["sprint"] for e in events], [f"v{i}" for i in range(5)])

    def test_sprint_auto_detected_when_not_passed(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "sprints" / "v4").mkdir(parents=True)
            with _silence_stdout():
                m.cmd_log_gate(_ns(gate="security", result="pass"), repo)
            self.assertEqual(m.load_events(repo)[0]["sprint"], "v4")

    def test_sprint_field_is_none_when_no_sprints_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            with _silence_stdout():
                m.cmd_log_gate(_ns(gate="reconcile", result="fail"), repo)
            self.assertIsNone(m.load_events(repo)[0]["sprint"])


class LoadEventsTests(unittest.TestCase):
    def test_no_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(m.load_events(Path(tmp)), [])

    def test_skips_blank_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            f = m.events_file(repo)
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(
                json.dumps({"event_type": "gate", "gate": "reconcile", "result": "pass"})
                + "\n\n  \n"
                + json.dumps({"event_type": "gate", "gate": "security", "result": "fail"})
                + "\n",
                encoding="utf-8",
            )
            events = m.load_events(repo)
            self.assertEqual(len(events), 2)

    def test_malformed_line_warns_and_continues(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            f = m.events_file(repo)
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(
                "{not json\n"
                + json.dumps({"event_type": "gate", "gate": "reconcile", "result": "pass"})
                + "\n",
                encoding="utf-8",
            )
            # Capture stderr to verify the warning fires without polluting test output.
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                events = m.load_events(repo)
            self.assertEqual(len(events), 1)
            self.assertIn("malformed event line skipped", buf.getvalue())


class ListEventsTests(unittest.TestCase):
    def _seed(self, repo: Path) -> None:
        with _silence_stdout():
            m.cmd_log_gate(_ns(gate="reconcile", result="pass", sprint="v1"), repo)
            m.cmd_log_gate(_ns(gate="security", result="pass", sprint="v1"), repo)
            m.cmd_log_gate(_ns(gate="reconcile", result="fail", sprint="v2"), repo)
            m.cmd_log_gate(_ns(gate="security", result="pass", sprint="v2"), repo)

    def test_filter_by_sprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._seed(repo)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                m.cmd_list_events(_ns(sprint="v1", json=True), repo)
            payload = json.loads(buf.getvalue())
            self.assertEqual(len(payload), 2)
            self.assertTrue(all(e["sprint"] == "v1" for e in payload))

    def test_filter_by_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._seed(repo)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                m.cmd_list_events(_ns(gate="security", json=True), repo)
            payload = json.loads(buf.getvalue())
            self.assertEqual(len(payload), 2)
            self.assertTrue(all(e["gate"] == "security" for e in payload))

    def test_combined_filters(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._seed(repo)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                m.cmd_list_events(_ns(sprint="v2", gate="reconcile", json=True), repo)
            payload = json.loads(buf.getvalue())
            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["result"], "fail")


class CLIIntegrationTests(unittest.TestCase):
    """End-to-end via subprocess to confirm the CLI surface matches the docs."""

    def test_log_gate_then_list_events_jsonl(self):
        import subprocess
        script = Path(__file__).resolve().parent.parent / "scripts" / "metrics.py"
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run(
                ["python3", str(script), "--repo-root", tmp,
                 "log-gate", "--gate", "reconcile", "--result", "pass", "--sprint", "v1"],
                capture_output=True, text=True, check=True,
            )
            self.assertIn("Logged gate reconcile: pass", r.stdout)

            r2 = subprocess.run(
                ["python3", str(script), "--repo-root", tmp, "list-events", "--json"],
                capture_output=True, text=True, check=True,
            )
            payload = json.loads(r2.stdout)
            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["gate"], "reconcile")

    def test_help_subcommand_exits_zero(self):
        import subprocess
        script = Path(__file__).resolve().parent.parent / "scripts" / "metrics.py"
        r = subprocess.run(
            ["python3", str(script), "--help"],
            capture_output=True, text=True,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("log-gate", r.stdout)
        self.assertIn("list-events", r.stdout)


if __name__ == "__main__":
    unittest.main()
