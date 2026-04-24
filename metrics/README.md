# Metrics

A lightweight development metrics system for the AI-Assisted Development Method (AADM). Two event types ship today:

- **Gate events** (Phase 1, stable) — every time a structural gate (`reconcile`, `security`, `gap`, `ui_qa`, `sprint_close`) runs, an append-only JSONL record captures the result. Called from CI; no engineer discipline required.
- **Session events** (Phase 2 partial, [#13](https://github.com/colaberry/AADM-Ai-Assisted-Development-Method/issues/13)) — logged by the engineer at session end. `sprint_close.py` refuses to lock a sprint with zero logged sessions, so the discipline is structural not cultural. The retro template has a Session metrics section populated from raw counts.

**Deliberately not shipped yet:** threshold ranges that would *interpret* session counts (healthy / high / low, rework-rate alerts, tokens/session). Calibrating them against simulated data produces metrics that mislead more than they inform. They land in a follow-up once at least one real engagement has run 3+ sprints under both Phase 1 gate logging and Phase 2 session logging.

## What's here

```
scripts/
└── metrics.py           # log-gate, log-session, count-sessions, list-events
docs/
└── METRICS.md           # Schema, CI wiring, session logging, anti-patterns, deferred items
tests/
└── test_metrics.py      # Unit tests (32 tests)
```

## Getting started on a client repo

```bash
# Install the script
mkdir -p <your-repo>/scripts
cp scripts/metrics.py <your-repo>/scripts/
chmod +x <your-repo>/scripts/metrics.py

# Install the interpretation guide
mkdir -p <your-repo>/docs/metrics
cp docs/METRICS.md <your-repo>/docs/metrics/

# Verify
python3 <your-repo>/scripts/metrics.py --help
```

Then add a `Log gate event` step to each of your gate workflows (`reconcile.yml`, `security.yml`, etc.). The exact pattern is in [`docs/METRICS.md`](docs/METRICS.md#from-ci-the-default-mode); the AADM template workflows already include it.

## Quick usage

```bash
# After a CI gate run (pattern from inside reconcile.yml / security.yml)
python3 scripts/metrics.py log-gate --gate reconcile --result pass

# Manually after running /gap
python3 scripts/metrics.py log-gate --gate gap --result pass --findings 7

# At the end of every work session (required by sprint_close.py)
python3 scripts/metrics.py log-session --kind dev --task T007
python3 scripts/metrics.py log-session --kind tests --task T007
python3 scripts/metrics.py log-session --kind dev --task T004 --rework

# Count sessions; read what's been captured
python3 scripts/metrics.py count-sessions --sprint v3
python3 scripts/metrics.py list-events --event-type session --sprint v3
```

## Persistence — important caveat

`scripts/metrics.py` writes one JSONL line per event to `metrics/events.jsonl` in whatever working tree it runs in. That file is the only persistence layer — there's no database, no remote sink, no aggregation service.

What that means in practice:

- **Local runs persist.** When an engineer runs `python3 scripts/metrics.py log-session ...` locally, the line lands in the working tree's `metrics/events.jsonl`. Commit the file (or commit it as part of `/sprint-close`) to keep the record on `main`.
- **CI runs on PR branches are ephemeral.** Events written from CI on a feature branch live in that branch's checkout and are lost when the PR squash-merges. The `Logged gate ...` line still appears in the Actions run log — you have run-level visibility, just not aggregation across PRs.
- **`main`-branch CI runs persist** if your workflow commits the file back. AADM's template workflows leave that wiring as a follow-up; until then, the highest-value events to capture are the ones engineers log locally: `/gap` runs, `/sprint-close` outcomes, session events, and any gate run on `main` directly.

`sprint_close.py`'s `sessions_logged` check reads `metrics/events.jsonl` directly — if the file is missing or empty for the active sprint, the close refuses with a "no session events logged for vN" message. That's the structural backstop for the discipline.

## Honest caveats

- This is the first cut. The CI persistence story is incomplete by design.
- A team that runs Phase 1 for a quarter and finds the data isn't changing decisions should stop — not keep wiring more of it. See "When to stop tracking" in `docs/METRICS.md`.
- Treat metrics as **prompts for conversation in retros**, not as verdicts about performance.

## Relationship to other AADM tooling

- **`reconcile.py` / `security.yml`** are the gates. Metrics record that they ran.
- **`state-check.py`** answers "where am I right now"; metrics answer "what happened across these sprints." Orthogonal.
- **Developer Handbook Part 6 ("Getting better at this")** points here for calibration data once you've collected enough events to read patterns.

## Version

0.2 — gate events (Phase 1) + session events with structural `sprint_close.py` refusal (Phase 2 partial, #13). Threshold calibration lands in a follow-up when one engagement has produced ≥3 sprints of combined gate + session data.
