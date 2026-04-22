# State Check — Documentation

*User guide, technical reference, and integration notes for the state-check CLI and Claude Code skill*

---

## Part 1: What this is and why it exists

State-check is a pair of tools — a Python CLI and a Claude Code skill — that answer one question:

> **"Where are we in the method right now, and what should I work on next?"**

It exists because the AI-Assisted Development Method (AADM) has real surface area. A mid-size engagement has a design doc, a SOW, a failures log, multiple sprints, CLAUDE.md, retros, and a set of conventions to follow. An engineer sitting down at the start of a session — especially if they've been away for a few days or joined recently — has to reconstruct "where are we?" before doing anything. That reconstruction is slow and error-prone. Worse, it's the exact moment when skipping steps is easiest, because nobody is watching.

State-check collapses that reconstruction into a 30-second run that tells you:

- Which mode the repo is in (client delivery or internal product)
- Which phase or stage you're currently in
- What's active (sprint, tasks, flags)
- What needs attention (P0/P1/P2 issues)
- What to work on next
- What judgment calls you're sitting on (not resolved for you — flagged so you can resolve them)

**It is a heads-up display, not an autopilot.** That distinction is important and shows up throughout this document.

### What it does not do

- It does not make product decisions. Gate graduations, kill-signal interpretation, and priority calls are human decisions.
- It does not evaluate code quality. Tests either pass or fail; state-check doesn't judge whether they're good tests.
- It does not replace `/dev`, `/prd`, `/sprint-close`, or any other method command. It tells you which one to run.
- It does not modify the repo. Always safe to run.

---

## Part 2: Installation

### As part of the method bundle

If you've unzipped `ai-dev-method-FINAL.zip`, state-check is already in the `state-check/` folder. Skip to "Adding to your client repo" below.

### Adding to your client repo

From the root of the client repo:

```bash
# The CLI (required)
mkdir -p scripts
cp /path/to/state-check/scripts/state-check.py scripts/
chmod +x scripts/state-check.py

# The Claude Code skill (optional but recommended)
mkdir -p .claude/skills
cp /path/to/state-check/.claude/skills/state-check.md .claude/skills/
```

That's it. No dependencies beyond Python 3.11+ stdlib. Does not require git (though it uses git if present for test-modification detection).

### Verifying the install

```bash
python3 scripts/state-check.py
```

You should see a report. If the repo isn't set up for the method yet, you'll see `Mode: Unknown (method not yet set up)` and a P0 flag about missing CLAUDE.md — that's expected and correct.

---

## Part 3: Typical user workflow

### At the start of a session

You sit down to work. Before opening anything else:

```bash
python3 scripts/state-check.py
```

Or in Claude Code:

```
/state-check
```

Read the output. In 95% of cases, this takes under a minute and you know exactly what to do.

### When the output is clean

A clean run looks something like:

```
========================================================================
Repository state check
========================================================================

Mode:               Client delivery (v3.2.1)
Active initiative:  payment-integration
Active sprint:      sprints/v3
Phase:              sprint
Tasks:              2 open, 4 complete, 1 deferred

Flags:              None

Recommended next:   2 open task(s) in sprints/v3. Pick the next one and run /dev.

========================================================================
```

Two open tasks, no flags. Open `sprints/v3/TASKS.md`, pick one, start `/dev`.

### When flags appear

Flags come in three severities.

**P0 flags** are blocking. Resolve before doing anything else.

Examples:
- Task missing a `Satisfies:` line — `/reconcile` will fail in CI
- CLAUDE.md missing at repo root — Claude Code sessions won't have context
- Sprint has no PRD.md — method can't track coverage

The tool exits with code 1 when a P0 is present. This makes it CI-integratable: a pre-commit hook or a periodic job can reject states with P0 issues.

**P1 flags** are anti-pattern indicators or calibration issues. Not blocking but should be addressed soon.

Examples:
- CLAUDE.md is 612 lines (threshold 500) — LLMs start skipping middle content
- Test files modified in recent commits — possible "tests modified to match code" anti-pattern
- No SOW at `docs/contract/SOW.md` — contract traceability incomplete

