# /state-check — Conversational state guidance

This skill provides conversational guidance about what to work on next, based on the current state of the repo. It wraps the `state-check.py` CLI with human dialogue.

## When to invoke

- Start of a Claude Code session when the engineer isn't sure what to pick up
- After `/sprint-close` when deciding what to tackle next
- When joining an unfamiliar repo for the first time
- When something feels off and the engineer wants a sanity check

## What this skill does

1. Run `scripts/state-check.py --json` to get mechanical state detection
2. Parse the output
3. Present findings conversationally
4. Ask targeted questions where human judgment is required
5. Recommend a next action grounded in the current state and the method document

## What this skill does NOT do

- **It does not make judgment calls.** Gate graduations, kill-signal decisions, and prevention-rule quality are human calls. The skill surfaces them, doesn't resolve them.
- **It does not replace `/dev`, `/prd`, or other method commands.** It tells you which one to run.
- **It does not modify the repo.** If the engineer agrees to an action (e.g., "draft the gate-1-to-2-decision.md"), the skill can help with it, but only after explicit confirmation.

## Workflow

### Step 1: Run the CLI

```bash
python3 scripts/state-check.py --json
```

If the script is missing or fails:
- Tell the engineer that the CLI isn't available
- Offer to do a manual state check by inspecting the repo (look for `docs/intake/`, `docs/contract/SOW.md`, `docs/hypothesis.md`, `sprints/`, `.lock` files)
- Proceed with best-effort guidance

### Step 2: Present the state

Summarize in 2-4 sentences. Match the engineer's tone — if they asked casually, answer casually; if they asked formally, match that.

Good presentation example:

> You're in Client Delivery mode on the payment-integration initiative. Sprint v2 is active with 2 open tasks, 1 complete. Task T004 is flagged — it's missing a Satisfies: line, which will block `/reconcile` in CI.
>
> Before you start new work, you'll want to fix T004. After that, T003 is ready to go.

Bad presentation example:

> The state-check CLI returned the following information:
> - Mode: client-delivery
> - Stage: None
> - Phase: sprint
> ...

The CLI produces structured output. Your job is to translate it into natural prose.

### Step 3: Surface judgment calls

If the CLI produced `judgment_calls`, present them as questions, not as tasks. The engineer decides; you prompt.

Example:

> Two things worth thinking about before picking the next sprint:
>
> 1. The hypothesis doc says the kill signal was "5 of 5 test users fail the workflow." Where are you on that measurement? If the signal has fired, the method says pivot or kill — not add a feature.
>
> 2. You have 3 internal users who've used the product this week. If any of them came back unprompted and found value, you might be ready to draft `gate-1-to-2-decision.md`. What does the usage data show?

Resist the urge to infer answers from context. Let the engineer answer.

### Step 4: Recommend a next action

Ground the recommendation in the method document. Cite the specific phase or rule. Example:

> Based on what you've said, here's what I'd suggest:
>
> Since T004 is blocking `/reconcile`, start there. Method Rule 2 requires every task to have a `Satisfies:` line citing design-doc requirement IDs — open the task and ask what requirement it closes. If there isn't a clear one, the task shouldn't have been in the sprint in the first place; defer it.
>
> Once T004 has a valid Satisfies line, T003 is next. It satisfies D5 (session cookies), which is a security-touching requirement — that means `/security-review` will be required before this sprint can close. Want me to kick off T003 with the standard `/dev` task kickoff?

### Step 5: Offer to help with the next action

After the engineer confirms direction, offer specific help:
- For `/dev`: run the task kickoff prompt from Part 2.1 of the Developer Handbook
- For `/prd`: help scope the next sprint from the design doc
- For a gate decision: help draft the gate decision document
- For a failures-log entry: help write the prevention rule

But only after the engineer confirms — don't leap into action.

## Handling specific states

### State: Unknown mode

The repo isn't set up for the method. Likely reasons:

- Fresh repo, hasn't been bootstrapped
- Legacy repo, method being adopted retroactively
- This is a spike or exploratory repo (which the method explicitly excludes)

Ask the engineer which situation this is. If fresh, offer to walk through the setup steps from `START-HERE.md`. If legacy, offer to help with a gradual adoption path. If a spike, confirm that's intentional and don't push the method.

### State: Between sprints (all sprints locked)

The team has closed the last sprint and hasn't started the next. This is a legitimate state — sprints are demand-driven, not automatic.

Ask what the next sprint should tackle. If the engineer doesn't know, offer to run `/gap` on the initiative (if applicable) to see what's left, or to re-read the design doc to find the next priority.

### State: Sprint active, all tasks complete

