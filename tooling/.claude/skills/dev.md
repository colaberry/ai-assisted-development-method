# /dev — Router for the two-session task flow

**`/dev` no longer executes a task end-to-end in one session.** Method
rule 4 requires test writing and implementation to be in separate
Claude Code sessions, and the previous single-session `/dev` defeated
that rule in practice. The flow is now split into two skills that must
run in two Claude Code sessions:

1. **`/dev-test T-NNN`** — writes the failing test matrix, commits, and
   drops the marker `sprints/vN/.in-progress/T-NNN.test-session-done`.
2. **`/dev-impl T-NNN`** — refuses to proceed without that marker and
   until the recorded test commit is verifiable on disk. Then
   implements against the failing tests and marks the task `[x]`.

## How to invoke

- If the task has no `.test-session-done` marker yet → run `/dev-test`.
- If the task has the marker and the test commit is on disk → open a
  **new Claude Code session** and run `/dev-impl`.
- Never run both in the same session. The marker-verification check in
  `dev_session.py check-impl-ready` is what keeps the two sessions
  actually separate; working around it collapses the discipline.

## Why the split

The single-session flow let Claude draft tests and implementation from
the same cache of context, which produced test-after dressed up as TDD.
The split forces the test matrix to be written without knowledge of the
implementation it will guide, and forces the implementation to answer
to tests already committed. The marker file is the structural signal
that the two sessions happened; without it, `/dev-impl` refuses and the
task cannot be marked `[x]`.

## What to read next

- [dev-test.md](dev-test.md) — the test-writing session.
- [dev-impl.md](dev-impl.md) — the implementation session.
- [tooling/scripts/dev_session.py](../../scripts/dev_session.py) — the
  marker/verification script the two skills call.
