# AI-Assisted Development Method (AADM)

**AADM** is a structured process for shipping enterprise-grade software with Claude Code. Designed for small teams (3–10 engineers) delivering to external clients, with a companion mode for internal product development that may eventually ship as SaaS.

**Current versions:** Method v3.2.1 · Internal Product Mode v1.0 · state-check v0.1

## Core thesis

Automate what you would otherwise ask reviewers to check, and make skipping steps structurally impossible instead of culturally discouraged. Requirements carry stable IDs (§X.Y, Dn, Qn, SOW-§X.Y) that propagate from the contract through the design doc, sprint PRDs, and tasks to code. [`reconcile.py`](tooling/scripts/reconcile.py) enforces traceability in CI.

The method operates at two levels:

- **Initiative level** — a multi-sprint effort to ship a design document. Preceded by **Phase 0** (discovery and design-doc authoring) when the client hasn't handed you a complete spec. Gated by `/gap` at the end.
- **Sprint level** — one sprint of an initiative. Gated by `/sprint-close` before the next sprint can start.

## What this solves

- **PRD → gap analysis → new PRD loops.** Solved by stable requirement IDs plus CI-enforced coverage.
- **Vague client input instead of a spec.** Phase 0 with the intake template turns vague input into signed-off requirements.
- **Sprint-skipping across multi-sprint initiatives.** Solved by `/sprint-close` as a structural gate.
- **Silent descoping.** Solved by the `[DEFERRED]` discipline in tasks.
- **Tests that look thorough but miss real bugs.** Solved by the test matrix (categories D and E specifically) plus periodic mutation testing.
- **Repeating the same class of bug.** Solved by the failures log feeding forward into new design docs.

## What's in this repo

```
.
├── START-HERE.md             # Reading order and bootstrap steps
├── method/                   # Method document (v3.2.1)
├── handbook/                 # Practical guide for engineers
├── internal-mode/            # Companion mode for internal product work
├── state-check/              # Repo-state detection CLI + Claude Code skill
├── metrics/                  # Gate-event logger (Phase 1) — calibration data for retros
└── tooling/                  # reconcile.py, CI workflows, templates
```

## Quick start

Read [START-HERE.md](START-HERE.md) first. It covers the reading order (60–90 min for tech leads, 45 min for engineers) and the bootstrap steps for a new client repo.

If you want to adopt AADM on an existing project but can't take a full-bundle bootstrap, read [MINIMUM-VIABLE-ADOPTION.md](MINIMUM-VIABLE-ADOPTION.md) instead — four pieces (CLAUDE.md + stable IDs + `Satisfies:` + `reconcile.py` in CI) under a day, compatible with adopting the rest later.

## Reading order by role

- **Tech leads and PMs:** [method/](method/) first. Read [internal-mode/](internal-mode/) if you build products internally. Reference [handbook/](handbook/) when onboarding engineers.
- **Engineers:** [handbook/](handbook/) first. Reference [method/](method/) for context and rationale.
- **New engineer onboarding:** [handbook/](handbook/) + your project's `CLAUDE.md` + recent entries in `docs/failures/`.

## Tooling

