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

---

## Tasks

- [ ] T001: <Short task title>
  - Satisfies: §X.Y, Dn
  - Acceptance: <one-line acceptance criterion>
  - Files: src/path/to/file.py, tests/path/to/test_file.py
  - Tests required: A (happy), B (empty-input edge), D (pre-existing fallthrough)
  - Notes: <any implementation notes>

- [ ] T002: <Short task title>
  - Satisfies: SOW-§X.Y
  - Acceptance: <criterion>
  - Files: <paths>
  - Tests required: A, C (error on invalid input), E (guards against regression of deleted symbol `old_handler`)

- [x] T003: <Completed task title>
  - Satisfies: Q3
  - Acceptance: <criterion>
  - Files: src/auth/session.py
  - Tests required: A, B, D
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
