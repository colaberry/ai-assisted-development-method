# AI-Assisted Development Method

**Version 3.2.1**

*A process for developing reliable enterprise-grade products with Claude Code, for small teams building for external clients*

This document defines how our team uses Claude Code to build software for external clients. It exists because unstructured AI-assisted development produces an endless cycle of PRDs, gap analyses, and regressions — and because even structured single-feature workflows fail to prevent sprint-skipping across multi-sprint initiatives. The method is designed for the specific context of **small teams shipping enterprise-grade software to paying clients** — where a missed requirement is not "we'll grab it next sprint" but "the client paid for §7.3 and didn't get it."

It is opinionated. Half-measures do not work. If parts of this process feel slower at first, that is expected — the cost is being paid upfront instead of later in rework or client escalation.

## What's New

### v3.2.1 (this version)

Adds **Phase 0 (Client Intake and Design Authoring)** to the Initiative Level, and introduces the **client intake template** as a structured artifact for capturing requirements during discovery. The template lives in the method bundle at `templates/client-intake-TEMPLATE.md` and is designed to be both human-fillable during discovery interviews and structured enough to hand to Claude Code as input for generating the initial design document.

No other changes from v3.2. If you have already adopted v3.2, the migration is: start using the intake template on every new client engagement and acknowledge Phase 0 as an explicit phase before `/prd` for sprint v1 can run.

### v3.2 (prior)

Version 3.2 calibrates the method for **small teams (typically 3–10 engineers) building enterprise-grade products for external clients**. The core pipeline is unchanged; this version adds enterprise-specific mechanisms and calibrates the cadence of periodic checks so overhead matches team size. Specifically:

- **Contract-to-requirement mapping.** Enterprise contracts have acceptance criteria (SOW §4.2, etc.). Those become the initial set of stable requirement IDs in the design doc. The `Satisfies:` chain now reaches all the way from contract clause → design doc → task → code.
- **Per-client repo isolation.** Each client engagement gets its own repo with its own CLAUDE.md, failures log, and decision records. This prevents confidentiality leaks and context confusion when working across multiple client engagements simultaneously.
- **Security review as a mandatory phase, not a CI prerequisite alone.** Any sprint touching auth, data handling, PII, or external integrations runs a `/security-review` step (OWASP Top 10 + STRIDE lens) before `/sprint-close`. Static scanning in CI is necessary but not sufficient for enterprise client acceptance.
- **Browser-automation QA for user-facing features.** For any sprint shipping UI, `/ui-qa` drives an actual browser through acceptance flows and generates regression tests for every bug found. Test-matrix category A (happy path) for UI work becomes mechanical, not aspirational.
- **Client-facing artifact variants.** `/gap` reports, sprint walkthroughs, and requirement coverage tables get a client-facing variant — same data, no internal jargon — for delivery milestones and trust-building.
- **Per-sprint retrospective.** A short, structured retro after `/sprint-close` that feeds the failures log. High-value on small teams where lessons compound.
- **Calibrated cadence for periodic checks.** `/gap` per initiative and quarterly; mutation testing monthly on critical modules; not weekly. The original cadences were written for larger teams.
- **Onboarding-aware documentation.** CLAUDE.md, failures log, and past `/gap` reports are written to also serve as onboarding material for new engineers. Style shift, not a structural one, but a real one.

### v3.1 (prior)

- `/gap` findings require structured citations and confidence scoring (HIGH / MEDIUM / LOW). HIGH-confidence findings feed the failures log; MEDIUM and LOW require human review first.
- `/reconcile` is promoted from a skill to a CI check that runs on every PR touching an active sprint directory.
- Known Limitations section acknowledges the asymmetric memory (negatives well-captured, positives thin) and gives sizing guidance for the memory system.
- Repo-vs-PMS guidance — the repo is the source of truth for anything machine-checkable; the PMS is the coordination layer for humans.

### v3 (prior)

Structural change organizing the method around **two levels** — initiative and sprint — to address between-sprint drift:

- Stable requirement IDs (§X.Y, Dn, Qn) propagating from design doc into sprint PRDs, tasks (via `Satisfies:` line), and code.
- `/sprint-close` as a structural gate that blocks the next sprint from starting until the current is locked.
- `/gap` as a multi-agent audit (decisions, subsections, deletions) against the original design doc.
- Test matrix with five categories (A happy, B edge, C error, D fallthrough, E architecture guards).

Retained from v2 and v2.1: test pyramid, mutation testing, CI-enforced perf and security budgets, docs/failures/, scope limits, senior-skill test review.

---

## Scope and Limits

This method is designed for **feature work that will ship to production**, typically organized as multi-sprint initiatives driven by a design document. Within that scope, it is deliberately strict.

It is **not** the right process for:

- **Spikes and prototypes** — code written to answer a question, not to ship. Spikes use a lighter process: a clear question, a timebox, a decision at the end. Spike code is discarded or rewritten; it does not graduate to production by accident.
- **Throwaway experiments** — A/B test scaffolding, one-off scripts, demos, internal tools with no users beyond the author.
- **Exploratory UX work before product-market fit is established** — when the goal is to learn what users want rather than ship reliably, the full pipeline kills the iteration speed exploration requires.

The critical rule: **code from a spike or experiment does not merge to main**. If an approach proves out, the work re-enters the pipeline at the design-document level — not at a sprint or task level — because anything that skips design-doc authorship will miss initiative-level context and will drift when downstream sprints reference things that were never specified.

If the team finds itself asking "is this a spike or a real feature?", default to treating it as a real feature. Most "spikes" that people do not want to put through the pipeline are actually features someone wants to ship quickly.

---

## Core Principle

Claude Code is not a replacement for engineering discipline. It is a force multiplier that works only when the team provides three things: **verifiable constraints** (tests, types, schemas, budgets), **persistent context** (CLAUDE.md, decision records, failures log, stable requirement IDs), and **small well-defined tasks with explicit traceability** to the design-doc requirements they satisfy. If any of these are missing, output quality collapses.

Treat Claude Code as a highly capable engineer with no memory and no ability to verify its own work unless you give it the tools to do so. The fix for unreliable output is never more prose instructions — it is better infrastructure and better forcing functions.

The single line that summarizes the whole method: **automate what you would otherwise ask reviewers to check, and make skipping steps structurally impossible instead of culturally discouraged.**

---

## Team and Client Context

This method is calibrated for a specific profile:

- **Small team** — typically 3–10 engineers. Not a solo founder, not a 200-person org. Method overhead needs to be proportional to headcount.
- **Enterprise-grade deliverables** — software shipped to paying external clients with contractual acceptance criteria, SLAs, and security expectations.
- **Client trust is the product's long-term value.** A missed requirement is not a backlog item; it is a trust deficit that compounds across the relationship.

Three consequences flow from this profile:

**Failure cost is asymmetric.** When a solo founder ships a bug, they fix it quietly. When a small team ships a bug to an enterprise client, there is an escalation, a post-mortem the client participates in, and sometimes a contract clause invoked. The structural gates in this method (`/sprint-close`, `/reconcile` in CI, `/gap`) exist specifically to catch the class of issue that is cheap to catch internally and expensive to catch at the client.

**Memory compounds harder per engineer.** On a large team, a new engineer can learn by osmosis from 50 others. On a small team, every engineer needs to ramp fast on every client engagement, and every time you prevent a repeat mistake, you save a meaningful percentage of your team's bandwidth. The failures log is disproportionately valuable here.

**Multi-sprint is the default, not the exception.** Enterprise features are rarely one-sprint features. Integrations, compliance reviews, UAT cycles, and staged rollouts mean most meaningful deliveries span multiple sprints. The initiative-level structure is not optional for this context; it is the normal unit of work.

### Per-client repo isolation

Unless you have strong reasons to do otherwise, **each client engagement gets its own repo** with its own CLAUDE.md, failures log, decision records, and sprints directory. Do not mix multiple clients' contexts in one repo. Two reasons:

1. **Confidentiality.** CLAUDE.md and failures log entries frequently contain client-specific context (their API shapes, their business rules, their incidents). Mixing this across clients creates leak risk the first time someone runs `/gap` or reads CLAUDE.md in the wrong context.
2. **Context coherence.** Claude Code operates better with a focused CLAUDE.md that describes one system than with a sprawling one that tries to describe several. Per-client repos keep the context tight.

**Shared infrastructure** (internal libraries, tooling, methodology documents — this one included) lives in separate repos and is pulled in by client repos as dependencies or documented conventions.

