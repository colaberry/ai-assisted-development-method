# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The method document carries its own version scheme (v3.x.y); tooling and skills are versioned independently and listed in each release section.

## [Unreleased]

### Added

- **Semgrep security merge gate** ([#7](https://github.com/colaberry/ai-assisted-development-method/issues/7)) — [tooling/.github/workflows/security.yml](tooling/.github/workflows/security.yml) runs Semgrep (`--config=auto --severity=ERROR`) on every PR and push to main as a structural merge gate alongside [reconcile.yml](tooling/.github/workflows/reconcile.yml). Traceability + security are now the two structural gates; manual `/security-review` becomes the escalation path, not the only layer. Deliberate suppressions live in `docs/security/suppressions.md` (see [tooling/templates/security-suppressions-TEMPLATE.md](tooling/templates/security-suppressions-TEMPLATE.md)) with a 90-day re-review ceremony enforced by `state-check.py`. Handbook §1.9 "Security as a merge gate" documents the discipline.
- **Metrics Phase 1 — gate-event logger** ([#12](https://github.com/colaberry/ai-assisted-development-method/issues/12)) — new [`metrics/`](metrics/) module with [`metrics.py log-gate`](metrics/scripts/metrics.py) and `list-events` commands. The two structural-gate workflows ([reconcile.yml](tooling/.github/workflows/reconcile.yml), [security.yml](tooling/.github/workflows/security.yml)) now call `log-gate` as a final step with `if: always()`, so pass/fail records accumulate as JSONL in `docs/metrics/events.jsonl` without requiring engineer discipline. Phase 1 persistence has a known limitation (PR-branch events are lost on squash merge); durable commit-back lands in [Phase 2 (#13)](https://github.com/colaberry/ai-assisted-development-method/issues/13). Session-level token tracking, rework-reason logging, and retro auto-sections are deferred to Phase 2 — the threshold ranges that would interpret session data have not been validated against real teams.

### Planned

Prioritized roadmap — items listed in rough order of leverage-per-effort.

- **Symbol-presence check in `reconcile.py`** — today it verifies that `Files:` paths exist; upgrade to also grep each path for a symbol implied by `Satisfies:` or `Acceptance:`. Closes the "empty stub passes reconcile" hole.
- **`sprint-close.py`** — atomic closure script that runs `reconcile.py --ci`, verifies required artifacts (RETRO.md with non-template content, reviewer sign-off marker), and writes `.lock` only on success.
- **PreToolUse hook** — blocks `Write`/`Edit` under `sprints/vN+1/` when `sprints/vN/.lock` is missing. Makes the anti-skip gate structural rather than cultural.
- **state-check fixes** — path-component match for test-modification detection (currently substring), widen the detection window from 2 days to "since last `.lock`," add unfilled-`<BRACKETED>`-placeholder check in CLAUDE.md, parse `Status:` in failures-log entries to count only active rules, warn when `find_active_initiative()` has multiple design docs to choose from.
- **Minimum-viable adoption doc** — a lighter-touch starting path (CLAUDE.md + stable IDs + `Satisfies:` + `reconcile.py` in CI) for teams who can't adopt the full method day one.
- **Method skills** — `/prd`, `/dev`, `/sprint-close` as Claude Code skills that wrap the enforcement scripts. Each reads `state-check.py --json` to verify preconditions before proceeding.
- **Gate ceremony skills** — `/gate-1-to-2`, `/gate-2-to-3` for Internal Product Mode graduation gates, reusing the interview protocol from the state-check skill.
- **Tightened Gate 2 criteria in Internal Product Mode** — add a concrete retention metric (e.g., N-week self-directed return rate) to prevent graduation on optimism.
- **Resolve the Stage 1 test-matrix contradiction** — Internal Product Mode lists Category D as "only if time permits" in the table but treats it as required in the anti-patterns section. Reconcile.
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
