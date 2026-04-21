# Security review — Sprint vN

**Sprint:** vN
**Scope:** <auth / data / integrations / infra / multiple>
**Reviewer:** <name>
**Date:** YYYY-MM-DD
**Decision:** <passed | n/a | blocked>

> `sprint_close.py` parses `Reviewer:`, `Date:`, and `Decision:` above. Decision must be one of `passed`, `n/a`, or `blocked`. A `blocked` decision refuses the sprint lock until the blocker is resolved and the review is re-run.

---

## What was reviewed

<Concrete list of the changes reviewed this sprint. Reference commit ranges, PR numbers, or the TASKS.md entries that touched security-relevant code. Do not write "everything" — name the surfaces.>

- <touched area 1 — PR #N / commit range>
- <touched area 2>

---

## Findings

<One bullet per finding. If no findings, write exactly `- None identified.` — that one-line form is the passed-clean signal.>

- <finding 1 — severity — summary — fix or suppression reference>
- <finding 2>

---

## Suppressions added this sprint

<If any `# nosemgrep` or similar suppression was added, list it here with the entry from `docs/security/suppressions.md` that justifies it. Suppressions without a registered entry are a blocker, not a passed finding.>

- <none> / <suppression-id — file:line — reason>

---

## Notes

<Optional. Context the reviewer wants to leave for future sprints — areas that felt risky but aren't blocking, patterns worth capturing in CLAUDE.md, etc.>
