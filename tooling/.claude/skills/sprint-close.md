# /sprint-close — Atomically close the current sprint

This skill runs the end-of-sprint ceremony and invokes `sprint_close.py` to write `sprints/vN/.lock` when every check passes. The `.lock` file is the structural signal that downstream tooling (`sprint_gate.py` PreToolUse hook, `state-check.py`, `/prd` preconditions) uses to decide whether work on sprint vN+1 is allowed. No `.lock`, no next sprint — that's the rule the script enforces.

`sprint_close.py` is the authority; this skill is the conversational wrapper that collects the artifacts the script needs, handles the retro and walkthrough, and orchestrates the security/UI-QA escalation when the PRD said they were required.

## When to invoke

- Every open `[ ]` task in the sprint's TASKS.md is either `[x]` or `[DEFERRED]`.
- The engineer is ready to commit to the close — no pending in-flight implementation work.
- The reviewer who will sign off is available (or a `SIGNOFF.md` exists from a prior review).

Do not invoke `/sprint-close` to:
- Lock a sprint with open tasks. Either finish them, defer them with a `[DEFERRED]` entry naming the target sprint, or decide the scope was wrong and revise before closing. Silent descoping — closing a sprint where a requirement just quietly disappeared — is the anti-pattern this entire method exists to prevent.
- "Lock later, the script is annoying." The whole point of `sprint_close.py` is to make this non-skippable. The `.lock` file is what `/prd` looks for before starting vN+1; skipping it blocks the next sprint structurally.
- Close and immediately reopen. A sprint is closed once. If you got it wrong, the next sprint inherits the fallout (including an `/incident` if the wrong-close reached production).

## Preconditions

Before doing anything, run:

```bash
python3 state-check/scripts/state-check.py --json
```

Refuse to proceed if:

- **No active sprint** — there is nothing to close.
- **The target sprint already has a `.lock` file** — it's already closed. Don't re-run.
- **Tests are red** — green suite is the baseline. Failing CI is a pre-close blocker.
- **P0 flags present** — resolve them first. They usually indicate exactly the kind of structural problem `/sprint-close` would trip over anyway.

Also verify: every non-deferred task in TASKS.md is `[x]` with a `Completed:` date. If any are still `[ ]`, stop and list them.

## What this skill does

1. **Collects the artifacts `sprint_close.py` expects:**
   - `RETRO.md` — filled in (not the template stub). The skill walks the engineer through it section by section if empty.
   - `WALKTHROUGH.md` — written or signed off. For client-facing engagements, this is the projection the client sees; for internal products, it's a short demo script.
   - Sign-off — either an existing `SIGNOFF.md` with `Reviewer:` + `Date:` lines, or a reviewer name to pass as `--reviewer` on the CLI.
2. **Invokes `/security-review` if the PRD said `Yes`** in the security-scope line. `/security-review` writes `sprints/vN/SECURITY-REVIEW.md`; `sprint_close.py` refuses to lock when the PRD says `Yes` and that artifact is missing or marked `Decision: blocked`. Security is structurally enforced on two layers now: the Semgrep CI gate catches mechanically-detectable issues, the manual review catches design-level ones.
3. **Invokes `/ui-qa` if the PRD said `Yes`.** `/ui-qa` writes `sprints/vN/UI-QA.md`; `sprint_close.py` refuses to lock when the PRD says `Yes` and that artifact is missing or blocked. Skipping UI QA because "it probably works" used to be the kind of omission that landed as an `/incident` three weeks later — the close now refuses structurally.
4. **Orchestrates the retro.** Fills `RETRO.md` by asking about: what went well, what went poorly, what surprised the team, what to carry forward, what to drop. Pushes for specifics — "communication was bad" is not a finding. The retro is a `sprint_close.py` gate: template markers (`<placeholder>`, `vN`, `YYYY-MM-DD`) in the file will cause the close to refuse.
5. **Verifies the deferred aggregate view is in sync** with the `[DEFERRED]` tasks. If a requirement was silently dropped (no `[DEFERRED]` entry, but also no `[x]` task covering it), `reconcile.py --ci` will surface the gap and `sprint_close.py` will refuse.
6. **Invokes `sprint_close.py`:**
   ```bash
   python3 scripts/sprint_close.py sprints/vN --reviewer "<NAME>"
   # or, if SIGNOFF.md already exists:
   python3 scripts/sprint_close.py sprints/vN
   ```