- **[sprint_close.py](tooling/scripts/sprint_close.py)** — atomic sprint closure. Runs `reconcile.py --ci`, verifies `RETRO.md` is filled (no template markers, sections 1-2 have real content), verifies `SIGNOFF.md` exists with `Reviewer:` + `Date:` (or accepts `--reviewer NAME` to create one), then writes `sprints/vN/.lock` recording who closed the sprint and when. No partial closures. Python stdlib only.
- **[reconcile.py](tooling/scripts/reconcile.py)** — sprint coverage check. Verifies every PRD requirement is satisfied by a completed task or marked `[DEFERRED]`, that listed `Files:` exist, and (new) that symbols extracted from each task's title and `Acceptance:` line actually appear in those files — closes the "empty stub passes reconcile" hole. `--strict-symbols` opts into hard-failing on stubs. Python stdlib only. Runs in CI via [reconcile.yml](tooling/.github/workflows/reconcile.yml) as a merge gate.
- **[security.yml](tooling/.github/workflows/security.yml)** — Semgrep-based security merge gate. Blocks PRs on any ERROR-severity finding. Deliberate suppressions live in [docs/security/suppressions.md](tooling/templates/security-suppressions-TEMPLATE.md) with a 90-day re-review ceremony enforced by `state-check.py`.
- **[sprint_gate.py](tooling/hooks/sprint_gate.py)** — Claude Code `PreToolUse` hook. Blocks `Write`/`Edit`/`MultiEdit`/`NotebookEdit` under `sprints/vK/` when any earlier `sprints/vJ/` (J < K) is missing a `.lock` file. The structural complement to `sprint_close.py`: `sprint_close.py` decides when `.lock` gets written, `sprint_gate.py` decides what the agent can touch based on whose `.lock` exists. Install via [claude-settings-hooks-TEMPLATE.json](tooling/templates/claude-settings-hooks-TEMPLATE.json).
- **[state-check.py](state-check/scripts/state-check.py)** — detects current repo state (mode, stage, active sprint, flags). Heads-up display, not autopilot. Ships with a [Claude Code skill](state-check/.claude/skills/state-check.md) for conversational use.
- **[metrics.py](metrics/scripts/metrics.py)** — append-only event log for development metrics. Two event types ship: **gate events** (Phase 1 — CI workflows call `log-gate` on every gate run; pass/fail records accumulate as JSONL) and **session events** (Phase 2 partial — engineers run `log-session` at the end of each work session; `sprint_close.py` refuses to lock a sprint with zero logged sessions when the metrics module is installed, so the discipline is structural). Threshold ranges that *interpret* session counts (healthy / high / low, rework-rate alerts) are deliberately deferred until one engagement has run 3+ sprints under both event types — calibration against simulated data misleads. See [metrics/docs/METRICS.md](metrics/docs/METRICS.md).
- **[/incident skill](tooling/.claude/skills/incident.md)** — post-deployment learning loop. Orchestrates the post-mortem using [incident-TEMPLATE.md](tooling/templates/incident-TEMPLATE.md), extracts a specific prevention rule into `docs/failures/`, names the enforcement surface where the rule will actually run (CLAUDE.md / CI / architecture-guard test / security prompt / test-matrix), and optionally drafts a design-doc update PR or a superseding ADR when an incident invalidates a requirement. Completes the SDLC coverage that today stops at sprint close. Open incidents (post-mortems without a `Resolved:` timestamp) are surfaced as P1 learning-loop flags by `state-check.py`.
- **Method skills** — conversational wrappers around the enforcement scripts: [/prd](tooling/.claude/skills/prd.md) scopes a single sprint from the design document and produces `sprints/vN/PRD.md` + `TASKS.md` that `reconcile.py` parses; [/dev](tooling/.claude/skills/dev.md) executes one task per session, enforces the test-matrix categories named in `Tests required:`, and reads the task's `Autonomy:` annotation to tune checkpoint cadence; [/sprint-close](tooling/.claude/skills/sprint-close.md) wraps `sprint_close.py` and walks the engineer through `RETRO.md`, sign-off, and the security/UI-QA escalation when the PRD said they were required.
- **Gate ceremony skills** — Internal Product Mode graduation gates: [/gate-1-to-2](tooling/.claude/skills/gate-1-to-2.md) runs the Stage 1 → 2 evidence interview (real problem, real users, named commitment) and produces `docs/gates/stage-1-to-2.md`; [/gate-2-to-3](tooling/.claude/skills/gate-2-to-3.md) runs the Stage 2 → 3 commercialization gate, including the structural pre-committed-retention check (the metric and threshold must be in the Stage 2 PRD *before* the data is read), and produces `docs/gates/stage-2-to-3.md`. Both refuse to graduate without explicit evidence and named decisions.
- **[AI-assisted PR review checklist](tooling/templates/code-review-AI-CHECKLIST.md)** — ~25-item checklist reviewers attach to PRs marked `AI-assisted: yes`. Targets AI-specific failure modes generic PR review misses: invented APIs, plausible-but-wrong docstrings, defensive coding for impossible states, silent scope creep beyond the task's `Satisfies:` IDs, tests modified to match implementation. `[blocking]` items are merge-blockers. The [.github/pull_request_template.md](.github/pull_request_template.md) carries the `AI-assisted: yes / no` field that points reviewers at the checklist; handbook §1.8 covers when to skip it honestly.
- **Templates** — [CLAUDE.md](tooling/templates/CLAUDE.md), [client intake](tooling/templates/client-intake-TEMPLATE.md), [sprint PRD](tooling/templates/sprint-PRD-TEMPLATE.md), [tasks](tooling/templates/sprint-TASKS-TEMPLATE.md), [failures log](tooling/templates/failures-log-TEMPLATE.md), [retro](tooling/templates/retro-TEMPLATE.md), [security suppressions](tooling/templates/security-suppressions-TEMPLATE.md), [incident post-mortem](tooling/templates/incident-TEMPLATE.md), [AI-assisted PR review checklist](tooling/templates/code-review-AI-CHECKLIST.md).

