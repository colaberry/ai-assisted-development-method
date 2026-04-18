# Sprint vN — Retrospective

**Sprint:** vN
**Sprint dates:** YYYY-MM-DD to YYYY-MM-DD
**Facilitator:** <name>
**Participants:** <names>

> **Goal of this document:** feed the failures log and CLAUDE.md from within-sprint experience, not just from shipped bugs. A retro with zero resulting updates to the memory layer is a retro that did not do its job.

---

## 1. What went well this sprint?

<Concrete, specific. "We shipped everything" is not an answer; "The integration-test pattern for async webhooks caught two real bugs before they reached staging" is.>

**Candidate patterns worth capturing** (these may become entries in a future `docs/patterns/` folder or updates to CLAUDE.md):

- <pattern 1>
- <pattern 2>

---

## 2. What went poorly?

<Be specific about root causes, not symptoms. "The sprint was too big" is a symptom; "We underestimated the SAML integration because we did not account for the client's non-standard attribute mapping" is a root cause.>

**Recurrences:** Did any past failure (see `docs/failures/`) repeat itself? If yes, the prevention rule did not work as intended — log that separately.

- <recurrence 1, with pointer to the original failures-log entry>

**New failure modes:** What went wrong that was not predicted by any existing rule?

- <new failure 1>

---

## 3. What surprised us?

<Things that were not predicted: client behavior, dependency behavior, emergent integration issues, architectural assumptions that turned out wrong. These often become prevention rules or CLAUDE.md updates, but not always — some surprises are one-offs.>

- <surprise 1>
- <surprise 2>

---

## 4. What prevention rules should we add?

For each new rule, this retro drafts the failures-log entry. A human reviewer should validate before the entry is marked canonical. One retro can produce zero entries (normal for a routine sprint) or multiple.

### Draft entry 1 (if applicable)

**Title:** <short descriptive title>
**Root cause:** <one-paragraph description>
**Prevention rule:** <specific, actionable>
**Where it lives:** <CLAUDE.md / CI check / test-matrix category / ambiguity-pass prompt>

**Action:** Create `docs/failures/YYYY-MM-DD-<slug>.md` from this draft, using the failures-log template. Assign to <name> by <date>.

### Draft entry 2 (if applicable)

<same structure>

---

## 5. Client communication

<This section is specific to enterprise client work. What patterns worked or failed in communicating with the client during this sprint?>

**Worked well:**

- <pattern, e.g., "Sending a mid-sprint status update including the /reconcile coverage table prevented an escalation about §4.2">

**Did not work:**

- <pattern, e.g., "The initial estimate did not account for client-side review cycles; add 3 business days buffer to future SAML-type integrations">

**Client-specific additions to CLAUDE.md:**

- <specific context that emerged this sprint and should persist, e.g., "Client's IdP sends `mail` attribute as the user identifier, not `email`">

---

## 6. Method calibration

<Briefly: is the method serving us? Are any gates being skipped? Any overhead that feels disproportionate to value?>

- **`/sprint-close` ran as expected:** Yes / No — <details if no>
- **`/reconcile` blocked a merge this sprint:** Yes / No — <details if yes, since this is the method working>
- **`/security-review` was in scope:** Yes / No — <if yes, were findings acted on?>
- **`/ui-qa` was in scope:** Yes / No — <if yes, bug-find rate?>
- **Test matrix category D and E were used:** Yes / No — <if no, why?>

---

## 7. Actions

Who does what by when. Keep to 5 items max; more means the retro is accumulating instead of acting.

- [ ] <action 1> — owner: <name>, by: <date>
- [ ] <action 2> — owner: <name>, by: <date>
- [ ] <action 3> — owner: <name>, by: <date>

---

## Retrospective on the retrospective

<Quarterly, review this field across the last ~10 retros. Are retros producing failures-log entries? Are actions getting completed? If the answer is "not really" to either, the retro itself needs calibration — it may be too long, too short, scheduled at the wrong time, or missing the right people.>

**This retro was:** useful / routine / performative
**Failures-log entries produced:** <count>
**CLAUDE.md updates produced:** <count>
