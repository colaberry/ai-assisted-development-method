# Sprint vN — Tasks

Status markers:
- `[ ]` — open
- `[x]` — complete
- `[DEFERRED]` — deferred to a later sprint (must include Target: and Reason:)

The `/reconcile` script parses this file. Format must be preserved:

- Each task starts with `- [status] TNNN: title` as a top-level list item.
- Sublines are indented two spaces and start with `- Key: value`.
- The `Satisfies:` subline lists requirement IDs separated by commas or spaces.
- The `Files:` subline lists paths the task touches, comma-separated.

> **`Files:` is load-bearing, not advisory.** `sprint_gate.py` runs as a PreToolUse hook in `/dev-impl` and structurally blocks `Edit`/`Write` calls against any path not on the active task's `Files:` allowlist. A vague or incomplete `Files:` line translates directly into refused writes during implementation. List every file the task is expected to touch; if a refactor reveals a file you missed, close the `/dev-impl` session, amend `Files:` here, and restart — that's the seam where scope expansion becomes visible. Empty `Files:` is acceptable only for research-style tasks that produce no code.

**Optional `Autonomy:` annotation.** Each task may declare how much human checkpointing `/dev-impl` should do while executing it. Valid values:

- `direct` — Claude proceeds task end-to-end; reviewer sees the diff. Use for low-risk, well-tested, easily reversible work (refactors with strong test coverage, doc updates, isolated utility additions).
- `checkpoint` — Claude pauses at intermediate milestones for confirmation. The default. Use for ordinary feature work.
- `review-only` — every step requires explicit human go-ahead before continuing. Use for high-risk changes: security boundaries, payment paths, schema migrations, anything touching production data.

Tie the level to actual risk and test coverage, not to how much you trust the engineer or the model. A task with thin Category D fallthrough coverage on production-touching code is `review-only` even if the diff looks small. `reconcile.py` parses `Autonomy:` and warns on unknown values; `/dev-impl` reads it to tune confirmation cadence during implementation.

---

## Tasks

- [ ] T001: <Short task title>
  - Satisfies: §X.Y, Dn
  - Acceptance: <one-line acceptance criterion>
  - Files: src/path/to/file.py, tests/path/to/test_file.py
  - Tests required: A (happy), B (empty-input edge), D (pre-existing fallthrough)
  - Autonomy: checkpoint
  - Notes: <any implementation notes>

- [ ] T002: <Short task title>
  - Satisfies: SOW-§X.Y
  - Acceptance: <criterion>
  - Files: <paths>
  - Tests required: A, C (error on invalid input), E (guards against regression of deleted symbol `old_handler`)
  - Autonomy: review-only

- [x] T003: <Completed task title>
  - Satisfies: Q3
  - Acceptance: <criterion>
  - Files: src/auth/session.py
  - Tests required: A, B, D
  - Autonomy: direct
  - Completed: YYYY-MM-DD

- [DEFERRED] T004: <Deferred task title>
  - Satisfies: §X.Z
  - Status: DEFERRED
  - Target: vN+1
  - Reason: <rationale for deferral — what blocked it, when it will be picked up>
  - Files: <expected paths for when it resumes>

---

## Deferred (aggregate view)

For quick reference, all deferred tasks in one list:

- **T004** (§X.Z) → **v{N+1}** — <one-line reason>

> Keep this section in sync with the `[DEFERRED]` tasks above. This list is what makes silent descoping visible. If a requirement is dropped without landing here, `/reconcile` flags it as missing.

---

## Completion checklist

Before marking this sprint done and running `/sprint-close`:

- [ ] All non-deferred tasks are marked `[x]`
- [ ] Every task has a `Satisfies:` line
- [ ] Every task with a `Files:` line has those files in the repo (verified by `/reconcile`)
- [ ] Every deferred task has `Target:` and `Reason:`
- [ ] The Deferred aggregate view matches the `[DEFERRED]` tasks
- [ ] `/reconcile` passes (run it manually: `python3 scripts/reconcile.py sprints/vN`)
