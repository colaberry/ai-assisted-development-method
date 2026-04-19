# /dev — Execute a single sprint task end-to-end

This skill runs one task from `sprints/vN/TASKS.md` through implementation. One task per session, always. The skill reads the task's `Autonomy:` annotation (if present) to tune how often it pauses for human confirmation, and enforces the test-matrix categories named in the task's `Tests required:` line. Its job is to take a task from `[ ]` to `[x]` with real tests and no silent scope expansion.

## When to invoke

- You have an open sprint (a `sprints/vN/` directory without a `.lock` file).
- There is at least one `[ ]` task in `sprints/vN/TASKS.md`.
- The previous sprint is locked. If it isn't, `sprint_gate.py` will block writes and `state-check.py` will flag it as P0. Close it first.

Do not invoke `/dev` to:
- Work on multiple tasks concurrently. One task per session is a non-negotiable method rule — it's the only way to keep test/implementation separation honest and to keep diffs reviewable.
- Touch requirements that have no task in TASKS.md. That's a scope change, not implementation. Either add a task via `/prd` rescope, or stop and fix the spec.
- Re-open a completed task. If a `[x]` task turned out to be wrong, that's either an `/incident` (shipped) or a follow-up task in the next sprint (caught before ship), not a silent `[x]` → `[ ]` flip.

## Preconditions

Before starting work, run:

```bash
python3 state-check/scripts/state-check.py --json
```

Refuse to proceed if:

- **Mode is `unknown`** — the repo isn't set up for the method.
- **No active sprint** — there's nothing to `/dev` against; run `/prd` first.
- **P0 flags exist** — resolve them before writing code. P0 flags are the things that break the method structurally (unlocked prior sprint, missing design doc, missing hypothesis in exploration mode).

If the engineer specifies a task ID, verify it exists and is `[ ]` in TASKS.md. If they don't specify one, list the open tasks with their `Autonomy:` levels and ask which one.

## What this skill does

1. **Loads the task.** Reads the full task block from TASKS.md — `Satisfies:`, `Files:`, `Acceptance:`, `Tests required:`, and `Autonomy:`. Cross-references each requirement ID in `Satisfies:` against the active design document to confirm the task's target hasn't drifted.
2. **Announces the autonomy level.** Before writing anything, states the `Autonomy:` level and what that means for this session (see §1.10 of the handbook). If absent, defaults to `checkpoint` and says so.
3. **Writes the tests first, in this session, failing.** Enforces the categories named in `Tests required:` (A happy, B edge, C error, D fallthrough, E architecture guards). Commits the failing tests before a single line of implementation — this is the method rule that keeps test-after from masquerading as TDD. For `review-only` tasks, pauses here for human review of the test matrix before implementation.
4. **Implements against the failing tests.** Works only against the files listed in `Files:`. If implementation naturally requires touching a file not on that list, stops and surfaces it — unplanned-file creep is the symptom of scope drift.
5. **Runs the full relevant test suite** (unit + integration + architecture guards that cover touched modules). Does not declare done on a subset. For UI work, exercises the feature in a browser per the handbook's testing discipline — type checks and tests verify code correctness, not feature correctness.
6. **Checks the acceptance criterion.** The `Acceptance:` one-liner isn't the test suite — it's the behavioral claim. The skill verifies it observationally (runs the code, reads the output, confirms the behavior) before marking the task complete.
7. **Marks the task `[x]` with a `Completed: YYYY-MM-DD` line** in TASKS.md. Does not touch `Satisfies:`, `Files:`, `Acceptance:`, or `Tests required:` — those are the contract; completion is the only field the skill changes.
8. **Confirms `reconcile.py` still passes** on the sprint directory. A `[x]` task must survive the coverage check — symbol-presence check included. `STUB-WARNING:` is not acceptable for a finished task; either the implementation is real or the task isn't done.

## Autonomy levels and checkpoint cadence

| Level | Cadence | When it applies |
|---|---|---|
| `direct` | End-to-end; show the diff at the end | Low-risk work with strong existing test coverage: doc edits, typo fixes, isolated utility additions, refactors in a module with Category E architecture guards. |
| `checkpoint` (default) | Pause at: test matrix drafted, tests committed failing, implementation complete, suite green | Ordinary feature work. Each checkpoint is a short "here's what I did, moving on unless you object." |
| `review-only` | Pause for explicit go-ahead before each step: test matrix, each test file, each implementation file, suite run | High-risk work: security boundaries, payment paths, schema migrations, anything touching production data. The level is chosen against risk and coverage, not against trust. |

If the task has no `Autonomy:` line, treat it as `checkpoint` and note that at the start. Do not upgrade a task to `direct` mid-session.

## What this skill does NOT do

- **Does not edit the task's `Satisfies:`, `Files:`, or `Acceptance:` lines.** Those are the scope contract. If they're wrong, stop and fix the task via a PRD-level change before resuming.
- **Does not split one task into two.** If the task is too big, close the session, add the second task via scope adjustment (a follow-up task within the current sprint, or a `[DEFERRED]` entry for the next sprint), and re-run `/dev` against the smaller piece.
- **Does not merge multiple tasks into one session.** One task per session. Batching produces unreviewable diffs and destroys the test/implementation separation.
- **Does not modify a failing test to make it pass.** Per the handbook's testing discipline: if a test appears wrong, stop and flag it to the human reviewer. Do not "fix" it.
- **Does not mark the task `[x]` while `reconcile.py` warns on it.** The coverage check is the gate.
- **Does not commit or push.** The engineer reviews the diff and commits. The skill prepares the change; the human lands it.

## Interaction with other skills

- `/prd` produces the tasks `/dev` consumes. If `/dev` needs a task that doesn't exist, stop and return to `/prd` — don't invent requirement IDs in place.
- `/sprint-close` reads the `[x]` markers and `Completed:` dates `/dev` writes. Every non-deferred task must be `[x]` before `/sprint-close` will lock.
- `/incident` is the reverse flow: when something `/dev` shipped breaks in production, `/incident` extracts the prevention rule and names the enforcement surface.

## Deliverables at the end of `/dev`

- Tests written, committed failing before implementation, now passing. Categories match `Tests required:`.
- Implementation in the files named in `Files:` — no unannounced extras.
- `Acceptance:` observationally confirmed, not just assumed from a green suite.
- Task marked `[x]` with a `Completed: YYYY-MM-DD` line.
- `python3 scripts/reconcile.py sprints/vN` exit code 0 with no `STUB-WARNING:` on this task.
- The engineer has reviewed the diff and is ready to commit.
