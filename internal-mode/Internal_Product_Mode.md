# Internal Product Mode

**Version 1.0**

*A companion process for building internal products that may eventually ship as SaaS*

---

## Why this exists

The main method (v3.2.1) is calibrated for client-delivery work: a paying client defines what "done" means, and the process exists to prevent drift from that definition. Internal product development is different. Nobody external has paid for a spec. You are the one defining what to build, and that definition is expected to change as you learn.

Applying client-mode rigor to exploratory internal work produces high-quality implementations of wrong products. Applying no rigor produces shelfware that you can't commercialize when the product direction becomes clear. The goal of Internal Product Mode is to thread this needle: **engineering quality stays high throughout; product rigor graduates as evidence accumulates.**

---

## Core principle

In client mode, the spec is the constraint and the code serves the spec.

In Internal Product Mode, **learning is the constraint and both the spec and the code serve the learning.** Every sprint should produce evidence that either strengthens conviction ("this product is worth building") or weakens it ("users don't actually behave the way we thought"). A sprint that ships code but produces no evidence is a failed sprint, even if the code works.

This doesn't mean code quality drops. It means the definition of "done" includes "we learned something actionable" alongside "the code works."

---

## Three stages

Internal products move through three stages. Each stage has different rules. The stages are not age-based; they are evidence-based. A product can sit in Stage 1 for months and that's fine. A product can also jump directly to Stage 3 if you already have strong evidence (e.g., you've sold the idea to two pilot clients before building). What matters is the evidence, not the calendar.

| | Stage 1 — Exploration | Stage 2 — Validation | Stage 3 — Commercialization |
|---|---|---|---|
| **What you're doing** | Testing whether the problem is real and the approach is plausible | Testing whether real users (internal or pilot) derive real value | Preparing the product for external paying clients |
| **Primary risk** | Wrong problem or wrong approach | Right problem, wrong solution | Right problem + right solution, wrong execution |
| **Who uses the product** | The team building it; maybe a handful of friendlies | Internal users beyond the team; possibly design-partner clients | External paying clients |
| **Sprint length** | 3–5 days | 1 week | 2 weeks (same as v3.2.1) |
| **Spec form** | Hypotheses + lightweight doc (5–10 pages max) | Living design doc with stable IDs | Fully-formed design doc; client SOW if applicable |
| **Spec stability** | Changes weekly | Changes monthly | Changes through formal CR process |
| **`/reconcile`** | Runs in CI; coverage is for what was in *this sprint's* PRD | Same as Stage 1, plus cross-sprint drift checks | Same as v3.2.1 |
| **`/gap`** | Skip. Doc changes too often to audit against. | Quarterly, against *current* doc. Job is drift detection, not deviation. | Per initiative + quarterly, as in v3.2.1 |
| **`/security-review`** | Light — OWASP basics only, since internal users | Moderate — full OWASP for anything exposed outside the team | Full v3.2.1 rigor before external exposure |
| **`/ui-qa`** | Optional — dogfooding covers most UI issues | Mandatory on any user-visible change | Mandatory as in v3.2.1 |
| **Mutation testing** | Skip on feature code; apply to shared libraries only | Monthly on critical modules | Monthly, as in v3.2.1 |
| **Failures log** | Mandatory, same as client work | Same | Same |
| **CLAUDE.md** | Mandatory, same | Same | Same |
| **Test matrix** | A + C required; B/D/E if time permits | A + B + C + D required; E where structurally relevant | All five categories, as in v3.2.1 |
| **What the sprint PRD must include** | A hypothesis + what we expect to learn + a kill signal | Hypothesis + user-behavior metric to watch + acceptance criteria | Acceptance criteria tied to stable IDs |
| **Dogfooding** | First-class activity — the team is the primary user | First-class — expand beyond the team | Optional if clients can be the validators |

The rest of this document explains each stage in detail and, critically, the gates between them.

---

## Stage 1 — Exploration

### What Stage 1 is for

You believe a problem exists. You have a rough idea of an approach. You don't know whether the problem is really real, whether the approach will work, or whether the resulting product would be worth building. Stage 1 exists to cheaply answer those questions before you commit significant engineering time.

### What the starting document looks like

