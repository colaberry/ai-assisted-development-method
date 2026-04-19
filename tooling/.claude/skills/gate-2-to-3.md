# /gate-2-to-3 — Internal Product Mode: exit Validation, enter Commercialization

This skill runs the Stage 2 → Stage 3 graduation gate for Internal Product Mode. The gate is the decision to commercialize: external clients, contracts, support obligations, the works. It is the most consequential gate in Internal Product Mode because the cost of getting it wrong is high — both shipping a product that shouldn't have shipped (technical debt + client debt simultaneously) and not shipping one that should have (opportunity cost on real validated value).

The gate produces a written decision document at `docs/gates/stage-2-to-3.md`. The skill enforces the **pre-committed retention** rule: the metric and threshold must have been written into the Stage 2 PRD *before* the team read the data. Picking the metric after seeing the data is how this gate becomes "I think it's enough" with extra steps.

## When to invoke

- The repo is in Internal Product Mode, Stage 2 (`stage == "validation"`).
- Stage 2 has been running long enough to have meaningful retention data — typically 4+ weeks of usage by the Stage 2 user cohort.
- The team has named decision-makers ready to commit to the commercialization path (or not).
- The current sprint is closed.

Do not invoke `/gate-2-to-3` to:
- Force a graduation because the team is excited. Excitement is not retention.
- Skip the pre-commitment check because "we know what the threshold should be." If the threshold isn't in the Stage 2 PRD before the data is read, the gate fails on principle. This is non-negotiable.
- Graduate based on trial evidence (sign-ups, single sessions, prompted return). Trial is Stage 2's job; retention is Stage 3's bar.

## Preconditions

Before doing anything, run:

```bash
python3 state-check/scripts/state-check.py --json
```

Refuse to proceed if:

- **Mode is not `internal_product`** — this skill doesn't apply.
- **Stage is not `validation`** — either you haven't run `/gate-1-to-2` yet, or you're already in Stage 3.
- **The Stage 2 design document is missing or template-stub** — there's nothing to graduate from.
- **The Stage 2 PRD does not declare a pre-committed retention metric and threshold** — this is the structural blocker. Before doing anything else, the team must point at a written line in their Stage 2 PRD that says "this is the metric, this is the threshold." If it's not there, the gate refuses. The team can amend the PRD now, but if they do, they must wait through one more cohort window before re-running the gate. Picking the metric after seeing the data is the bias the rule prevents.
- **The current sprint is open** — close it first.
- **P0 flags exist** — resolve them.

## What this skill does

The skill walks the team through six evidence questions. Each question has a hard bar; below the bar, the gate cannot graduate.

### 1. What is the pre-committed retention metric and threshold?

The skill asks the team to read the metric and threshold from the Stage 2 PRD. The skill then locates that line in the PRD and quotes it back. If the line doesn't exist or doesn't pre-date the data, the gate stops here.

The default starting heuristic (from the Internal Product Mode doc): **≥40% of Stage 2 users return self-directed (no nudge, no scheduled session) in at least 3 of the 4 weeks following first meaningful use.** Tighten for daily-use products (e.g., DAU/WAU ≥ 0.5); loosen the cadence for monthly-use compliance tooling but keep the self-directed requirement.

What does not count:
- Prompted return (the team Slacked them, sent reminders, scheduled a session)
- Single-session try-it (no return)
- Aggregate "users used it" with no per-user cohort cut

### 2. Did the actual retention clear the threshold?

The skill asks for the per-user cohort data and computes the retention rate against the pre-committed metric. It does not allow recomputation against a different metric ("well if we count it this way…"). The metric is fixed; the answer is yes or no.

If the threshold cleared, advance. If it didn't clear, the gate cannot graduate — go to outcome 2 or 3 below.

### 3. What is the engineering readiness state?

What in the codebase needs to be re-done with client-grade rigor before external exposure? The team should be able to name:
- Which Stage 1 code is still in production paths and is missing Category D and E coverage
- Which dependencies were chosen for Stage 1 expedience and need to be revisited
- Which security boundaries weren't tested because Stage 1 didn't have external users
- Which monitoring/alerting/runbooks don't exist yet

This becomes the first Stage 3 initiative — typically 2–6 weeks of hardening work *before* the first external client touches the product.

### 4. What is the commercial commitment?

