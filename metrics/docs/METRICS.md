# Development Metrics — Schema and Interpretation Guide (Phase 1)

*How the metrics system works, what each metric means, and how to interpret the output*

This document covers the metrics system added to the AI-Assisted Development Method (AADM). It pairs with [`metrics.py`](../scripts/metrics.py).

> **Phase 1 scope.** This release ships **gate events only**. The CLI exposes `log-gate` and `list-events`. Session-level token tracking, rework reasons, sprint-over-sprint trend analysis, and retro auto-sections are deferred to Phase 2 (issue [#13](https://github.com/colaberry/ai-assisted-development-method/issues/13)) until at least one engagement has produced calibration data. The threshold ranges that would interpret session/token data have not been validated against real teams; shipping them now would be guessing dressed up as metrics.

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

Phase 1 records one event type. Each event is an append-only JSON line in `docs/metrics/events.jsonl`. Events are immutable — if something is wrong, log a correcting event; don't edit history.

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

For ad-hoc logging — e.g. when running `/gap` manually:

```bash
python3 metrics/scripts/metrics.py log-gate --gate gap --result pass --findings 7
```

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

Phase 1 doesn't ship a `show-sprint` rollup CLI — `list-events` plus a five-line shell pipe gets you the same answer for the only event type that exists. The richer rollup commands are Phase 2.

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

**Default mental model for Phase 1:** wire `log-gate` into every gate workflow with `if: always()`. Read `list-events` at sprint close. Defer everything else (token tracking, rework reasons, rollups) until [#13](https://github.com/colaberry/ai-assisted-development-method/issues/13) — the data is worth more once the schema has been validated against real engagements.
