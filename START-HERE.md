# AI-Assisted Development Method — Final Bundle (v3.2.1)

This bundle contains everything needed to adopt the AI-Assisted Development Method on a new or existing client repo. Read this file first, then follow the "Getting Started" steps below.

## What's in this bundle

```
.
├── START-HERE.md                              # This file
├── method/
│   ├── AI_Assisted_Development_Method_v3_2_1.md   # Method document — client delivery (markdown)
│   └── AI_Assisted_Development_Method_v3_2_1.docx # Method document — client delivery (Word)
├── handbook/
│   ├── Developer_Handbook.md                  # Practical guide for engineers (markdown)
│   └── Developer_Handbook.docx                # Practical guide for engineers (Word)
├── internal-mode/
│   ├── Internal_Product_Mode.md               # Companion process for internal products (markdown)
│   └── Internal_Product_Mode.docx             # Companion process for internal products (Word)
├── state-check/
│   ├── README.md                              # Brief setup overview
│   ├── DOCUMENTATION.md                       # Full user guide + technical + integration (markdown)
│   ├── DOCUMENTATION.docx                     # Full user guide + technical + integration (Word)
│   ├── scripts/
│   │   └── state-check.py                     # Repo state detector CLI (tested, works)
│   └── .claude/skills/
│       └── state-check.md                     # Claude Code conversational skill
└── tooling/
    ├── README.md                              # Tooling-specific setup guide
    ├── scripts/
    │   └── reconcile.py                       # Sprint coverage check (tested, works)
    ├── .github/workflows/
    │   └── reconcile.yml                      # CI merge gate
    └── templates/
        ├── client-intake-TEMPLATE.md          # Phase 0 intake — capture requirements from vague client input
        ├── CLAUDE.md                          # Per-client persistent context
        ├── failures-log-README.md             # Folder README for docs/failures/
        ├── failures-log-TEMPLATE.md           # Single failures-log entry template
        ├── retro-TEMPLATE.md                  # Per-sprint retrospective
        ├── sprint-PRD-TEMPLATE.md             # Sprint planning document
        └── sprint-TASKS-TEMPLATE.md           # Task list (format /reconcile parses)
```

## Reading order

- **Tech leads and PMs:** Read `method/` first (60–90 min). Read `internal-mode/` if you build products internally. Reference `handbook/` when onboarding engineers.
- **Engineers:** Read `handbook/` first (45 min). Reference `method/` for context and rationale. Install and use `state-check/` when starting a session or switching contexts.
- **New engineer onboarding:** `handbook/` + your project's CLAUDE.md + most recent entries in `docs/failures/` + run `/state-check` or `state-check.py` to orient. That's enough to contribute.
- **Building something internally that might become SaaS:** Read `internal-mode/` — it's a companion process calibrated for the exploration → validation → commercialization lifecycle.
- **Unsure what to work on right now:** Run `python3 state-check/scripts/state-check.py` or `/state-check` in Claude Code.

## What this method is

A structured process for shipping enterprise-grade software to external clients using Claude Code. Designed for small teams (3–10 engineers). The core idea: **automate what you would otherwise ask reviewers to check, and make skipping steps structurally impossible instead of culturally discouraged.**

The method operates at two levels:

- **Initiative level** — a multi-sprint effort to ship a design document. Preceded by **Phase 0** (discovery and design-doc authoring) when the client hasn't provided a complete spec. Gated by `/gap` at the end.
- **Sprint level** — one sprint of an initiative. Gated by `/sprint-close` before the next sprint can start.

Requirements have stable IDs (§X.Y, Dn, Qn, SOW-§X.Y) that propagate from the contract through the design doc, sprint PRDs, and tasks to code. The `/reconcile` script enforces traceability in CI.

## What problem this solves