**P2 flags** are informational. Schedule a pruning pass when you have bandwidth.

Examples:
- Failures log has 127 entries — consolidation pass recommended
- Sprint has no RETRO.md yet — run `/retro` before `/sprint-close`

### When judgment calls appear

For internal-product work especially, state-check surfaces questions the method expects humans to answer. Example:

```
Judgment calls (for humans, not automated):
  1. Has the kill signal fired? If yes, the gate says: pivot or kill, not continue. Revisit the hypothesis doc.
  2. Is there evidence of real user value from non-team users? If yes, draft docs/gate-1-to-2-decision.md to graduate to Stage 2. If no, next sprint should test the next hypothesis, not add features.
```

These are not action items. They are prompts to think. The tool cannot know whether your kill signal fired because it requires reading user behavior data that doesn't live in the repo. It's your job to answer them and act accordingly.

If the judgment call is genuinely ambiguous — "I'm not sure if the kill signal fired" — that's itself an answer: it means you haven't measured what you said you'd measure, and the next sprint should fix that.

---

## Part 4: Interpreting the output

### Mode detection

State-check examines the repo for specific signals:

| Signal | Interpretation |
|---|---|
| `docs/hypothesis.md` exists | Internal Product Mode, Stage 1 at minimum |
| `docs/gate-1-to-2-decision.md` exists | Internal Product Mode, Stage 2 |
| `docs/gate-2-to-3-decision.md` exists | Internal Product Mode, Stage 3 |
| `docs/contract/SOW.md` or `docs/intake/<file>.md` exists | Client delivery |
| None of the above | Unknown — not set up for the method |

Internal Product Mode is checked first. If your repo is transitioning from internal product to client delivery (common scenario: a successful internal product being commercialized to a first client), you might have both hypothesis.md and SOW.md. State-check will call it internal-product in that case. This is intentional — the transition process lives in Internal Product Mode's Stage 3, not in client delivery.

If you've finished commercialization and want state-check to treat the repo as client delivery, delete `docs/hypothesis.md` (or move it to `docs/hypothesis-archive.md`). The hypothesis document has served its purpose by that point.

### Active sprint detection

The active sprint is the highest-numbered `sprints/vN/` directory **without a `.lock` file**. If all sprints have lockfiles, the repo is in "between-sprints" state — a legitimate state, not a problem. It means the last sprint closed cleanly and the team hasn't started the next one yet.

If no sprint directories exist at all, you're pre-sprint (Phase 0 for client delivery, or pre-first-sprint for internal product).

### Task counting

Tasks are counted by status:

- `[ ]` → open
- `[x]` → complete
- `[DEFERRED]` → deferred

Tasks without the expected format (`- [status] TNNN: title`) are not counted. If your team uses a different convention, update the `TASK_HEADER_RE` regex in the CLI.

### Coverage flag logic

The P0 "task missing Satisfies: line" flag scans `TASKS.md` for any task entry where the task block doesn't contain a `Satisfies:` subline. This mirrors the `/reconcile` check that would fail in CI. Running state-check locally catches it before you push.

### Flag severity rationale

I chose the P0/P1/P2 severities based on what would actually block a team:

- **P0 → blocks the method from working.** If these aren't fixed, `/reconcile` fails, Claude Code lacks context, or sprint traceability breaks. Exit code 1 makes these loud.
- **P1 → allows the method to work but erodes quality.** Bloated CLAUDE.md still loads but LLMs skip parts of it. Missing SOW still allows client-delivery work but traceability to contract clauses is incomplete. Address before they compound.
- **P2 → schedule, don't rush.** A large failures log is technical debt in the memory layer; missing retro is a style issue if the sprint just ended. Quarterly cleanup is enough.

---

## Part 5: Recommended usage patterns

### Daily / per-session

Run state-check at the start of any session where you're unsure what to pick up. It's designed to be cheap; 30 seconds is the upper bound.

### Before commits

Consider a pre-commit hook that runs `state-check.py --json` and fails if P0 flags are present:

