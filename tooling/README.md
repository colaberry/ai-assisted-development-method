# Day-One Tooling for the AI-Assisted Development Method (AADM)

This bundle contains the minimum tooling to start using the method on a new client repo:

- A working `/reconcile` script (Python, stdlib only)
- A GitHub Actions workflow that runs `/reconcile` as a CI merge gate
- Templates for CLAUDE.md, the failures log, retrospectives, and sprint artifacts

## Contents

```
scripts/
└── reconcile.py                    # Sprint coverage check
.github/workflows/
└── reconcile.yml                   # CI integration
templates/
├── CLAUDE.md                       # Per-client persistent context
├── failures-log-README.md          # Folder-level README for docs/failures/
├── failures-log-TEMPLATE.md        # Single entry template
├── retro-TEMPLATE.md               # Per-sprint retrospective
├── sprint-PRD-TEMPLATE.md          # Sprint planning document
└── sprint-TASKS-TEMPLATE.md        # Task list in the format /reconcile parses
```

## Getting started on a new client repo

From the root of a fresh client repo:

```bash
# 1. Copy the reconcile script
mkdir -p scripts
cp /path/to/tooling/scripts/reconcile.py scripts/
chmod +x scripts/reconcile.py

# 2. Wire the CI check
mkdir -p .github/workflows
cp /path/to/tooling/.github/workflows/reconcile.yml .github/workflows/

# 3. Set up the docs structure
mkdir -p docs/contract docs/decisions docs/failures docs/client-facing
cp /path/to/tooling/templates/failures-log-README.md docs/failures/README.md
cp /path/to/tooling/templates/failures-log-TEMPLATE.md docs/failures/TEMPLATE.md

# 4. Create CLAUDE.md — customize for this client
cp /path/to/tooling/templates/CLAUDE.md ./CLAUDE.md
# Now open CLAUDE.md and fill in the <BRACKETED> placeholders:
#   client name, stack, deploy target, code organization, commands,
#   client-specific context, never-do rules.

# 5. Drop in the SOW with stable IDs
# Place the client's signed SOW at docs/contract/SOW.md and assign
# stable IDs (SOW-§X.Y) to each acceptance criterion. These become
# the root of the Satisfies: traceability chain.

# 6. Set up the first sprint directory
mkdir -p sprints/v1
cp /path/to/tooling/templates/sprint-PRD-TEMPLATE.md sprints/v1/PRD.md
cp /path/to/tooling/templates/sprint-TASKS-TEMPLATE.md sprints/v1/TASKS.md
cp /path/to/tooling/templates/retro-TEMPLATE.md sprints/v1/RETRO.md
# (WALKTHROUGH.md and .lock are produced by /sprint-close; no template needed.)

# 7. First commit
git add .
git commit -m "bootstrap: AI-assisted development method scaffolding"

# 8. Test the reconcile script locally before pushing
python3 scripts/reconcile.py sprints/v1
# It will probably show missing requirements — that is correct at this
# stage, since you haven't filled in real requirements or tasks yet.
```

## How `/reconcile` works

- **Input:** a sprint directory (`sprints/vN/`) containing `PRD.md` and `TASKS.md`.
- **What it does:** extracts requirement IDs from the PRD, extracts `Satisfies:` citations from TASKS, and for each requirement determines whether a completed task satisfies it, the claimed files exist in the repo, AND symbols extracted from the task's title and `Acceptance:` line actually appear in those files. Deferred requirements must have a `[DEFERRED]` entry with `Target:` and `Reason:`.
- **Output:** a human-readable coverage table (default) or JSON (`--json`).
- **Exit code:** 0 if all requirements are covered or explicitly deferred; 1 if any are missing.
- **CI mode:** `--ci` suppresses the verbose table and emits a clear FAIL message on gaps.

### Assumptions the script makes

Most are tunable by editing the regex patterns near the top of `reconcile.py`.

- **Requirement IDs match:** `§X.Y`, `§X.Y.Z`, `Dn`, `Qn`, `SOW-§X.Y`. Add patterns if your team uses different conventions.
- **Task format:** markdown list items in the shape `- [x] T001: title` with two-space-indented sublines like `  - Satisfies: §4.2, D5`. Both `- ` prefixes and plain indented sublines are accepted.
- **File presence means existence**, not correctness. `/reconcile` answers "did we build it?" Tests in CI answer "does it work?" This separation is deliberate.
- **Symbol presence is a heuristic.** Backticked tokens in the task title and `Acceptance:` are the strongest signal; bare `snake_case`/`camelCase`/`ALL_CAPS` identifiers are also picked up. Plain English words are filtered out. A "covered" task whose listed files exist but contain none of the extracted symbols gets a `STUB-WARNING:` and is demoted to MEDIUM confidence. Pass `--strict-symbols` to upgrade that pattern to a hard failure.
- **Active sprint detection (CI):** the highest-numbered `sprints/vN/` directory without a `.lock` file is considered active.

### Running it

```bash
# Human-readable table, any sprint
python3 scripts/reconcile.py sprints/v1

# JSON output for tooling integration
python3 scripts/reconcile.py sprints/v1 --json

# CI mode (terse, non-zero exit on gaps)
python3 scripts/reconcile.py sprints/v1 --ci

# CI mode with the strict symbol-presence check (fails on empty stubs)
python3 scripts/reconcile.py sprints/v1 --ci --strict-symbols

# Custom repo root (default: cwd)
python3 scripts/reconcile.py sprints/v1 --repo-root /path/to/repo
```

## What this bundle does NOT include

Intentionally out of scope for day-one tooling:

- **`/sprint-close`, `/walkthrough`, `/gap`, `/security-review`, `/ui-qa` automation.** These are higher-leverage to build later once the team has used the basic pieces and knows what shape each one needs. Start with manual checklists invoked as Claude Code slash commands; promote to scripts when the manual process stabilizes.
- **Mutation testing setup.** Language-specific; set up with Stryker / mutmut / PIT when you pick the critical modules.
- **`docs/patterns/` folder for positives.** Per v3.2 guidance, do not pre-emptively add this until you have a clear signal the team needs it.

## Calibration notes

- **CLAUDE.md stays under ~500 lines.** The template is a starting point; as you add project-specific rules, push detail into linked docs so CLAUDE.md remains the index.
- **Failures log active rules: 20–50** for a mature codebase. Prune quarterly.
- **Mutation testing: monthly, critical modules only** for a small team. Not weekly across the codebase.
- **`/gap`: per initiative and quarterly**, not monthly.

## Questions the tooling does not answer

These are genuine gaps to watch for when you start using this:

- **"What happens if a requirement applies across two sprints?"** Currently, it is covered in one sprint and absent from the other. If your team needs cross-sprint requirement tracking, extend the script to look across sprints — but be cautious; simpler is better here.
- **"How does this interact with branch-based workflows?"** The CI workflow assumes PRs target main and that sprint state is tracked on main. If your team uses long-lived feature branches per sprint, the active-sprint detection needs adjustment.

## Feedback

These templates and scripts are starting points. Expect to modify them within the first month of real use. The point is to get the structure in place, not to have everything perfect on day one.
