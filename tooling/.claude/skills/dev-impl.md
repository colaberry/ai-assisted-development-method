# /dev-impl — Implement against the failing tests (session 2 of 2)

This is the second of the two sessions that replace the old `/dev`. It
implements one task against the tests that `/dev-test` committed in a
separate prior session. The skill refuses to begin until
`dev_session.py check-impl-ready` confirms the marker from `/dev-test`
exists and the test commit it names is on disk. That is what makes
Method rule 4 structural: the two sessions cannot be silently merged.

## When to invoke

- `/dev-test` has already run for the task in a **separate Claude Code
  session** and committed the failing tests.
- `sprints/vN/.in-progress/T-NNN.test-session-done` exists and references
  a real commit SHA.
- The previous sprint is locked.

Do not invoke `/dev-impl` to:
- Add tests. That's `/dev-test`; if coverage is missing, return to
  `/dev-test` in a new session.
- Work on multiple tasks. One task per session.
- Re-open a completed task.

## Preconditions

Before starting work, run:

```bash
python3 state-check/scripts/state-check.py --json
python3 tooling/scripts/dev_session.py check-impl-ready sprints/vN T-NNN
```

The `check-impl-ready` call is the hard gate. Exit code 0 is the only
go signal. The possible refusals are:

- **No marker file** — `/dev-test` hasn't run for this task. Open a new
  Claude Code session and run `/dev-test T-NNN`.
- **Marker malformed** — missing the `test_commit:` line. Delete the
  marker and re-run `/dev-test`.
- **Test commit not on disk** — the commit SHA in the marker doesn't
  resolve in this repo. The marker is stale; re-run `/dev-test`.
- **Not a git repo** — `/dev-test`'s commit isn't verifiable. Fix the
  environment before implementing.

If `state-check.py` reports P0 flags, resolve them first.

## What this skill does

1. **Re-loads the task.** Reads the full block from TASKS.md —
   `Satisfies:`, `Files:`, `Acceptance:`, `Tests required:`, `Autonomy:`.
2. **Announces the autonomy level.** Before writing, states the level
   and what it means for this session.
3. **Confirms the failing-test baseline.** Runs the committed tests —
   they must fail before implementation begins. If they pass, the
   marker's commit is ahead of HEAD or the wrong tests were committed;
   stop and return to `/dev-test`.
4. **Implements against the failing tests.** Works only against the
   files listed in `Files:`. This isn't a soft norm — `sprint_gate.py`
   runs as a PreToolUse hook and structurally blocks `Edit`/`Write` calls
   against any path not on the active task's `Files:` allowlist. If
   implementation naturally requires touching a file not on that list,
   the hook will refuse the write and the skill must stop and surface
   the drift to the engineer. Resolution paths: (a) the new file is in
   scope and the task's `Files:` line was incomplete — close the
   `/dev-impl` session, edit `Files:` in TASKS.md, restart `/dev-impl`;
   (b) the new file is *out* of scope and the implementation is creeping
   — stop, log the realization in the failures-log draft, and either
   shrink the implementation or split a follow-up task. Silently
   expanding `Files:` to make the hook pass defeats the gate.
5. **Runs the full relevant test suite** (unit + integration +
   architecture guards that cover touched modules). Does not declare
   done on a subset. For UI work, exercises the feature in a browser
   per the handbook's testing discipline.
6. **Checks the acceptance criterion** observationally — runs the code,
   reads the output, confirms the behavior named in `Acceptance:`. A
   green suite is not the same as a satisfied acceptance criterion.
7. **Marks the task `[x]`** with a `Completed: YYYY-MM-DD` line. Does
   not touch `Satisfies:`, `Files:`, `Acceptance:`, or `Tests required:`.
8. **Moves the marker to `.complete`.** Runs:
   ```bash
   python3 tooling/scripts/dev_session.py mark-complete sprints/vN T-NNN
   ```
   The `T-NNN.test-session-done` file is renamed to `T-NNN.complete`,
   preserving the audit trail and clearing the way for the next
   `/dev-test` session on a different task.
9. **Confirms `reconcile.py` still passes** — symbol-presence check
   included. `STUB-WARNING:` on this task is not acceptable: either the
   implementation is real or the task isn't done.

## Autonomy levels and checkpoint cadence

| Level | Cadence | When it applies |
|---|---|---|
| `direct` | End-to-end; show the diff at the end | Low-risk work with strong existing test coverage. |
| `checkpoint` (default) | Pause at: baseline red confirmed, implementation complete, suite green, `[x]` written | Ordinary feature work. |
| `review-only` | Pause for go-ahead before each implementation file and before each suite run | High-risk work: security boundaries, payment paths, schema migrations. |

## What this skill does NOT do

- **Does not modify a failing test to make it pass.** If a test appears
  wrong, stop and flag it. The tests are the contract that was signed
  off in `/dev-test`.
- **Does not add new tests.** Coverage gaps that surface mid-session
  mean `/dev-test` wasn't thorough; finish the task under the existing
  matrix, then add a follow-up task for the missing coverage.
- **Does not edit the task's scope contract** (`Satisfies:`, `Files:`,
  `Acceptance:`, `Tests required:`).
- **Does not mark `[x]`** while `reconcile.py` warns on this task.
- **Does not commit or push.** The engineer reviews the diff and lands
  the change.

## Deliverables

- Implementation in the files named in `Files:`, no unannounced extras.
- Previously-failing tests now pass; full suite green.
- `Acceptance:` observationally confirmed.
- Task marked `[x]` with a `Completed: YYYY-MM-DD` line.
- Marker moved to `sprints/vN/.in-progress/T-NNN.complete`.
- `python3 scripts/reconcile.py sprints/vN` exit code 0 with no
  `STUB-WARNING:` on this task.

## Interaction with other skills

- `/dev-test` is the required predecessor. Its marker is the structural
  signal that this skill reads.
- `/sprint-close` reads the `[x]` markers and `Completed:` dates this
  skill writes. Every non-deferred task must be `[x]` before
  `/sprint-close` will lock.
- `/incident` is the reverse flow when something this skill shipped
  breaks in production.
