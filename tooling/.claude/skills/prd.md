# /prd — Scope the next sprint from the design document

This skill scopes a single sprint's PRD and TASKS from an initiative's design document. It is the start-of-sprint ceremony. Every task it produces has a `Satisfies:` line citing the design-doc requirement IDs it closes. The output is two files: `sprints/vN/PRD.md` and `sprints/vN/TASKS.md`, both in the format `reconcile.py` parses.

## When to invoke

- Starting a new sprint after `/sprint-close` has locked the previous one.
- Starting the first sprint of an initiative (after Phase 0 has produced a signed-off design doc).
- When a pivot during a sprint is large enough to warrant re-scoping — you close the in-flight sprint via `/sprint-close` and then re-run `/prd` for the next.

Do not invoke `/prd` to:
- Adjust scope mid-sprint. Use `[DEFERRED]` entries in the current sprint's TASKS, or close and re-scope.
- Start a new sprint while the previous one is open. The `sprint_gate.py` hook will block writes to the new directory; `state-check.py` will flag it as P0. Close the previous sprint first.

## Preconditions

Before doing anything, run:

```bash
python3 state-check/scripts/state-check.py --json
```

Refuse to proceed if any of these are true (explain why to the engineer and stop):

- **The previous sprint has no `.lock` file.** Run `/sprint-close` on it first. Starting v(N+1) while v(N) is open is the exact thing `sprint_gate.py` blocks structurally.
- **No active design document.** `find_active_initiative` returned none. Either Phase 0 hasn't run yet, or the design doc was deleted. Without a design doc there is no source of requirement IDs and therefore nothing to `Satisfies:` against.
- **Mode is `unknown`.** The repo isn't set up for the method. Run the `START-HERE.md` bootstrap first.
- **There are P0 flags.** Resolve those before starting sprint scope work.

For Internal Product Mode: if `stage == "exploration"` and `docs/hypothesis.md` is missing, stop — that's the P0 setup condition.

## What this skill does

1. **Reads the design document end-to-end.** Not just the section headings — the actual requirement prose. Stable IDs matter (§X.Y, Dn, Qn, SOW-§X.Y) but the text behind them is what decides what tasks are needed.
2. **Asks what this sprint should tackle.** Never auto-picks. The engineer names the scope ("finish auth module," "land the migration," "harden the /retro pipeline"). If they don't have an opinion, walks the design doc section by section and surfaces 3–5 plausible scopes with tradeoffs.
3. **Writes `sprints/vN/PRD.md`** using [tooling/templates/sprint-PRD-TEMPLATE.md](../../templates/sprint-PRD-TEMPLATE.md). The PRD mirrors only the requirement IDs being tackled this sprint — do not copy the entire design doc. Every requirement listed in the PRD should have at least one task covering it, or a `[DEFERRED]` entry with a target sprint.
4. **Runs a completeness pass before slicing tasks.** Walk the requirement IDs the engineer scoped into this sprint and ask, for each, "what's *implied* by this requirement that isn't written down?" Concrete prompts: error states, observability hooks, admin/operator paths, failure-mode handling, security review surface, data-migration step, runbook update. For each implication that's load-bearing, do exactly one of: (a) confirm an existing requirement ID already covers it; (b) add a new task with `Satisfies:` citing the parent ID and an explicit "implies:" note; (c) write a one-line "N/A because X" in a "Sprint scope assumptions" subsection of the PRD. Silent omission of an implied work item is the failure mode this step exists to prevent. Do not invent new requirement IDs here — IDs come from the design doc; if a real new requirement surfaces, stop and amend the design doc first (see step 7.6 below).
5. **Decomposes into tasks.** Each task gets a unique `TNNN` ID, a one-line title, a `Satisfies:` subline citing the requirement IDs, a `Files:` subline naming expected paths (may be empty for research tasks), an `Acceptance:` one-liner, a `Tests required:` line naming categories A–E, and an optional `Autonomy:` subline (`direct` | `checkpoint` | `review-only` — default to `checkpoint` if unsure; see handbook §1.10).
6. **Writes `sprints/vN/TASKS.md`** using [tooling/templates/sprint-TASKS-TEMPLATE.md](../../templates/sprint-TASKS-TEMPLATE.md). The Deferred aggregate view section is kept in sync with any `[DEFERRED]` tasks.
7. **Runs `reconcile.py` locally** against the freshly-written files to confirm the PRD-and-TASKS pair parses and that every requirement has a task or a deferral. If coverage gaps remain, surfaces them and asks the engineer to either add tasks or explicitly defer.
8. **Confirms the files are ready before committing.** This skill never silently commits. The engineer reviews and commits.

## What this skill does NOT do

- **Does not copy the entire design document into the PRD.** The PRD is a per-sprint projection; the design doc is the authority. Duplication rots.
- **Does not decide what goes in the sprint.** The engineer does. This skill structures the decision, surfaces tradeoffs, and enforces the format — it doesn't pick scope.
- **Does not invent requirement IDs.** If a task needs something not in the design doc, that's a spec problem. Stop and update the design doc first (with its own PR), then resume `/prd`. Silent requirement invention is how traceability dies.
- **Does not add `Autonomy:` levels the engineer didn't ask for.** Defaults to `checkpoint` for new tasks; does not upgrade existing tasks to `direct` without explicit sign-off.
- **Does not close previously-open tasks from older sprints.** If an in-flight task was missed, that's a sprint-close failure, not a new-sprint matter.

## Interaction with other skills

- `/prd` runs after `/sprint-close` on the previous sprint. Fresh sprints start with an unlocked directory; the hook and state-check expect that state.
- `/dev-test` and `/dev-impl` run inside a sprint, one task at a time, in separate Claude Code sessions. `/prd` produces the work those skills consume. The `Files:` allowlist on each task is load-bearing: `sprint_gate.py` reads it as a PreToolUse hook and blocks writes outside the active task's allowlist, so vague or missing `Files:` lines translate directly into friction during implementation. Write them carefully.
- `/sprint-close` reads the PRD and TASKS that `/prd` wrote and enforces coverage before allowing the lock.
- `/gap` is the complementary initiative-boundary gate. The completeness pass this skill runs (Step 4) works at the *sprint scope* — does every requirement the engineer scoped into vN have a task, a `[DEFERRED]`, or a documented N/A? `/gap` works at the *initiative scope* — does every requirement in `docs/<INITIATIVE>.md` ever make it into some sprint? Both passes are necessary. A requirement can pass `/prd`'s step 4 in every sprint (scope was honest) and still be orphaned at `/gap` (nobody ever scoped it).

## Deliverables at the end of `/prd`

- `sprints/vN/PRD.md` — requirement IDs and one-line summaries for only what this sprint tackles, plus an initial acceptance-criterion list.
- `sprints/vN/TASKS.md` — unique `TNNN` tasks, each with `Satisfies:`, `Files:`, `Acceptance:`, `Tests required:`, and optional `Autonomy:`. Deferred aggregate view in sync.
- Local `python3 scripts/reconcile.py sprints/vN` exit code 0 (or clearly-reasoned deferrals only).
- The engineer has reviewed both files and understands what's being committed.
