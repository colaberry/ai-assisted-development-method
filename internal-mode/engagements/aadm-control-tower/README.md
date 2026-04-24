# AADM Control Tower — dogfood engagement artifacts

This directory holds reference artifacts for the **AADM Control Tower** initiative, an internal webapp that Colaberry builds under AADM Internal Product Mode (see `../../Internal_Product_Mode.md`).

## What is here

| File | What it is |
|---|---|
| `intake.md` | Phase-0 intake produced on 2026-04-23. Captures the problem, users, constraints, and graduation signals for the initiative. |
| `design-stage-0.md` | Stage 0 design doc (localhost-only scope). Stable IDs §X.Y, D1–D7, Q12–Q17. Sprint v1 scope handoff in §13. |

## Canonical-source policy

**Today (before the Control Tower repo exists):** the files in this directory are the **canonical source of truth** for the initiative. All edits, reviews, and sign-offs happen here.

**After the Control Tower repo is bootstrapped** (Sprint v1 Task 1, per design doc §13): the files in this directory become **frozen snapshots**. The canonical source of truth moves to the Control Tower repo's `docs/` folder. At that point:

1. Sprint v1 Task 1 copies `intake.md` and `design-stage-0.md` into the new Control Tower repo.
2. Sprint v1 Task 1 also adds a "SNAPSHOT" banner to the top of each file in **this** directory, pointing to the canonical location.
3. From that point forward, edits happen only in the Control Tower repo. The snapshots in this directory are not updated unless explicitly re-synced (rare — only when a teaching-quality reason exists).

This is **Option B** of the three choices discussed on 2026-04-23. Option A (move entirely) and Option C (keep both synced) were rejected.

### Why Option B

- **AADM repo keeps teaching value.** Anyone reading the AADM method can see a real intake and real design doc produced by applying the method. Without a snapshot here, the AADM repo becomes method-only and loses its best example.
- **One source of truth for live work.** The Control Tower repo owns the live version. No risk of two diverging forks.
- **No sync-maintenance cost.** Snapshots are frozen, not kept in lockstep. The "SNAPSHOT" banner makes the frozen state obvious to readers.

### The snapshot banner (format, for reference)

When Sprint v1 Task 1 adds the banner, it looks like this at the top of each file in this directory:

```markdown
> **📸 SNAPSHOT — <date>.** This file is a frozen reference copy. The canonical, live version lives in the Control Tower repo at `docs/<filename>`. Edits made here will not propagate. To change the live document, edit it in the Control Tower repo.
```

## Convention for future dogfood engagements

This directory establishes the pattern `internal-mode/engagements/<initiative>/` for all future Colaberry internal-product-mode engagements. Each initiative gets its own subdirectory, its own `README.md`, and the same canonical-source-policy lifecycle (canonical here until the initiative's own repo exists, then snapshots).
