# <YYYY-MM-DD> — <Short descriptive title of the incident>

**Severity:** P0 / P1 / P2
**Detected:** <YYYY-MM-DD HH:MM timezone>
**Resolved:** <YYYY-MM-DD HH:MM timezone — leave blank until the incident is actually closed>
**Author:** <name>
**Reviewers:** <name(s) who reviewed this post-mortem>

> **Status rule:** a post-mortem without a filled-in `Resolved:` line is treated as an open incident by `state-check.py` and will show up as a P1 flag. Do not close the file by deleting the field — write the resolution timestamp.

---

## Summary (one paragraph)

<What happened, who was affected, how long, and what stopped it. Three to six sentences. A reader who only reads this paragraph should come away with the right mental model.>

---

## Timeline

<All times in a single timezone, stated explicitly. Be specific — "around 3pm" is not a timeline entry.>

- **<YYYY-MM-DD HH:MM tz>** — <What happened or was observed>
- **<YYYY-MM-DD HH:MM tz>** — <Next event>
- **<YYYY-MM-DD HH:MM tz>** — <Mitigation deployed>
- **<YYYY-MM-DD HH:MM tz>** — <Resolution confirmed>

---

## Impact

- **User-visible impact:** <What users saw / could not do. Quote the error message if there was one.>
- **Scale:** <How many users, how many requests, what percentage of traffic. Numbers, not adjectives.>
- **Data impact:** <None / corrupted / exposed / lost. Be precise — "3 user records had `last_login` set to NULL incorrectly" beats "some data was affected.">
- **Client/commercial impact:** <SLA breach? Revenue impact? Escalation to client leadership? None?>

---

## Root cause

<The underlying mechanism, not the symptom. One to three paragraphs. If multiple factors combined to produce the failure, list them and name the primary one. Distinguish between the *trigger* ("X deployed at Y time") and the *latent cause* ("the Z code path had never been exercised with empty input").>

---

## What went well

<2–4 bullets. Alerting fired correctly? Rollback was clean? Runbook existed? Name the things that worked so they don't atrophy.>

---

## What went poorly

<2–4 bullets. Slow detection? Unclear ownership during the page? Missing rollback capability? Miscommunication with the client? Be specific; "communication" is not a finding.>

---

## Does this invalidate a requirement or design decision?

Choose one:

- [ ] **No.** The spec was correct; the implementation drifted. Prevention is a failures-log rule (see below).
- [ ] **Yes — a requirement was wrong.** The SOW / design doc called for behavior that turned out to be incompatible with production reality. A design-doc update PR is required before the next sprint; name the requirement ID(s) and what the new language should say.
- [ ] **Yes — a decision was wrong.** An ADR in `docs/decisions/` assumed something that turned out to be false. Supersede that ADR with a new one; do not edit in place.

If "Yes": **Design-doc / ADR update PR:** <link or "TODO by <YYYY-MM-DD>">

---

## Action items

Each action item must have an owner and a due date. "We'll be more careful" is not an action item.

- [ ] <Specific, time-bounded change> — **Owner:** <name> — **Due:** <YYYY-MM-DD>
- [ ] <Specific, time-bounded change> — **Owner:** <name> — **Due:** <YYYY-MM-DD>

---

## Prevention rule for the failures log

Most incidents produce exactly one prevention rule — the specific, actionable thing that would catch this class of bug next time. "Write better tests" is not a prevention rule. "Token-expiry tests must advance real or fake-but-advancing time past the expiry threshold between generation and validation" is.

**Rule:** <the one-line rule>

**Where it lives** (check all that apply):

- [ ] New entry in `docs/failures/<YYYY-MM-DD>-<slug>.md` (using [failures-log-TEMPLATE.md](failures-log-TEMPLATE.md))
- [ ] Added to `CLAUDE.md` under "Never-do rules"
- [ ] Added as a CI check: `<name of the check>`
- [ ] Added to `/security-review` prompt as a specific lens
- [ ] Implemented as an architecture-guard test: `<test file and test name>`

**Failures-log entry link:** <docs/failures/YYYY-MM-DD-slug.md — or "TODO by <YYYY-MM-DD>">

---

## Related entries

- **Previous similar incidents:** <Links to prior post-mortems with similar root causes. If this is the third time we've hit this class, flag that prominently — the prevention rules aren't working.>
- **Related failures-log rules:** <Links. If a rule existed and did not catch this, note why.>

---

## Post-mortem review

- **Reviewed on:** <YYYY-MM-DD>
- **Attendees:** <names>
- **Action items added to tracker:** <link to ticket/issue/PR>
- **Failures-log entry committed:** <commit SHA or PR link>

---

*This post-mortem is blameless. Names appear for ownership of follow-ups, not assignment of fault. If the review devolves into "who did this," stop the meeting and reset.*
