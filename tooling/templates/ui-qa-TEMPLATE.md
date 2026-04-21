# UI QA — Sprint vN

**Sprint:** vN
**Scope:** <which UI surfaces were touched>
**Reviewer:** <name>
**Date:** YYYY-MM-DD
**Decision:** <passed | n/a | blocked>

> `sprint_close.py` parses `Reviewer:`, `Date:`, and `Decision:` above. Decision must be one of `passed`, `n/a`, or `blocked`. A `blocked` decision refuses the sprint lock until the blocker is resolved and UI QA is re-run.

---

## What was tested

<Concrete list of the user journeys or screens exercised this sprint. Reference TASKS.md entries or stories by ID.>

- <journey 1 — T001 — steps exercised>
- <journey 2>

---

## Environments

- **Browser(s):** <Chrome / Firefox / Safari / mobile Safari / ...>
- **Viewport(s):** <desktop / tablet / mobile>
- **Build:** <staging build SHA / PR preview URL>

---

## Findings

<One bullet per finding. If no findings, write exactly `- None identified.` — that one-line form is the passed-clean signal.>

- <finding 1 — severity — summary — bug link or fix reference>
- <finding 2>

---

## Accessibility

<Required for any sprint that added or modified user-facing UI. Note which axes were checked (keyboard nav, screen reader spot-check, color contrast, focus order). "N/A" is acceptable when the sprint did not add new UI.>

- <axis — tool/method — result>

---

## Notes

<Optional. Patterns worth capturing, surprises, bugs deferred with explicit target sprint, etc.>