- **PRD → gap analysis → new PRD → gap analysis loops.** Solved by stable requirement IDs plus CI-enforced coverage.
- **Client gave us a vague problem statement, not a spec.** Phase 0 with the intake template turns vague input into signed-off requirements before sprint work begins.
- **Sprint-skipping across multi-sprint initiatives.** Solved by `/sprint-close` as a structural gate.
- **Silent descoping.** Solved by the `[DEFERRED]` discipline in tasks.
- **LLM-written tests that look thorough but don't catch real bugs.** Solved by the test matrix (categories D and E specifically) plus periodic mutation testing.
- **Client delivery surprises.** Solved by client-facing artifacts that are projections of internal artifacts, never written independently.
- **Repeating the same class of bug.** Solved by the failures log feeding forward into new design docs.

## Getting started

### Step 1: Read the method document

`method/AI_Assisted_Development_Method_v3_2_1.md` or the `.docx` variant. Give yourself 60–90 minutes.

**Minimum sections to read on first pass:**

- Team and Client Context (establishes the small-team / enterprise fit)
- **Initiative Level → Phase 0** (how to start an engagement when the client hasn't given you a spec)
- Process Flow (the two-level diagram plus ASCII rendering)
- Sprint Level — the four sprint phases end to end
- Rules the Team Must Follow (all 15)
- Anti-Patterns to Kill Immediately

### Step 2: For a new client engagement, start with Phase 0

If you're engaging with a new client who hasn't handed you a complete design document, Phase 0 is where you start.

1. **Copy the intake template** to the client repo:
   ```bash
   mkdir -p docs/intake
   cp templates/client-intake-TEMPLATE.md docs/intake/<CLIENT>-<YYYY-MM-DD>.md
   ```
2. **Fill it in during discovery interviews.** Structured 1:1 conversations with the people who will use the system and the person who signs off on acceptance. Every `[REQUIRED]` section gets filled in — or marked as an open question with an assigned owner.
3. **Hand the completed intake to Claude Code** using the prompt in Section 14 of the template. It produces a draft design document, an ambiguity-pass question list, and a proposed first-sprint scope.
4. **Your team reviews the draft before showing it to the client.** The LLM will have made interpretive choices that need validation.
5. **Client reviews the draft, pushes back, signs off.** Output: a stable design document with assigned requirement IDs and a matched SOW.
6. **Phase 0 closes when:** signed-off design doc exists, SOW is mapped to requirement IDs, open questions are resolved or explicitly deferred.

Phase 0 is time-boxed to 1–3 weeks for typical enterprise engagements. Longer usually means the client doesn't know what they want — re-evaluate before continuing.

### Step 3: Set up the client repo

From the root of the client repo:

```bash
# Unzip this bundle somewhere accessible
BUNDLE=/path/to/this/bundle

# Copy the reconcile script
mkdir -p scripts
cp "$BUNDLE/tooling/scripts/reconcile.py" scripts/
chmod +x scripts/reconcile.py

# Wire the CI merge gate
mkdir -p .github/workflows
cp "$BUNDLE/tooling/.github/workflows/reconcile.yml" .github/workflows/

# Create the docs structure
mkdir -p docs/intake docs/contract docs/decisions docs/failures docs/client-facing
cp "$BUNDLE/tooling/templates/failures-log-README.md" docs/failures/README.md
cp "$BUNDLE/tooling/templates/failures-log-TEMPLATE.md" docs/failures/TEMPLATE.md

# Drop in the intake template (for Phase 0)
cp "$BUNDLE/tooling/templates/client-intake-TEMPLATE.md" docs/intake/TEMPLATE.md

# Drop in the root CLAUDE.md and customize
cp "$BUNDLE/tooling/templates/CLAUDE.md" ./CLAUDE.md
# Now open CLAUDE.md and fill in every <BRACKETED> placeholder.

# Set up the first sprint directory (after Phase 0 is done)
mkdir -p sprints/v1
cp "$BUNDLE/tooling/templates/sprint-PRD-TEMPLATE.md" sprints/v1/PRD.md
cp "$BUNDLE/tooling/templates/sprint-TASKS-TEMPLATE.md" sprints/v1/TASKS.md
cp "$BUNDLE/tooling/templates/retro-TEMPLATE.md" sprints/v1/RETRO.md

# First commit
git add .
git commit -m "bootstrap: AI-assisted development method scaffolding"
```

### Step 4: Set up the contract traceability

1. Place the client's SOW at `docs/contract/SOW.md`.
2. Assign stable IDs (SOW-§X.Y) to each acceptance criterion. These become the root of the `Satisfies:` chain.
3. Write the initiative design document at `docs/<INITIATIVE-NAME>.md`, referencing SOW-§X.Y in the requirements it satisfies. Assign stable IDs (§X.Y, Dn, Qn) to new requirements and decisions.

If you're using Phase 0, steps 3 and 4 are outputs of Phase 0 — you don't do them separately.

### Step 5: Run the first sprint

Follow the method's Sprint Level section:

1. `/prd` — scope the sprint from the design doc. Every task gets a `Satisfies:` line.
2. `/dev` — one task per session, test matrix first (categories A–E), separate sessions for tests and implementation.
3. `/reconcile` — runs in CI on every PR. Blocks merges when requirements aren't covered.
4. `/sprint-close` — runs `/reconcile`, `/walkthrough`, `/retro`, and writes the lockfile.

`/sprint-close` and `/walkthrough` are manual checklists for now; automate them after you've used them for a few sprints.

### Step 6: Watch for the common skips

From honest prediction: these will happen in your first initiative.

1. Someone wants to start sprint v2 before v1 is locked because "v1 is basically done." Refuse. That's the anti-skip gate working.
2. The test matrix D (fallthrough) gets skipped on a "small" task. It won't feel necessary until something breaks.
3. The ambiguity pass produces questions, they get answered in Slack, nobody updates the design doc. Check whether the doc actually got edited.
4. The failures log accumulates entries faster than prevention rules. Each entry needs a rule, or the log becomes a graveyard.
5. **New:** Phase 0 gets rushed. Intake has `[REQUIRED]` fields marked "TBD" and the design doc gets written against the gaps. Enforce the handoff-readiness checklist in Section 13 of the intake template.

## Version notes

- **Method:** v3.2.1 — adds Phase 0 and the client intake template to v3.2. If you were already planning to use v3.2, v3.2.1 is a drop-in replacement.
- **Tooling:** day-one essentials plus the intake template. `/reconcile` is a tested working script; `/sprint-close`, `/gap`, `/security-review`, and `/ui-qa` are manual checklists until your team has used the basics for a while.

## What this bundle deliberately does NOT include

- **`/sprint-close`, `/walkthrough`, `/gap`, `/security-review`, `/ui-qa` automation scripts.** Higher-leverage to build once the manual versions have stabilized.
- **Mutation testing setup.** Language-specific; add when you pick critical modules.

## Quick reference — the 15 rules

From the method document:

1. One sprint at a time per initiative stream.
2. One task at a time per `/dev` session.
3. Never skip the test matrix. Categories D and E matter most when they feel least necessary.
4. Test writing and implementation are in separate Claude Code sessions.
5. Never accept "it should work" without running it.
6. When Claude Code gets stuck in a loop, stop and re-specify.
7. Keep CLAUDE.md, decision records, and the failures log current.
8. Do not use gap analysis as a primary workflow.
9. Automate what you would otherwise ask reviewers to check.
10. Spike code re-enters at the design-doc level, not at a sprint or task level.
11. Silent descoping is an anti-pattern.
12. Requirement IDs are stable.
13. Per-client separation is hard. One repo per client.
14. Every client-facing artifact is a projection of an internal artifact.
15. SOW clauses get requirement IDs.

## Calibration for small teams

- **Mutation testing:** monthly, critical modules only. Not weekly.
- **`/gap`:** per initiative and quarterly for long-running. Not monthly.
- **Per-client repos:** one per engagement.
- **CLAUDE.md:** under ~500 lines.
- **Active failures-log rules:** 20–50 for a mature codebase. Prune quarterly.
- **Phase 0 duration:** 1–3 weeks for typical enterprise engagements.

## When to come back

Come back when something breaks, when a skip produces a real problem, or when a pattern emerges that the method doesn't account for. Real data beats hypotheticals. The best questions will start with "we tried X and Y happened."

Good luck.
