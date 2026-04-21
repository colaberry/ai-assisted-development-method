# /dev-test — Write the failing test matrix for one task (session 1 of 2)

This is the first of the two sessions that replace the old `/dev`. It
writes the failing test matrix for a single task, commits it, and drops
a marker file that `/dev-impl` must observe before it can write any
implementation. The split makes Method rule 4 — "test writing and
implementation are in separate Claude Code sessions" — structural rather
than cultural.

## When to invoke

- You have an open sprint (a `sprints/vN/` directory without a `.lock`).
- There is at least one `[ ]` task in `sprints/vN/TASKS.md` that does not
  already have a `sprints/vN/.in-progress/T-NNN.test-session-done`
  marker (i.e., tests haven't been written yet).
- The previous sprint is locked; `sprint_gate.py` and `state-check.py`
  will flag it if not.

Do not invoke `/dev-test` to:
- Write tests for two tasks in one session.
- Extend an existing passing test to cover new behavior (that's
  implementation-session work).
- Re-run after tests are already written and committed; the marker is
  the signal.

## Preconditions

Before starting, run:

```bash
python3 state-check/scripts/state-check.py --json
```

Refuse to proceed if:

- **Mode is `unknown`** — the repo isn't set up for the method.
- **No active sprint** — run `/prd` first.
- **P0 flags exist** — resolve them before writing code.
- **Marker already exists** for the requested task at
  `sprints/vN/.in-progress/T-NNN.test-session-done`. Tests were already
  written. Move on to `/dev-impl` in a new Claude Code session.

If the engineer specifies a task ID, verify it is `[ ]` in TASKS.md. If
not, list the open tasks with their `Tests required:` categories.

## What this skill does

1. **Loads the task.** Reads the full block from TASKS.md — `Satisfies:`,
   `Files:`, `Acceptance:`, `Tests required:`, and `Autonomy:`.
   Cross-references each requirement ID in `Satisfies:` against the
   active design document.
2. **Drafts the test matrix.** Produces one test per category named in
   `Tests required:` — A happy path, B edges, C errors, D fallthroughs
   per code path, E architecture guards. Each test is explicitly named
   after the behavior it asserts, not the code path it exercises. For
   `review-only` tasks, pauses here for human review of the matrix
   before writing any code.
3. **Writes the tests, failing.** Each test must fail for the right
   reason — an assertion, not an import error or missing symbol. If a
   test passes when run against the current code, it's the wrong test;
   rewrite it until it fails against real absent behavior.
4. **Commits the failing tests.** A real git commit with a message of the
   form `test(TNNN): <what the tests assert>`. The commit SHA is the
   receipt `/dev-impl` will verify.
5. **Writes the marker.** Runs:
   ```bash
   python3 tooling/scripts/dev_session.py test-done sprints/vN T-NNN \
     --commit-sha "$(git rev-parse HEAD)"
   ```
   This creates `sprints/vN/.in-progress/T-NNN.test-session-done`
   containing the test commit SHA and a UTC timestamp.
6. **Stops.** Does not begin implementation. Tells the engineer to open
   a new Claude Code session and run `/dev-impl T-NNN`.

## Autonomy levels

| Level | Cadence |
|---|---|
| `direct` | Draft, write, commit, marker — show the matrix at the end. |
| `checkpoint` (default) | Pause at matrix drafted, tests running red, commit written. |
| `review-only` | Pause for explicit go-ahead before each test file and before committing. |

Absent `Autonomy:`, default to `checkpoint`.

## What this skill does NOT do

- **Does not write implementation code.** That is a separate session.
  Even a one-line tweak to make a symbol importable belongs in
  `/dev-impl`.
- **Does not edit the task's `Satisfies:`, `Files:`, `Acceptance:`, or
  `Tests required:` lines.** Those are the scope contract.
- **Does not commit without the tests failing.** A green suite after
  `/dev-test` means the tests aren't asserting new behavior.
- **Does not skip the marker.** `/dev-impl` refuses without it; that's
  the whole mechanism.

## Deliverables

- Tests committed, failing for assertion reasons.
- `sprints/vN/.in-progress/T-NNN.test-session-done` exists, containing
  the test commit SHA.
- No implementation code touched.

## Interaction with other skills

- `/dev-impl` is the required successor. It refuses to proceed without
  this skill's marker.
- `/prd` produces the tasks this skill consumes.
- `/sprint-close` requires the task be `[x]` before locking; that only
  happens after `/dev-impl`.
