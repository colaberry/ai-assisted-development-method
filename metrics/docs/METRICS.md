# Development Metrics — Schema and Interpretation Guide

*How the metrics system works, what each metric means, and how to interpret the output*

This document covers the metrics system added to the AI-Assisted Development Method (AADM). It pairs with [`metrics.py`](../scripts/metrics.py).

> **What ships today.**
>
> - **Gate events** (Phase 1, #12 — stable): `log-gate` records every structural-gate pass/fail. Wired into [`reconcile.yml`](../../tooling/.github/workflows/reconcile.yml) and [`security.yml`](../../tooling/.github/workflows/security.yml) via `if: always()`.
> - **Session events** (Phase 2 partial, #13): `log-session` records a sprint-tagged work session. `sprint_close.py` refuses to lock a sprint with zero logged session events — the discipline is structural, not cultural. The retro template has a Session metrics section that pulls raw counts from the event log.
>
> **What is deliberately NOT shipped yet:**
>
> - **Interpretation ranges for sessions/rework/tokens.** The low/healthy/high thresholds that would label a sprint "high rework" or "healthy session volume" are NOT in this doc yet. Calibrating them against simulated data produces metrics that mislead more than they inform. They land in a follow-up issue once at least one real engagement has run 3+ sprints under both Phase 1 and Phase 2 logging.
> - **Per-engineer attribution.** Never, any phase. See anti-patterns below.
> - **Token / cost auto-calculation.** Deferred with the thresholds.
> - **Automated retro rollup CLI.** The retro template pulls raw counts manually via `list-events`; a `retro-section` subcommand lands with the calibrated thresholds.

---

## What Phase 1 is for

Two goals, in order of importance:

1. **Method calibration.** After a few sprints, you should be able to answer: "Are our gates actually catching things? Which gate fails most? Are failure rates dropping over time?" Today these questions get answered by vibes; vibes mislead.

2. **Gate visibility.** When `reconcile` or `security` blocks a merge, that's a structural success of the method. The events.jsonl record makes those successes — and the patterns of failure they expose — durable across sprints.

**What this system is not for:**

- Monitoring individual engineers. Events are tagged by sprint and gate, not by person. Don't add that field.
- Gaming. No metric here is meant to be optimized in isolation. A team that "improves" by skipping gates is producing worse outcomes, not better ones.
- Replacing qualitative retros. Metrics surface questions; retros answer them.

---

## What gets recorded

Two event types land as append-only JSON lines in `docs/metrics/events.jsonl`. Events are immutable — if something is wrong, log a correcting event; don't edit history.

### Event type: `gate`

Logged every time a structural gate runs — typically called automatically from CI as the final step of `reconcile.yml`, `security.yml`, etc. Pass or fail.

| Field | Meaning |
|---|---|
| `ts` | ISO 8601 timestamp (auto) |
| `event_type` | `gate` |
| `sprint` | Sprint name like `v3` (auto-detected from highest-numbered unlocked `sprints/vN/` if not specified) |
| `gate` | One of: `reconcile`, `security`, `gap`, `ui_qa`, `sprint_close` |
| `result` | `pass` or `fail` |
| `findings_count` | Optional. Number of findings (relevant for `gap`, or for `security` if you want to record non-zero finding counts on PRs that still passed) |

Gate events are the highest-signal lowest-cost metric you can capture. They take five seconds of CI config and they tell you whether the method is catching things.

### Event type: `session`

Logged at the end of every work session — whether it's a `/dev-test` or `/dev-impl` task session, a code review, or an ad-hoc investigation. The logging is done by the engineer (or the skill wrapping the engineer's session) via `log-session`, and `sprint_close.py` structurally refuses to lock a sprint with zero logged sessions. That turns session logging from cultural discipline into a hard gate.

| Field | Meaning |
|---|---|
| `ts` | ISO 8601 timestamp (auto) |
| `event_type` | `session` |
| `sprint` | Sprint name like `v3` (auto-detected if not specified) |
| `kind` | One of: `dev`, `tests`, `review`, `other` |
| `task` | Optional. Task ID like `T007` if the session was scoped to one task. |
| `rework` | Optional boolean. `true` if the session was rework on already-closed work (revisiting a completed task because of a regression, missed edge case, or post-merge issue). |

**Why the `rework` flag.** Rework rate is the single highest-signal indicator that a sprint's scope or spec quality is off. A sprint with 40% rework sessions is telling you something the gate-pass rate is not. We record it today so that when thresholds are calibrated, the data is already there. Until then: record honestly, discuss in retro, don't react to single-sprint numbers.

**What is deliberately NOT in this schema.** No `engineer` field — individual attribution creates bad incentives and doesn't answer any method-calibration question. No token counts — they're coming once cost-per-sprint becomes worth tracking against real engagement data. No `duration` field — durations self-report badly (engineers over-report short sessions and under-report long ones) and aren't worth the noise.

**On-disk shape.** Each event is one JSON object per line in `metrics/events.jsonl`:

```json
{"ts": "2026-04-21T17:32:14Z", "event_type": "session", "sprint": "v3", "kind": "tests", "task": "T007"}
{"ts": "2026-04-21T18:45:02Z", "event_type": "session", "sprint": "v3", "kind": "dev", "task": "T007"}
{"ts": "2026-04-21T20:11:48Z", "event_type": "session", "sprint": "v3", "kind": "dev", "task": "T004", "rework": true}
{"ts": "2026-04-21T20:14:33Z", "event_type": "gate", "gate": "reconcile", "result": "pass"}
```

JSONL means: one line per event, append-only, never rewrite history. `sprint_close.py` reads this file directly to confirm the active sprint has at least one session event before allowing the lock.

---

## How to log

### From CI (the default mode)

Add a final step to `reconcile.yml`:

```yaml
- name: Log gate event
  if: always()
  run: |
    if [ "${{ job.status }}" = "success" ]; then
      python3 metrics/scripts/metrics.py log-gate --gate reconcile --result pass
    else
      python3 metrics/scripts/metrics.py log-gate --gate reconcile --result fail
    fi
```

The `if: always()` is critical — without it the step is skipped when `reconcile` fails, which is exactly the case you most want to record. The same pattern works for `security.yml` (with `--gate security`) and any other gate workflow.

### From a developer terminal

For ad-hoc gate logging — e.g. when running `/gap` manually:

```bash
python3 metrics/scripts/metrics.py log-gate --gate gap --result pass --findings 7
```

### Logging a work session

At the end of every `/dev-test`, `/dev-impl`, or code-review session:

```bash
# Ordinary dev session on a specific task
python3 metrics/scripts/metrics.py log-session --kind dev --task T007

# Test-authoring session (separate context, per the method rule)
python3 metrics/scripts/metrics.py log-session --kind tests --task T007

# Rework on an already-closed task
python3 metrics/scripts/metrics.py log-session --kind dev --task T004 --rework
```

`sprint_close.py` will refuse to write `.lock` if zero session events exist for the sprint. That makes the discipline structural: forgetting to log means the sprint doesn't close.

If the `metrics/` module isn't installed in the target repo (minimum-viable adoption path: CLAUDE.md + stable IDs + `Satisfies:` + `reconcile.py` only), the session check passes with a "not installed" note and `sprint_close.py` proceeds without blocking. The structural requirement applies only when the team has opted into metrics logging.

---

## Persistence — important caveat

In Phase 1 the CLI writes to `docs/metrics/events.jsonl` in the working tree. When called from CI on a PR branch, the resulting event is **lost on squash merge** — PR branches are ephemeral. This is a known limitation.

Two workable patterns until Phase 2 closes this:

1. **Check the Actions run log.** The `Logged gate ...` line appears in the CI output. For Phase 1 you have visibility, just not aggregation.
2. **Local logging.** Engineers running `/gap` or `/sprint-close` locally write to the committed `events.jsonl`, which lives on `main`. This captures the events that matter most for retro discussions.

Phase 2 (issue [#13](https://github.com/colaberry/ai-assisted-development-method/issues/13)) will add a commit-back pattern from CI on merged PRs, so gate events from PR runs become durable. Don't build that yet — it requires a bot identity and branch-protection coordination that's worth doing once, against real demand.

---

## Querying

```bash
# All events
python3 metrics/scripts/metrics.py list-events

# Just security gates
python3 metrics/scripts/metrics.py list-events --gate security

# Just sprint v3
python3 metrics/scripts/metrics.py list-events --sprint v3

# As a JSON array (for piping into jq, a notebook, etc.)
python3 metrics/scripts/metrics.py list-events --json
```

For session counts:

```bash
# Count sessions in the current sprint (auto-detected)
python3 metrics/scripts/metrics.py count-sessions

# Count sessions in a specific sprint, as JSON
python3 metrics/scripts/metrics.py count-sessions --sprint v3 --json

# Just session events, one per line
python3 metrics/scripts/metrics.py list-events --event-type session --sprint v3
```

The retro template's Session metrics section pulls raw counts from these commands. Rollup commands that would *interpret* the counts (healthy / high / low thresholds, rework-rate alerts, sprint-over-sprint trends) are deferred until real engagement data calibrates the ranges — see the opening caveat.

---

## Anti-patterns

### Logging only passes

The whole point of CI integration is that **failure** events get captured automatically. If your wiring uses `if: success()` instead of `if: always()`, you're filtering out the most interesting data. Pass-only logs tell you nothing about whether the method is catching things.

### Gaming gate counts

If gate-pass rates get used for performance evaluation, engineers will route around the gates (commit directly to main, mark sprints `[DEFERRED]` to dodge `/sprint-close`, etc.). The metrics are method calibration data, not engineer scorecards. Don't publish per-engineer aggregations.

### Acting on noise

A single sprint with three reconcile failures is one sprint. Three sprints with three reconcile failures each is a pattern. Wait for a pattern before changing process.

### Ignoring the data

The other failure mode: events accumulate but no one reads them. If you're not pulling `list-events` into retros at least every other sprint, the system isn't earning its keep — either start using it or stop wiring it.

---

## What NOT to track (in any phase)

These were considered and deliberately excluded:

| Metric | Why excluded |
|---|---|
| Lines of code | Gamed trivially. A refactor that deletes 500 lines is good work that would look like negative progress. |
| Test count | Rewards writing more tests, not better tests. The test matrix already constrains test quality better than a count does. |
| Commit count | Rewards noise. Forces choice between atomic commits and batch commits for metric purposes. |
| Time per engineer | Surveillance. Not useful for method calibration. Creates bad incentives. |
| Typing speed / keystrokes | Correlated with nothing useful. Full-stop surveillance. |

If you're tempted to add one, check your actual question first. Usually there's a better metric — or a qualitative retro discussion — that answers the same question without the incentive problems.

---

## Retention

Events are append-only and never deleted. Some consequences:

- The file grows. At Phase 1 volumes (gate events only, a handful per sprint), this is a non-issue — a year of active development produces a few hundred lines.
- You can reconstruct any historical sprint's gate metrics exactly.
- Privacy considerations: events contain sprint names and gate names. They're safe to share externally; they don't contain sensitive content.

For projects that run for years, consider an annual archive: move older events to `docs/metrics/archive/YYYY.jsonl` and start a fresh `events.jsonl`.

---

## Integration with the method

Gate events complement but don't replace existing method artifacts:

- **`reconcile.py` and `security.yml`** are the gates themselves. The metrics system records that they ran and what they found.
- **Failures log** captures *what went wrong and why*. Metrics capture *that the gate caught it*. A high-rework area might or might not become a failures-log entry.
- **Retrospectives** remain qualitative and human-led. Metrics inform retros; they don't replace retro discussion.
- **Client-facing artifacts** should generally exclude metrics. These are internal data for internal decisions.

---

## When to stop tracking

A legitimate outcome is: you run Phase 1 for 3 months, review it at a retro, find that you're not acting on the data, and stop. That's fine — deliberately abandoning a tool that isn't earning its keep is better than maintaining it out of obligation.

Before stopping, ask:

- Did we make any process change based on a gate-failure pattern? If yes, it's earning its keep.
- Did a retro reference the events.jsonl content? If yes, keep going.
- Is the CI overhead being paid but the data never read? If yes, either start reading it or remove the wiring.

Tools are levers. If the lever isn't moving anything, put it down.

---

## Summary

| Task | Command |
|---|---|
| Log a gate event (CI or manual) | `metrics.py log-gate --gate <name> --result pass\|fail` |
| Log with a findings count | `metrics.py log-gate --gate gap --result pass --findings 7` |
| List all events | `metrics.py list-events` |
| Filter by sprint or gate | `metrics.py list-events --sprint v3 --gate security` |
| Emit as JSON | `metrics.py list-events --json` |

| Log a session event | `metrics.py log-session --kind dev --task T007` |
| Mark a session as rework | `metrics.py log-session --kind dev --task T004 --rework` |
| Count sessions for a sprint | `metrics.py count-sessions --sprint v3 --json` |
| List just session events | `metrics.py list-events --event-type session --sprint v3` |

**Default mental model.** Wire `log-gate` into every gate workflow with `if: always()`. Log a session event at the end of every `/dev-test`, `/dev-impl`, or code-review session — the `sprint_close.py` check will bounce the lock if you don't. Read the raw session counts in retro. Defer threshold-based interpretation (healthy / high / low) until real engagement data calibrates the ranges in a follow-up to [#13](https://github.com/colaberry/ai-assisted-development-method/issues/13).