```bash
# .git/hooks/pre-commit
#!/usr/bin/env bash
python3 scripts/state-check.py > /dev/null 2>&1
if [ $? -eq 1 ]; then
    python3 scripts/state-check.py >&2
    echo "Commit blocked: P0 state-check flag(s) present. See above." >&2
    exit 1
fi
```

This is optional. Some teams prefer state-check as information-only; others want it as a blocking check. Depends on your team's appetite for tooling enforcement.

### In CI

The `/reconcile` CI check already covers the specific requirement-coverage case. State-check in CI would add broader flag detection. Worth it if your team has ignored P0 flags and shipped broken state to branches; skip it otherwise. Running two slightly-overlapping checks in CI risks noise.

### During retros

Running state-check during `/retro` surfaces any residual P1/P2 issues from the sprint that didn't get addressed. Good hygiene check before locking.

### When joining a new repo

First thing a new engineer on an existing engagement should do, ahead of reading CLAUDE.md. The state-check output plus CLAUDE.md gives them a 10-minute orientation.

---

## Part 6: Troubleshooting common situations

### "It says my repo is in Unknown mode"

The repo doesn't have the indicator files state-check looks for. Either:

- You haven't bootstrapped the method yet (normal for fresh repos) → follow the setup in `START-HERE.md`
- You have the method scaffolding but under different paths → either move your docs to match the method layout, or edit the detection functions in `state-check.py` to match your paths

### "It says mode is internal-product but I'm actually doing client work"

You probably have a stale `docs/hypothesis.md` from earlier internal exploration. Move or delete it; state-check will re-detect as client-delivery on the next run.

### "It's flagging tasks without Satisfies: lines but I'm sure they have them"

Check the format. State-check expects:

```
- [ ] T001: Task title
  - Satisfies: §X.Y, Dn
```

Not:

```
- [ ] T001: Task title
    Satisfies: §X.Y    ← wrong indentation, no list marker
```

Nor:

```
- [ ] T001: Task title (Satisfies: §X.Y)    ← inline, not a subline
```

Adjust your format to match, or update the `SATISFIES_RE` regex in the CLI.

### "The CLAUDE.md size flag is noisy — we need more than 500 lines"

Push detail into linked documents. If 500 lines still feels tight after pruning, you probably have multiple concerns crammed into one file. Split into:

- `CLAUDE.md` — index, critical conventions, never-do rules (≤300 lines)
- `docs/stack-conventions.md` — detailed stack info
- `docs/testing-patterns.md` — project-specific test patterns

Then CLAUDE.md just references the detailed docs. LLMs will read the index reliably and fetch the linked docs on demand.

If you've genuinely tried and still need more, increase the threshold in the CLI (look for the number `500` in `check_claude_md_size`). But try pruning first; most 600+ line CLAUDE.md files have accumulated content that should be elsewhere.

### "The tool is surfacing a judgment call but I don't want to decide right now"

That's fine. State-check never requires a decision. Close the report, come back to it when you're ready. The judgment call will still be there.

What's not fine is making a decision by default. If state-check prompts "has the kill signal fired?" and you don't answer, the next sprint will proceed as if the answer were "no." If you haven't actually measured, that's an implicit "no" that you didn't earn. Better to explicitly say "we haven't measured yet, so Sprint 4's hypothesis is: set up the measurement."

### "My team keeps ignoring state-check's recommendations"

Two possibilities:

1. **The recommendations are wrong.** The tool's heuristics don't match your actual priority. Investigate which recommendations get ignored and whether they were correct in retrospect.
2. **The tool is right but inconvenient.** This is the harder case. Either your team is systematically skipping steps the method cares about (the tool is catching this — good) or the method is miscalibrated for your context (which is a broader problem than state-check).

Log a few specific cases over a sprint and bring them to a retro. Don't tune the tool in isolation; tune it based on what actually happened.

---

## Part 7: Technical reference

### Architecture

The pair has two components that are designed to work together but function independently:

