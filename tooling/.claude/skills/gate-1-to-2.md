# /gate-1-to-2 — Internal Product Mode: exit Exploration, enter Validation

This skill runs the Stage 1 → Stage 2 graduation gate for Internal Product Mode. The gate is not a checkbox; it's a decision meeting that produces a written decision document (`docs/gates/stage-1-to-2.md`) explaining *why* the evidence supports graduation — or why it doesn't. The skill structures the interview, pushes back on thin evidence, and refuses to produce the decision document unless the evidence is real.

Graduating without a gate is the most common way Internal Product Mode degrades: the team "just kind of" moves to Stage 2 because momentum says so, and the Stage 2 commitment (4–8 weeks of investment) gets made by accident rather than on purpose. This skill exists to keep that accident from happening.

## When to invoke

- The repo is in Internal Product Mode, Stage 1 (`stage == "exploration"`).
- The team believes they have real user-value evidence — not a hunch, not team enthusiasm, actual usage or reported value from real users.
- There is a `docs/hypothesis.md` with stated exit criteria. If there isn't, the gate is premature by definition.

Do not invoke `/gate-1-to-2` to:
- Justify a decision already made. The skill is the decision, not the paperwork for it.
- Paper over thin evidence. If the team wants to ship to external users but the evidence is weak, the correct output is a "not graduating" document naming what's missing — not a graduation document that fudges the bar.
- Graduate with only team-internal dogfooding. Stage 1 dogfooding is baseline; the gate requires evidence from users outside the immediate build team.

## Preconditions

Before doing anything, run:

```bash
python3 state-check/scripts/state-check.py --json
```

Refuse to proceed if:

- **Mode is not `internal_product`** — this skill doesn't apply.
- **Stage is not `exploration`** — you're either already graduated (in which case `/gate-2-to-3` is the next gate) or not yet in a mode where this gate applies.
- **`docs/hypothesis.md` is missing** — no hypothesis, no exit criteria, no gate. This is the Stage 0 setup condition the state-check flags as P0.
- **The current sprint is open** — close it via `/sprint-close` first. Gate decisions should be made at sprint boundaries, not mid-sprint.
- **P0 flags exist** — resolve them before running a graduation meeting.

## What this skill does

The skill walks the team through five evidence questions in order. Each question has a minimum bar; below the bar, the skill records the answer and continues but flags it as blocking at decision time. Nothing is forced — the skill records what the team says — but the skill is honest about whether what was said clears the bar.

### 1. Is the problem real?

Not "users said they had the problem." Real means: evidence of the problem existing in the user's behavior before the product was proposed.

- **Clears the bar:** quantified pain in production tickets, recorded user sessions showing the workaround, external data (industry reports, academic studies) matching the problem shape.
- **Does not clear the bar:** "users told us they'd use this" in a survey, team intuition, competitor-exists-therefore-problem-exists.

Record the answer verbatim in the decision doc. If the answer is below the bar, say so — don't paraphrase it into something stronger.

### 2. Does the exploration artifact do something useful?

The Stage 1 prototype or thin product should be doing *something* — not full quality, not all edge cases, but the core value delivered at least for the happy path.

- **Clears the bar:** a specific user can describe the task they accomplished with it in one sentence, without prompting.
- **Does not clear the bar:** the team can describe what the product *would* do once it's finished; users have used a demo but haven't used it on their own data.

### 3. Have real users (not the build team) used it without being prompted?

This is the load-bearing question. Stage 1 usage by the team is noise; Stage 1 usage by external users is signal.

- **Clears the bar:** at least 3 users outside the immediate build team have used the artifact on their own data for their own goals, with at least one returning on their own.
- **Does not clear the bar:** usage during scheduled demos, the CEO used it once, three users signed up but none returned.

The "3" is a floor, not a target — if the team can only name 3, the evidence is thin. 10+ is where this gets credible.

### 4. What did users actually do? What did they say?

Aggregate claims ("users love it") are inadmissible. The skill asks for specific user quotes and specific usage patterns.

- **Clears the bar:** three or more direct quotes from different users describing a specific value they got; usage patterns showing depth (multiple sessions, real data, unprompted return).
- **Does not clear the bar:** one enthusiastic user who also happens to be an investor; survey NPS with no free-text support; internal team "users love this."

Record the quotes verbatim. If they're thin, the decision doc says they're thin.

### 5. Are you ready to commit 4–8 weeks to Stage 2?

Stage 2 is a committed bet. The team is saying: for the next 4–8 weeks, we are going to harden this product and broaden its user base — this is not a thing we'll revisit in two weeks if something shinier appears.

- **Clears the bar:** named team members, named timeline, named Stage 2 success criteria (written into the upgraded design document as `docs/<PRODUCT>.md`).
- **Does not clear the bar:** "probably a couple of weeks"; no named owner; no success criteria stated before starting.

## What this skill produces

`docs/gates/stage-1-to-2.md` with:

- **Date of the gate meeting** (today's ISO date)
- **Attendees** (names of decision-makers present)
- **The five evidence questions** and the team's answers — verbatim, not paraphrased
- **Per-question bar assessment** — clears / below bar, with a short reason
- **Decision** — one of three options:
  1. **Graduate to Stage 2.** Includes named owner, timeline, and Stage 2 success criteria.
  2. **Stay in Stage 1** with a refined hypothesis — includes what needs to change and when the gate will be re-run.
  3. **Kill the product** — includes what the team learned and where the learnings go (ADR, failures log, or a writeup).
- **If graduating:** a checklist of Stage 2 opening moves:
  - Upgrade `docs/hypothesis.md` → `docs/<PRODUCT>.md` (living design document)
  - Write the first Stage 2 sprint PRD and TASKS via `/prd`
  - Add retroactive Category D and E test coverage to Stage 1 code that's surviving into Stage 2
  - Set `/ui-qa` to `Yes` on user-visible changes going forward (Stage 2 mandatory)

## What this skill does NOT do

- **Does not decide the outcome.** The skill structures the evidence and names the bars; the team decides. But the skill will tell the team clearly when the evidence does not meet the bar — that's the whole value.
- **Does not produce a "we'll revisit" document.** The three outcomes are graduate, refine hypothesis, or kill. "We'll come back to this" is not on the list; it's how Stage 1 becomes permanent.
- **Does not skip questions** because the team is sure. All five questions get asked, every time. A team that's sure will answer quickly; a team that should be sure but isn't will struggle on question 3 or 4, which is exactly the signal the gate is looking for.
- **Does not update any project state.** The decision document is the artifact; the actual state change (hypothesis → design doc, `stage` transition) happens in follow-up work the team decides on.
- **Does not overwrite prior gate documents.** If a prior gate meeting didn't graduate, its decision doc stays. The new meeting produces a new document with today's date, so the history of attempts is preserved.

## Interaction with other skills

- Runs after `/sprint-close` on the final Stage 1 sprint. Gate decisions live at sprint boundaries.
- Feeds into `/prd` for the first Stage 2 sprint, if the decision is graduate.
- `/gate-2-to-3` is the next gate in this sequence, triggered months later when the team is deciding whether to commercialize.
- `state-check.py` surfaces the gate-overdue condition — a Stage 1 repo that's been in exploration for many sprints with no gate document is a P1 flag.

## Deliverables at the end of `/gate-1-to-2`

- `docs/gates/stage-1-to-2.md` with verbatim evidence, bar assessments, and an explicit decision.
- If graduating: a concrete opening-moves checklist for Stage 2.
- If staying or killing: the learnings recorded and the next action named.
- The team leaves the meeting knowing which of the three outcomes happened and why.
