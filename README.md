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
└── tooling/                  # reconcile.py, CI workflow, templates
```

## Quick start

Read [START-HERE.md](START-HERE.md) first. It covers the reading order (60–90 min for tech leads, 45 min for engineers) and the bootstrap steps for a new client repo.

## Reading order by role

- **Tech leads and PMs:** [method/](method/) first. Read [internal-mode/](internal-mode/) if you build products internally. Reference [handbook/](handbook/) when onboarding engineers.
- **Engineers:** [handbook/](handbook/) first. Reference [method/](method/) for context and rationale.
- **New engineer onboarding:** [handbook/](handbook/) + your project's `CLAUDE.md` + recent entries in `docs/failures/`.

## Tooling

- **[reconcile.py](tooling/scripts/reconcile.py)** — sprint coverage check. Python stdlib only. Runs in CI via [reconcile.yml](tooling/.github/workflows/reconcile.yml) as a merge gate.
- **[security.yml](tooling/.github/workflows/security.yml)** — Semgrep-based security merge gate. Blocks PRs on any ERROR-severity finding. Deliberate suppressions live in [docs/security/suppressions.md](tooling/templates/security-suppressions-TEMPLATE.md) with a 90-day re-review ceremony enforced by `state-check.py`.
- **[state-check.py](state-check/scripts/state-check.py)** — detects current repo state (mode, stage, active sprint, flags). Heads-up display, not autopilot. Ships with a [Claude Code skill](state-check/.claude/skills/state-check.md) for conversational use.
- **Templates** — [CLAUDE.md](tooling/templates/CLAUDE.md), [client intake](tooling/templates/client-intake-TEMPLATE.md), [sprint PRD](tooling/templates/sprint-PRD-TEMPLATE.md), [tasks](tooling/templates/sprint-TASKS-TEMPLATE.md), [failures log](tooling/templates/failures-log-TEMPLATE.md), [retro](tooling/templates/retro-TEMPLATE.md), [security suppressions](tooling/templates/security-suppressions-TEMPLATE.md).

## What this deliberately does NOT include yet

- **Automation for `/sprint-close`, `/gap`, `/ui-qa`** — currently manual checklists. Promote to scripts after the manual process has stabilized on at least one engagement. (Security has moved from checklist to structural gate via [security.yml](tooling/.github/workflows/security.yml); manual `/security-review` remains as the escalation path for deeper human review.)
- **Enforcement hooks** — a PreToolUse hook blocking cross-sprint writes is on the roadmap. Until it ships, the anti-skip gate is cultural for sprint boundaries and automated only for `/reconcile`.
- **Skill bundle** — the `/prd`, `/dev`, `/sprint-close` skills that would wrap the enforcement scripts are on the roadmap. See [CHANGELOG.md](CHANGELOG.md) for what's planned.
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
