# Client Intake Template

**Instructions:** Fill out this document during client discovery. It captures everything needed to produce an initial design document, ambiguity-pass questions, and a first-sprint scope. Sections marked `[REQUIRED]` must be filled in before Phase 0 can close; sections marked `[OPTIONAL]` improve output quality but don't block progress.

**How to use:**
1. Copy this template to `docs/intake/<CLIENT>-<DATE>.md` at the start of every new client engagement.
2. Fill it in during discovery interviews. Do not guess — if a field is unknown, write `UNKNOWN — need to ask <stakeholder>` and track it as an open question.
3. When all `[REQUIRED]` fields are filled, hand this document to Claude Code (or a senior engineer) to draft the initial design document.
4. Keep this intake document in the repo. It's the source of truth for what the client told you; the design document is your team's interpretation of it.

**Philosophy:** Better to have fewer fields captured accurately than many fields filled with "TBD." An empty `[REQUIRED]` field blocks progress; that's the point.

---

## Section 1: Engagement metadata `[REQUIRED]`

- **Client organization name:**
- **Intake date:**
- **Intake interviewer(s):** (your team's names)
- **Primary client contact (champion):** (name, role, email)
- **Decision maker for acceptance:** (name, role — this is who signs off that the work is done)
- **Budget / engagement size:** (rough order of magnitude; "fixed-bid $200K" or "T&M, budget ~$500K" is fine — "TBD" is not)
- **Target start date:**
- **Target first-delivery date:** (not the full engagement end, but the first milestone the client expects something)
- **Deadline driver:** (what makes this deadline matter — fiscal year, compliance date, contract clause, competitive pressure, internal board commitment)
- **Engagement type:** (fixed-bid project / time & materials / retainer / staff augmentation)

---

## Section 2: The client organization `[REQUIRED]`

- **Industry and what the client actually does:** (2–3 sentences, not marketing language; describe the real business)
- **Company size:** (headcount, revenue if known, rough complexity signal)
- **Where the users are:** (geographic distribution, matters for performance and compliance)
- **Regulatory environment:** (SOC 2, HIPAA, GDPR, FedRAMP, industry-specific — list all that apply; if none, write "none known" explicitly)
- **Existing technology stack:** (what they run today, what we'll have to integrate with or avoid disrupting)
- **Prior engagements with vendors for this problem:** (have they tried to solve this before? With whom? Why did it not work?)

---

## Section 3: The problem `[REQUIRED]`

- **Stated request, verbatim in client's own words:** (quote them; don't paraphrase — their framing reveals how they think about the problem)
- **What triggered this conversation happening now?** (something changed — a new regulation, a lost deal, a merger, a senior leader demanding it — naming the trigger reveals the real urgency)
- **Three to five specific examples of the pain:** (concrete situations, not hypotheticals. "Last Tuesday, Mary in accounting spent 4 hours doing X because Y" is good. "Users have trouble with reports" is not.)
- **Anti-examples — things the client explicitly does NOT want:** (what has been ruled out already, and why)
- **What they've tried so far:** (internal attempts, other vendors, workarounds; what worked partially, what didn't)
- **What does success look like 6 months after delivery?** (how will they know this was worth doing — specific metric, observable behavior change, capability gained)

---

## Section 4: Users and stakeholders `[REQUIRED]`

- **Primary users — who will actually use the system day to day:** (role, count, technical sophistication, daily context of use)
- **Secondary users:** (admins, auditors, integrators, anyone touching the system less frequently)
- **Buyer vs. user:** (often different — the person paying is rarely the person using; flag if they are different)
- **Other stakeholders affected:** (people impacted by the system who aren't direct users — compliance, operations, customer support, the client's own customers)
- **Who is against this project internally at the client?** (there is almost always someone; naming them early prevents surprise)

---

## Section 5: Integrations and dependencies `[REQUIRED]`

- **Systems this must integrate with:** (list each: name, purpose, who owns it, integration method if known — REST, file drop, database replication, SSO)
- **Systems this replaces or will eventually replace:** (named; sunset timeline if known)
- **External data sources:** (what data flows in, from where, in what format, at what frequency)
- **External destinations:** (what data flows out, to where, under what conditions)
- **SSO / identity:** (what IdP, what protocol, whose responsibility to configure)
- **Deployment target:** (client's cloud / on-prem / our cloud / client's existing Kubernetes / serverless — and who operates it post-delivery)

---

## Section 6: Non-functional requirements `[REQUIRED]`

