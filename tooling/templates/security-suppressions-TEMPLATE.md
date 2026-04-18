# Security Suppressions

**Path:** `docs/security/suppressions.md`

Every `# nosemgrep` (or equivalent) comment in the codebase must have a matching entry here. An unannotated suppression is a silent exception to the security gate — it defeats the whole point of having the gate.

> **Multi-tool note.** This template assumes Semgrep. If you add other scanners (Bandit uses `# nosec`, ESLint uses `// eslint-disable-next-line`, Trivy uses `#trivy:ignore`, etc.), record the tool in the `Rule:` field (e.g. `bandit: B602`) and extend the removal ceremony to cover that tool's suppression syntax. The 90-day re-review discipline applies tool-agnostically.

Entries are re-reviewed every 90 days. [state-check.py](../state-check/scripts/state-check.py) flags entries older than that as P2. Re-review means one of:

- Remove the suppression (the rule now applies).
- Update `Re-reviewed:` to today's date with reviewer name (the suppression still applies; reasoning unchanged).
- Supersede with a fix (code change + remove suppression + remove entry).

---

## Entry format

```markdown
### S<NNN>: <one-line description>

- **File:** path/to/file.py:123
- **Rule:** semgrep rule id (e.g. `python.lang.security.audit.dangerous-subprocess-use-tainted-env-args`)
- **Suppressed:** YYYY-MM-DD by @reviewer
- **Re-reviewed:** YYYY-MM-DD by @reviewer
- **Satisfies affected:** SOW-§X.Y, Dn (which requirements does this touch?)
- **Justification:** <why the rule does not apply in this specific case. Be concrete. "The input comes from an authenticated admin session that is validated upstream in middleware/auth.py:42" beats "the input is trusted.">
- **Expiry:** YYYY-MM-DD (optional — if the suppression is tied to a specific dependency upgrade or deprecation date)
```

---

## Entries

<!-- Keep entries in numerical order. Do not delete removed entries — strike them through and add a `Removed: YYYY-MM-DD` line so history survives. -->

### S001: <example — replace or delete>

- **File:** src/example.py:42
- **Rule:** python.lang.security.audit.example-rule
- **Suppressed:** 2026-01-01 by @example-reviewer
- **Re-reviewed:** 2026-01-01 by @example-reviewer
- **Satisfies affected:** SOW-§X.Y
- **Justification:** This is a placeholder entry. Replace with a real suppression or delete this section.

---

## What is NOT a valid justification

- "This is a false positive." → Say *why* it's false positive. If the rule is truly noisy, file an upstream issue and disable the rule globally; don't inline-suppress.
- "We'll fix it later." → Open an issue and link it here. An entry without a tracked follow-up becomes permanent.
- "The reviewer said it was fine." → What did the reviewer *reason*? Capture the reasoning, not the conclusion.

## Removal ceremony

When the underlying issue is fixed:

1. Delete the `# nosemgrep` comment in code.
2. Run the security workflow locally (`semgrep scan --config=auto --severity=ERROR`) and confirm no finding at that location.
3. In this file: strike through the entry (`~~### S001: ...~~`) and add a `**Removed:** YYYY-MM-DD by @reviewer — fixed in <commit-sha-or-PR>.` line below the entry.
4. Do not renumber — S001's number stays S001 forever.
