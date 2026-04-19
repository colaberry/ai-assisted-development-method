# /incident — Post-deployment learning loop

This skill runs when something has gone wrong in production. It orchestrates the post-mortem, extracts a prevention rule into the failures log, and — when the incident reveals that a requirement or design decision was wrong — optionally drafts a design-doc update PR.

The AADM SDLC coverage today stops at `/sprint-close`. `/incident` completes the loop: what breaks in production feeds back into CLAUDE.md, the failures log, and (when needed) the design document itself. Without this loop the team learns only from things caught *before* merge; shipped bugs recur because nobody promoted the lesson into the prevention surface.

## When to invoke

- **Immediately after a production incident is mitigated.** Not while the page is still active — mitigation first, post-mortem second. The skill is for the after, not the during.
- **When a client reports a material defect** that made it through sprint-close. Even if you rolled back quickly, the fact that it merged is itself the finding.
- **When discovering a latent bug** (a problem that shipped but hadn't yet manifested visibly). The post-mortem format applies even without a customer-visible outage.

Do not invoke `/incident` for:
- Known-and-tracked bugs in the backlog. Those are defect tickets, not incidents.
- Development-environment problems. Use `docs/failures/` directly if you want a prevention rule.
- Near-misses caught by CI. `/reconcile` and the test suite are working as designed; no incident occurred.

## What this skill does

1. Confirms the incident is actually over (mitigated / resolved), not in-progress. If the user describes an active incident, the skill declines and suggests coming back after mitigation.
2. Creates `docs/incidents/<YYYY-MM-DD>-<slug>.md` from `tooling/templates/incident-TEMPLATE.md`.
3. Walks the user through the template section by section, asking targeted questions where human judgment is required. Does **not** fabricate timestamps, scales, or root causes.
4. Helps extract a specific, actionable prevention rule — challenges vague rules ("write better tests") and pushes for testable, rule-shaped output.
5. Creates a corresponding `docs/failures/<YYYY-MM-DD>-<slug>.md` entry using the failures-log template, cross-linked to the incident.
6. If the user indicates a requirement or ADR was wrong: drafts a design-doc update or a superseding ADR as a separate PR — does not edit design docs silently.
7. Reminds the user to close the loop by adding the prevention rule to the appropriate enforcement surface (CLAUDE.md, CI check, architecture-guard test, etc.).

## What this skill does NOT do

- **Does not decide severity.** P0/P1/P2 is a human call based on business impact and SLA.
- **Does not page people, open tickets, or notify stakeholders.** That's the on-call flow, not the post-mortem flow.
- **Does not assign blame.** Post-mortems are blameless. Names appear on action items for ownership only.
- **Does not close the incident.** The `Resolved:` timestamp goes in when the human confirms the fix is live and stable — not when the skill finishes.
- **Does not silently update design docs.** Any requirement or ADR change is a separate, reviewed PR.

## Workflow

### Step 1: Confirm the incident is over

Before anything else, ask:
- Is the mitigation deployed?
- Is the fix confirmed live in production?
- Are customer-visible effects resolved?

If any answer is "not yet," stop. Tell the user to come back to `/incident` once the page is closed. Running a post-mortem during an active incident produces bad post-mortems and takes focus off mitigation.

### Step 2: Create the incident file

```bash
mkdir -p docs/incidents
cp tooling/templates/incident-TEMPLATE.md docs/incidents/<YYYY-MM-DD>-<slug>.md
```

Use today's date in the filename and a short kebab-case slug describing the incident (e.g., `2026-04-19-auth-session-expiry-regression.md`).

### Step 3: Fill the template section by section

Walk the user through the template in order. For each section, ask the questions that section implies rather than producing a first draft from thin air. Specifically:

- **Timeline:** ask for concrete timestamps with a stated timezone. "Around 3pm" is not a timeline entry — push for the actual time in the monitoring tool or the first Slack message. If the user genuinely doesn't know within 5 minutes, ask them to check the alerting log before answering.
- **Impact:** push for numbers, not adjectives. "Some users" → "how many, over what window?" "A few failed requests" → "what percentage of traffic?"
- **Root cause:** distinguish *trigger* from *latent cause*. If the user answers only with the trigger ("X deployed and broke things"), ask "why did the deployment break things?" until you reach a latent cause that could have been caught by a test or a review.
- **What went poorly:** ensure bullets are specific. "Communication was bad" isn't a finding; "the on-call didn't know the runbook location for the auth subsystem" is.

### Step 4: Surface the requirement/ADR question

Ask explicitly: **does this incident invalidate any requirement or design decision?**

- **If no:** proceed to prevention-rule extraction. The spec was right; the implementation drifted.
- **If a requirement was wrong:** name the specific requirement ID(s). Draft the language change. Create it as a separate PR against the design doc; reference the incident post-mortem in the PR body. Do not edit the design doc in the same PR as the incident file — design changes deserve their own review.
- **If an ADR was wrong:** do not edit the existing ADR in place. Create a superseding ADR with the corrected decision and mark the old ADR with `**Superseded by:** <new ADR>`. This preserves the historical record.

### Step 5: Extract the prevention rule

Most incidents produce exactly one prevention rule. Push for specificity:

- "Write better tests" — not a rule.
- "Add a Category D test" — closer, but still underspecified.
- "Token-expiry tests must advance real or fake-but-advancing time past the expiry threshold between generation and validation" — a rule. It's specific enough to implement as a test, a linter check, or a CLAUDE.md never-do entry.

Once the rule is concrete, create the corresponding failures-log entry from `tooling/templates/failures-log-TEMPLATE.md`. Cross-link the incident post-mortem and the failures-log entry.

### Step 6: Name the enforcement surface

A rule in the failures log but nowhere else will not catch the next occurrence. Ask where the rule will actually run:

- **CLAUDE.md "Never-do rules"** — good for invariants the agent should honor in every session
- **CI check** — good for rules that can be mechanically verified (schema enforcement, config validation)
- **Architecture-guard test (Category E)** — good for structural invariants ("this function must be called from this middleware")
- **`/security-review` prompt lens** — good for judgment-laden security patterns
- **Test matrix discipline in `/dev`** — good for coverage gaps that keep recurring

Commit the prevention-rule addition to the enforcement surface in the same PR as the failures-log entry. If this isn't done, state-check will continue to see an open incident.

### Step 7: Schedule the review

Post-mortems are reviewed — ideally in the next sprint's retro, or in a dedicated 30-minute meeting within 5 business days. Remind the user that the `Post-mortem review` section of the template needs filling in after that meeting. Until it's filled, the incident isn't fully closed.

## Closing the incident

The incident is closed when all of these are true:

1. `Resolved:` timestamp is filled in on the post-mortem.
2. A failures-log entry exists and is cross-linked.
3. The prevention rule is live on at least one enforcement surface (CLAUDE.md / CI / test / prompt).
4. If a requirement or ADR change was needed, that PR has been merged.
5. The post-mortem review has occurred and the `Post-mortem review` section is filled in.

`state-check.py` checks for condition 1 (missing `Resolved:` timestamp) and will flag open incidents. Conditions 2–5 are human checks.

## Anti-patterns this skill refuses to enable

- **"Let's skip the post-mortem, we know what happened."** If you know, writing it down takes 20 minutes and prevents recurrence. If you don't know, you need the post-mortem even more.
- **"This was a one-off."** Everything looks like a one-off until it happens the second time. The failures-log entry is cheap insurance.
- **"The prevention rule is: be more careful."** Not a rule. Push back until you have something a test or linter could enforce.
- **"We'll update the design doc later."** "Later" means after another incident that invalidates the same requirement. Draft the update PR now.
- **Silently editing a requirement or ADR to match reality.** Traceability depends on the history being accurate. Supersede; don't overwrite.

## Deliverables at the end of `/incident`

- `docs/incidents/<YYYY-MM-DD>-<slug>.md` with every section filled in except `Resolved:` (waits for confirmed live fix) and `Post-mortem review` (waits for the review meeting).
- `docs/failures/<YYYY-MM-DD>-<slug>.md` with a concrete prevention rule and its intended enforcement surface.
- One or more PRs (separately) landing the prevention rule on the enforcement surface.
- If applicable: a design-doc update PR or a superseding ADR.