- **Performance expectations:** (response time, throughput, concurrent users — gather what the client has said, even if rough; if they haven't said anything, write "none stated — will ask")
- **Availability / uptime expectations:** (is there an SLA? 99.9%? 99.99%? Business hours only?)
- **Security and compliance:** (encryption requirements, data classification, audit logging expectations, pen test expectations, specific controls required)
- **Data residency:** (must data stay in a specific region? Are there cross-border restrictions?)
- **Scale expectations:** (data volume at launch, growth rate, peak vs. steady load)
- **Support model post-delivery:** (do we maintain? Do they? Is there a handover? What SLA on support?)

---

## Section 7: Constraints `[REQUIRED]`

- **Non-negotiable technical constraints:** (must use specific vendor, specific language, specific cloud; usually imposed by client's existing environment or procurement)
- **Non-negotiable process constraints:** (must follow their change management, must go through their security review, must be accessible for their users, specific QA or certification requirements)
- **Licensing constraints:** (open-source policies, commercial-license restrictions, IP ownership terms in the SOW)
- **Timeline constraints that cannot flex:** (regulatory go-live date, contract milestone, market window)
- **Known political constraints:** (the client's internal politics that will affect the project — "CTO doesn't want this but CEO mandated it," "Department A is buying but Department B will operate")

---

## Section 8: What the client gave us `[OPTIONAL but valuable]`

Attach or link. More is better; raw is better than cleaned up.

- **RFP or original request document:**
- **Screenshots, wireframes, mockups:**
- **Existing system documentation:**
- **Sample data files:**
- **Emails or transcripts from sales conversations:**
- **Their internal requirements documents (if shared):**
- **Anything else the client handed you:**

---

## Section 9: Open questions `[REQUIRED to list; may remain unanswered]`

Every intake conversation surfaces questions that couldn't be answered in the moment. List them here. These will feed the first ambiguity pass. Assign each to a stakeholder who can answer.

- **Q1:** <question> — Owner: <stakeholder> — Blocks: <what this blocks; "design doc drafting" / "first sprint scope" / "nothing urgent">
- **Q2:**
- **Q3:**

Keep adding to this list through Phase 0. Close questions only with answers in writing (email, Slack with the decision maker, meeting minutes).

---

## Section 10: Your team's context `[REQUIRED]`

This isn't about the client — it's about what your team is bringing to the engagement.

- **Engagement team:** (who's assigned: roles, percent-allocation, start dates)
- **Tech lead for this engagement:**
- **Similar work your team has done before:** (name specific past projects; link to their failures-log entries if they contain relevant prevention rules)
- **Prevention rules from `docs/failures/` that apply:** (list specific entries by date-slug that are relevant to this engagement's domain — auth failures if this has auth, integration failures if this has integrations)
- **Skills gaps on this engagement:** (what does the team not know yet that this work will require — be honest)
- **Risk signals from this intake:** (flags that concern the tech lead — vague scope, political tension, aggressive timeline, known-hard integrations, novel domain for the team)

---

## Section 11: Initial risk assessment `[REQUIRED]`

Your tech lead's honest assessment, written before the design doc exists. Revisit and update as Phase 0 progresses.

- **Top 3 risks to this engagement, ranked:** (concrete; "client will keep changing scope" is concrete, "it might be hard" is not)
- **For each risk: mitigation approach or explicit acceptance**
- **What's the most likely reason this engagement fails?** (if you can't answer this, you haven't thought hard enough about it)
- **What would cause us to walk away?** (rare, but naming it prevents sunk-cost decisions later)

---

## Section 12: Commercial / contractual `[OPTIONAL at intake, REQUIRED before Phase 0 closes]`

- **SOW status:** (draft / in negotiation / signed)
- **SOW acceptance criteria:** (list each clause with a reference ID — these become SOW-§X.Y stable IDs)
- **Change request process:** (how does the client expect scope changes to be handled — formal CR, email approval, ignored until invoice)
- **Payment terms:** (milestone-based, time-based, mixed; matters for what "done" means per sprint)
- **Warranty / post-delivery obligations:**

---

## Section 13: Handoff readiness `[REQUIRED before this intake is "closed"]`

Before this intake document is considered complete enough to drive Phase 0 design-doc authoring:

- [ ] All `[REQUIRED]` sections filled (no "TBD" placeholders — "UNKNOWN — need to ask X" is acceptable but counts as an open question)
- [ ] Open questions list is populated and owners assigned
- [ ] Tech lead has signed off that the intake reflects what was actually said
- [ ] Client champion has reviewed this intake for accuracy (send it to them; capture their corrections)
- [ ] SOW exists at least in draft form with numbered acceptance criteria
- [ ] Initial risk assessment done and reviewed with business lead
- [ ] Intake document committed to `docs/intake/` in the client repo

Once checked, the intake is ready to hand off to design-doc authoring (Phase 0b in the method).

---

## Section 14: How to use this intake as LLM input

When you hand this document to Claude Code (or me) to draft the initial design document, use a prompt like:

```
Here is the intake document for client <CLIENT>, engagement <NAME>. Using this as
the sole source of truth about what the client said:

1. Draft an initial design document at docs/<INITIATIVE>.md with the standard
   sections (problem, scope, users, decisions, open questions, integrations,
   non-functional requirements, acceptance criteria, assumptions).
2. Assign stable IDs to each requirement (§X.Y, Dn, Qn). SOW clauses become
   SOW-§X.Y.
3. Run an ambiguity pass on your own draft: list questions the client would
   need to answer before this document can be signed off.
4. Propose a first-sprint scope — a subset of requirements that can be
   delivered in 1–2 weeks and that demonstrates enough value that the client
   would want to continue.

Do NOT invent requirements the client didn't ask for. Do NOT fill gaps with
plausible-sounding defaults. Where the intake says UNKNOWN, preserve that
uncertainty in the design doc and flag it in the ambiguity pass.

Check against the failures log at docs/failures/ for prevention rules that
apply to this engagement's domain.
```

**Expected output from this prompt:**
- A draft `docs/<INITIATIVE>.md` (10–15 pages, not 50)
- A numbered list of ambiguity-pass questions for the client
- A proposed first-sprint scope with 5–10 tasks

Review the draft yourself before showing it to the client. The LLM will have made interpretive choices that you need to validate.

---

## Intake completion summary

- **Date intake opened:**
- **Date intake closed:** (all `[REQUIRED]` sections filled, handoff-readiness checklist complete)
- **Total time invested in intake:** (hours — worth tracking to calibrate future engagements)
- **Number of open questions at intake close:** (if >15, the engagement is underspecified; consider a second round of discovery)
- **Link to resulting design doc:** `docs/<INITIATIVE>.md`
- **Link to SOW:** `docs/contract/SOW.md`
