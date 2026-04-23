# AADM Roadmap — Third-Party Skill Extension Framework

| | |
|---|---|
| **Status** | Captured; **not building.** Gated on §4 graduation signal. |
| **Owner** | Ram Kotamaraja |
| **Created** | 2026-04-23 |
| **Prerequisite refactor (§3)** | Queued as an independent sprint — tracked in [issue #48](https://github.com/colaberry/ai-assisted-development-method/issues/48). Independently valuable; ships regardless of whether §2 ever fires. |

---

## §1 Intent

AADM's current enforcement surface is intentionally closed: the method ships its own skills, scripts, templates, and hooks, and those enforce themselves against AADM-native lifecycle phases. This is the correct posture **for the base-method proving period**. Trying to become a plugin platform before being a proven method would risk attribution confusion (did the method work, or did the plugins help?) and would dilute the structural-enforcement story that separates AADM from prompt libraries.

For external adoption — especially once AADM goes open-source — users will eventually want to combine AADM with:

- **Third-party skill bundles** (Anthropic-published Engineering / PM packs, community-published domain skills)
- **User-authored custom skills** (team-specific workflows, organization-specific conventions)
- **Tool-integrated skills** (wrappers over vendor-specific deployment, observability, compliance tools)

The strategic direction is to **remain open to this integration, once the base method has proven itself, and without weakening any of the structural gates** that make AADM valuable in the first place.

This roadmap captures:

- §2 — the architectural shape of that future framework
- §3 — the one prerequisite refactor that unlocks it (queued now, independently valuable)
- §4 — the graduation signal that gates investment in §2 itself
- §5 — explicit non-goals

**This document is not a sprint plan.** No code is written against §2 until §4 fires. §3 can proceed on its own merits at any time.

---

## §2 Integration surface

The future extension framework exposes **five architectural seams** to third-party skills, in increasing implementation weight.

### §2.1 Skill manifest convention

Third-party skills declare compatibility via frontmatter:

```yaml
---
name: write-prd-thorough
description: A more thorough PRD writer
aadm_compatible: true
aadm_phases: [design, prd]
aadm_version: ">=3.2.0"
---
```

- `aadm_compatible: true` — skill author asserts the skill does not attempt to bypass AADM's gate model.
- `aadm_phases` — lifecycle phases where the skill is safe. Valid values: `intake`, `design`, `prd`, `test`, `impl`, `close`, `retro`, `gap`, `any`.
- `aadm_version` — semver range the skill is known to work with.

AADM's loader checks the manifest at startup. Skills without the manifest are tolerated but marked "unregistered" in `state-check` output. Skills whose `aadm_version` excludes the running version are refused.

### §2.2 Discovery directory

Third-party skills live in `.claude/skills/external/<bundle>/<skill>.md`. AADM's skill discovery walks both the native directory (`.claude/skills/*.md`) and the external tree.

`state-check` reports installed skills in three groups:

```
AADM-native skills:   intake, design-doc, prd, dev-test, dev-impl, sprint-close, gap, ...
AADM-compatible:      engineering/code-review, pm-pack/stakeholder-map, ...
Unregistered:         my-team/deploy-to-staging  (no aadm_compatible flag)
```

This makes the installed-skill surface legible at a glance and makes it impossible for a third-party skill to silently "run under AADM."

### §2.3 Events contract

Third-party skills that want to appear in metrics and the Control Tower dashboard emit entries to `events.jsonl` following AADM's stable event schema:

```jsonl
{"ts":"2026-04-23T14:30:00Z","skill":"engineering/code-review","phase":"impl","action":"review_requested","sprint":"v3","tenant_id":"colaberry","extra":{...}}
```

Documented event types, required fields, and schema versioning live in `metrics/docs/EVENTS_CONTRACT.md` (future work, part of §2 investment). Third-party skills that conform become first-class in dashboards; those that don't are invisible to aggregated metrics but remain fully usable.

### §2.4 Capability-based `Files:` enforcement

Third-party skills declare the file patterns they intend to read and write, either in frontmatter or in a companion `capabilities.yml`:

```yaml
capabilities:
  reads: [src/**/*.py, tests/**/*.py]
  writes: [tests/**/*.py]
```

AADM cross-references the declared patterns against the active sprint task's `Files:` allowlist when the skill is invoked. Mismatches are refused the same way `sprint_gate.py` refuses native-skill writes today. **The third-party skill inherits AADM's scope-discipline enforcement without needing to know about `sprint_gate.py` internally.**

This only works after §3 has landed — PreToolUse hooks are what make the enforcement skill-agnostic.

### §2.5 Curated registry

A `docs/skills-registry.md` (or marketplace-style index) listing third-party skills that have been reviewed for AADM compatibility. Convention, not enforcement — nothing in AADM depends on the registry, and users can install skills not on it.

Heaviest-weight item in §2 and the last to ship. Listed here for completeness.

---

## §3 Prerequisite refactor: move lifecycle enforcement into PreToolUse hooks

- **Status:** Queued as an independent sprint.
- **Shipping status:** Not started.
- **Target window:** After the Control Tower webapp's Stage 0 reaches usable state; not blocked by §4 graduation.
- **Tracked in:** [issue #48](https://github.com/colaberry/ai-assisted-development-method/issues/48).

### §3.1 Problem

Current AADM lifecycle enforcement (e.g., "`/dev-impl` refuses without a `/dev-test` marker") lives **inside the skill file itself** — the skill's markdown prompts Claude to check the marker before proceeding. This works for AADM-native skills but fails in two cases:

1. **Third-party skills that do similar work** (e.g., an `engineering/write-impl` from a third-party bundle) don't carry the check, so calling them bypasses test-first discipline.
2. **Raw `Edit` / `Write` calls** from Claude outside any skill (agent-driven flows that decide to edit files directly) bypass the check by not invoking the skill at all.

Case (2) is not a plugin scenario — it's the current Claude Code runtime. The refactor is needed for today's use, not only for tomorrow's plugin story.

### §3.2 Fix

Move the lifecycle-stage checks out of skill prompts and into **PreToolUse hooks** in the same shape as `sprint_gate.py`:

- Hook fires on any `Edit` / `Write` / `NotebookEdit` call.
- Hook reads the active sprint state: test marker present? sprint `.lock` present? next-sprint directory allowed?
- Hook refuses writes that violate lifecycle state **regardless of which skill (or no skill) triggered the write.**

The skill files become *polite* interfaces that prompt the user through the happy path. The gates are the hooks — load-bearing regardless of driver.

### §3.3 Why this ships independently of §2

§3 is **independently valuable**:

- Hardens AADM against agent-driven raw-Edit flows in today's runtime.
- Makes the enforcement surface auditable (hooks are declarative and few; skill-embedded checks are distributed and many).
- Unlocks §2 as a byproduct — but §2 can be postponed or never-built and the refactor still pays for itself.

This is why §3 is queued now even though the rest of the roadmap is gated on §4. If §4 never fires, §3 still ships and still wins.

### §3.4 Sprint shape (rough sketch)

- **Design doc:** `method/lifecycle-hook-refactor.md` (name TBD) — stable IDs for each gate (test-marker check, sprint-lock check, next-sprint-directory-ban), migration plan skill-by-skill.
- **Implementation scope:** ~6–10 tasks — one hook per lifecycle gate, migration of the check logic from each affected skill, Category E tests that prove both native skills and raw Edit calls are gated identically.
- **Risk:** low. Hooks are already a first-class AADM primitive (`sprint_gate.py`). This refactor generalizes a pattern that's already shipped and proven.
- **Backward compatibility:** skill files can retain their in-prompt checks during migration — hooks are the source of truth, skill checks become redundant-but-harmless. Remove skill-level checks only after hook coverage is proven equivalent.

---

## §4 Graduation signal for opening the extension framework

§2 work does **not** start until **all** of the following are true:

- **3+ client engagements, ≥2 sprints each, zero method-level gaps.** AADM has run at least 3 client engagements through complete multi-sprint cycles (≥2 sprints each, end-to-end through `/sprint-close`) without a method-level gap requiring a rule change mid-engagement. "Gap" = the shipped method was insufficient and a new enforcement surface had to be added.
- **50 sprints-worth of data, ≥90% pass rates.** `events.jsonl` / `sessions_logged` across those engagements shows at least 50 closed-sprint events, with reconcile-pass rate ≥90% and sprint-close-lock rate ≥90%. The method is delivering structural enforcement consistently — not because a particular engineer or model is being careful.
- **At least one external demand signal.** At least one user outside Colaberry, asking unprompted, to combine AADM with a specific third-party skill bundle. Demand must be documented (GitHub issue, email, Slack thread) — not speculative.
- **§3 has landed.** Without the PreToolUse lifecycle-hook refactor, §2 is aspirational rather than structural.

If any of these are absent, **do not start §2 work.** Revisit quarterly.

### §4.1 Why the signal is strict

Opening §2 prematurely has three specific failure modes:

1. **Attribution confusion.** A user combines AADM + a third-party skill and succeeds; the method's contribution becomes indistinguishable from the plugin's. Base-method legitimacy becomes harder to defend externally.
2. **Surface-area inflation.** Every seam in §2 is a thing that has to be documented, tested, versioned, and supported forever. Adding it before there's proven demand is carrying capacity that isn't paying rent.
3. **Method drift risk.** If third-party skills declare `aadm_phases` before AADM's own phase model has been hardened by 3+ engagements, external skill authors pin to a model that later shifts — creating a compatibility-break problem that didn't need to exist.

The signal is strict because the downside of opening too early is worse than the downside of making users wait.

---

## §5 Non-goals

- **Not a skill marketplace.** AADM will not host, curate, or warrant third-party skills. The registry (§2.5) is convention-only.
- **Not a plugin SDK.** AADM will not ship a "how to write an AADM-compatible skill" framework with Python helpers or a testing harness. Compatibility is **declarative** (manifest) and **structural** (hooks), not SDK-driven.
- **Not a skill execution runtime.** AADM does not run skills — Claude Code runs skills. AADM gates the writes they produce. This distinction is load-bearing: AADM remains a method, not a platform.
- **Not a version-compatibility matrix.** Third-party skill authors declare `aadm_version: ">=X.Y"` in their manifest; AADM refuses to load skills whose declared range excludes the running version. AADM does not maintain a central list of "which skill versions work with which AADM versions."
- **Not opinionated about which third-party skills to use.** AADM's job is to gate the writes, not to recommend productivity stacks.

---

## §6 Cross-references

- `method/AI_Assisted_Development_Method_v3_2_1.md` — current base method; enforcement surfaces this roadmap extends.
- `tooling/scripts/sprint_gate.py` — the PreToolUse-hook shape that §3 generalizes.
- `tooling/scripts/dev_session.py` — current marker mechanism; a migration target for §3.
- `metrics/docs/METRICS.md` — event log spec that §2.3 extends with a third-party-skill contract.
- `handbook/Developer_Handbook.md` — user-facing narrative; gets an "Extending AADM" section once §2 ships.

---

## §7 Change log

| Date | Change | Author |
|---|---|---|
| 2026-04-23 | Document created. §3 queued as independent sprint. §4 graduation signal set. | Ram Kotamaraja (with Claude Code) |