Not a design doc — a **product hypothesis document** at `docs/hypothesis.md`. Five to ten pages, not fifty. It answers:

- **The problem, concretely.** Who has this problem, how do they experience it today, what evidence do you have that it's real? Not "users struggle with X" but "we watched Mary spend 40 minutes on Tuesday doing X and she said 'this is ridiculous.'"
- **The hypothesis.** If we build approach Y, we believe users will experience outcome Z.
- **The test.** How will we know the hypothesis is correct? What specific observable behavior or metric tells us yes or no?
- **The kill signal.** What would cause us to stop? Be specific: "if five out of five test users fail to complete the workflow unaided within 10 minutes, we kill this direction."
- **The timeline.** How long are we willing to spend before we decide to continue, pivot, or kill?
- **Out of scope, explicitly.** Things we are not trying to prove in Stage 1.

This document has stable IDs from day one (H1, H2 for hypotheses; §1.1, §1.2 for scope sections) even though it will change. Stable IDs are the only thing that lets `/reconcile` work across sprints where the doc is evolving.

### Stage 1 sprint rhythm

Short sprints — 3 to 5 days. Each sprint PRD has four required sections:

1. **Hypothesis being tested.** Reference the hypothesis ID (H2) from the product hypothesis doc.
2. **What we expect to learn.** Specific and falsifiable.
3. **What would cause us to pivot.** Concrete evidence that would change our direction.
4. **Scope.** The tasks being done this sprint, each with `Satisfies:` citing hypothesis IDs or design-doc section IDs.

Each `/sprint-close` answers one additional question beyond the v3.2.1 checklist: **"Did we learn what we set out to learn? If not, why?"** This answer goes in `WALKTHROUGH.md` as a "Learning" section. A sprint that shipped code but produced no learning is flagged — not failed, but flagged — because it means the sprint was executing, not exploring.

### What's lighter in Stage 1

- **No `/gap` runs.** The doc changes faster than gap audits are useful. Pick it back up in Stage 2.
- **Test matrix: A (happy path) and C (error paths) required; B, D, E only if time permits.** Exploration code has a higher chance of being thrown away; full test coverage on code that won't ship is waste. The Category E architecture guards are specifically the ones that matter *if* you commercialize — so when you graduate to Stage 2, you'll add them retroactively to code that survives.
- **`/security-review` is light.** OWASP basics (injection, auth fundamentals), STRIDE only if the feature crosses a trust boundary. No external clients means lower acute risk.
- **Mutation testing on shared libraries only.** Feature code in Stage 1 isn't worth mutation-testing because much of it gets rewritten before Stage 2.
- **`/walkthrough` is thin.** A page, not three. The format: "here's what we built, here's the learning section, here's what changed in the hypothesis doc."

### What stays strict in Stage 1

- **CLAUDE.md is mandatory and current.** Context discipline doesn't get cheaper just because the product is exploratory.
- **Failures log is mandatory.** Bugs you learn from in Stage 1 are doubly valuable because they often expose wrong assumptions in the hypothesis.
- **Separate sessions for tests and implementation.** This rule is about code correctness, not about product certainty. It stays.
- **`/reconcile` in CI.** Requirement drift is a problem at every stage.
- **Stable requirement IDs.** The hypothesis doc changes; the IDs within it do not.

### Stage 1 anti-patterns specific to this mode

- ✗ Shipping a feature with no attached hypothesis or learning goal. If you can't articulate what you'll learn, you shouldn't build it yet.
- ✗ Ignoring the kill signal when it triggers. The kill signal exists to prevent sunk-cost escalation. If it fires and you ignore it, you didn't have a real kill signal.
- ✗ Skipping the failures log "because it's just a prototype." Prototype bugs are a signal source, not throwaway noise.
- ✗ Treating code quality as optional. You will ship some of this. Category D (fallthrough) is the one that's easiest to defer and most painful to retrofit later — apply it wherever the code touches existing production systems.

---

## Gate 1 → 2: Evidence of real user value

This is the first graduation gate. It exists to prevent the common failure where a team's enthusiasm for their own product mistakes "the team thinks it's cool" for "users derive value."

**To cross this gate, you must have:**