```
┌─────────────────────────┐      ┌──────────────────────────┐
│  state-check.py (CLI)   │◀─────│  state-check.md (Skill)  │
│                         │      │                          │
│  - Reads repo files     │      │  - Invoked as /state-    │
│  - Detects mode/state   │      │    check in Claude Code  │
│  - Emits JSON or text   │      │  - Calls CLI for data    │
│  - Exit code semantics  │      │  - Adds conversational   │
│                         │      │    layer                 │
└─────────────────────────┘      └──────────────────────────┘
        │                                    │
        │ reads                              │ consumes
        ▼                                    ▼
┌────────────────────────────────────────────────────────┐
│  Repo structure (CLAUDE.md, sprints/, docs/, etc.)      │
└────────────────────────────────────────────────────────┘
```

The CLI is the source of truth for state detection. The skill is a presentation layer. This separation matters: if you find a bug in state detection, fix it in the CLI; the skill will pick up the change automatically through the JSON output.

### Detection pipeline

The CLI runs these steps in order:

1. **`detect_mode(repo)`** — examines presence of key files to determine client-delivery vs. internal-product vs. unknown. For internal-product, also determines stage.
2. **`find_sprint_dirs(repo)`** — enumerates and sorts `sprints/vN/` directories.
3. **`find_active_sprint(sprint_dirs)`** — finds the highest-numbered directory without a `.lock` file.
4. **`count_tasks(tasks_file)`** — parses TASKS.md to count open / complete / deferred.
5. **`find_active_initiative(repo)`** — finds the most recently modified top-level `docs/*.md` file (excluding known subfolders and hypothesis.md) as a heuristic for active initiative.
6. **Flag checks** — runs each `check_*` function, appending any flags returned.
7. **`compose_recommendation()`** — produces a single "what to work on next" suggestion from the detected state.
8. **`compose_judgment_calls()`** — surfaces stage-appropriate questions for humans.

### Regex patterns (what to tune)

All patterns are near the top of `state-check.py`. Change them to match your team's conventions:

| Pattern name | What it matches | When to change |
|---|---|---|
| `REQ_ID_RE` (implicit in `SATISFIES_RE` handling) | `§X.Y`, `Dn`, `Qn`, `SOW-§X.Y`, `Hn` | If your IDs use different prefixes |
| `TASK_HEADER_RE` (in `count_tasks` and `check_sprint_state`) | `- [x] T001: title` / `- [ ] T001: title` / `- [DEFERRED] T001: title` | If your task format differs |
| `SATISFIES_RE` (in `check_sprint_state`) | `  - Satisfies: IDs` / `  Satisfies: IDs` | If your subline format differs |

When you change a pattern, run against a known-good sprint to confirm state-check still detects everything correctly.

### Adding a new check

Structure of a check function:

```python
def check_something(repo: Path) -> Optional[Flag]:
    # Examine repo state
    if condition_indicating_issue:
        return Flag(
            severity="P0" | "P1" | "P2",
            category="short-tag",
            message="What's wrong (human-readable)",
            suggested_action="What to do about it",
        )
    return None
```

Then register it in `run_state_check`:

```python
for check in (check_claude_md_size, check_failures_log_size, check_test_modifications, check_something):
    flag = check(repo)
    if flag:
        state.flags.append(flag)
```

Checks that need more than `repo: Path` (like sprint-specific checks) follow the same pattern with different signatures — see `check_sprint_state(sprint, mode)` for an example.

**When you add a check, also update the skill.** The skill's "Handling specific states" section should describe how to handle the new flag conversationally. Drift between CLI and skill is the main risk of having two components.

### Adding mode-specific behavior

`check_mode_specific(mode, stage, repo)` is where mode-specific or stage-specific checks live. Branch on `mode` and `stage` as needed. Keep general-purpose checks out of this function — they should be their own top-level checks.

### Output format

JSON mode produces a `ModeState` dataclass serialized to JSON. The structure is stable across versions (additions only, not removals). The skill relies on specific field names — if you rename or remove fields, update the skill.

Human-readable mode formats the same data for terminal display. The presentation is cosmetic; tweak freely.

### Exit codes

- `0` → no P0 flags
- `1` → at least one P0 flag
- `2` → usage error or repo not accessible

P1 and P2 flags do not affect the exit code. They're informational.

---