## What this deliberately does NOT include yet

- **Automation for `/gap`, `/ui-qa`** — currently manual checklists. Promote to scripts after the manual process has stabilized on at least one engagement. (Security has moved from checklist to structural gate via [security.yml](tooling/.github/workflows/security.yml); manual `/security-review` remains as the escalation path for deeper human review. `/sprint-close` is now scripted via [sprint_close.py](tooling/scripts/sprint_close.py).)
- **Enforcement hooks** — structural cross-sprint write blocking now ships via [sprint_gate.py](tooling/hooks/sprint_gate.py) as a `PreToolUse` hook. Cultural discipline graduated to structural enforcement.
- **Mutation testing setup** — language-specific; add when you pick critical modules.

## Status

This is a **production v1**, not a finished product. Ready to adopt on a real engagement, but expect to modify scripts and templates within the first month of real use. Real data beats hypotheticals — the best feedback starts with "we tried X and Y happened." See [CHANGELOG.md](CHANGELOG.md) for version history and roadmap.

## Calibration for small teams

- **Mutation testing:** monthly, critical modules only. Not weekly.
- **`/gap`:** per initiative and quarterly for long-running engagements. Not monthly.
- **Per-client repos:** one per engagement.
- **CLAUDE.md:** under ~500 lines.
- **Active failures-log rules:** 20–50 for a mature codebase. Prune quarterly.
- **Phase 0 duration:** 1–3 weeks for typical enterprise engagements.

## Local conventions for private notes

For maintainers who want to keep client-specific notes, engagement writeups, or internal discussion of how this methodology is being applied to a real client *alongside* the public repo (without those notes leaking publicly), the following folder/file patterns are gitignored and safe for private content:

- `clients/` — anything under here, e.g. `clients/acme-corp/notes.md`
- `private/` — generic catchall
- `*.private.md` — any markdown file ending in `.private.md`
- `*.private/` — any folder ending in `.private`

These patterns are enforced by [`.gitignore`](.gitignore). Verify with `git status` before committing if you're not sure — Git will silently ignore matching paths and they will never be staged.

## Contributing

Feedback, bug reports, and method refinements are welcome. Issue templates cover three kinds of input:

- **Tooling bugs** — for problems in `reconcile.py`, `state-check.py`, or the CI workflow.
- **Method feedback** — for content-level refinements to the method, handbook, or internal mode.
- **New skill proposals** — for skills that should be promoted from manual checklist to tooling.

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

Apache-2.0. See [LICENSE](LICENSE).