### Contract-to-requirement mapping

Enterprise contracts have acceptance criteria, typically in a Statement of Work (SOW) or equivalent. **Treat those acceptance criteria as the initial stable requirement IDs in your design doc.** Concretely:

- If the SOW says "§4.2: The system shall support SSO via SAML 2.0 with the client's IdP," then `SOW-§4.2` is a stable ID.
- The design doc cites `Satisfies: SOW-§4.2` on the section implementing it.
- Task 27 cites `Satisfies: SOW-§4.2, D12`.
- The code line implementing SAML auth is traceable from the SOW clause in under a minute.

This is the single highest-leverage enterprise-specific mechanism. When a client asks "did you implement §4.2?", you answer with a `file:line` citation, not "I think so."

---

## Repository Prerequisites

Before any work begins, the repository must have the following. If these are missing, stop and build them first. This is the single biggest cause of the PRD-to-gap-analysis loop.

| Requirement | Why it matters |
|---|---|
| **Test runner** | Jest, pytest, or equivalent. At least one passing test before feature work begins. |
| **Test pyramid** | Unit, integration (across service boundaries), and E2E tests for critical flows. Without the upper layers, every feature passes its own tests while the system is broken. |
| **Linter and formatter** | Catches style and simple correctness issues automatically. Runs in CI. |
| **Type checker** | TypeScript strict, mypy, or equivalent. Fails hallucinated field names at compile time. |
| **Static security scanning** | Semgrep, CodeQL, or language equivalent in CI. Catches injection and insecure defaults without human vigilance. |
| **Performance budgets** | Latency, bundle-size, throughput assertions that fail the build when exceeded. Required if your contracts specify SLAs. |
| **CI pipeline** | All of the above on every PR. No merges while red. |
| **Per-client repo** | One repo per client engagement. Do not mix clients in a single codebase. See Team and Client Context. |
| **docs/intake/** | Client intake documents, one per engagement at `<CLIENT>-<DATE>.md`. Source of truth for what the client told you during Phase 0 discovery. See the intake template in the method bundle. |
| **CLAUDE.md at repo root** | Persistent context loaded at every session: stack, conventions, directory layout, how to run tests, coding style, "never do this" rules, pointer to failures log, and **client-specific context** (their IdP, their API conventions, their compliance requirements). |
| **docs/contract/** | Client SOW or equivalent, with acceptance criteria assigned stable IDs (SOW-§X.Y). Source for the requirement IDs that propagate through the method. |
| **docs/decisions/ folder** | One ADR per significant choice. Dated. |
| **docs/failures/ folder** | One entry per significant bug or `/gap` finding. Records root cause, which phase should have caught it, and prevention rule. |
| **docs/client-facing/ folder** | Client-facing variants of `/gap` reports and delivery walkthroughs. Same data, no internal jargon. Produced at delivery milestones. |
| **sprints/ directory layout** | `sprints/vN/PRD.md`, `TASKS.md`, `WALKTHROUGH.md`, `RETRO.md`. Sprint has a lockfile indicating closure. |
| **Skills installed** | `/prd`, `/dev`, `/reconcile`, `/sprint-close`, `/walkthrough`, `/retro`, `/security-review`, `/ui-qa`, `/gap` — or manual checklists if not yet automated. `/reconcile` wired as a CI check. |

---

## Process Flow

The diagram below shows the full cycle. The key structural insight: the method operates at two levels. **Initiative level** is the multi-sprint effort to ship a design document. **Sprint level** is one sprint of that initiative. `/sprint-close` is a gate between sprints; `/gap` is a gate between the initiative and "done."

*(See the embedded diagram in the Word version; the ASCII rendering below is equivalent.)*

```
┌──────────────────────────────────────────────────────────────────────────┐
│ PREREQUISITES                                                            │
│ Test pyramid • Linter • Types • Security scan • Perf budgets • CI        │
│ CLAUDE.md • docs/decisions • docs/failures • sprints/ layout • Skills    │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────── INITIATIVE LEVEL ─────────────────────────────┐
│                                                                          │
│   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────┐  │
│   │ Design Document │───▶│   Sprint Cycle  │───▶│ /gap — Initiative   │  │
│   │ docs/<INIT>.md  │    │   (repeat)      │    │ Audit (3 agents)    │  │
│   │ IDs: §X.Y Dn Qn │    │ /prd → /dev × N │    │ decisions • subs •  │  │
│   │ Ambiguity pass  │    │   → /sprint-    │    │ deletions           │  │
│   │ Check failures  │    │   close → lock  │    │ → failures log      │  │
│   │ log             │    │                 │    │ → cleanup sprint    │  │
│   └─────────────────┘    └─────────────────┘    └─────────────────────┘  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                                  │
┌───────────────────────────── SPRINT LEVEL ───────────────────────────────┐
│                                                                          │
│   /prd — Sprint Planning                                                 │
│     Step 1: Refuse if prior sprint not locked                            │
│     Step 2: Ambiguity pass on this sprint's scope                        │
│     Step 3: Decompose into tasks; every task has `Satisfies:` line       │
│     Output: sprints/vN/PRD.md + TASKS.md (with Deferred section)         │
│                                    │                                     │
│                                    ▼                                     │
│   /dev — one task at a time                                              │
│     Step 1: Re-read PRD, announce Satisfies: IDs                         │
│     Step 2: Ambiguity pass on the task (if still underspecified)         │
│     Step 2.5: Test matrix A (happy) + B (edge) + C (error)               │
│                + D (fallthrough) + E (architecture guards)               │
│     Step 3: Senior-reviewed failing tests committed                      │
│     Step 4: Implementation — full automated suite in loop                │
│                                    │                                     │
│                                    ▼                                     │
│   /reconcile — coverage check (mid-sprint or pre-close)                  │
│     Parses PRD IDs + TASKS Satisfies: + code symbols                     │
│     Fails if any requirement unsatisfied without [DEFERRED]              │
│                                    │                                     │
│                                    ▼                                     │
│   /sprint-close — GATE (not optional)                                    │
│     1) /reconcile — abort if uncovered requirements                      │
│     2) /walkthrough — embeds Reconciliation section                      │
│     3) Lock sprint; next /prd is blocked until this exists               │
│                                    │                                     │
│            ┌───────────────────────┘                                     │
│            ▼                                                             │
│   Next sprint /prd (only if vN is locked)                                │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────── PERIODIC CHECKS ─────────────────────────────┐
│  Mutation testing (weekly): validates that Step 2.5 tests actually fail  │
│  when the code is wrong. If the matrix is full but mutation score is     │
│  low, the tests are theatre.                                             │
│                                                                          │
│  /gap (end of initiative, or monthly for long initiatives): three        │
│  parallel agents audit against the design doc. Findings → failures log.  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Initiative Level

An **initiative** is a coherent body of work described by a single design document and delivered across one or more sprints. Initiatives are the unit at which design is specified and at which gap audits run. Sprints are how the work gets broken into shippable chunks.

### Phase 0 — Client Intake and Design Authoring

**Applies to:** any new client engagement where the design doc does not yet exist.

In most enterprise engagements, the client does not hand you a complete design document. They hand you a problem statement, a few examples of the pain, a deadline, and an incomplete set of expectations. Phase 0 is the explicit period during which your team turns that raw input into a design document your team can execute against.

**Phase 0 is time-boxed.** For a typical enterprise engagement, 1–3 weeks of engineering-plus-business-lead time. Longer than three weeks usually means either the client does not know what they want (re-evaluate whether to take the engagement) or the team is gold-plating the spec.

**Phase 0 sub-phases:**

- **0a. Discovery.** Structured 1:1 conversations with the people who will use the system and the people who will sign off on acceptance. Fill in the client intake template at `docs/intake/<CLIENT>-<DATE>.md` (see the AI-Assisted Development Method bundle for the template). Every `[REQUIRED]` field must be filled — "UNKNOWN — need to ask X" is acceptable but counts as an open question.
- **0b. Design-doc drafting.** Your tech lead (with Claude Code assist) drafts `docs/<INITIATIVE>.md` from the intake. Ten to fifteen pages for a first-milestone-worth of scope, not fifty. Use the prompt at the bottom of the intake template to hand the intake to Claude Code as structured input.
- **0c. Ambiguity pass on the draft.** Claude Code lists every ambiguity in the drafted design doc. Questions get answered by follow-up with the client. Resolved questions become Qn IDs in the design doc.
- **0d. Client review.** The client reads the draft, pushes back, negotiates scope. Output: a signed-off design document with stable IDs.
- **0e. SOW reconciliation.** If the SOW acceptance criteria do not match the design doc, reconcile now. Either amend the SOW or explicitly note which design-doc requirements are out of SOW scope. Every SOW clause becomes a SOW-§X.Y stable ID.

**Phase 0 gate:** A signed-off design document exists with stable requirement IDs. The SOW is mapped to design-doc IDs. Open questions are either resolved or explicitly deferred with an owner and date. Until this gate passes, `/prd` for sprint v1 cannot run.

**What Phase 0 is not:** it is not where you write a 200-page specification or solve every technical unknown. It produces a document good enough to start sprint v1 against, knowing that Phase 0 outputs will be refined as the work proceeds. The design doc is versioned; later sprints may add Dn decisions or Qn resolutions. But **requirement IDs are stable** — the document evolves additively.

**If the client cannot sign off a design doc:** they genuinely do not know what they want yet. This is a pre-PMF situation, not an enterprise-delivery situation. Consider one of three options: (1) propose a smaller discovery engagement to produce the spec, billed separately; (2) decline the engagement; (3) propose time-and-materials with explicit "we are figuring it out together" framing and weekly check-ins — accept that `/gap` and `/reconcile` will be noisier in this mode. Do not pretend to have a signed-off spec when you do not.

### Design Document

The initiative has a design document at `docs/<INITIATIVE>.md`. This is the authoritative source of truth, produced by Phase 0 or by the client up-front. Every requirement gets a stable ID (§X.Y for sections, Dn for decisions, Qn for resolved questions) that will propagate through every downstream artifact. **Once assigned, IDs do not change.** If a requirement is updated, the ID is retained and the change is logged.

Before handoff to sprint work, the design document is run through three checks (these run within Phase 0, but they're listed here because they apply to any design doc, Phase-0-produced or client-provided):

1. **Spec-lint.** No vague words (fast, intuitive, seamless, robust, leverage, optimize). All inputs and outputs defined. Every edge case explicit.
2. **Ambiguity pass.** Claude Code is asked to list every ambiguity, unstated assumption, and decision that would need to be made to implement the document. Output is questions only — no code, no proposals. Human answers and updates the doc. IDs are assigned to the resolved questions.
3. **Failures-log cross-check.** Claude Code reads `docs/failures/` and flags any past failure in a domain this initiative touches. Prevention rules from those failures are restated in the design doc or explicitly marked "not applicable."

The design doc is not a sprint PRD. It can span multiple sprints. Breaking it into sprints is the first job of `/prd`.

### Sprint Cycle

The team executes sprints until the design doc is exhausted. Each sprint follows the sprint-level flow (below). Sprints are numbered (v1, v2, v3 …) and sprint vN+1 is structurally blocked from starting until sprint vN is locked via `/sprint-close`. **This is the anti-skip gate.** No amount of "we'll come back to v2.2 later" is allowed; it either finishes, or its remaining tasks are explicitly deferred to a named future sprint with documented rationale.

### /gap — Initiative Audit

At the end of the initiative, or periodically for long-running ones, run `/gap` against the original design document. This is a multi-agent audit with three orthogonal prompts run in parallel:

- **Agent A — decisions.** "For every decision D1–DN in the design doc, find the implementation and cite `file:line`. Flag any decision without a citation."
- **Agent B — subsections.** "For every numbered subsection §X.Y, find the implementation or an explicit deferral. Flag gaps."
- **Agent C — deletions.** "Find code the design doc requires be deleted that still exists in the codebase."

Running the three in parallel with isolated contexts prevents the common failure where a single reviewer anchors on an interpretation and misses what another lens would catch.

**Every finding must include:**

- A requirement ID reference (§X.Y, Dn, Qn, or equivalent)
- A `file:line` citation for the implementation — or the literal string `NO_CITATION_FOUND` if the agent searched and did not find one
- A confidence level: **HIGH** (direct textual or symbolic match), **MEDIUM** (strong inference from call graph, naming, or structure), or **LOW** (plausible match but uncertain — may be a false positive)
- A one-line rationale explaining the citation or the absence of one

`/gap` findings without all four fields are rejected and the agent is asked to re-run. **HIGH**-confidence findings feed directly into the failures log if they surface a gap. **MEDIUM** and **LOW** findings are flagged for human review before any failures-log entry is written. This prevents hallucinated gaps from polluting the team's memory.

Consolidate findings into a severity-ranked gap report at `docs/<INITIATIVE>_GAP_ANALYSIS.md`. For each gap, write an entry into `docs/failures/` with the prevention rule — but only for findings confirmed by a human reviewer or marked HIGH confidence. Feed confirmed gaps into `/prd` as a cleanup-sprint candidate.

**Why `/gap` exists beyond `/reconcile`:** `/reconcile` checks one sprint against its own PRD. It will show green for a sprint that internally implements every task, even if the original design-doc requirement was silently dropped when the sprint was scoped. Only `/gap`, which reads the design doc directly, catches that class of failure. This is the sprint-skipping fix.

**Why `/gap` needs confidence scoring:** `/gap` runs LLM agents against a large design document. It is not deterministic. Without confidence scoring, a high-volume run could produce many plausible-looking but wrong findings, and those wrong findings would become failures-log entries and prevention rules that constrain future work incorrectly. Confidence scoring plus human review of non-HIGH findings keeps the failures log clean.

---

## Sprint Level

Each sprint goes through four gates: `/prd`, `/dev` (once per task), `/reconcile`, `/sprint-close`. The whole sprint lives under `sprints/vN/`.

### /prd — Sprint Planning

**Owner:** Human (with Claude Code assist).

**Preconditions:**
- Sprint vN-1 must be locked (verified by `/sprint-close` having run). If not, `/prd` refuses.
- The design doc must have been through the ambiguity pass.

**Steps:**

1. **Scope this sprint.** Select which design-doc requirements (by ID) this sprint will close. The rest are explicitly out of scope — listed in the PRD's "Out of scope for this sprint, deferred to [future sprint]" section.

2. **Ambiguity pass on the sprint's scope.** Even with a good design doc, selecting a subset raises new ambiguities about interfaces and sequencing. Run the ambiguity prompt against the sprint scope specifically.

3. **Decompose into tasks.** Each task gets a stable task ID (T001, T002, …) and a `Satisfies:` line citing the design-doc requirement IDs it closes. Tasks include explicit acceptance criteria, affected files, and any architectural constraints.

Example task:

```
- [ ] T003: Wire _routes_differ into Check 1.7 load_ref path (P0)
  - Satisfies: D5, §7.3
  - Acceptance: When load_ref matches, routes are compared; if they differ,
    mark as new_in_thread.
  - Files: rfq_threading_service.py
  - Tests required: categories A, B (empty route), D (pre-existing fallthrough)
```

4. **Capture decisions in-line during brainstorming.** After every substantive exchange with the team during planning, summarize agreed decisions with stable IDs and append them to the PRD before moving on. The PRD is the contract, not the chat history.

5. **Write the Deferred section.** Any requirement from the design doc that is in scope for the initiative but not this sprint is listed with its target sprint and rationale. Silent descoping is the anti-pattern.

**Output:** `sprints/vN/PRD.md` and `sprints/vN/TASKS.md`.

**Gate:** Every task has a `Satisfies:` line. Every design-doc ID within this sprint's scope is either in a task or in the Deferred section.

### /dev — Task Implementation

**Owner:** Claude Code (with human review at defined checkpoints).

Run `/dev` once per task. Each task is a separate session. Batching tasks into one session is an anti-pattern; context pollution makes Claude Code drift toward the earliest task and shortcut later ones.

**Steps:**

1. **Re-read the PRD.** Claude Code reads `sprints/vN/PRD.md` and the specific task. Announces: *"Working on T003, which satisfies D5 and §7.3. Key constraints from the PRD: … From CLAUDE.md: … From docs/failures/: …"* Explicit recall defeats the pattern-match shortcut.

2. **Ambiguity pass on the task.** If the task spec is underspecified, Claude Code lists questions and stops. Human answers and updates the task before continuing. Most tasks will not need this step if the PRD ambiguity pass was thorough.

3. **Step 2.5 — Design the test matrix.** Before writing any test code, enumerate the tests across five categories and commit the plan in writing:

   | Category | Minimum | Covers |
   |---|---|---|
   | **A — Happy path** | 1 | Intended behavior works as specified |
   | **B — Edge cases** | 2 | Empty/null, boundary values (0, 1, max), single vs multi-element, missing optional fields |
   | **C — Error paths** | 1 | Preconditions fail, dependencies error, malformed data |
   | **D — Fallthrough / integration** | 1 per code path | When new code's precondition fails, how does pre-existing code behave? Cross-products: (new feature active × old edge case), (new feature inactive × new edge case). |
   | **E — Architecture guards** | 1 per structural change | `inspect.getsource()` or equivalent assertions that deleted symbols stay deleted, new symbols exist, required call patterns are present. |

   Categories D and E are the ones teams skip and the ones that catch the real drift. D catches "feature works in isolation, breaks in composition." E catches "someone re-added the thing we deleted."

4. **Senior-reviewed failing tests committed.** Claude Code writes the tests from the matrix. A human engineer reviews them against two questions: *"If all these tests pass, is the task actually done?"* and *"Would these tests catch a wrong implementation?"* Test review is a senior skill; pair junior reviewers with senior ones for the first several cycles and capture the patterns in CLAUDE.md.

   **Important isolation note:** test writing and implementation should not share a single Claude Code session. Context pollution — where Claude sees the intended implementation during test writing — degrades test-first into test-after. Use separate sessions or subagents.

5. **Implementation.** Only after tests are committed failing, Claude Code writes the minimum implementation to make them pass. The full automated suite (tests, lint, types, security scan, perf assertions) runs in Claude's own loop after every change. If a test appears wrong, flag it — do not modify unilaterally.

**Gate:** All tests green. Linter, type checker, security scan clean. Performance budgets met. The task's `Satisfies:` IDs are traceable to specific `file:line` locations.

### /reconcile — Coverage Check

**Owner:** Automated (CI) and Claude Code (interactive).

**Purpose:** Answer *"does the code produced in this sprint satisfy the sprint's PRD?"*

**Where it runs:**

- **In CI, on every PR that touches `sprints/vN/` where vN is the active sprint.** The PR is blocked from merging if `/reconcile` fails. This makes coverage a hard merge gate, not an advisory check.
- **Interactively, on demand**, for mid-sprint self-checks or when debugging a failing sprint-close.
- **Automatically, as step 1 of `/sprint-close`**, as the final coverage verification before a sprint is locked.

**Workflow:**

1. Parse `sprints/vN/PRD.md` — enumerate all requirement IDs.
2. Parse `sprints/vN/TASKS.md` — map each completed task's `Satisfies:` line.
3. For each PRD requirement ID:
   - Is there ≥1 completed task claiming to satisfy it?
   - Does the code actually contain the function/flag/symbol the task promised?
   - If not, is there an explicit `[DEFERRED]` entry naming the target sprint?
4. Emit a coverage table: *requirement → satisfying task → file:line → confidence*.

**Failure mode:** Any requirement that is unsatisfied without an explicit deferral entry fails the reconcile. In CI, this blocks the merge. Interactively, it produces a list of gaps to fix.

**Runtime:** Typically under a minute for a normal sprint.

**What `/reconcile` does not check:** It verifies symbol *presence*, not *correctness* or *integration*. A function can exist and pass reconcile while being broken, never called, or wrong. Correctness is the job of the test suite (Step 2.5 categories A–E) and the full CI pipeline. This is a deliberate separation — conflating coverage and correctness checks would weaken both. `/reconcile` answers "did we build it?" and tests answer "does it work?"

### /security-review — Enterprise Security Lens (conditional)

**Owner:** Claude Code, invoked by a human. Mandatory for sprints touching auth, data handling, PII, external integrations, or anything in scope of the client's compliance regime.

**Purpose:** Apply an OWASP Top 10 + STRIDE threat model lens to the sprint's changes. Static security scanning in CI catches known bad patterns; this step catches design-level security issues that static analysis misses.

**Workflow:**

1. Parse the sprint's changes (files touched, new endpoints, new data flows).
2. Run Claude Code with an OWASP Top 10 + STRIDE prompt against the changes. Each finding must include a concrete exploit scenario, a severity (P0 / P1 / P2), and a suggested fix.
3. Apply a confidence threshold (HIGH only, or HIGH + human-reviewed MEDIUM) before treating a finding as actionable.
4. P0 and P1 findings block `/sprint-close`. P2 findings can be deferred with an explicit entry.

**Why this is separate from static scanning:** Static scanners catch known antipatterns (SQL injection templates, hardcoded secrets, etc.). STRIDE catches design flaws (trust boundary violations, missing authorization checks, insecure direct object references). Both matter; neither substitutes for the other.

**When to skip:** For sprints that genuinely do not touch auth, data, or integrations — internal refactors, pure UI work on already-authenticated pages, documentation — this step can be skipped with a brief note in `WALKTHROUGH.md` explaining why it did not apply. Do not skip by default.

### /ui-qa — Browser-Automation QA (conditional)

**Owner:** Claude Code driving a real browser, invoked by a human. Mandatory for sprints shipping user-facing changes.

**Purpose:** Mechanically verify acceptance flows and auto-generate regression tests. Test-matrix category A (happy path) for UI work becomes a real test instead of an aspiration.

**Workflow:**

1. Claude Code launches a headless Chromium and walks through the acceptance criteria of each completed task that has a UI component.
2. For each failed flow, Claude records screenshots, traces the issue, fixes it in an atomic commit, and verifies the fix by re-running the flow.
3. For each bug found, Claude generates a regression test that replicates the failure scenario. This test becomes permanent.
4. A structured report summarizes passes, fixes, and any remaining issues.

**Why browser automation specifically:** Unit tests of UI components miss integration issues — state management, routing, race conditions, auth handoffs, real-world form behavior. `/ui-qa` catches the class of bug that only shows up in an assembled system being driven by a real browser.

**When to skip:** Pure backend sprints. API-only work (for API-only products where there is no UI client).

### /sprint-close — Structural Gate

**Owner:** Claude Code, invoked by a human, not optional.

**Purpose:** The single forcing function that prevents sprint-skipping.

**Workflow:**

1. Run `/reconcile`. Abort if any requirement is unsatisfied without a `[DEFERRED]` entry.
2. Run `/security-review` if the sprint is in scope. Abort on open P0 or P1 findings.
3. Run `/ui-qa` if the sprint ships UI. Abort on open acceptance-flow failures.
4. Run `/walkthrough`. The walkthrough template embeds the reconciliation coverage table, the security-review summary, and the UI-QA summary.
5. Run `/retro` (see below). Append to `RETRO.md`.
6. Mark `TASKS.md` status as "Complete." Write a sprint memory entry.
7. **Lock the sprint.** Write a lockfile that `/prd` reads before allowing sprint vN+1 to start.

**This is the anti-skip gate.** If a team wants to abandon a sprint mid-flight, that is allowed — but the sprint must be closed with all incomplete tasks explicitly `[DEFERRED]` to a named future sprint. Silent skips are structurally impossible.

### /retro — Per-Sprint Retrospective

**Owner:** The team. Claude Code prepares prompts; humans answer.

**Purpose:** Feed the failures log from within-sprint experience, not just from bugs that shipped. High-value on small teams where lessons compound.

**Workflow (15–30 minutes per sprint):**

1. What went well? (Claude prompts with: did any test pattern catch something important? Did any tool save meaningful time?)
2. What went poorly? (Claude prompts with: were there any recurrences of past failures? Did we underestimate any tasks?)
3. What surprised us? (Claude prompts with: did the client change requirements? Did a dependency behave unexpectedly?)
4. What prevention rules should we add? For each, write a failures-log entry or amend CLAUDE.md.
5. What client-communication patterns worked or failed? Relevant because client trust is the long-term product value.

**Output:** `sprints/vN/RETRO.md` with the four answers and any new failures-log entries.

**Why this matters for small teams:** On a large team, retros happen at multiple levels and lessons slowly percolate. On a small team, one engineer's insight needs to become everyone's context within one sprint or it is lost. `/retro` is the mechanism.

---

## Periodic Checks (not per-PR)

Some checks are too slow or too noisy for per-PR but essential for long-term quality. Cadence is calibrated for a small team (3–10 engineers); larger teams can run them more frequently.

### Mutation Testing (monthly, critical modules only)

Mutation testing tools (Stryker for JS/TS, mutmut or Cosmic Ray for Python, PIT for Java) systematically break the code in small ways and check whether the test suite catches each mutation. Tests that pass when the code is wrong are silently useless. LLMs readily produce such tests — they exercise the code and assert something, but do not fail when the logic is broken.

The Step 2.5 test matrix is necessary but not sufficient. Mutation testing is the automated backstop for weak test review.

**Cadence for small teams:** Run monthly, not weekly. Focus on **critical modules only** — auth, payments, data integrity, anything touching PII or client-secret data, anything with regulatory or contractual consequences. For a small team, weekly mutation runs on the whole codebase burn a disproportionate share of engineering hours; monthly on the modules that matter gives most of the benefit at a fraction of the cost. Set a mutation-score threshold per critical module; failures become work for the next sprint.

### /gap (end of initiative, or quarterly for long initiatives)

Already described under Initiative Level. Findings feed the failures log, which feeds the next initiative's design-doc review.

**Cadence for small teams:** At every initiative close, and quarterly for any initiative that has been running longer than three months. Not monthly. On a small team, `/gap` too frequently produces more findings than the team can act on, and the marginal finding becomes noise.

---

## The Failures Log

The failures log is how the team stops repeating mistakes. Each significant bug that reaches late-stage testing or production, and each gap surfaced by `/gap`, gets one entry at `docs/failures/YYYY-MM-DD-<slug>.md`.

**Entry format:**

- Date and short title
- What happened (the observable failure)
- Root cause (not the symptom)
- Which phase should have caught this (design doc, `/prd` ambiguity pass, test matrix, `/reconcile`, `/sprint-close`, `/gap`, mutation testing)
- The specific prevention rule going forward

**Example entry:**

```
2026-03-14 — Password reset link accepted after expiry

What happened: Users could use password reset links hours after the
documented 30-minute expiry.

Root cause: Token expiry was checked at generation, not validation.
Tests asserted that expired tokens returned the right error code but
mocked the clock to a fixed time.

Should have caught at: /dev Step 2.5 test review, or weekly mutation
testing. The test labeled "expired token" did not actually advance
time, so a mutation that removed the expiry check would have survived.

Prevention rule: Expiry tests must advance real or fake-but-advancing
time past the expiry threshold between generation and validation. Add
to CLAUDE.md under "test patterns". Apply to session expiry, OTP,
signed URLs, and rate-limit windows.
```

CLAUDE.md references the failures log at the top. Design-doc reviews check against it. When a new initiative touches a domain with past failures, prevention rules get restated in the design doc.

---

## Client-Facing Artifacts

Several method artifacts are also the right inputs for client communication at delivery milestones. Producing client-facing variants is a small cost for a disproportionate trust benefit.

**What to produce for each delivery milestone:**

A delivery milestone is any point where the client reviews and accepts work — end of a major initiative, contracted milestone, quarterly review, or formal acceptance testing. For each milestone, produce a `docs/client-facing/<milestone>.md` that contains:

1. **Coverage summary.** A table of SOW-§X.Y requirements → status (Delivered / Deferred / Not in scope) → brief description of what was built. Derived from `/reconcile` + `/gap` output but in the client's language, not internal jargon.
2. **Known limitations.** Anything delivered with caveats (performance under specific conditions, feature flags, known-issue list). The client finding these at acceptance testing is far worse than the client being told upfront.
3. **Open items with rationale.** For anything deferred, a one-line reason and the target milestone or sprint.
4. **Security and compliance summary.** `/security-review` findings at a level appropriate to share (P0 / P1 resolved, methodology applied, no open issues above threshold). Most enterprise clients want this explicitly.

**What not to include:**

- Internal code references (`file:line` citations are fine for internal artifacts but not for client docs)
- Task IDs or sprint IDs (translate to client-relevant milestones instead)
- Failures-log entries (these describe internal mistakes; the client doesn't need them)
- Decision records (the *outcome* belongs in client docs; the internal debate does not)

**Who writes these:** Typically a tech lead or PM derives the client-facing variant from internal artifacts. Claude Code can draft them by reading `/gap` output, `/reconcile` coverage tables, and the walkthrough, and applying a "translate to client audience" transformation. Humans review before sending.

**A principle:** the client-facing variant should **never contradict** internal artifacts. If the client-facing doc says "Delivered" and the `/reconcile` table says `[DEFERRED]`, that is a trust-destroying discrepancy waiting to happen. The client-facing version is a *projection* of the internal version, not a separate document.

---

## Roles and Handoffs

Small teams often have people wearing multiple hats. This section is descriptive, not prescriptive — describing which role touches which phase, so that whoever is wearing that hat at the moment knows where their work begins and ends.

| Phase / Artifact | Owner | Contributes | Consumes Output |
|---|---|---|---|
| Client SOW / contract | Sales / business lead | PM, tech lead | Design doc author |
| Design doc | PM with tech lead | Engineers, designers | `/prd`, `/gap` |
| Ambiguity pass | Claude Code produces; PM + tech lead answer | Engineers on domain questions | Design doc (updated) |
| `/prd` (sprint planning) | Tech lead | PM for scope, engineers for task granularity | `/dev` |
| `/dev` (implementation) | Engineer + Claude Code | Reviewer for tests | `/reconcile`, `/sprint-close` |
| `/reconcile` (CI) | Automated | — | Merge gate |
| `/security-review` | Engineer + Claude Code | Tech lead for triage | `/sprint-close` |
| `/ui-qa` | Engineer + Claude Code driving browser | Designer for acceptance-flow clarity | `/sprint-close` |
| `/walkthrough` | Claude Code | Engineer validation | PM, client-facing artifacts |
| `/retro` | Whole team | Facilitated by tech lead or PM | Failures log, CLAUDE.md |
| `/sprint-close` | Tech lead | — | Next sprint |
| `/gap` (initiative audit) | Claude Code | Tech lead review, PM consolidation | Client-facing delivery doc, next initiative |
| Client-facing variant | PM or tech lead drafts | Engineer validates for accuracy | Client |
| Failures log entry | Whoever hit the failure | Team at retro | Every future design doc |
| CLAUDE.md updates | Tech lead | Engineers suggest | Every future session |

**Key handoff observations:**

- **PMs own the client-interface parts** (SOW, design-doc framing, client-facing variants) and **do not own the engineering internals** (`/dev`, `/reconcile`, `/security-review`, mutation testing). PMs do not need to run these; they need to know they exist and trust the output.
- **Tech leads own the sprint boundaries** (`/prd`, `/sprint-close`) because those are the gates that protect delivery commitments.
- **Engineers own the tasks and tests** and should push back if `/prd` decomposition gives them tasks without clear `Satisfies:` lines or acceptance criteria.
- **The whole team owns retros and the failures log.** These are the compounding memory layer; an engineer's insight that doesn't make it into the log is lost.

If the team is very small (say, three engineers with one acting as tech lead), one person will wear multiple hats. The method still works — the roles are real, just not separate people. The critical separation to preserve is **whoever reviews tests should not be the same person who wrote the implementation for that task in the same session**, because that defeats the test-first discipline. On a three-person team, rotate.

---

## Rules the Team Must Follow

1. **One sprint at a time per initiative stream.** Concurrent sprints on the same initiative produce merge chaos and break `/reconcile`. Parallel initiatives are fine if they touch different code.

2. **One task at a time per `/dev` session.** Batching tasks in one session pollutes context and degrades test discipline. Start a fresh session per task.

3. **Never skip the test matrix.** Categories D and E are the ones teams skip and the ones that catch real drift. If time pressure prompts you to skip them, that is exactly when they are most needed.

4. **Test writing and implementation must be in separate sessions.** Single-context TDD with an LLM tends to produce implementation-first code disguised as test-first.

5. **Never accept "it should work" without running it.** If a task finishes without the full automated suite passing, it is not finished.

6. **When Claude Code gets stuck in a loop, stop and re-specify.** Third round of "fix this, still broken" means the spec is underdetermined. Go back to `/prd` or to the design doc.

7. **Keep CLAUDE.md, decision records, and the failures log current.** Stale context is worse than no context.

8. **Do not use gap analysis as a primary workflow.** `/gap` is an end-of-initiative audit. If `/gap` is running constantly and finding many issues, that is a signal `/reconcile` or `/sprint-close` is being skipped.

9. **Automate what you would otherwise ask reviewers to check.** Performance, security, requirement coverage, test adequacy — all automated. Human vigilance is not a reliable control.

10. **Spike code re-enters at the design-doc level, not at a sprint or task level.** Exploratory code becomes production code only by passing through the full initiative pipeline.

11. **Silent descoping is an anti-pattern.** Dropping a requirement requires an explicit `[DEFERRED]` entry naming the target sprint and the rationale. A skipped requirement with no record is a bug.

12. **Requirement IDs are stable.** Once §X.Y or Dn is assigned, the ID does not change. Updates are logged under the same ID.

13. **Per-client separation is hard.** Never mix two clients' contexts in one repo, one CLAUDE.md, or one failures log. Client A's incident should not appear in Client B's context window.

14. **Every client-facing artifact is a projection of an internal artifact.** Never write a client-facing doc that contradicts `/reconcile` or `/gap` output. If the two disagree, the internal source is the one the engineering team trusts, and the client-facing doc needs to be corrected.

15. **SOW clauses get requirement IDs.** Enterprise contract acceptance criteria are the root of the traceability chain. `Satisfies: SOW-§X.Y` is a real line in tasks.

---

## Anti-Patterns to Kill Immediately

- ✗ Starting a new sprint before the previous one is locked via `/sprint-close`
- ✗ Tasks without a `Satisfies:` line citing design-doc requirement IDs
- ✗ Treating "task complete" as "requirement closed" without running `/reconcile`
- ✗ Silent descoping — dropping a requirement without a `[DEFERRED]` entry
- ✗ Skipping Step 2.5 test matrix categories D (fallthrough) and E (architecture guards)
- ✗ Writing tests in the same session as implementation
- ✗ Handing a full design doc to Claude Code and saying "build this"
- ✗ Letting Claude Code modify tests to make them pass instead of fixing the implementation
- ✗ Running sessions without CLAUDE.md loaded
- ✗ Relying only on unit tests — integration and E2E gaps produce "features work, system broken"
- ✗ Treating perf and security as a review checklist instead of CI-enforced budgets
- ✗ Letting CLAUDE.md or the failures log go stale
- ✗ Fixing the same class of bug repeatedly without updating `docs/failures/`
- ✗ Using gap analysis as the primary development loop — it is an audit, not a method
- ✗ Letting spike or prototype code become load-bearing without re-entering at the design-doc level
- ✗ Writing failures-log entries from LOW- or MEDIUM-confidence `/gap` findings without human review
- ✗ Renaming or renumbering requirement IDs
- ✗ Mixing two clients' contexts in one repo, one CLAUDE.md, or one failures log
- ✗ Client-facing artifact contradicting internal `/reconcile` or `/gap` output
- ✗ Skipping `/security-review` on a sprint that touches auth, data, or external integrations
- ✗ Skipping `/ui-qa` on a sprint that ships user-facing changes
- ✗ Treating `/retro` as performative — filling in the template without generating any failures-log entries or CLAUDE.md updates
- ✗ Writing client-facing artifacts without tracing each claim back to an internal source
- ✗ Accepting SOW clauses without assigning them stable requirement IDs

---

## What to Expect

The first initiative through this method will feel slower than the current approach. The overhead is front-loaded: writing a real design doc, assigning IDs, running the ambiguity pass, writing `Satisfies:` lines. By the second initiative, `/reconcile` and `/sprint-close` start paying off — nothing gets silently dropped, and gap-analysis documents stop being written by hand because `/gap` produces them.

If the improvement is not materializing, something is being skipped. The most common skips, in order of frequency:

1. **`/sprint-close` treated as a soft step** — teams close sprints without actually running `/reconcile` first. Look for uncovered requirements that "someone will pick up later."
2. **The ambiguity pass is performative** — questions are listed, nobody updates the doc, the spec stays vague. Check whether the doc was actually edited after ambiguity-pass output.
3. **The test matrix's D and E categories are omitted** — the categories that catch real drift are the ones that feel most like busywork in the moment.
4. **The failures log is write-only** — entries get written but never consulted during new design docs. Check whether design-doc reviews actually cross-reference `docs/failures/`.
5. **`/retro` becomes performative** — the four questions get filled in but no failures-log entries or CLAUDE.md updates result. If three retros produce zero updates to the memory layer, the retro is not working.
6. **`/security-review` gets skipped under deadline pressure** — always on sprints that happen to be the highest-risk ones. If the team skipped it because "it was a small change," audit the change: did it touch auth, data, or integrations? If yes, the skip is the problem.
7. **Client-facing artifacts drift from internal state** — someone updates the client-facing doc without updating `/reconcile` or `/gap`. The inverse is the only safe direction: internal state is the source; client-facing is derived.

Do not loosen the method. Find what is being skipped and reinforce it.

---

## Success Metrics

Leading indicators (check weekly):

- 100% of tasks in active `TASKS.md` files have a `Satisfies:` line.
- 100% of locked sprints have a `WALKTHROUGH.md` with a Reconciliation section.
- 100% of closed initiatives have a `docs/<INITIATIVE>_GAP_ANALYSIS.md` produced by `/gap`.

Lagging indicators (check per initiative):

- Gap count from `/gap`. Baseline from the pre-v3 threading initiative: 8/30. Target: approaching 0.
- Number of hand-written `*_GAP_ANALYSIS.md` docs. Target: zero. Gap analyses are produced by the skill, not by hand.
- Mutation score on critical modules. Target: agreed threshold per module, trending up.
- Number of failures-log entries whose prevention rule was violated again in a later initiative. Target: zero. This is the "stop repeating mistakes" metric.

---

## What This Method Does Not Do

- It does not prevent wrong-but-implemented requirements (the requirement itself is wrong but the code matches it). Pre-design-doc review and stakeholder alignment cover that; this method assumes the design doc is correct.
- It does not reduce the hours spent on design and planning. It increases the return on those hours by making silent descoping and sprint-skipping structurally impossible.
- It does not make Claude Code smarter. It constrains what Claude Code is asked to do so that its existing capability is applied to narrow, verifiable tasks with explicit traceability.

---

## Known Limitations

### Asymmetric memory — negatives captured, positives mostly not

The method has a well-developed memory of what goes wrong (`docs/failures/`, anti-patterns in CLAUDE.md, `/gap` findings) and a much thinner memory of what goes right. `docs/decisions/` captures architectural choices and their rationale, but there is no structured place for "this test pattern repeatedly catches the bugs we care about" or "this refactoring approach scaled cleanly." Positive patterns currently live in individual engineers' heads and are lost when people move on.

This is a known gap, not a hidden one. The method is biased toward negative memory because negative memory has clearer triggers (a bug shipped, a gap was found) and higher-value entries (each prevention rule blocks a specific class of failure). Positive memory is softer and at greater risk of becoming aspirational entries nobody reads.

If the team notices during retrospectives or `/sprint-close` that they keep re-deriving the same good approaches and losing them between engineers, add a `docs/patterns/` folder with entries mirroring the failures-log format (date, what worked, why it worked, when to apply it, reference). To keep it honest, require a *second* reference — a later sprint where the pattern was deliberately reapplied — before an entry is considered canonical. One-off successes that are never reused are probably just luck.

Until that signal is clear, do not pre-emptively add a patterns folder. Speculative memory systems usually become write-only.

### Memory has a cost — prune as deliberately as you add

Every entry in CLAUDE.md, every failures-log item, every prevention rule has ongoing cost: context-window space if it's loaded into Claude Code sessions, cognitive load if humans read it, and noise if it's stale. Memory compounds in both directions — useful rules compound into wisdom, outdated rules compound into friction.

Practical sizing guidance:

- **CLAUDE.md stays under roughly 500 lines.** LLMs demonstrably skip content in the middle of longer files. If yours is longer, push detail into linked docs and keep CLAUDE.md as the index.
- **The failures log can grow without bound, but the set of *active* prevention rules should stay small** — roughly 20–50 for a mature codebase. Rules older than 12 months without a recent reference are candidates for retirement or consolidation.
- **The right unit of memory is the prevention rule, not the incident.** If two failures-log entries produce the same rule, consolidate them. A log with 100 entries distilled into 20 rules is a codebook; a log with 100 entries and no consolidation is a graveyard.
- **ADRs are append-only, but superseded decisions are explicitly marked as such** with a forward link. Nothing is more confusing than reading a decision that was quietly reversed.
- **Requirement IDs are the exception** — they are permanent. Stable IDs are worth more than clean history.

A useful test for any entry: *would a new engineer joining next month benefit from this?* If the entry refers to a module that no longer exists, a vendor the team no longer uses, or a person-specific quirk, it is technical debt in the memory system. Prune it.

The sharpest principle: **memory exists to change future behavior.** If an entry would not change what someone does when they encounter it during a `/prd` ambiguity pass or a `/dev` task kickoff, it should not be there. Entries are levers, not journals.

Add a memory-pruning review to the team's rhythm — perhaps quarterly, or as part of the `/gap` end-of-initiative audit. Specifically: read through `docs/failures/`, identify rules that have not been referenced or violated in the last year, and either retire them or fold them into a broader rule. Read through CLAUDE.md and ask "is this still true?" for each rule. Small, deliberate pruning beats occasional purges.

### Where these artifacts live — repo vs. project-management system

A common and expensive mistake is putting method artifacts in the wrong layer. The short version: **the repo is the source of truth for anything machine-checkable; the PMS is the coordination layer for humans.** Different artifacts belong in different places, and the boundary matters.

**What belongs in the repo:**

- **Design documents** (`docs/<INITIATIVE>.md`). They reference code, evolve with code, and need to move together with the codebase they describe. In a PMS they would drift.
- **Sprint PRDs, TASKS, WALKTHROUGHs** (`sprints/vN/`). The `Satisfies:` traceability model depends on these being grep-able from the codebase. If they live in Jira, `/reconcile` has to hit an external API — slow, flaky, and introduces an auth boundary. In the repo, it is a file parse.
- **CLAUDE.md.** Not optional. Claude Code loads it from the working directory.
- **`docs/decisions/` (ADRs).** Architectural decisions are code context and need to be versioned with the code they describe.
- **`docs/failures/`.** Claude Code consults this during ambiguity passes and `/dev` task kickoffs. If it lives in a wiki or PMS, Claude cannot read it efficiently during sessions.
- **Requirement IDs (§X.Y, Dn, Qn).** Stable IDs are what make `/reconcile` work at all. Trying to sync IDs between a ticket system and code is where real teams lose traceability.

**What belongs in the PMS (Jira, Linear, GitHub Issues, Basecamp, etc.):**

- **Work tracking and coordination** — who is on what, what is the current sprint's board, what is blocked, who is reviewing. Day-to-day operational layer. A PMS is built for this; the repo is not.
- **Stakeholder-facing communication** — status updates, roadmap visibility, cross-functional discussion. Product managers, designers, and leadership do not read markdown files in a repo.
- **Ticket-level discussion** — "I tried X, it didn't work because Y, now trying Z." Comment threads beat git blame for this.
- **External reporting and metrics** — velocity, throughput, cycle time, bug rates.

**How the two layers link:**

Each task in `TASKS.md` has a task ID (T001, T002 …) and optionally a link to a PMS ticket (e.g., `Jira: PROJ-1234` or `GitHub Issue: #456`). The PMS ticket links back to the task ID, the sprint, and eventually the PR. PR descriptions cite the task ID and the `Satisfies:` requirement IDs. `/reconcile` reads the repo, not the PMS. **The PMS is downstream of the repo, not upstream.**

**Failure modes when this boundary is violated:**

- **Jira becomes the PRD.** Requirements get written as tickets. Tickets close when "done." But there is no stable ID system, no `Satisfies:` line, and no machine-checkable coverage. `/reconcile` against a Jira board is not cheap and not deterministic. The traceability argument collapses.
- **Requirements drift silently in the PMS.** Jira ticket descriptions can be edited in place without version history. Design docs in git are versioned; changes are visible in the diff. `/gap` needs a stable target to audit against.
- **Claude Code operates without context.** If CLAUDE.md, failures log, or design doc live outside the repo, Claude Code cannot efficiently read them during a session. Context that lives in a PMS is context Claude operates without — which defeats most of the method.

**MCP connectors do not change the recommendation.** Claude can now reach Jira, GitHub, and similar systems via MCP servers and connectors. This is genuinely useful for operational context ("what tickets does this PR relate to?") but does not change where the machine-checkable parts of the method should live. Ticket data is coordination, not spec. The parts of the method that have teeth — `Satisfies:`, `/reconcile`, `/gap`, the failures log — still need to live in the repo where they can be parsed deterministically and read without an external round-trip.

**The one-line test** for any artifact: *does Claude Code need to read it during a session?* If yes, it belongs in the repo. If it is purely for humans to coordinate, the PMS is fine — or even better.

**The gray area — the failures log for non-engineers.** If your org is small, keep the failures log in the repo only. If you are larger and product or leadership genuinely need to consult it, mirror it to an internal wiki or Notion page with the repo copy as the source of truth and the wiki auto-updating from it. Do not let the wiki become the primary copy; the prevention rules have to stay grep-able from Claude Code sessions.

---

## Appendix A — Prompt Templates

### Design-Doc Ambiguity Pass

```
Here is a design document at docs/<INITIATIVE>.md. Read it carefully and
list every ambiguity, unstated assumption, or decision that would need to
be made to implement it. Include edge cases not addressed. Check the
document against docs/failures/ and flag any domains with past issues
whose prevention rules are not reflected. Do NOT write code. Do NOT
propose solutions. Output a numbered list of questions only, grouped by
section.
```

### /prd — Sprint Scope and Task Decomposition

```
Here is the design document at docs/<INITIATIVE>.md and the planned
scope for sprint vN. Decompose the scope into tasks. Each task must have:
(1) a stable task ID (T001, T002, …); (2) a `Satisfies:` line citing the
design-doc requirement IDs (§X.Y, Dn, Qn) it closes; (3) explicit
acceptance criteria; (4) affected files; (5) which test-matrix categories
are required. Requirements in scope for the initiative but not this
sprint must be listed in a Deferred section with target sprint and
rationale. Fail loudly if any requirement cannot be cleanly scoped.
```

### /dev — Task Kickoff

```
Working on task T003 in sprints/vN/. Before writing any code, re-read
sprints/vN/PRD.md and the specific task entry. Announce which
design-doc IDs the task satisfies and the key constraints from the PRD,
CLAUDE.md, and docs/failures/ that apply. If the task is underspecified
to implement safely, stop and list questions. Otherwise proceed to the
test matrix.
```

### /dev — Test Matrix Design

```
Before writing any test code, design the test matrix for task T003.
Enumerate tests across five categories and commit the plan in writing:
A (happy path) ≥ 1, B (edge cases) ≥ 2, C (error paths) ≥ 1, D
(fallthrough / integration) ≥ 1 per code path, E (architecture guards)
≥ 1 per structural change. For each planned test, briefly note what
it is guarding against. A test whose failure would not indicate a real
problem is not a real test.
```

### /dev — Test Writing (separate session from implementation)

```
You are writing failing tests for task T003. You do NOT have access to
the implementation and will not write the implementation in this
session. Write tests that match the approved test matrix. Tests must
fail against the current codebase. Follow conventions in CLAUDE.md.
For each test, include a one-line comment naming the category (A–E)
and the Satisfies: ID.
```

### /dev — Implementation (separate session from test writing)

```
Here are the failing tests committed for task T003. Implement the
minimum code needed to make them pass. Do not add functionality not
covered by tests. Run the full automated suite (tests, linter, type
checker, security scan) after each change. If a test appears incorrect,
stop and flag it — do not modify tests unilaterally. Follow conventions
in CLAUDE.md and the prevention rules in docs/failures/.
```

### /reconcile

```
Parse sprints/vN/PRD.md to enumerate all requirement IDs. Parse
sprints/vN/TASKS.md to map each completed task's Satisfies: line. For
each PRD requirement ID, determine: (1) is there a completed task
satisfying it? (2) does the code contain the promised symbol? (3) if
not, is there an explicit [DEFERRED] entry? Emit a coverage table:
requirement → task → file:line → confidence. Flag any requirement
unsatisfied without a deferral entry as FAIL.
```

### /security-review

```
Review the sprint's changes through two lenses: OWASP Top 10 and
STRIDE threat modeling. For each lens, walk the changed files, new
endpoints, and new data flows. For each finding output a structured
entry with: category (OWASP rule or STRIDE category), location
(file:line), a concrete exploit scenario (not abstract — "an
unauthenticated user could …"), severity (P0 / P1 / P2), confidence
(HIGH / MEDIUM / LOW), and suggested fix.

Do not report findings below MEDIUM confidence. Do not report style
issues or non-security code quality — those are covered by other
checks. Apply known false-positive exclusions from docs/failures/.

P0 and P1 findings block /sprint-close. P2 findings can be deferred
with rationale.
```

### /ui-qa

```
Launch a headless browser. For each task in sprints/vN/TASKS.md with
a UI component, walk through its acceptance criteria as a real user
would. Record:

  - Which criteria passed end-to-end
  - Which failed, with screenshot, URL, and reproduction steps
  - For each failure, attempt a fix as an atomic commit; re-run the
    flow to verify
  - For each fix, generate a regression test that replicates the
    original failure

Output a report: passes, fixes with commit SHAs, any remaining
failures, and the list of new regression tests. Remaining failures
block /sprint-close.
```

### /retro — End-of-Sprint Retrospective

```
Facilitate a short retrospective for sprint vN. Read
sprints/vN/WALKTHROUGH.md, the reconcile output, the security-review
output, and any UI-QA findings. Then produce a template for the team
to fill in:

  1. What went well this sprint? (Claude: did any test pattern
     catch something important? Did any approach save meaningful
     time? Flag candidates.)
  2. What went poorly? (Claude: were there recurrences of past
     failures from docs/failures/? Did we underestimate any tasks?
     Flag candidates.)
  3. What surprised us? (Claude: did the client change
     requirements? Did a dependency behave unexpectedly?)
  4. What prevention rules should we add? For each, draft a
     failures-log entry or a CLAUDE.md update for human review.
  5. What client-communication patterns worked or failed?

Write the output to sprints/vN/RETRO.md. Any new failures-log
entries are written as draft and must be reviewed by a human before
being marked canonical.
```

### Client-facing artifact generation

```
Given the internal artifacts for this delivery milestone —
sprints/vN/WALKTHROUGH.md (for each sprint in scope),
docs/<INITIATIVE>_GAP_ANALYSIS.md, docs/contract/SOW.md, and the
/reconcile coverage tables — produce a client-facing delivery
document at docs/client-facing/<milestone>.md.

Include:
  - Coverage table: SOW-§X.Y → status (Delivered / Deferred / Not in
    scope) → brief description in client's language
  - Known limitations with any caveats
  - Deferred items with one-line rationale and target milestone
  - Security and compliance summary (methodology applied, findings
    resolved, no open issues above threshold)

Exclude:
  - file:line citations
  - Task IDs, sprint IDs (translate to client-relevant milestones)
  - Failures-log entries (internal only)
  - Decision records (outcome only, not debate)

Every claim in the client-facing doc must be traceable to a specific
line in an internal artifact. If any claim cannot be traced, flag it
for human review — do not invent supporting evidence.
```

### /gap — Three Parallel Agents

Agent A prompt:

```
For every decision D1–DN in docs/<INITIATIVE>.md, find the
implementation in the codebase. For each decision, output a structured
finding with exactly these fields:

  - id: the decision ID (e.g., D5)
  - citation: "file:line" if found, or "NO_CITATION_FOUND" if absent
  - confidence: HIGH | MEDIUM | LOW
      HIGH   = direct textual or symbolic match
      MEDIUM = strong inference from call graph, naming, or structure
      LOW    = plausible match but uncertain
  - rationale: one line explaining the citation or its absence
  - status: IMPLEMENTED | MISSING | PARTIAL

Do not output findings that lack any of these fields. If uncertain,
mark LOW confidence rather than guessing HIGH. False positives
pollute the failures log.
```

Agent B prompt:

```
For every numbered subsection §X.Y in docs/<INITIATIVE>.md, find the
implementation in the codebase or an explicit deferral in any
sprints/vN/TASKS.md. Output structured findings with exactly these
fields: id, citation, confidence (HIGH/MEDIUM/LOW with the same
definitions as Agent A), rationale, status (IMPLEMENTED | DEFERRED |
MISSING). No field may be omitted.
```

Agent C prompt:

```
Read docs/<INITIATIVE>.md. For every passage that specifies code,
symbols, or patterns should be deleted or replaced, search the
codebase for residue. Output structured findings with exactly these
fields: what-should-be-deleted (quote from design doc), citation
(file:line of residue, or NO_RESIDUE_FOUND), confidence (HIGH/MEDIUM/
LOW), rationale, status (CLEAN | RESIDUE_FOUND). No field may be
omitted.
```

Consolidation prompt:

```
Given the three gap reports from Agents A, B, and C, produce a
severity-ranked consolidated gap analysis at
docs/<INITIATIVE>_GAP_ANALYSIS.md. For each gap:

  - plan ref
  - severity (P0 / P1 / P2)
  - what spec says
  - what code does
  - citation (from agent output)
  - confidence (from agent output)
  - impact
  - suggested fix

Sort by severity, then by confidence (HIGH findings first within each
severity tier). For HIGH-confidence gaps at P0 or P1, draft a
corresponding failures-log entry. For MEDIUM- or LOW-confidence gaps,
flag for human review before any failures-log entry is written.
```

### Anti-Hallucination Modifier (append to any prompt)

```
If any requirement is unspecified, stop and ask — do not assume.
Prefer failing loudly over guessing. Before starting, list any
ambiguities you see. Do not invent API fields, library functions, or
file paths you have not verified against the actual codebase.
```

---

## Appendix B — Directory Layout

```
<client-repo>/
├── CLAUDE.md                          # Persistent context, client-specific
├── docs/
│   ├── intake/
│   │   └── <CLIENT>-<DATE>.md         # Phase 0 intake document
│   ├── contract/
│   │   └── SOW.md                     # Acceptance criteria with SOW-§X.Y IDs
│   ├── <INITIATIVE-NAME>.md           # Authoritative design docs
│   ├── <INITIATIVE>_GAP_ANALYSIS.md   # Produced by /gap
│   ├── client-facing/
│   │   └── <milestone>.md             # Client-facing variants
│   ├── decisions/
│   │   └── YYYY-MM-DD-<slug>.md       # ADRs
│   └── failures/
│       └── YYYY-MM-DD-<slug>.md       # Failures log entries
├── sprints/
│   ├── v1/
│   │   ├── PRD.md
│   │   ├── TASKS.md
│   │   ├── WALKTHROUGH.md
│   │   ├── RETRO.md                   # Written by /retro
│   │   └── .lock                      # Written by /sprint-close
│   ├── v2/
│   │   └── …
│   └── …
└── <application code>
```

**Note:** one repo per client. Shared infrastructure (internal libraries, methodology docs, CI templates) lives in separate repos and is referenced as dependencies or documented conventions, not vendored into client repos.

---

## Appendix C — Migration from Earlier Versions

### From v3.1

Version 3.2 adds enterprise-specific layers on top of v3.1. The core pipeline (design doc → `/prd` → `/dev` → `/reconcile` → `/sprint-close` → `/gap`) is unchanged. What's new:

1. **Add `docs/contract/` folder.** Place the client SOW there and assign stable IDs (SOW-§X.Y) to each acceptance criterion. Update the design doc to reference these IDs in its own `Satisfies:` chain.
2. **Add `docs/client-facing/` folder.** At each delivery milestone, produce a client-facing variant of the coverage and gap artifacts.
3. **Split repos if you're working with multiple clients.** One repo per client, each with its own CLAUDE.md and failures log.
4. **Add three new skills / phases:** `/security-review` (conditional, for sprints touching auth / data / integrations), `/ui-qa` (conditional, for sprints shipping UI), `/retro` (every sprint). Update `/sprint-close` to run them before locking.
5. **Calibrate periodic-check cadence.** Mutation testing moves from weekly to monthly on critical modules only. `/gap` moves from monthly to per-initiative + quarterly.
6. **Update CLAUDE.md** to include client-specific context (IdP, API conventions, compliance requirements) and the pointer to `docs/contract/`.

### From v3 or earlier

Follow the v3 → v3.1 migration first (structured `/gap` findings, `/reconcile` in CI), then apply the v3.1 → v3.2 steps above.

### From v2.1 (single-feature method)

If the team has been using v2.1:

1. Treat each current feature as an initiative with one sprint. The jump to multi-sprint structure happens when the team starts multi-sprint work.
2. The v2.1 Phase 1–6 pipeline maps onto `/prd` (Phases 1–2) and `/dev` (Phases 3–4 per task) plus `/sprint-close` (Phases 5–6). No concepts are lost; the structure is reorganized.
3. The failures-log layout from v2 is unchanged. Existing entries carry over.
4. Apply the v3 additions (stable requirement IDs, `Satisfies:`, `/sprint-close`, test matrix D and E, `/gap`), the v3.1 additions (structured `/gap` findings, `/reconcile` in CI), and then the v3.2 additions (contract folder, per-client repos, security review, UI QA, retros, calibrated cadence).
