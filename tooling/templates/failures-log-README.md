# Failures Log

This folder records significant bugs, near-misses, and `/gap` findings that revealed a systemic issue. Each entry exists to **change future behavior** — if an entry would not change what someone does when they encounter it, it should not be here.

## When to write an entry

Write a new entry when any of these happen:

- A bug reaches late-stage testing or production.
- `/gap` surfaces a requirement that was silently dropped between sprints.
- Mutation testing catches a class of weak test.
- A `/retro` identifies a recurring pattern worth capturing.
- A client escalates an issue that tracing shows could have been caught earlier.

**Do not write an entry for:**

- A bug caught by unit tests before merge. That is the system working correctly.
- A style or formatting issue. Those live in the linter config.
- A one-off mistake with no underlying pattern. If it would not happen again under similar circumstances, it does not need a prevention rule.

## Entry format

Every entry has these fields. Filename pattern: `YYYY-MM-DD-short-slug.md`.

See `TEMPLATE.md` for the blank template.

## Rules for this folder

1. **Entries describe root causes, not symptoms.** "The UI showed the wrong number" is a symptom. "Currency conversion was run twice because two call sites both applied it" is a root cause.

2. **Every entry ends in a prevention rule.** A rule that names the specific check, test, or pattern that would catch this class of bug in the future. If you cannot write a prevention rule, the entry is not done.

3. **Prevention rules feed forward.** Each rule either becomes a test pattern (added to `/dev` Step 2.5), a check in CI, an entry in `CLAUDE.md` under "never-do rules," or a question in the ambiguity pass. Track where each rule landed.

4. **Entries are referenced, not just written.** During design-doc ambiguity passes and `/dev` task kickoffs, Claude Code reads this folder and flags applicable prevention rules. An entry that is never read is an entry that never helped.

5. **Prune quarterly.** Rules older than 12 months that have not been referenced or violated are candidates for consolidation or retirement. The active prevention-rule set should stay around 20–50 entries for a mature codebase. A log with 200 entries is a graveyard; 20 well-maintained entries is a codebook.

6. **Consolidation beats accumulation.** If two entries produce the same prevention rule, merge them under the more general rule. Preserve references to the original incidents for traceability.

## What this folder is not

- **Not a blame log.** Entries describe what failed and why. They do not name individuals or imply fault. Everyone makes mistakes; the system captures lessons without making them personal.
- **Not a bug tracker.** Individual bug tickets live in the project management system. This folder records lessons from bugs, not the bugs themselves.
- **Not a client-facing document.** These entries describe internal learning. The client-facing variant of a significant incident goes under `docs/client-facing/` with the internal jargon stripped.

## Current index

Entries, newest first. Update when adding a new entry.

<!-- INDEX:START -->
<!-- INDEX:END -->
