# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The method document carries its own version scheme (v3.x.y); tooling and skills are versioned independently and listed in each release section.

## [Unreleased]

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