7. **Surfaces failures clearly.** If the script exits non-zero, the skill reads `CloseReport.checks` (via `--json`) and names the specific check that failed — retro-unfilled, reviewer-missing, reconcile-CI-failing, or an unresolved symbol-presence stub warning.
8. **Confirms the lock landed.** On success, reads `sprints/vN/.lock` and confirms `locked_at`, `reviewer`, and `reconcile_status` are present. Reminds the engineer that `/prd` for vN+1 is now unblocked.

## What this skill does NOT do

- **Does not edit `sprint_close.py`'s checks.** If a check is failing, fix the underlying artifact — don't loosen the gate. The checks are deliberately strict because the failure cost (shipping a sprint that didn't actually close) is high.
- **Does not skip the retro.** `sprint_close.py` refuses a template-stub RETRO.md structurally; there is no "skip retro" flag and the skill doesn't simulate one.
- **Does not forge a sign-off.** `--reviewer` writes a real SIGNOFF.md with a real name. If the reviewer hasn't actually reviewed, wait.
- **Does not push.** The engineer reviews the close artifacts and commits them. The skill prepares the close; the human lands it.
- **Does not reopen a sprint.** If the close was wrong, the next sprint inherits the cleanup work via a new task that satisfies the dropped requirement. Mutating a sealed `.lock` file breaks the historical record downstream tooling depends on.

## Handling the common refusal modes

- **RETRO.md still has template markers.** Re-run the retro walk-through. The placeholders exist because no one filled them in; the fix is filling them in, not deleting them.
- **`reconcile.py --ci` fails with a missing requirement.** Either the requirement needs a task (re-open the sprint briefly, add the task, run `/dev-test` then `/dev-impl` in separate sessions), or it needs a `[DEFERRED]` entry with `Target:` and `Reason:`. Silent drop is not an option.
- **Symbol-presence `STUB-WARNING:` on a `[x]` task.** The task claims to be done but the files don't contain the symbols the title/acceptance imply. Either finish the implementation or un-mark the task.
- **`sessions_logged` fails with "no session events logged for vN".** `sprint_close.py` refuses to lock a sprint with zero logged sessions when the `metrics/` module is installed. The fix is honesty: if sessions happened and weren't logged, log them retroactively from memory; if you genuinely never logged any, that's the signal the discipline hasn't landed yet and the retro should call it out. If the repo is on the minimum-viable adoption path (no `metrics/` module), the check passes with a "not installed" note — this refusal mode only fires for teams that opted into metrics logging.
- **`security_review` / `ui_qa` fails with "SECURITY-REVIEW.md is missing" or "UI-QA.md is missing".** The PRD's scope flag says `Yes` but no artifact is committed. Run `/security-review` or `/ui-qa`; commit the artifact; re-run `/sprint-close`.
- **`security_review` / `ui_qa` fails with "missing field(s): Decision".** The artifact exists but the reviewer never signed the `Decision:` line. Get the sign; don't forge.
- **`security_review` / `ui_qa` fails with "Decision: blocked".** Working as intended. Resolve the blocker, re-run the scope skill, commit the updated artifact with `Decision: passed`.
- **No SIGNOFF.md and `--reviewer` not passed.** Pass `--reviewer NAME` or get a reviewer to create SIGNOFF.md and re-run.

## Interaction with other skills

- `/dev-impl` produces the `[x]` markers and `Completed:` dates `/sprint-close` verifies (after `/dev-test` has committed the failing matrix in a separate session).
- `/sprint-close` unlocks the next `/prd`. Without the `.lock`, `/prd` for vN+1 refuses to start and `sprint_gate.py` blocks writes into vN+1.
- `/incident` is the post-close safety net. Bugs caught in Stage 1 before sprint-close are defects; bugs caught after are incidents and run the failures-log loop.

## Deliverables at the end of `/sprint-close`

- `sprints/vN/RETRO.md` filled in with real content, not template stubs.
- `sprints/vN/WALKTHROUGH.md` written (or confirmed signed off).
- `sprints/vN/SIGNOFF.md` exists with a real reviewer name and today's date.
- `python3 scripts/reconcile.py sprints/vN --ci` exit code 0.
- `sprints/vN/.lock` written with `locked_at`, `reviewer`, and `reconcile_status` fields.
- If scope required it: `sprints/vN/SECURITY-REVIEW.md` and/or `sprints/vN/UI-QA.md` committed with `Decision: passed` or `Decision: n/a` (the close refuses structurally if they are missing or blocked).
- The engineer has reviewed the close artifacts and is ready to commit.
