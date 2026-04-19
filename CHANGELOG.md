# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The method document carries its own version scheme (v3.x.y); tooling and skills are versioned independently and listed in each release section.

## [Unreleased]

### Added

- **Semgrep security merge gate** ([#7](https://github.com/colaberry/ai-assisted-development-method/issues/7)) — [tooling/.github/workflows/security.yml](tooling/.github/workflows/security.yml) runs Semgrep (`--config=auto --severity=ERROR`) on every PR and push to main as a structural merge gate alongside [reconcile.yml](tooling/.github/workflows/reconcile.yml). Traceability + security are now the two structural gates; manual `/security-review` becomes the escalation path, not the only layer. Deliberate suppressions live in `docs/security/suppressions.md` (see [tooling/templates/security-suppressions-TEMPLATE.md](tooling/templates/security-suppressions-TEMPLATE.md)) with a 90-day re-review ceremony enforced by `state-check.py`. Handbook §1.9 "Security as a merge gate" documents the discipline.
- **`sprint_close.py` — atomic sprint closure** — [tooling/scripts/sprint_close.py](tooling/scripts/sprint_close.py) promotes the manual `/sprint-close` checklist to a script. Runs `reconcile.py --ci` (with optional `--strict-symbols` pass-through), verifies that `RETRO.md` is no longer the template stub (no `<placeholder>`, no literal `vN`, no literal `YYYY-MM-DD`, sections "What went well" and "What went poorly" contain real content), and verifies a sign-off (either an existing `SIGNOFF.md` with `Reviewer:` + `Date:` lines, or `--reviewer NAME` to create one). Writes `sprints/vN/.lock` only when every check passes — no partial closures. The `.lock` content records `locked_at`, `reviewer`, and `reconcile_status`, ready for downstream tooling (the planned PreToolUse hook will read this). Tests in [tooling/tests/test_sprint_close.py](tooling/tests/test_sprint_close.py) (23/23 pass).
- **Symbol-presence check in `reconcile.py`** — [tooling/scripts/reconcile.py](tooling/scripts/reconcile.py) now extracts candidate symbols from each task's title and `Acceptance:` line (backticked tokens are the strongest signal; bare `snake_case`/`camelCase`/`ALL_CAPS` identifiers are also picked up) and greps each task's `Files:` for them. A completed task whose listed files exist but contain none of those symbols gets a `STUB-WARNING:` note and is demoted to MEDIUM confidence — the "empty stub passes reconcile" pattern. New `--strict-symbols` flag elevates that pattern to a missing requirement (CI exit 1); off by default so existing pipelines don't break. Tests in [tooling/tests/test_reconcile.py](tooling/tests/test_reconcile.py) (21/21 pass). Method §/reconcile already promised this behavior — this lands the implementation.
- **Method document text fixes** — three method-level cleanups in [internal-mode/Internal_Product_Mode.md](internal-mode/Internal_Product_Mode.md) plus a new minimum-viable adoption path. (1) Stage 1 test-matrix contradiction resolved: Category D is now explicitly required wherever code touches existing production systems and optional otherwise — the table, the prose, and the anti-pattern now agree. (2) Gate 2 → 3 retention criterion tightened from "users keep coming back without being prompted" to a concrete pre-committed metric (default heuristic: ≥40% of Stage 2 users return self-directed in ≥3 of the 4 weeks following first meaningful use), with explicit guidance to pick metric and threshold before reading the data. (3) New [MINIMUM-VIABLE-ADOPTION.md](MINIMUM-VIABLE-ADOPTION.md) at repo root describes a four-piece adoption path (CLAUDE.md + stable IDs + `Satisfies:` + `reconcile.py` in CI) under a day for teams who can't take the full-bundle bootstrap; linked from [README.md](README.md) and [START-HERE.md](START-HERE.md).
- **Metrics Phase 1 — gate-event logger** ([#12](https://github.com/colaberry/ai-assisted-development-method/issues/12)) — new [`metrics/`](metrics/) module with [`metrics.py log-gate`](metrics/scripts/metrics.py) and `list-events` commands. The two structural-gate workflows ([reconcile.yml](tooling/.github/workflows/reconcile.yml), [security.yml](tooling/.github/workflows/security.yml)) now call `log-gate` as a final step with `if: always()`, so pass/fail records accumulate as JSONL in `docs/metrics/events.jsonl` without requiring engineer discipline. Phase 1 persistence has a known limitation (PR-branch events are lost on squash merge); durable commit-back lands in [Phase 2 (#13)](https://github.com/colaberry/ai-assisted-development-method/issues/13). Session-level token tracking, rework-reason logging, and retro auto-sections are deferred to Phase 2 — the threshold ranges that would interpret session data have not been validated against real teams.

### Planned

Prioritized roadmap — items listed in rough order of leverage-per-effort.

- **PreToolUse hook** — blocks `Write`/`Edit` under `sprints/vN+1/` when `sprints/vN/.lock` is missing. Makes the anti-skip gate structural rather than cultural.
- **state-check fixes** — path-component match for test-modification detection (currently substring), widen the detection window from 2 days to "since last `.lock`," add unfilled-`<BRACKETED>`-placeholder check in CLAUDE.md, parse `Status:` in failures-log entries to count only active rules, warn when `find_active_initiative()` has multiple design docs to choose from.
- **Method skills** — `/prd`, `/dev`, `/sprint-close` as Claude Code skills that wrap the enforcement scripts. Each reads `state-check.py --json` to verify preconditions before proceeding.
- **Gate ceremony skills** — `/gate-1-to-2`, `/gate-2-to-3` for Internal Product Mode graduation gates, reusing the interview protocol from the state-check skill.
- **AI code-smell review checklist** ([#5](https://github.com/colaberry/ai-assisted-development-method/issues/5)) — handbook chapter + `tooling/templates/code-review-AI-CHECKLIST.md` targeting AI-specific PR review failure modes (surface correctness, invented APIs, silent scope creep). Pure-doc change; land first.
- **`/incident` skill** ([#6](https://github.com/colaberry/ai-assisted-development-method/issues/6)) — post-deployment learning loop. Writes a post-mortem, extracts prevention rules into `docs/failures/`, optionally drafts a design-doc update PR when an incident invalidates a requirement. Completes the SDLC coverage that today stops at sprint close.
- **`Autonomy:` annotation in TASKS.md** ([#8](https://github.com/colaberry/ai-assisted-development-method/issues/8)) — optional per-task line (`direct` | `checkpoint` | `review-only`) that tunes how often `/dev` pauses for human confirmation. Ties autonomy to task risk and test coverage.

## [3.2.1] — 2026-04-16

### Added

- **Phase 0** — client discovery and design-doc authoring before sprint work begins. Turns vague client input into signed-off requirements with assigned stable IDs. See [method/AI_Assisted_Development_Method_v3_2_1.md](method/AI_Assisted_Development_Method_v3_2_1.md).
- **Client intake template** ([tooling/templates/client-intake-TEMPLATE.md](tooling/templates/client-intake-TEMPLATE.md)) — 14 sections covering engagement metadata, problem framing, users and stakeholders, integrations, non-functional requirements, constraints, open questions, team context, risk assessment, commercial terms, and handoff readiness. `[REQUIRED]` fields block Phase 0 closure.
- **Internal Product Mode v1.0** ([internal-mode/Internal_Product_Mode.md](internal-mode/Internal_Product_Mode.md)) — companion process for internal product development that may eventually ship as SaaS. Three evidence-based stages (Exploration → Validation → Commercialization) with explicit graduation gates requiring written decision documents.
- **state-check v0.1** — paired CLI ([state-check/scripts/state-check.py](state-check/scripts/state-check.py)) and Claude Code skill ([state-check/.claude/skills/state-check.md](state-check/.claude/skills/state-check.md)) that detect repo mode, stage, active sprint, and flag P0/P1/P2 issues. Filesystem-derived detection (no separate config); heads-up display, not autopilot. First skill in the bundle.

### Notes

- v3.2.1 is a drop-in replacement for v3.2. Teams already on v3.2 can adopt Phase 0 incrementally on the next new engagement.
- Internal Product Mode is v1.0 intentionally, not v3.x — it is synthesized from general principles and has not yet been validated on a full engagement cycle. Treat as a starting point, not settled doctrine.

## [3.2] and earlier

Version history prior to v3.2.1 is not tracked in this changelog. See the method document for context on the evolution of the approach and the post-mortem (8-of-30 missing requirements on a threading initiative) that motivated the structural-gate design.