Stage 3 means real clients with real contracts. The skill asks:
- Who is the first commercial client? (Named, not "we have leads.")
- What does the contract look like? (Pilot? Paid? SLA?)
- Who owns commercial success? (Named individual.)
- What does a commercialization timeline look like over the next 6 months?

If commercial commitment is "we'll figure it out after we ship," the gate fails — that's a Stage 2 extension, not a Stage 3 graduation.

### 5. What is the support model?

External clients have support expectations Stage 1 and Stage 2 internal users don't. The team should be able to answer:
- Who is on call when the product breaks?
- What is the SLA the team is committing to?
- Where does an external client report a bug?
- Who handles the `/incident` post-mortem when something goes wrong in production?

A Stage 3 product without a support model is going to acquire client debt within weeks of launch.

### 6. Are you ready to inherit the AADM v3.x discipline in full?

Stage 3 is "v3.2.1 with no asterisks." That means:
- `/gap` runs are mandatory (Stage 1 and 2 skipped this; Stage 3 doesn't)
- Failures log is reviewed every sprint
- Mutation testing on shared libraries (Stage 2 had this; Stage 3 broadens it)
- All `/security-review` and `/ui-qa` requirements honored without exception
- Test matrix is full A/B/C/D/E on every task
- The PreToolUse hook (`sprint_gate.py`) and the security CI gate are both live

If the team is "going to ramp into" the full discipline, the gate fails — Stage 3 is the discipline.

## What this skill produces

`docs/gates/stage-2-to-3.md` with:

- **Date of the gate meeting** (today's ISO date)
- **Attendees** (names of decision-makers present)
- **Quoted line from the Stage 2 PRD** establishing the pre-committed retention metric and threshold (with file path and line context)
- **Per-user cohort data** showing retention against the metric — actual numbers, not summaries
- **Per-question answers and bar assessments**
- **Decision** — one of three options:
  1. **Graduate to Stage 3.** Includes:
     - Named first commercial client and contract type
     - Engineering readiness initiative scope (the first Stage 3 work)
     - Support model (on-call, SLA, bug intake)
     - Commercial owner and commercialization timeline
  2. **Extend Stage 2** with a focused plan to answer what's missing — names what specifically is missing, what would clear it, and when the gate will be re-run.
  3. **Decide not to commercialize** — a legitimate outcome, not a failure. The product can keep running internally indefinitely; or it can be sunset. Either path is recorded with rationale.

If graduating, the document also includes the engineering-debt repayment scope (typically 2–6 weeks of hardening before the first external client).

## What this skill does NOT do

- **Does not allow post-hoc metric selection.** This is the structural rule. If the metric isn't pre-committed in the Stage 2 PRD, the gate fails — full stop.
- **Does not allow trial-evidence substitution for retention.** Sign-ups are not retention. Single sessions are not retention. Prompted return is not retention.
- **Does not graduate without a named commercial commitment.** "We'll find clients after we ship" is Stage 2 thinking.
- **Does not graduate without an engineering readiness initiative.** The first Stage 3 work is hardening; it is never a new feature.
- **Does not produce a "we're basically ready" document.** The three outcomes are graduate, extend Stage 2, or decide not to commercialize. There is no fourth option.
- **Does not soften the bars when the team is enthusiastic.** Enthusiasm is the strongest predictor of motivated reasoning at this gate. The skill is here to apply the bars consistently.

## Interaction with other skills

- Runs after `/sprint-close` on the final Stage 2 sprint.
- If graduating: triggers the first Stage 3 `/prd` for the engineering readiness initiative.
- `/incident` becomes much more consequential after this gate — Stage 3 incidents are external-client-visible and the failures-log loop has to be tight.
- `state-check.py` surfaces the gate-overdue condition — a Stage 2 repo that's been in validation for 6+ months without a gate document is a P1 flag (per the Internal Product Mode doc's "Stage 2 is not a permanent state" rule).

## Deliverables at the end of `/gate-2-to-3`

- `docs/gates/stage-2-to-3.md` with the pre-committed metric quoted from the Stage 2 PRD, actual cohort retention data, per-question evidence, and an explicit decision.
- If graduating: a hardening initiative scope, a named first client, a support model, and a commercial timeline.
- If extending Stage 2: a focused plan naming what's missing and when the gate re-runs.
- If not commercializing: rationale recorded, ongoing-internal-use or sunset path named.
- The team leaves the meeting knowing which outcome happened and why.