- **Quantitative evidence of use.** Not team use. Users outside the build team using the product in at least 3 distinct sessions each, with observable behavior that indicates value (task completion, return usage, expressed preference over status quo). "5 internal users tried it once" does not cross the gate.
- **A qualitative why.** You can articulate, in users' own words, what value they got. If the best you can say is "users seemed to like it," you haven't crossed the gate.
- **Remaining kill signals are known and haven't fired.** If there are still plausible failure modes you haven't tested, the gate hasn't been crossed yet.
- **A committed bet.** The team agrees to invest the next 4–8 weeks in Stage 2 rather than exploring further. This is an explicit decision, not a default.

**Gate ceremony:**

Produce `docs/gate-1-to-2-decision.md`. Content:

- What evidence we have (specific, cited, not vibes)
- What we still don't know and are accepting as risk
- The commitment (timeline, team, success criteria for Stage 2)
- Sign-off by whoever owns the product decision

This document is the artifact. If you can't write it, you haven't crossed the gate.

**If you can't cross the gate:**

Three options: (1) stay in Stage 1 longer with a refined hypothesis; (2) pivot to a different hypothesis within the same problem space; (3) kill the product. All three are acceptable; continuing as if the gate were crossed is not.

---

## Stage 2 — Validation

### What Stage 2 is for

You've shown the product does something useful for some users. Stage 2 is about broadening that, understanding what's essential vs incidental, and hardening the pieces that matter. The goal is **conviction strong enough to commit to commercialization** — or to discover you shouldn't.

### What the document looks like in Stage 2

The product hypothesis doc from Stage 1 gets upgraded to a **living design document** at `docs/<PRODUCT>.md`. It:

- Carries forward all stable IDs from Stage 1
- Adds new IDs as scope grows
- Marks removed requirements as `[REMOVED: reason, date]` rather than deleting them
- Has a versioned changelog at the top showing the evolution of direction

Stable IDs are now doing real work: they appear in `Satisfies:` lines, they're tracked by `/reconcile`, and they support the periodic drift audits that replace `/gap`.

### Stage 2 sprint rhythm

One-week sprints. Sprint PRD adds one section beyond Stage 1:

- **User-behavior metric to watch.** Something measurable: "X% of users who start the onboarding flow complete it within 10 minutes," "retention from week 1 to week 2 stays above Y%," "support tickets about feature Z stay below N per week."

Each `/sprint-close` reviews usage data in addition to running `/reconcile` and `/retro`. If the user-behavior metric moved the wrong way, that's a signal — not to revert the change necessarily, but to investigate why.

### What tightens in Stage 2

- **Test matrix: A, B, C, D required.** Category E (architecture guards) is applied where structure is genuinely load-bearing, not everywhere.
- **`/security-review` becomes moderate rigor.** Full OWASP Top 10 review on anything exposed beyond the team. STRIDE on authentication, authorization, and data-handling changes.
- **`/ui-qa` becomes mandatory** on user-visible changes. Dogfooding is no longer sufficient coverage because Stage 2 users include people who aren't on the team.
- **`/gap` runs quarterly**, but its purpose is different from v3.2.1. It's not "did we build what we said 3 months ago?" — it's "has the code drifted from our *current* intent?" The audit runs against the *current* design doc, and the `[REMOVED]` markers tell `/gap` not to flag removed things as missing.
- **Mutation testing runs monthly** on critical modules (same as v3.2.1 calibration).

### What stays lighter than client mode

- **No SOW mapping** — you don't have a client to have a contract with yet.
- **No client-facing artifacts.** Internal status updates are sufficient.
- **Design-doc changes don't go through a formal CR process.** Updates happen through normal PR review plus a note in the changelog.
- **Sprint length stays at one week**, shorter than v3.2.1's two-week default.

### Stage 2 anti-patterns

- ✗ Confusing "some users like it" with "validated." Stage 2's job is to build real conviction, not to declare victory early.
- ✗ Shipping features that don't move any behavior metric. If nothing changes in how users interact, you're adding surface area without validation.
- ✗ Treating Stage 2 as a permanent state. Stage 2 is for reaching a decision point about commercialization. If you've been in Stage 2 for 6+ months with no graduation and no kill, something is wrong.
- ✗ Carrying Stage 1 code quality into Stage 2. Specifically: add the D and E test coverage to code that survived Stage 1 before building on top of it.

