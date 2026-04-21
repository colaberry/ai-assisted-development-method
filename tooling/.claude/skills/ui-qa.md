# /ui-qa — Manual UI QA for the current sprint

This skill runs end-user QA on the UI surfaces the sprint changed. Unit and integration tests verify that components render and handlers fire; this skill catches the things only a human exercising the real UI catches — broken journeys, overlapping elements, missing focus states, unreadable contrast, mobile-viewport regressions. Output is a committed `sprints/vN/UI-QA.md` artifact that `sprint_close.py` structurally requires when the PRD declared `` `/ui-qa` required: Yes ``.

`sprint_close.py` is the authority. If the PRD flag is `Yes` and the artifact is missing or marked `Decision: blocked`, the sprint refuses to lock. "The tests passed, it probably works" is exactly the omission that lands as an `/incident` three weeks later; this skill exists because it keeps doing so.

## When to invoke

- The PRD for the active sprint has `` `/ui-qa` required: **Yes** ``.
- The sprint's UI changes are deployed to a staging build or a PR preview — QA against localhost-only screenshots misses build-config bugs.
- The tester (the engineer, reviewer, or a designated QA) has time to walk the journeys, not just click once and move on.

Do not invoke `/ui-qa` to:
- Satisfy the gate by generating a file. `sprint_close.py` parses `Decision:` and requires `passed`, `n/a`, or `blocked`; malformed artifacts are rejected.
- Skip QA on a UI-bearing sprint by flipping the flag to `No`. If the scope changed, edit the PRD explicitly; silent flag flipping loses the audit trail.
- Run against localhost when a staging build exists. Build-config and deployment-only bugs (env vars, CDN paths, SSR mismatches) hide from localhost.

## Preconditions

- `sprints/vN/PRD.md` exists with `` `/ui-qa` required: **Yes** ``.
- A staging or PR-preview URL is available for the changes this sprint landed.
- The tester can articulate at least one concrete user journey to exercise — "click through the app" is not a journey.

Refuse to proceed if:
- **PRD flag is `No` or unset.** If QA is warranted anyway, update the PRD first.
- **No running UI target.** Spin up staging or a PR preview; do not QA against a blank localhost.

## What this skill does

1. **Pulls the list of UI-touching changes from the sprint's TASKS.md.** Tasks whose `Files:` touch frontend paths (`src/components/`, `src/pages/`, `app/`, `web/`, etc. — whatever CLAUDE.md's code-organization section declares) define the review surface.
2. **Prompts the tester to name user journeys.** One journey per touched surface, minimum. "Login → dashboard → export report" counts; "checked the app" does not.
3. **Walks each journey in at least one browser.** Records browser version, viewport, and the staging build SHA or preview URL in the artifact.
4. **Spot-checks accessibility** on any new or modified UI:
   - Keyboard navigation — every interactive element reachable and operable without a mouse.
   - Focus order — logical and visible.
   - Color contrast — WCAG AA minimum on text and interactive states.
   - Screen reader — at least spot-check that new controls have sensible labels.
5. **Checks mobile viewport** on any new or modified layout. Overlapping elements, off-screen controls, and broken tap targets are the usual finds.
6. **Drafts `sprints/vN/UI-QA.md`** from `tooling/templates/ui-qa-TEMPLATE.md`. Fills in scope, environments, findings, and the accessibility section. Leaves `Reviewer:` and `Decision:` for the tester to own on commit.
7. **On findings,** each bullet names severity, the reproducing steps, and whether it blocks the close or is deferred with a target sprint. Blockers flip `Decision:` to `blocked` and `sprint_close.py` will refuse to lock.
8. **On passed clean runs,** `Findings` reads `- None identified.` — the one-line structural signal that QA ran and found nothing.

## What this skill does NOT do

- **Does not set `Decision: passed` on the tester's behalf.** The decision is the tester's to sign.
- **Does not flip the PRD flag.** If the sprint turned out to have no UI changes, the flag was set incorrectly; fix the PRD and leave the `n/a` decision for sprints where the flag was right but nothing shipped to test.
- **Does not substitute screenshots for walking the journey.** A screenshot is evidence inside the journey; it is not the journey.
- **Does not skip because "the change was tiny".** Tiny changes ship the most regressions. Tiny changes should produce tiny artifacts — a one-line scope, one journey, `- None identified.` — not no artifact.

## Handling the common refusal modes

- **`sprint_close.py` refuses with "UI-QA.md is missing".** The PRD says `Yes` but no artifact exists. Run `/ui-qa` and commit the result.
- **`sprint_close.py` refuses with "missing field(s): Decision".** The `Decision:` line wasn't filled in. Get the tester's sign.
- **`sprint_close.py` refuses with "Decision: blocked".** Working as intended. Fix the blocker, re-run `/ui-qa`, commit the updated artifact with `Decision: passed`.
- **No staging build available because deploy is flaky.** That is itself a blocker worth recording; either flip to `Decision: blocked` on "QA could not run against a real build," or fix the deploy and re-run.

## Interaction with other skills

- `/sprint-close` structurally requires this artifact when the PRD says so. This skill produces it.
- `/incident` runs the failures-log loop. UI regressions that reached production become failures-log entries; subsequent `/ui-qa` runs should confirm the prevention rule is in place.
- `/dev` produces the UI code this QA exercises. A `/dev` session adding new UI should flag the journeys worth exercising in its session log.

## Deliverables at the end of `/ui-qa`

- `sprints/vN/UI-QA.md` committed, with:
  - `Reviewer:` with a real name.
  - `Date:` with today's date in `YYYY-MM-DD`.
  - `Decision:` one of `passed`, `n/a`, or `blocked`.
  - Scope, environments, findings (or `- None identified.`), and accessibility sections non-stub.
- Any new failures-log entries created for issues found.
