# Metrics (Phase 1)

A lightweight development metrics system for the AI-Assisted Development Method (AADM). Phase 1 ships **gate event logging only** — every time a structural gate (`reconcile`, `security`, `gap`, `ui_qa`, `sprint_close`) runs, an append-only JSONL record captures the result. Designed to be called from CI so no engineer discipline is required.

Token-level session metrics, rework-reason tracking, and retro auto-sections are deferred to [Phase 2 (#13)](https://github.com/colaberry/ai-assisted-development-method/issues/13). Threshold ranges that would interpret session data have not been validated; shipping them now would be guessing dressed up as metrics.

## What's here

```
scripts/
└── metrics.py           # log-gate + list-events
docs/
└── METRICS.md           # Schema, CI wiring, interpretation, anti-patterns, deferred items
tests/
└── test_metrics.py      # Unit tests
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

# Read what's been captured
python3 scripts/metrics.py list-events --sprint v3
```

## Persistence — important caveat

In Phase 1, events written from CI on a PR branch are lost on squash merge (PR branches are ephemeral). The `Logged gate ...` line still appears in the Actions run log — you have visibility, just not aggregation across PRs.

Phase 2 (#13) adds a commit-back pattern from CI on merged PRs. Until then, the highest-value events to capture are the ones engineers log locally: `/gap` runs, `/sprint-close` outcomes, and any gate run on `main` directly.

## Honest caveats

- This is the first cut. The CI persistence story is incomplete by design.
- A team that runs Phase 1 for a quarter and finds the data isn't changing decisions should stop — not keep wiring more of it. See "When to stop tracking" in `docs/METRICS.md`.
- Treat metrics as **prompts for conversation in retros**, not as verdicts about performance.

## Relationship to other AADM tooling

- **`reconcile.py` / `security.yml`** are the gates. Metrics record that they ran.
- **`state-check.py`** answers "where am I right now"; metrics answer "what happened across these sprints." Orthogonal.
- **Developer Handbook Part 6 ("Getting better at this")** points here for calibration data once you've collected enough events to read patterns.

## Version

0.1 — Phase 1, gate events only. Phase 2 (#13) lands when one engagement has produced ≥3 sprints of Phase 1 data.