---

## Gate 2 → 3: Decision to commercialize

The second graduation gate. This one is often a business decision as much as an engineering decision.

**To cross this gate, you must have:**

- **A clear commercialization plan.** Who buys this, at what price, through what channel, and why would they choose it over alternatives.
- **An identified first client or segment.** Either a specific paying pilot client or a clearly defined early-adopter segment with evidence that they'll pay.
- **Retention evidence, not just trial evidence.** Users keep coming back without being prompted.
- **An engineering readiness assessment.** What in the codebase needs to be re-done with client-grade rigor before external exposure? This becomes the first Stage 3 initiative.
- **A commitment from your team to the commercialization timeline.** External clients mean SLAs, support, and commitments. If the team can't commit to that, don't cross the gate.

**Gate ceremony:**

Produce `docs/gate-2-to-3-decision.md`. Content:

- Commercialization plan (who, what, when, how much)
- Summary of Stage 2 evidence supporting the decision
- Engineering debt to be repaid in Stage 3's first initiative (often 2–6 weeks of hardening work)
- Commitments on SLAs, support, and ongoing investment
- Sign-off by the product and engineering leads

**If you can't cross the gate:**

Either extend Stage 2 with a more focused plan to answer what's missing, or conclude that the product shouldn't be commercialized (which is a legitimate outcome, not a failure). Do not proceed to Stage 3 without a commercialization plan. Shipping to external clients without commitment is how you acquire technical debt and client debt simultaneously.

---

## Stage 3 — Commercialization

### What Stage 3 is for

The product is now going to external paying clients. Internal Product Mode's job is done; the v3.2.1 client-delivery method takes over. Stage 3 is the *transition*, not a permanent state — after the first external delivery, your product is simply in client-delivery mode.

### What happens in Stage 3

The first Stage 3 initiative is typically **hardening work**, not new features. Specifically:

1. **Full v3.2.1 method adoption.** Switch to two-week sprints; add `/security-review` at v3.2.1 rigor; add full test matrix (all five categories); enable mutation testing on critical modules; set up `/ui-qa` as a mandatory step.
2. **Design-doc cleanup pass.** The living design doc from Stage 2 may have accumulated `[REMOVED]` markers, changelog entries, and exploratory sections. Produce a clean, current-state design doc (retaining stable IDs) that will serve as the reconcile target going forward.
3. **SOW creation if applicable.** If you have a specific first client, write the SOW and map its acceptance criteria to design-doc IDs. If you're shipping as self-service SaaS without per-client SOWs, create a "public specification" document that plays the same role — the product's guaranteed behavior, publicly documented.
4. **Repo separation if needed.** If you've been developing in a single internal repo, decide now whether per-client isolation is needed. For SaaS products, usually one multi-tenant repo is correct. For customized deployments, per-client repos per v3.2.1 apply.
5. **Retroactive architecture guards.** Category E tests that were skipped in Stages 1 and 2 get written now for the components that survived.
6. **Client-facing artifacts.** Per v3.2.1, produce the client-facing variants of coverage and gap artifacts for the first external milestone.

The first external delivery is the exit from Stage 3. From there, it's v3.2.1 client-delivery mode end to end.

### Stage 3 timeline

Typically 2–6 weeks of hardening before the first external delivery, depending on how much technical debt accumulated in Stages 1 and 2. Budget for this explicitly; do not treat it as overhead.

---

## What to provide me for internal product work

Similar structure to the client intake template, but different inputs. For any new Stage 1 work, provide:

**About the product hypothesis:**

- The problem, with 3–5 concrete examples (not hypotheticals). Watch someone experience the problem; describe what you saw.
- The hypothesis: if we build Y, users will experience Z. One or two sentences.
- The target segment, specifically. "Enterprise customers" is not specific; "compliance teams at mid-market fintech companies doing SOC 2 audit prep" is.
- Evidence you have so far that the problem is real.
- What would constitute validation: specific observable behavior or metric.
- The kill signal: what would make you stop.
- Timeline to decision: how long are you willing to invest before committing, pivoting, or killing.