## Part 8: Integration with the rest of the method

State-check relates to other method artifacts as follows:

### vs. `/reconcile`

`/reconcile` is about one specific check: does every PRD requirement have a task satisfying it, with code present? It runs in CI and blocks merges.

State-check is broader. It includes a subset of `/reconcile`'s logic (the Satisfies: coverage check) plus many other state and flag checks. It's designed for interactive, pre-commit use, not CI enforcement.

**Relationship:** `/reconcile` is the CI-enforced gate. State-check is the heads-up display that lets you notice problems before `/reconcile` rejects your PR. Don't replace one with the other.

### vs. `/sprint-close`

`/sprint-close` is a structural gate that runs `/reconcile`, `/walkthrough`, `/retro`, and writes a lockfile. It happens once at the end of each sprint.

State-check runs anytime and doesn't modify the repo. It can tell you "the sprint looks done, consider running `/sprint-close`" but it doesn't run `/sprint-close` itself.

**Relationship:** State-check surfaces the decision; `/sprint-close` is the decision.

### vs. `/gap`

`/gap` is an initiative-boundary audit that diffs requirement IDs in `docs/<INITIATIVE>.md` against the union of `Satisfies:` citations across every sprint and emits `docs/<INITIATIVE>_GAP_ANALYSIS.md`.

State-check is not `/gap`. It doesn't audit against the design doc; it checks whether state artifacts are present and consistent. But state-check **does** track the gap analysis as an artifact: the `gap_analysis_staleness` P1 flag fires when `docs/<INITIATIVE>_GAP_ANALYSIS.md` is missing or older than the newest sprint `.lock`. That's how state-check surfaces "the analysis exists but no longer reflects the current sprint state" without re-running `/gap` itself.

**Relationship:** They're complementary. State-check observes that the gap analysis is fresh; `/gap` is the skill that produces and refreshes it. `/sprint-close` reads the analysis to refuse the lock when orphaned requirements remain.

### vs. CLAUDE.md and the failures log

CLAUDE.md and the failures log are the memory layer. They're consulted at the start of each `/dev-test` session (and inherited into `/dev-impl` via the committed tests) and during ambiguity passes.

State-check reads both but doesn't update them. It flags if CLAUDE.md is bloated or the failures log is unpruned, but it doesn't rewrite either.

**Relationship:** State-check observes the memory layer's health. The Developer Handbook describes how to maintain it.

### vs. the Developer Handbook

The handbook describes daily practices in general. State-check tells you which practice applies right now.

**Relationship:** If an engineer asks "how do I write a good Satisfies: line?" — that's handbook territory. If an engineer asks "which task needs a Satisfies: line right now?" — that's state-check territory.

### Integration diagram

```
Engineer sits down to work
         │
         ▼
┌──────────────────────────┐
│  /state-check or         │  ← "What's going on?"
│  state-check.py          │
└──────────────────────────┘
         │
         ├── Flags? ──────▶  Fix the P0 first
         │
         ├── Judgment call? ▶  Answer it (may involve data outside the repo)
         │
         └── Recommendation ▶  Execute it
                   │
                   ├── /dev task kickoff ────▶  See Handbook Part 2.1
                   ├── /prd                  ────▶  See Method document
                   ├── /sprint-close         ────▶  See Method document
                   └── Gate decision ceremony ▶  See Internal Product Mode
```

---

## Part 9: Maintenance and calibration

### When to update the pair

State-check is a living pair, not a fixed artifact. Update it when:

- **The method itself changes.** New phase, new rule, new artifact — state-check should know about it.
- **A failures-log entry reveals a pattern the tool should flag.** If three engineers miss the same thing and it made it through, consider adding a state-check for it.
- **Your team changes conventions.** Different ID format, different sprint structure, different commit patterns.
- **The skill and CLI drift.** If what the skill says and what the CLI detects diverge, one or both are stale.

### How to update without breaking things

1. Update the CLI first. Add the check, verify with a test case.
2. Update the skill to explain how to handle the new flag conversationally.
3. Update this documentation if the change affects user-visible behavior.
4. Commit all three in the same PR.

