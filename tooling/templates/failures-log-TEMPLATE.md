# <YYYY-MM-DD> — <Short descriptive title>

**Domain:** <e.g., auth, payments, data integrity, client-X-integration>
**Severity of the originating incident:** P0 / P1 / P2
**Status:** Active prevention rule / Consolidated into <other entry> / Retired

## What happened

<2–4 sentences describing the observable failure. What did the user see, what did the system do, what was the client impact. Concrete details; no hedging.>

## Root cause

<The underlying mechanism, not the symptom. One paragraph. If the root cause was a combination of factors, list them and name the primary one.>

## Should have caught at

<Which phase of the method would have caught this if it had been applied correctly? Pick one:>

- [ ] Design-doc spec-lint or ambiguity pass (requirement was ambiguous or missing)
- [ ] `/prd` — task decomposition missed a requirement or failed to add a `Satisfies:` line
- [ ] `/dev` Step 2.5 — test matrix was incomplete, especially category D (fallthrough) or E (architecture guards)
- [ ] `/dev` test review — tests existed but would not have caught a wrong implementation
- [ ] `/reconcile` — coverage check did not run, or ran but was overridden
- [ ] `/security-review` — security lens was skipped or findings were dismissed
- [ ] `/ui-qa` — browser automation did not cover the failing flow
- [ ] Mutation testing — the test suite had a coverage gap that mutation testing would have exposed
- [ ] `/sprint-close` — sprint was closed without running the full checklist
- [ ] `/gap` — cross-sprint drift was not caught because `/gap` was not run or findings were not acted on
- [ ] Not in scope of the method — describe what kind of check would have caught it

## Prevention rule

<The specific, actionable rule that would catch this class of bug going forward. "Write better tests" is not a prevention rule. "Expiry tests must advance real or fake-but-advancing time past the expiry threshold between generation and validation" is. The rule should be specific enough that you could implement it as a test, a linter check, or a CLAUDE.md "never do" entry.>

## Where this rule lives

<Name the artifact(s) where this rule now lives. Check all that apply:>

- [ ] Added to `CLAUDE.md` under "Never-do rules"
- [ ] Added to `/dev` Step 2.5 test-matrix guidance (which category: A/B/C/D/E)
- [ ] Added as a CI check: `<name of the check>`
- [ ] Added to `/security-review` prompt as a specific lens
- [ ] Added to the ambiguity-pass prompt as a domain-specific question
- [ ] Implemented as an architecture-guard test: `<test file and name>`

## Related entries

<Links to other failures-log entries with similar root causes. If this entry should be consolidated with another, name the more general entry.>

## Timeline

- **<date>:** Incident detected
- **<date>:** Root cause identified
- **<date>:** Prevention rule written
- **<date>:** Prevention rule deployed (in CI / CLAUDE.md / prompt)
- **<date>:** Last referenced by <initiative/sprint> (update when consulted)
