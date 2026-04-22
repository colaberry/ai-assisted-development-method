# Day-One Tooling for the AI-Assisted Development Method (AADM)

This bundle contains the minimum tooling to start using the method on a new client repo:

- A working `/reconcile` script (Python, stdlib only)
- A `sprint_close.py` script that atomically closes a sprint after running `/reconcile`, verifying RETRO + sign-off, checking the security/UI-QA artifacts, and confirming session events were logged
- A `gap.py` script that diffs design-doc requirement IDs against sprint `Satisfies:` citations and writes `docs/<INITIATIVE>_GAP_ANALYSIS.md`
- A `dev_session.py` script that records `/dev-test`/`/dev-impl` markers so the test-writer and implementation author cannot share a Claude Code session
- A `sprint_gate.py` PreToolUse hook that blocks writes outside the active sprint and outside the active task's `Files:` allowlist
- GitHub Actions workflows for `/reconcile` and `/security` as CI merge gates
- Templates for CLAUDE.md, the failures log, retrospectives, sprint artifacts, the client intake (with the §7.5 elicitation completeness pass), security/UI-QA reviews, and incident post-mortems

## Contents

```
scripts/
├── reconcile.py                    # Sprint coverage check
├── sprint_close.py                 # Atomic sprint closure (writes .lock)
├── gap.py                          # Initiative-boundary orphan/conflict detection
└── dev_session.py                  # /dev-test → /dev-impl marker verification
hooks/
└── sprint_gate.py                  # PreToolUse hook: sprint-lock + Files: allowlist
.github/workflows/
├── reconcile.yml                   # CI integration for /reconcile
└── security.yml                    # CI integration for Semgrep
templates/
├── CLAUDE.md                       # Per-client persistent context
├── client-intake-TEMPLATE.md       # Phase 0 intake (incl. §7.5 completeness pass)
├── claude-settings-hooks-TEMPLATE.json  # Hooks block to merge into .claude/settings.json
├── failures-log-README.md          # Folder-level README for docs/failures/
├── failures-log-TEMPLATE.md        # Single entry template
├── incident-TEMPLATE.md            # Post-mortem template
├── retro-TEMPLATE.md               # Per-sprint retrospective
├── security-review-TEMPLATE.md     # Manual security review artifact
├── security-suppressions-TEMPLATE.md
├── ui-qa-TEMPLATE.md               # UI quality artifact
├── code-review-AI-CHECKLIST.md     # AI-assisted PR review checklist
├── sprint-PRD-TEMPLATE.md          # Sprint planning document
└── sprint-TASKS-TEMPLATE.md        # Task list in the format /reconcile parses
```

## Getting started on a new client repo

From the root of a fresh client repo:

```bash
# 1. Copy the scripts
mkdir -p scripts
cp /path/to/tooling/scripts/reconcile.py scripts/
cp /path/to/tooling/scripts/sprint_close.py scripts/
chmod +x scripts/reconcile.py scripts/sprint_close.py

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

## How `sprint_close.py` works

When you're ready to close a sprint, this is the one entry point. It:

1. Confirms the sprint has `PRD.md` and `TASKS.md` and isn't already locked.
2. Runs `reconcile.py --ci` against the sprint. Pass `--strict-symbols` to also fail on empty stubs.
3. Verifies `RETRO.md` is no longer the template (no `<placeholder>`, no literal `vN`, no literal `YYYY-MM-DD`, and the "What went well" / "What went poorly" sections contain real content).
4. Verifies sign-off — either an existing `SIGNOFF.md` containing `Reviewer: <name>` and `Date: YYYY-MM-DD`, or `--reviewer NAME` to create one.
5. **Verifies the security and UI-QA artifacts** named by the PRD's scope flags. If `/security-review required: Yes`, `sprints/vN/SECURITY-REVIEW.md` must exist with a non-blocked `Decision:` line; same for `/ui-qa required: Yes` and `UI-QA.md`. Either missing or `Decision: blocked` refuses the lock.
6. **Verifies session events were logged** for the sprint when the `metrics/` module is installed. `sprint_close.py` reads `metrics/events.jsonl` and refuses to lock with "no session events logged for vN" if no `session` events name the active sprint. Repos on the minimum-viable adoption path (no `metrics/` module) get a "not installed" pass on this check — the refusal only fires for teams that opted into metrics.
7. **Verifies the initiative-level gap analysis is current** when `docs/<INITIATIVE>_GAP_ANALYSIS.md` is present. Orphaned requirements in the analysis refuse the lock; run `/gap` to clear them or document the resolution before retrying.
8. Writes `sprints/vN/.lock` only if every check above passed. The `.lock` file records `locked_at`, `reviewer`, and `reconcile_status` — `sprint_gate.py` reads this on every PreToolUse to decide whether writes into vN+1 are allowed.

```bash
# Close v3 with the reviewer recorded inline
python3 scripts/sprint_close.py sprints/v3 --reviewer "Jane Doe"

# Use a pre-existing SIGNOFF.md
python3 scripts/sprint_close.py sprints/v3

# Run all checks but never write .lock — useful for CI smoke tests
python3 scripts/sprint_close.py sprints/v3 --dry-run

# Strict mode: also fail on tasks whose files exist but contain no symbol
python3 scripts/sprint_close.py sprints/v3 --strict-symbols --reviewer "Alex"

# JSON output for tooling integration
python3 scripts/sprint_close.py sprints/v3 --json
```

Exit code `0` means locked (or, with `--dry-run`, would have locked). Exit code `1` means at least one check failed and `.lock` was not written. There is no partial-close path.

## How the sprint-gate PreToolUse hook works

[`sprint_gate.py`](hooks/sprint_gate.py) is the structural complement to `sprint_close.py`. Where `sprint_close.py` decides *when* to write `.lock`, the hook decides *what the agent is allowed to touch* based on whose `.lock` files exist.

On every `Write`, `Edit`, `MultiEdit`, or `NotebookEdit` the hook:

1. Extracts the target `file_path` from the tool input.
2. If it's under `sprints/vK/...`, lists every `sprints/vJ/` dir in the repo.
3. If any `J < K` is missing a `.lock`, blocks the write with exit code 2 and a stderr message naming the unlocked sprints.

This turns the anti-skip rule from cultural ("please don't start v2 before v1 is closed") into structural (you literally cannot). The hook is permissive by design: if it can't parse its input, doesn't recognize the tool, or can't find the repo root, it exits 0 and allows the operation. It's a reminder, not a security boundary.

**Install in a client repo:**

```bash
mkdir -p .claude/hooks
cp /path/to/tooling/hooks/sprint_gate.py .claude/hooks/
chmod +x .claude/hooks/sprint_gate.py
# Then merge the hooks: block from templates/claude-settings-hooks-TEMPLATE.json
# into .claude/settings.json.
```

**What it does NOT do:** it doesn't block writes to already-locked sprints (retroactive edits to a closed retro are still allowed — people do fix typos), and it doesn't care about Read/Bash. Tighten if your team needs it; keep `evaluate()` in the hook as the single decision point.

## What this bundle does NOT include

Intentionally out of scope for day-one tooling:

- **`/walkthrough` automation.** Still a manual checklist invoked as a Claude Code slash command; promote to a script when the manual process stabilizes. (`/gap` is scripted via `gap.py`; `/sprint-close` via `sprint_close.py`; `/security-review` and `/ui-qa` ship as templates with `sprint_close.py` enforcement on the artifacts.)
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
