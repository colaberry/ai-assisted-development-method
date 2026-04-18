# CLAUDE.md

This file is persistent context loaded by Claude Code at the start of every session.
It describes the system, its conventions, and the rules Claude Code must follow.

> **Keep this file under 500 lines.** Below that, Claude Code reads it reliably.
> Above it, content in the middle gets skipped. Detail goes in linked documents.

---

## This repository

**Client:** <CLIENT NAME>
**Project:** <PROJECT NAME>
**Stack:** <e.g., Python 3.11 + FastAPI + PostgreSQL + React/TypeScript>
**Deployment target:** <e.g., AWS ECS, client's on-premises Kubernetes, ...>

<One paragraph describing what the system does, who uses it, and what makes
this client engagement specific. Avoid marketing; describe the actual system.>

---

## Key references

Always consult these before answering a non-trivial question:

- **Contract / SOW:** `docs/contract/SOW.md` — authoritative acceptance criteria with stable IDs (SOW-§X.Y)
- **Design documents:** `docs/*.md` — initiative-level specs. Each requirement has a stable ID (§X.Y, Dn, Qn)
- **Failures log:** `docs/failures/` — past mistakes and their prevention rules. Check this during every ambiguity pass and at the start of any task touching a previously-failed domain.
- **Decisions:** `docs/decisions/` — ADRs. Explain what was decided and why. Superseded ADRs are explicitly marked.
- **Current sprint:** `sprints/vN/` where N is the highest-numbered sprint without a `.lock` file. Look at `PRD.md` and `TASKS.md`.

---

## Directory layout

```
<repo root>/
├── CLAUDE.md                          # This file
├── docs/
│   ├── contract/SOW.md                # Client SOW with stable IDs
│   ├── <INITIATIVE>.md                # Design docs
│   ├── <INITIATIVE>_GAP_ANALYSIS.md   # Produced by /gap
│   ├── client-facing/                 # Client-facing delivery docs
│   ├── decisions/                     # ADRs (YYYY-MM-DD-slug.md)
│   └── failures/                      # Failures log (YYYY-MM-DD-slug.md)
├── sprints/
│   └── vN/
│       ├── PRD.md
│       ├── TASKS.md
│       ├── WALKTHROUGH.md
│       ├── RETRO.md
│       └── .lock (when closed)
├── scripts/reconcile.py               # CI coverage check
└── <application code>                 # see "Code organization" below
```

---

## Code organization

<Describe your repo's actual code layout. Examples:>

- `src/auth/` — authentication and session management. Touches `docs/failures/*-auth-*.md`.
- `src/api/` — HTTP layer. All endpoints declared in `openapi.yaml` — source of truth for request/response shapes.
- `src/domain/` — business logic. Free of framework dependencies; pure functions where possible.
- `src/integrations/` — external-system clients. One module per external dependency.
- `tests/unit/` — fast, pure tests. Run on every save.
- `tests/integration/` — cross-module; hit real DB (test container). Run on PR.
- `tests/e2e/` — browser-driven against deployed staging. Run pre-merge and nightly.

---

## How to run things

```bash
# Install dependencies
<your install command>

# Run tests
<unit test command>             # fast; run on save
<integration test command>      # slower; run before committing
<e2e test command>              # slowest; run before merging

# Run the linter and type checker
<lint command>
<typecheck command>

# Run the security scan
<security scan command>

# Start the dev environment
<dev env command>

# Run the /reconcile coverage check interactively
python3 scripts/reconcile.py sprints/vN

# Run /reconcile in CI mode (exit non-zero on gaps)
python3 scripts/reconcile.py sprints/vN --ci
```

---

## Coding conventions

<Opinionated list. Keep to the things Claude Code needs to know that aren't
obvious from looking at existing code.>

- <Language-specific style — "no single-letter variable names", "prefer composition over inheritance", etc.>
- <Error-handling pattern — "all external calls wrapped in Result[T, E]", "exceptions only for programmer errors">
- <Naming pattern — "domain objects in PascalCase, database columns in snake_case, API fields in camelCase">
- <Test pattern — "AAA (Arrange-Act-Assert) layout; one behavior per test; test names describe behavior not implementation">
- <Commit pattern — "conventional commits: feat(scope): summary">

