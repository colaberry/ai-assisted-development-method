# Sprint vN — PRD

**Initiative:** <INITIATIVE-NAME> (see `docs/<INITIATIVE>.md`)
**Sprint dates:** YYYY-MM-DD to YYYY-MM-DD
**Tech lead:** <n>
**Prior sprint locked:** Yes (`sprints/v{N-1}/.lock` exists) / N/A (first sprint)

> `/prd` refuses to produce this PRD until the prior sprint is locked. If the prior sprint is not locked, stop and run `/sprint-close` on it — or explicitly defer its remaining work and lock it.

---

## Scope

This sprint will close the following requirements from the design document:

- [§X.Y] <short description> — <brief implementation approach>
- [§X.Y] <short description>
- [Dn] <decision statement>
- [SOW-§X.Y] <contract acceptance criterion>

> Each line starts with a requirement ID in brackets. The `/reconcile` script will look for these IDs and match them against tasks' `Satisfies:` lines.

---

## Ambiguities resolved during planning

<Output of the ambiguity pass on this sprint's scope. Questions Claude Code raised and the answers the team gave. Each resolved question gets a stable ID (Qn) that can be cited in `Satisfies:` lines going forward.>

- **Q1:** <question> → **Resolution:** <answer>
- **Q2:** <question> → **Resolution:** <answer>

---

## Out of scope for this sprint (deferred)

Explicitly listed here so `/reconcile` can distinguish "in scope but not done" from "not in scope this sprint." These are requirements from the design doc that belong to the initiative but have been pushed to a later sprint.

- [§X.Y] <description> — **Target:** vN+1 — **Reason:** <rationale>
- [Dm] <decision> — **Target:** vN+2 — **Reason:** <rationale>

---

## Architectural notes

<Any design decisions that scope this sprint specifically. Reference ADRs in `docs/decisions/` when applicable. If a new ADR emerged during planning, draft it here and move to `docs/decisions/` when finalized.>

---

## Performance and security budgets

<If this sprint's work affects performance-budgeted paths or security-sensitive areas, restate the budgets and any specific constraints.>

- **Latency budget:** <p50/p99 targets if applicable>
- **Security scope:** <touches auth / data / integrations / none>
- **`/security-review` required:** Yes / No
- **`/ui-qa` required:** Yes / No

---

## Known risks

<Things the team identified as likely to cause drift or rework. Each one gets a mitigation or an explicit "accept and move on" note.>

- **Risk:** <description> → **Mitigation:** <plan>
