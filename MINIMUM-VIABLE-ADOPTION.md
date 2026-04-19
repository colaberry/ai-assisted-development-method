# Minimum-Viable AADM Adoption

**Audience:** Teams who like the AADM thesis but can't adopt the full method on day one. You have an active project, a backlog, real users, and an honest answer of "no" to "can we stop and bootstrap a 6-piece process this week?"

**Goal of this doc:** get the *one structural property* that makes the rest of AADM payoff — **CI-enforced traceability from requirement to code** — running on your existing repo in under a day, in a way that's compatible with adopting the full method later.

If you have time to read [START-HERE.md](START-HERE.md) and adopt the whole bundle, do that instead. This doc is for the case where the alternative to "minimum viable" is "nothing."

---

## What you give up by going minimum-viable

Be honest about what's not in this path so you don't claim more than you have:

- **No Phase 0** — you keep whatever requirements process you have today. AADM does not improve your spec quality in this mode; it only catches drift between the spec and the code.
- **No `/sprint-close`, no `.lock`, no anti-skip gate** — sprint boundaries stay cultural. Teams that skip sprints today will keep skipping them.
- **No security or UI gates** — you keep your existing review process. AADM adds nothing here in minimum-viable mode.
- **No retros, no failures log** — you don't get the institutional-memory loop. Same bug class can recur.
- **No mutation testing, no test matrix discipline** — your test suite stays as good or as bad as it is today.

What you do get: **silent descoping becomes structurally impossible on the work you tag.** That's the highest-leverage single property in the method. Everything else is incremental.

---

## The four pieces

In order, smallest first:

### 1. CLAUDE.md at the repo root (15 minutes)

Copy [tooling/templates/CLAUDE.md](tooling/templates/CLAUDE.md) to your repo root and fill in the `<BRACKETED>` placeholders. Don't perfect it — fill in the obvious ones (stack, deploy target, commands, two or three never-do rules) and ship.

Why first: every Claude Code session in this repo will load this file. Even without the rest of the method, this single file dramatically improves consistency of AI-generated changes.

**Done when:** every `<BRACKETED>` placeholder is replaced or deleted, and the file is committed.

### 2. Stable requirement IDs in your existing spec (1–2 hours)

Wherever your requirements live today — a Notion doc, a PRD in the repo, a Jira epic, the SOW — assign each acceptance criterion a stable ID using one of the AADM patterns: `§X.Y`, `§X.Y.Z`, `Dn` (decisions), `Qn` (open questions), or `SOW-§X.Y` (contract clauses).

These IDs do **not** have to be in the AADM templates. They just have to exist somewhere greppable, be unique, and never get reused after assignment.

If your requirements don't live in the repo, paste the IDs and one-line summaries into `docs/requirements.md` so `/reconcile` can find them. The source of truth can stay where it is; the IDs need to be in the repo.

**Done when:** every acceptance criterion has an ID, and the IDs are committed to the repo (either in your existing doc or a mirror file).

### 3. `Satisfies:` lines in your task tracking (per-task, ongoing)

For new work going forward, every task includes a one-line `Satisfies:` citation pointing to the IDs from step 2. The format `reconcile.py` parses lives in [tooling/templates/sprint-TASKS-TEMPLATE.md](tooling/templates/sprint-TASKS-TEMPLATE.md):

```markdown
- [ ] T001: Add password complexity validation
  - Satisfies: §3.2, SOW-§4.1
  - Files: src/auth/password.py, tests/auth/test_password.py
  - Acceptance: `validate_password()` rejects passwords under 12 chars
```

You don't need a `sprints/vN/` directory layout to start. A single `TASKS.md` (or one per backlog chunk) is enough. The script doesn't care about the parent folder name; it cares about the file format.

**Done when:** the next task you start has a `Satisfies:` line, and your team has agreed that no PR merges without one.

### 4. `reconcile.py` in CI as a merge gate (30 minutes)

Copy two files:

```bash
mkdir -p scripts .github/workflows
cp tooling/scripts/reconcile.py scripts/
cp tooling/.github/workflows/reconcile.yml .github/workflows/
```

Edit [reconcile.yml](tooling/.github/workflows/reconcile.yml) to point at the directory containing your `PRD.md` (or `requirements.md`) and `TASKS.md`. If you put both files in the repo root, the path is `.`; if you used `docs/`, it's `docs/`.

Run it locally first to confirm it parses your files:

```bash
python3 scripts/reconcile.py docs/
```

Expect it to flag missing requirements on the first run. That's the whole point — those are the requirements you didn't have a task for. Add the tasks (with `Satisfies:` lines) and run again until it returns 0.

Then enable the workflow as a required check on your default branch in GitHub branch protection. From this point forward, any PR that merges code without a `Satisfies:` chain back to a requirement ID will fail CI.

**Done when:** the workflow is required on `main`, and your team has experienced one PR being blocked by it (this is good — it means it's working).

---

## What you do *not* need to do

To keep this minimum-viable, explicitly skip:

- The `sprints/vN/` directory layout. Use one flat `TASKS.md` if that fits your existing flow.
- `sprint_close.py` and the `.lock` discipline. You can run sprints however you run them today.
- The retro template, walkthrough, and failures log. Add later.
- The Semgrep [security gate](tooling/.github/workflows/security.yml). High-value, but additive — bring it in once `/reconcile` is sticking.
- `state-check.py`. Useful, not load-bearing in this mode.
- Internal Product Mode, the handbook, the metrics module. All optional in minimum-viable.

---

## What "ready to graduate" looks like

After 4–8 weeks of running the four pieces above, you should have:

- A handful of PRs that were caught by the `/reconcile` gate. (If zero PRs were caught, either you have unusually disciplined ID hygiene, or the gate isn't actually wired up — verify.)
- A clear sense of which AADM pieces would have prevented bugs you actually shipped during this period. That sense is the prioritization signal for what to add next.

The natural next pieces, in rough order of leverage:

1. **`sprint_close.py` + the `.lock` discipline.** Once you've felt the pain of someone "starting v2 because v1 is basically done" and shipping a regression, this becomes obviously worth the cost. See [tooling/scripts/sprint_close.py](tooling/scripts/sprint_close.py).
2. **The failures log.** As soon as the same bug class recurs twice, you want this. See [tooling/templates/failures-log-TEMPLATE.md](tooling/templates/failures-log-TEMPLATE.md).
3. **Semgrep security gate.** Cheap and additive. See [tooling/.github/workflows/security.yml](tooling/.github/workflows/security.yml).
4. **`/reconcile --strict-symbols`.** Catches the empty-stub-passes-reconcile pattern. Turn this on once your team has internalized that `Satisfies:` is not a checkbox.
5. **The full method.** At this point you've earned the context for [START-HERE.md](START-HERE.md) to make sense.

There's no badge for "graduated to full AADM." The point is to add the next piece when the team feels the absence of it, not on a schedule.

---

## What this doc deliberately doesn't promise

- **It doesn't fix bad requirements.** Garbage IDs in, garbage coverage out. Phase 0 exists in the full method specifically to address this; minimum-viable mode does not.
- **It doesn't catch wrong implementations.** `/reconcile` answers "did we build something for this requirement?" not "does it work?" Your test suite still has to do that job.
- **It doesn't prevent silent skipping at sprint boundaries.** That's `sprint_close.py`'s job, and it's intentionally out of scope here.

If you want those properties, you want the full method. If you want the single highest-leverage structural change you can make this week without restructuring how your team works, you want this doc.