---

## Never-do rules (project-specific)

These are rules specific to this client/project. Add entries here when a mistake almost shipped or actually shipped. Keep to 10–20 rules; consolidate when entries overlap.

- **Never <the thing>.** <One-line rationale linking to the failures-log entry that motivated this rule.> See `docs/failures/YYYY-MM-DD-slug.md`.
- **Never <the thing>.** <Rationale.>

<Examples to populate from your own failures log as you go. Delete these stubs
when you have real entries.>

---

## Testing discipline

- **Test writing and implementation must be in separate Claude Code sessions.** Single-context TDD degrades into test-after.
- **Every new task requires a test matrix.** Categories: A (happy path) ≥ 1, B (edge) ≥ 2, C (error) ≥ 1, D (fallthrough) ≥ 1 per code path, E (architecture guards) ≥ 1 per structural change.
- **Tests are committed failing before implementation begins.**
- **Do not modify a test to make it pass.** If a test appears wrong, stop and flag it to a human reviewer.
- **Architecture guards (Category E) use `inspect.getsource()` or equivalent** to assert that deleted symbols stay deleted and required call patterns exist.

---

## Security considerations

<Client-specific. Examples:>

- <PII handling — "All user email addresses must be pseudonymized in logs; see docs/failures/2026-02-01-pii-in-logs.md">
- <Auth pattern — "All API endpoints require X-Auth-Token validated against table `auth.sessions`; no endpoint runs before `validate_session()` middleware">
- <Data residency — "Client requires data stored in EU region only; see docs/decisions/2026-01-15-eu-data-residency.md">
- <Compliance scope — "This project is in scope for <SOC 2 / HIPAA / etc.> — security-review is mandatory for every sprint">

---

## Client-specific context

<Things only this client does that affect code. Examples:>

- **SSO:** Client uses Okta as IdP. SAML metadata is in `config/idp-metadata.xml`. Do not assume generic SAML; Okta has specific attribute naming.
- **API conventions:** Client's existing APIs use snake_case field names. Match that; do not introduce camelCase in client-facing responses.
- **Deployment windows:** Production deploys only on Tuesday and Thursday mornings; no Friday deploys.
- **Client-specific rate limits:** Their upstream systems have a 30 req/s cap; our code must not exceed.

---

## Method rules (non-negotiable)

These come from the AI-Assisted Development Method (AADM) and apply to every session:

1. **Never start work on sprint vN+1 until sprint vN has been locked via `/sprint-close`.**
2. **Every task has a `Satisfies:` line citing the design-doc requirement IDs it closes.**
3. **Silent descoping is an anti-pattern.** Dropping a requirement requires an explicit `[DEFERRED]` entry naming the target sprint.
4. **Test writing and implementation are in separate sessions.**
5. **One task at a time per `/dev` session.**
6. **`/sprint-close` runs `/reconcile`, `/security-review` (if in scope), `/ui-qa` (if in scope), `/walkthrough`, and `/retro` before locking.**
7. **Client-facing artifacts are projections of internal artifacts. They never contradict `/reconcile` or `/gap` output.**
8. **Requirement IDs are stable. Never renamed or renumbered.**

---

## When Claude Code gets stuck

If you are on the third round of "fix this, still broken," **stop.** The problem is almost always underspecification, not a missing code tweak. Go back to `sprints/vN/PRD.md` or `docs/<INITIATIVE>.md` and re-read the relevant section. If the spec is genuinely ambiguous, run an ambiguity pass and produce questions for a human — do not invent answers.

---

## Memory pruning

This file is living context, not a journal. Quarterly, review and:

- Remove rules tied to modules or vendors that no longer exist
- Consolidate rules that overlap
- Move detail into linked documents when this file is approaching 500 lines
- Update stack, commands, and conventions to match current reality

Stale context is worse than no context.