**About the internal context:**

- Who's building: team composition, percent-allocation, start dates.
- Runway: how much time and engineering budget you have for this bet before you need a decision.
- Technical constraints: must use our existing stack, must integrate with our auth, must not disrupt existing products.
- Adjacent products or teams: what this could complement or cannibalize.

**About the commercialization path:**

- Do you have specific clients in mind? Named, with expected use cases.
- What would commercialization require: compliance scope, SLA expectations, support model.
- Do you already have a pilot client committed? (If yes, Stage 1 and 2 may be compressed; you have a forcing function.)
- At what rough point do you expect to transition to Stage 3?

Given these inputs, I can help with: drafting the hypothesis document with stable IDs, proposing the first sprint's scope as a learning experiment with explicit kill signals, designing the user-behavior metric for Stage 2, and structuring the graduation-gate decision documents.

---

## What this mode does NOT do

- **Does not remove the need for engineering discipline.** Code quality, test discipline, and context hygiene stay at client-mode levels throughout. What graduates is product rigor, not code quality.
- **Does not guarantee commercialization.** Some Stage 1 and Stage 2 work ends in "kill." That's correct, not a failure. The gates exist to make these decisions visible, not to prevent them.
- **Does not replace product management.** This is a process, not a PM function. You still need someone (or the tech lead wearing a PM hat) making product decisions, running user research, and owning the hypothesis. The process structures how their decisions flow into engineering; it doesn't make the decisions for them.
- **Does not apply to client work pretending to be internal.** If you're building something for a specific known client, that's client work. Use v3.2.1. "Internal product that one particular client asked for" is client work in disguise.

---

## Anti-patterns specific to Internal Product Mode

- ✗ Declaring PMF after a handful of friendly users tried the product once.
- ✗ Staying in Stage 1 indefinitely because you don't want to commit.
- ✗ Graduating to Stage 3 without repaying engineering debt from Stages 1 and 2.
- ✗ Treating learning as optional ("we shipped features, that's enough").
- ✗ Ignoring the kill signal when it fires.
- ✗ Skipping CLAUDE.md or the failures log because "we'll clean it up later" — later never comes, and both are harder to retrofit than to maintain.
- ✗ Applying full v3.2.1 rigor in Stage 1 and wondering why you can't iterate quickly.
- ✗ Applying Stage 1 rigor in Stage 3 and wondering why external clients escalate.
- ✗ Assuming the stage is defined by the calendar rather than the evidence.

---

## Honest caveats

Unlike v3.2.1, which grew from a specific post-mortem (the 8-of-30-missing-requirements threading initiative), Internal Product Mode does not yet have that empirical foundation in your team's work. This document is synthesized from general principles of lean product development, the structural insights from v3.2.1, and common failure modes I've seen described in adjacent teams — but it has not been validated on your specific context.

**What this means in practice:**

- Treat this as a starting point, not as settled doctrine.
- Expect to revise it after your first full cycle (Stage 1 → Stage 2 → Stage 3 or kill).
- Watch specifically for these possible miscalibrations: (1) the stages are wrong for your pace — you might need four stages or two; (2) the graduation gates are too strict or too loose — adjust based on what actually predicted success; (3) the test-matrix reduction in Stage 1 might be too aggressive and bite you when code survives into Stage 2 — track how often Stage 1 code needs rewriting versus hardening.
- Come back with data from one real Stage 1 → Stage 2 transition and we can calibrate this document.

The version is 1.0 intentionally, not 3.x. Expect a 2.0 after real use.

---

## Quick reference

**You are in Stage 1 if:** you don't yet have evidence that real users get real value. Sprint length 3–5 days. Hypothesis-driven. `/gap` off. Light security.

**You are in Stage 2 if:** you've passed Gate 1. Real users are using it and finding value. Sprint length 1 week. Watching behavior metrics. Living design doc. `/gap` quarterly as drift detection.

**You are in Stage 3 if:** you've passed Gate 2. You're preparing for or actively shipping to paying external clients. Full v3.2.1 rigor. 2-week sprints. Clean design doc. Client-facing artifacts.

**You are not in any stage if:** you haven't written the hypothesis document. Do that first.