Resist the temptation to update one at a time. The pair is a pair; asymmetric updates produce subtle bugs.

### Calibration signals (what to watch)

After one month of use:

- **Are engineers running it?** If yes, it's useful. If no, either the value isn't clear or the setup friction is too high.
- **Do flags produce action?** If flags appear and get ignored, either the flags are wrong or the method is being systematically bypassed. Both deserve investigation.
- **Is the skill overstepping?** If the conversational layer starts making judgment calls ("you should graduate to Stage 2"), tighten the prompts in the skill file. It should ask questions, not answer them.
- **Is the CLI missing something?** If engineers keep running into problems that state-check should have caught, add a check.

### Retiring a check

Sometimes a check that made sense initially becomes noise. Retire it deliberately:

1. Comment out the check first; don't delete it.
2. Run for a sprint without it.
3. If nothing bad happens, delete the commented code.
4. Add an entry to the project's `docs/decisions/` explaining what was removed and why.

Retired checks often return in a different form. Keep the reasoning documented.

---

## Part 10: Honest caveats

Like Internal Product Mode, state-check v1 is based on reasoning about what should be useful, not on empirical data from your team using it. Expect the first month of use to reveal:

- **Checks that are noisy** and need tuning down to P2 or retiring
- **Checks that are missing** — things that matter but aren't detected
- **Judgment-call prompts that are unclear** — rephrase based on how engineers actually respond
- **Recommendation logic that's wrong** in specific cases

None of these are bugs; they're the normal calibration that happens when a tool meets a real team. Budget time for it explicitly in the first few retros.

The version is 1.0 intentionally. Expect 2.0 after real use.

---

## Appendix: Quick reference

### Commands

```bash
# Standard invocation
python3 scripts/state-check.py

# JSON output (for scripting)
python3 scripts/state-check.py --json

# Different repo
python3 scripts/state-check.py --repo-root /path/to/repo

# In Claude Code
/state-check
```

### Flag severity

| Severity | Meaning | Exit code impact | When to act |
|---|---|---|---|
| P0 | Blocking — method can't function correctly | 1 | Before doing anything else |
| P1 | Anti-pattern or calibration issue | 0 | Within the current sprint |
| P2 | Informational | 0 | Schedule for when there's bandwidth |

### Common flags and what they mean

| Flag | Severity | What to do |
|---|---|---|
| CLAUDE.md missing | P0 | Copy template, fill in bracketed placeholders |
| Task missing Satisfies: | P0 | Add `Satisfies:` line, or defer the task |
| CLAUDE.md > 500 lines | P1 | Prune; push detail into linked docs |
| Tests modified recently | P1 | Verify not modified-to-match-code anti-pattern |
| No SOW (client mode) | P1 | Place SOW at `docs/contract/SOW.md`, assign IDs |
| Failures log > 100 entries | P2 | Schedule consolidation pass |
| No RETRO.md for active sprint | P2 | Run `/retro` before `/sprint-close` |

### When to run

| Situation | Run state-check? |
|---|---|
| Starting a session | Yes |
| Just finished a task | Yes |
| Before committing | Optional (as pre-commit hook) |
| Before pushing to remote | Yes — catches what CI would reject |
| Joining a new repo | Yes — first orientation step |
| During a retro | Yes — check for unaddressed flags |
| During `/sprint-close` preparation | Yes — ensures sprint can close cleanly |
| When "something feels off" | Yes — it's cheap |
| Every single commit automatically | No — creates noise fatigue |

### When NOT to run

State-check is always safe to run, but there are times when running it adds nothing:

- Immediately after already running it (nothing's changed)
- In the middle of writing code (break your flow for no benefit)
- When you already know exactly what to do next and are doing it

---

## Appendix: File locations

```
state-check/
├── README.md                              # Brief overview + setup
├── scripts/
│   └── state-check.py                     # The CLI
├── .claude/skills/
│   └── state-check.md                     # The Claude Code skill
└── (this documentation)                   # When distributed separately
```

In the main method bundle, this documentation lives at `state-check/DOCUMENTATION.md` and the README becomes a pointer to it.
