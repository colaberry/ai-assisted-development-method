# State Check — CLI + Claude Code Skill

A paired tool for detecting what state your repo is in and what to work on next, within the AI-Assisted Development Method (AADM).

## What's here

```
scripts/
└── state-check.py              # Python CLI (stdlib only)
.claude/skills/
└── state-check.md              # Claude Code skill (conversational layer)
```

These are a **pair**. The CLI does mechanical state detection; the skill wraps it with human dialogue. Keep them in sync when you modify either one.

## What the pair does

- Detects which mode the repo is in (client delivery or internal product)
- For internal product, detects the stage (exploration / validation / commercialization)
- Finds the active sprint and its state (tasks, completeness, lockfile)
- Flags issues that need attention (missing Satisfies: lines, bloated CLAUDE.md, stale retros, test modifications)
- Recommends a next action grounded in the method
- Surfaces judgment calls for humans to resolve (graduation gates, kill signals)

## What the pair does NOT do

- Does not make judgment calls. "Are we ready to graduate to Stage 2?" is a human decision; the tool surfaces the question, never answers it.
- Does not replace `/dev`, `/prd`, `/sprint-close`, or other method commands. It tells you which one to run.
- Does not modify the repo. Safe to run anytime.

## Installing

### CLI only

```bash
cp scripts/state-check.py <your-repo>/scripts/state-check.py
chmod +x <your-repo>/scripts/state-check.py
```

Run with: `python3 scripts/state-check.py`

### CLI + skill

```bash
cp scripts/state-check.py <your-repo>/scripts/state-check.py
chmod +x <your-repo>/scripts/state-check.py
mkdir -p <your-repo>/.claude/skills
cp .claude/skills/state-check.md <your-repo>/.claude/skills/state-check.md
```

In Claude Code, invoke as `/state-check`.

## CLI reference

```bash
# Human-readable report
python3 scripts/state-check.py

# JSON for scripting (or for the skill to consume)
python3 scripts/state-check.py --json

# Inspect a different repo
python3 scripts/state-check.py --repo-root /path/to/other/repo
```

Exit codes:
- `0` — state detected, no P0 flags
- `1` — P0 flags present (e.g., task missing a Satisfies: line, CLAUDE.md missing)
- `2` — usage error or repo not accessible

## Flag severity

- **P0** — blocks correct operation of the method (coverage gaps, missing prerequisites). Exit code 1.
- **P1** — anti-pattern indicator or calibration issue (bloated CLAUDE.md, tests recently modified). Doesn't exit nonzero but worth addressing soon.
- **P2** — informational (failures log could be pruned, retro not yet written for current sprint). Schedule, don't rush.

## What the CLI checks

| Check | Severity | Rationale |
|---|---|---|
| CLAUDE.md present at repo root | P0 | Required for Claude Code sessions |
| CLAUDE.md under 500 lines | P1 | LLMs skip content in longer files |
| SOW exists (client mode) | P1 | Contract traceability depends on it |
| hypothesis.md exists (internal Stage 1) | P0 | Stage 1 requires explicit hypothesis |
| Every task in active sprint has a `Satisfies:` line | P0 | `/reconcile` will fail without it |
| Active sprint has PRD.md and TASKS.md | P0 | Sprint infrastructure required |
| Retro written for active sprint (non-first) | P2 | Per-sprint retro expected |
| Tests modified in recent commits | P1 | Possible "tests modified to match code" anti-pattern |
| Failures log under ~100 entries | P2 | Memory pruning discipline |

## How the skill uses the CLI

The skill is a markdown file Claude Code loads when the engineer invokes `/state-check`. It:

1. Runs the CLI with `--json` flag
2. Parses the output
3. Presents findings in natural prose (not as a bulleted data dump)
4. Surfaces judgment-call questions for the engineer
5. Recommends a next action
6. Offers to help with that action (but only after explicit confirmation)

## Tuning for your team

The CLI assumes certain conventions from the method:

- Requirement IDs look like `§X.Y`, `SOW-§X.Y`, `Dn`, `Qn`, `Hn`, `Tn` — adjust the regex patterns if your team uses different conventions
- Sprint directories are `sprints/vN/` — adjust the sprint_dirs finder if you use a different structure
- Lockfiles are `.lock` files — change if your closure mechanism differs

Search the script for `re.compile` to find the patterns. Each has a comment explaining what it matches.

## Expected calibration after first month of use

- **If engineers ignore the CLI output**: the recommendations aren't matching what they actually need to know. Check which flags they're dismissing and consider whether they're real issues or noise.
- **If engineers bypass flagged issues**: that's sometimes the method working (the flag is inconvenient but correct) and sometimes a sign the flag is too aggressive. Look at what was bypassed and whether a problem resulted later.
- **If the skill starts making judgment calls**: that's the skill overstepping its scope. Tighten the prompts in `.claude/skills/state-check.md`.
- **If the CLI and skill disagree**: one of them has drifted. Rebuild the pair together.

## When to rebuild the pair

- After the method itself changes (new phase, new rule)
- After a failures-log entry reveals a new pattern the tool should flag
- After your team changes conventions (ID format, sprint structure)

Do not rebuild incrementally. The CLI and skill are a pair; updating one without the other creates drift. When you update, check both.