The sprint appears done. Suggest running `/sprint-close`, which will run `/reconcile`, `/walkthrough`, `/retro`, and write the lockfile.

If the engineer seems uncertain whether the sprint is really done, ask specifically: did the `/reconcile` check pass locally? Did `/security-review` run if it was in scope? Did `/ui-qa` run if this sprint shipped UI? If any of those are "no" or "I didn't run it," that's the actual next step, not `/sprint-close`.

### State: Internal Product Mode, at a graduation gate

If judgment calls include "draft gate-1-to-2-decision.md" or "draft gate-2-to-3-decision.md," treat this as a significant decision, not a checklist item.

Ask the engineer the questions from the relevant gate section of Internal Product Mode. Don't compress them. The gates exist to make decisions weighty; compressing the conversation defeats the purpose.

Good prompt sequence for Gate 1→2:

1. "Who has used the product outside the build team? How many distinct people, in how many distinct sessions each?"
2. "What did they do? Walk me through one specific user's experience."
3. "In their own words, what value did they get? Can you quote them?"
4. "What kill signals are still in play that you haven't tested?"
5. "Is the team ready to commit 4-8 weeks to Stage 2, or is there still uncertainty about whether this is worth it?"

If any answer is weak, the gate is not crossed. Tell the engineer that directly and suggest what to focus on in the next Stage 1 sprint.

### State: Test files modified in recent commits

The CLI flagged this as a P1 anti-pattern candidate. It might be legitimate (test fixture updates, removed deprecated tests) or it might be the serious "tests modified to match code" failure.

Ask: what changed in the test files, and why?

- If the engineer can name a specific test that was wrong and describe why: fine, confirm that a note was added to the commit message or the retro, move on.
- If the engineer is vague ("just cleanup," "refactoring"): flag this. Suggest they review the diff themselves with fresh eyes before merging. This is the specific failure mode Method Rule 4 guards against.

### State: Gap analysis missing or stale (`gap_analysis_staleness`)

The CLI flagged this as a P1 traceability issue. Two shapes:

- **Missing:** `docs/<INITIATIVE>_GAP_ANALYSIS.md` does not exist for a design doc that has sprints against it. The initiative has never been audited for orphans. Before the next `/sprint-close`, run `/gap` on that initiative — `sprint_close.py` refuses to lock while orphans remain, and without an analysis there's no way to know whether any do.
- **Stale:** The analysis exists but its mtime is older than the newest sprint `.lock`. Sprints have been closed since the last audit. Orphans added by those sprints haven't been surfaced. Run `/gap` to refresh.

In both cases the next action is `/gap` on the named initiative, not "keep going on the current task." Surface this plainly to the engineer.

### State: Failures log has many entries but few recent prunes

The CLI flagged this as a P2 memory issue. Don't push hard; just note it:

> Your failures log has grown to 127 entries. The method suggests 20-50 active rules for a mature codebase; beyond that, the cross-check phase becomes noise. When you have bandwidth, consider a consolidation pass — merge entries producing the same rule, retire rules unused in 12 months. Not urgent, but worth scheduling.

## Meta-rules for this skill

- **Be direct.** Engineers using this skill are in the middle of work. They want information, not ceremony. Keep responses under ~10 sentences unless the engineer asks for detail.
- **Reference the method, don't invent.** If you find yourself recommending something the method doesn't say, stop and check. The CLI and the method document are the sources of truth.
- **Respect existing context.** If the engineer has been working on something specific, don't suggest they drop it without reason. State-check is a heads-up display, not a priority inverter.
- **When in doubt, ask.** A clarifying question is always better than a confident wrong recommendation.
- **Don't inflate value.** Most state-check invocations will end with "yes, keep doing what you were doing" and that's fine. Not every run needs to produce a finding.

## Integration with Developer Handbook

This skill complements Part 1 of the Developer Handbook (Daily Practices) by helping engineers figure out *which* daily practice applies right now. It does not replace reading the handbook — it assumes the engineer has absorbed the practices and needs orientation, not education.

If an engineer asks a "how do I..." question, defer to the handbook. If they ask a "what should I..." question, that's state-check territory.

## Calibration

Expect to tune this skill over the first few months of use. Specifically watch for:

- **Engineers running it and ignoring the output.** Means the recommendations are wrong or not relevant. Check the CLI logic first.
- **Engineers bypassing flags the skill surfaces.** Ask why. If the flag is noisy, adjust. If the flag is right but inconvenient, that's the method working as intended.
- **Judgment-call questions getting answered by the skill instead of the engineer.** That's the skill overstepping. Tighten the prompts.

When you update this skill, update `state-check.py` to match, and vice versa. They're a pair.
