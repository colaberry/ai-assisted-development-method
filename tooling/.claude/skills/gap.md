# /gap — Initiative-boundary coverage analysis

`/reconcile` guarantees that every PRD requirement is claimed by a task.
It does **not** guarantee that every *initiative* requirement — the
stable IDs in `docs/<INITIATIVE>.md` — ever makes it into a sprint PRD.
A requirement can be silently dropped across every sprint of an
initiative and each sprint still reconciles green. At client
acceptance, the gap becomes visible and expensive.

`/gap` is the audit at that boundary. It diffs the design document's
requirement IDs against the union of `Satisfies:` citations across
every sprint's `TASKS.md` and emits `docs/<INITIATIVE>_GAP_ANALYSIS.md`
with covered, deferred, orphaned, and conflicted sections. Running it
is how the method keeps initiative-level silent drop from being a
possible failure mode.

## When to invoke

- Before `/sprint-close` on any sprint that finishes a chunk of an
  initiative — `/sprint-close` will refuse to lock while orphaned
  requirements exist, so run `/gap` first and decide on each orphan.
- When a design document gets amended (new requirements added) — the
  new IDs need to route into a sprint PRD or land as `[DEFERRED]`
  somewhere before the next close.
- On a cadence: at a minimum every two sprints, so the failure mode
  "§7.3 missed every PRD from v1 through v6" becomes catchable in v2
  rather than at acceptance.

Do not invoke `/gap` to:
- Edit a design document. Gap analysis is read-only on the spec.
- Silently drop a requirement. The skill surfaces the silent-drop case
  so a human can decide (new task or `[DEFERRED]` with target); it does
  not make that decision itself.
- Renumber or rename requirement IDs. Method rule 12 — stable IDs.
  Supersession (issue #29) is the cleanup path.

## Preconditions

Run `state-check.py` first:

```bash
python3 state-check/scripts/state-check.py --json
```

Refuse to proceed if:

- **Initiative document does not exist** at the path given. Gap analysis
  against a missing spec is nonsensical.
- **No sprints exist yet.** In that case every requirement is orphaned
  trivially — run `/prd` first to create sprint v1.

## What this skill does

1. **Identifies the initiative.** If the engineer names a doc, use it.
   Otherwise list `docs/*.md` design documents and ask which to analyze.
2. **Runs the script.** Exactly:
   ```bash
   python3 tooling/scripts/gap.py docs/<INITIATIVE>.md sprints/
   ```
   The script writes `docs/<INITIATIVE>_GAP_ANALYSIS.md` with the four
   sections plus a supersession map when applicable.
3. **Walks the engineer through each orphaned requirement.** One at a
   time. For each:
   - Confirm the ID is real (not a typo in the design doc).
   - Ask: does this belong in the current sprint, a future sprint
     (`[DEFERRED]`), or is it obsolete (needs a design-doc amendment
     and a separate PR)?
   - Never silently drop. If the decision is "obsolete", the engineer
     opens an amendment PR against the design document; `/gap`
     documents the intent in the analysis's "Notes" section.
4. **Walks the engineer through each conflict.** Multiple open tasks
   claiming the same requirement is legitimate when they cover
   different slices; worth reviewing otherwise. Note the decision
   in the analysis.
5. **Re-runs the script in `--ci` mode to confirm.**
   ```bash
   python3 tooling/scripts/gap.py docs/<INITIATIVE>.md sprints/ --ci
   ```
   Exit 0 is the clean signal. Exit 2 means orphans remain — loop back
   to step 3. Exit 1 means conflicts remain — loop back to step 4.
6. **Commits the updated analysis.** Commit the
   `docs/<INITIATIVE>_GAP_ANALYSIS.md` file. This is the artifact
   `/sprint-close` reads to decide whether to refuse the lock.

## What this skill does NOT do

- **Does not create sprint PRDs or tasks.** Adding a requirement to a
  sprint is `/prd`'s job. `/gap` surfaces the gap; the engineer (with
  `/prd` as the tool) closes it.
- **Does not edit the design document.** Amendments flow through
  `/prd` or a dedicated design-doc review, with stable-ID supersession
  handled per Method rule 12 and issue #29.
- **Does not run during `/dev-test` or `/dev-impl`.** Those skills are
  task-local; `/gap` is initiative-wide and runs between sprints.

## Interaction with other skills and scripts

- `/sprint-close` refuses to lock while `docs/*_GAP_ANALYSIS.md` shows
  orphaned requirements for the active initiative. The analysis is the
  structural gate; `/gap` is how you clear it.
- `/prd` picks up requirements that `/gap` has flagged as orphaned —
  either scoping them into the current sprint or adding a `[DEFERRED]`
  entry with a real `Target:` sprint and `Reason:`.
- `state-check.py` emits a P1 flag if the gap analysis is older than
  the most recent `.lock` — a stale analysis is the second failure
  mode (analysis exists but doesn't reflect the latest sprint).
- `reconcile.py` is still the *sprint-level* gate; `/gap` is the
  complementary *initiative-level* gate. Both need to pass for the
  method's traceability promise to hold end-to-end.

## Deliverables

- `docs/<INITIATIVE>_GAP_ANALYSIS.md` up-to-date as of the current
  sprint state.
- Zero orphaned requirements in `--ci` mode, or documented decisions
  (new task / `[DEFERRED]` / design-doc amendment) for every orphan.
- A clean exit 0 from the `--ci` re-run, witnessed in the session log.

## v1 scope notes

- Supersession is handled at a single-hop level: a requirement carrying
  a `SUPERSEDED-BY: §X, §Y` line is treated as covered when any of
  `§X`, `§Y` is covered or deferred-with-target. Full multi-hop
  supersession chain semantics are [issue #29](https://github.com/colaberry/ai-assisted-development-method/issues/29)
  and will land with the stable-ID supersession protocol.
- Deferred tasks without a `Target:` line do not count as legitimate
  deferrals. They surface as orphaned until a target is added.
- Completed `[x]` tasks still count as covering their `Satisfies:` IDs
  — that's the historical record.
