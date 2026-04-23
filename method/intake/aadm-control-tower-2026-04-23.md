# Intake — AADM Control Tower (internal webapp)

**Instructions to reader:** This intake was drafted applying AADM to the AADM tooling itself — dogfood. The "client" is Colaberry (the consultancy); the "engagement" is an internal product initiative that runs under **AADM Internal Product Mode**. The same rigor applies: stable IDs, failures-log cross-check, Section 7.5 enumeration, handoff readiness gate.

---

## Section 1: Engagement metadata `[REQUIRED]`

- **Client organization name:** Colaberry (internal product engagement; not a paying external client)
- **Intake date:** 2026-04-23
- **Intake interviewer(s):** Ram Kotamaraja (author); Claude Code (draft assistance)
- **Primary client contact (champion):** Ram Kotamaraja
- **Decision maker for acceptance:** Ram Kotamaraja — the tech lead running AADM across the 3 active engagements + pipeline. Acceptance test: does this actually change how the tech lead operates day-to-day?
- **Budget / engagement size:** Internal build. Engineer-time only through Stage 1.
  - **Stage 0 spend:** $0 (localhost, single user, Docker Compose). ~1 engineer-week to first running dashboard.
  - **Stage 1 spend:** ~$25–$50/month GCP bill (Cloud Run + Cloud SQL + Secret Manager) + Zitadel self-host or Zitadel Cloud. ~2 additional engineer-weeks to deploy. Portable to AWS/Azure/self-hosted at comparable cost.
  - **Stage 2 spend:** TBD pending commercialization decision (Q1 — answered: internal first, eventual product, so Stage 2 is on the roadmap).
- **Target start date:** 2026-04-28 (Monday after this intake closes)
- **Target first-delivery date:** **Stage 0 v0** within 2 weeks of start — a localhost read-only portfolio dashboard against the 3 existing engagements (no auth, no cloud, no cost). Stage 1 cloud deploy follows only if Stage 0 graduation criteria (§11.2) are met.
- **Deadline driver:** The 3 active engagements are running AADM today with no portfolio view; pipeline engagements start in the next 4–6 weeks and will compound the pain. Earlier is better, but no external compliance date.
- **Engagement type:** Internal product — AADM Internal Product Mode. **Stage nomenclature refined for this initiative** (nomenclature documented here; mapping back to the canonical Mode stages below):
  - **Stage 0: localhost single-user.** Ram runs it on his laptop. Goal: validate the product idea before paying any cloud cost. Maps to AADM Internal Product Mode's **exploration** stage.
  - **Stage 1: cloud deploy, Colaberry-internal multi-user.** GCP reference deployment, portable containers. Goal: validate multi-user and operational patterns. Maps to **validation**.
  - **Stage 2: external tenants / open-source productization.** Maps to **commercialization**.
  - Each stage has a graduation signal in §11. Stage 0 → Stage 1 is the first gate; failing it halts the initiative before cloud spend.

---

## Section 2: The client organization `[REQUIRED]`

- **Industry and what the client actually does:** Colaberry is a consultancy that delivers software engineering services to enterprise clients, primarily in the data/AI space. The engagements are multi-sprint, often multi-month, and involve stable teams (tech lead + 1–3 engineers per engagement). AADM is the method Colaberry uses internally to run these engagements.
- **Company size:** [UNKNOWN — need to confirm] Roughly small-to-mid consultancy; for this intake's purposes, the relevant scale is "3 concurrent active engagements + pipeline of ~2–4 more over the next quarter."
- **Where the users are:** Users are Colaberry internal staff (tech leads, PMs, engineers). Geographic distribution: [UNKNOWN — need to confirm] — assume distributed, which affects deployment choice (cloud-hosted over on-prem LAN).
- **Regulatory environment:** None directly applicable to the control tower itself at v0. **Transitive risk:** individual Colaberry client engagements may be under SOC 2, HIPAA, or client-specific data-handling clauses. Any data the control tower caches from those engagements' repos (failures logs, intake documents) may inherit that classification. See §7.5 — Compliance.
- **Existing technology stack:** Each engagement repo runs AADM: Python 3.11 stdlib scripts (`reconcile.py`, `sprint_close.py`, `gap.py`, `dev_session.py`, `state-check.py`, `metrics.py`), a PreToolUse hook (`sprint_gate.py`), markdown artifacts, JSONL event log. GitHub hosts the repos. No existing central control plane.
- **Prior engagements with vendors for this problem:** None. This is the first attempt. Jira / Linear / GitHub Projects have been considered and rejected — they're PM tools, not method-aware; they don't read `Satisfies:` lines or gap-analysis output; integrating them would create the "parallel source of truth" failure mode.

---

## Section 3: The problem `[REQUIRED]`

- **Stated request, verbatim in client's own words:**
  > "I am wondering if a webapp can be created to help users methodically adopt this system with a proper control tower and tasks followup."
  Then, when asked about engagement count:
  > "We have a 3 client engagements going on and few in pipeline."

- **What triggered this conversation happening now?** AADM has shipped its structural gates in the last 2 weeks (`/dev-test`/`/dev-impl` split, `sprint_gate.py`, `/gap`, elicitation completeness pass). The method is now rich enough to operate across multiple engagements, and the consultancy is hitting portfolio-level pain that didn't exist when it was 1 engagement.

- **Three to five specific examples of the pain:**
  1. Tech lead has to `cd` into each of the 3 repos and run `python3 state-check/scripts/state-check.py` individually to know the state of each engagement. There is no "show me all 3 at once" command today.
  2. PM / partner has no non-terminal way to answer "is client B at risk this week?" Without that, engagement escalations are reactive rather than proactive.
  3. Cross-engagement failures-log learning is manual. When starting a new engagement in a domain where a past engagement had an incident, the engineer must remember that incident existed and grep the specific past repo. Prevention rules that *could* compound across engagements instead stay siloed — the exact compounding-memory benefit AADM promises.
  4. Pipeline engagements spin up with hand-drafted intakes every time. The §7.5 completeness pass is easy to skim past in the middle of a client kickoff when the tech lead is typing into a markdown file in a rush.
  5. Metric signal is lost today — `events.jsonl` accumulates per repo but there is no view of "gate-pass rate across the consultancy," "rework-rate trend across engagements," or "which engagement is burning the most sessions per task."

- **Anti-examples — things the client explicitly does NOT want:**
  1. **No "close sprint" button, no "mark task complete" button, no workflow mutation in the UI of any kind.** The method's gates run locally (or in CI); the webapp observes, never operates. This is explicitly ruled out.
  2. **Not a Jira / Linear replacement.** No "assigned to," "due date," "priority," or "blocked by" fields. The markdown IS the task state; adding a parallel state model would rot the `Satisfies:` chain.
  3. **Not a required control plane.** Today a team can clone, commit, CI, close sprints with zero network calls. The webapp must not become a dependency; engagements must remain fully operable even if the webapp is down.
  4. **No metric thresholds (healthy/high/low labels) at v0.** Per `metrics/docs/METRICS.md`, the ranges haven't been earned by real data yet. The webapp shows raw counts only; interpretation stays human.
  5. **No notifications, no alerting, no background watcher at v0.** No scheduled cron jobs, no email/Slack alerts, no "notify me when sprint closes" features. Refresh is on-demand (user-triggered) only. The staleness indicator + refresh button is the UX contract. Proactive signal paths re-open as a Stage 2 conversation, not before.
  6. **No cloud-locked services.** No GCP-specific components (Pub/Sub, Firestore, BigQuery, Identity Platform, etc.) without a clean cloud-agnostic abstraction behind them. The eventual open-source positioning requires portability across GCP, AWS, Azure, and self-hosted from day one of Stage 1. See Section 6 → Portability Principles.

- **What they've tried so far:**
  - **Per-repo `state-check.py`** (shipped, works, but only one repo at a time).
  - **Per-repo `reconcile.py`** (shipped, CI-enforced, but no rollup).
  - **Per-repo `gap.py`** (shipped last week, produces `<INITIATIVE>_GAP_ANALYSIS.md` per repo, but no cross-engagement view of orphans).
  - Nothing has been tried at the portfolio level — that's the gap this initiative addresses.

- **What does success look like 6 months after delivery?**
  - Tech lead checks the dashboard **at least daily, unprompted**, across the active engagements. If they don't, the pain wasn't real enough to sustain the tool — that's a Stage 1 kill signal.
  - PM / partner uses the RAG view in weekly engagement-review meetings.
  - At least **one documented "avoided incident"** attributed to cross-engagement failures-log search (i.e., "engineer about to start work on domain X found a prevention rule from client A's failures log and applied it, avoiding the bug").
  - At least **one pipeline engagement** is kicked off using the Phase 0 intake form (v1), with the resulting intake committed to the new repo.
  - Cross-engagement metrics have surfaced at least **one calibration insight** that would change the method itself (e.g., "rework rate above X correlates with sprints that skipped `/gap`").

---

## Section 4: Users and stakeholders `[REQUIRED]`

- **Primary users — who will actually use the system day to day:**
  - **Tech leads** (count: starts at 1; grows with engagement count). Daily. Technical, terminal-comfortable, but want at-a-glance portfolio view.
  - **Engineers on each engagement** (count: ~3–6 across the 3 active engagements). Ad-hoc use — mostly cross-engagement failures-log search when starting work in a new domain.

- **Secondary users:**
  - **PMs / partners** — weekly, during engagement-review meetings. Non-terminal. Need RAG status and drill-in, nothing more.
  - **Client principals** — [UNKNOWN — need to ask Q2] do client principals ever see a version of this? If yes, that's a scope expansion (client-branded projections, client-facing ACLs), probably v2+.

- **Buyer vs. user:** Same person at v0 (Ram). Future: if this becomes a product sold to other consultancies, buyer (their leadership) differs from user (their tech leads).

- **Other stakeholders affected:**
  - Engagement clients (indirectly) — their data (failures-log content, intake documents) is what the control tower caches. They aren't users but their confidentiality is the hard constraint. See §7.5 — Security and §7.5 — Compliance.
  - Future engineers onboarded to Colaberry — the control tower is part of their context. Affects training material scope (see §7.5 — Training).

- **Who is against this project internally?** [UNKNOWN — need to confirm] — unlikely to have explicit opposition since it's an internal tool, but worth flagging: engineers may resist if the dashboard starts being used as a performance scoreboard rather than a heads-up display. That's a framing risk, not a stakeholder-opposition risk.

---

## Section 5: Integrations and dependencies `[REQUIRED]`

- **Systems this must integrate with:**
  - **GitHub** (hosts all engagement repos). Integration: either clone-on-schedule using a Colaberry service-account token, or GitHub webhooks on `push` to `main`. See Q3.
  - **AADM scripts in each repo** (`state-check.py`, `reconcile.py`, `gap.py`, `metrics.py`). Integration: shell out, read `--json` output. No direct Python import — the control tower runs against whatever script version the repo has, which is the right way to avoid version coupling.
  - **Authn provider** — answered (Q4). **Stage 0**: `AUTH_MODE=dev` bypass, no external integration. **Stage 1 prod**: Zitadel (self-hosted on the chosen cloud, or Zitadel Cloud). OIDC-compliant → swappable with Keycloak/Authentik/Okta/Auth0 without code changes. **Stage 2+ authz**: thin internal RBAC module (~200 lines) covers Stage 1; Permit.io or equivalent evaluated only when actual policy complexity arrives (non-engineer policy editors, cross-tenant rules, audit compliance).

- **Systems this replaces or will eventually replace:** None. The webapp adds a view; it does not replace scripts, skills, or repos.

- **External data sources:** Only the repos themselves. No third-party APIs at v0.

- **External destinations:** None at v0. The dashboard displays; it does not export. (Notifications are post-v0 if needed.)

- **SSO / identity:** Answered (Q4). Stage 0 uses `AUTH_MODE=dev` bypass (no SSO). Stage 1 prod uses Zitadel (OIDC). Configuration responsibility in Stage 1: whichever Colaberry team runs internal-tool auth — the Zitadel integration is one-time config, rotatable like any OIDC client.

- **Deployment target:** Answered (Q5). **Stage 0:** `localhost` via `docker compose` on Ram's machine — FastAPI + Next.js + Postgres, `AUTH_MODE=dev`, repo sources pointed at local filesystem directories. Zero cloud spend. **Stage 1:** cloud-agnostic containers. Initial reference deployment on GCP (Cloud Run + Cloud SQL + Secret Manager). Second reference deployment on AWS (ECS/Fargate + RDS + Secrets Manager) shipped before Stage 2 to prove portability. Terraform modules + `docker-compose.yml` for self-hosted delivered at Stage 2. **Stage 2:** any container platform; bring-your-own Postgres + bring-your-own OIDC is the minimum install.

- **Post-delivery operator:** Stage 0 = Ram on his own laptop (support model: he owns it). Stage 1 = builder continues as operator until a designated ops owner is named [see Q6]. Stage 2 = depends on productization shape (Q10).

---

## Section 6: Non-functional requirements `[REQUIRED]`

### 6.0 Portability principles `[NON-NEGOTIABLE]`

These apply from Stage 1 onward, and their abstractions must be respected from Stage 0 code so that Stage 1 is a deploy, not a rewrite.

- **Containers everywhere.** Every service ships as a Docker image. Stage 0 is `docker compose up`; Stage 1 is "any container runtime" (Cloud Run, Fargate, Azure Container Apps, Fly.io, Render, DigitalOcean App Platform, K8s, self-hosted Docker). No service is allowed to depend on a platform-specific SDK without a pluggable abstraction behind it.
- **Postgres-wire-compatible DB only.** `DATABASE_URL` is the single config surface. Any managed Postgres (Cloud SQL, RDS, Azure Database, Supabase, Neon) or self-hosted works identically.
- **OIDC for authn.** Zitadel is the Stage 1 reference; any OIDC provider (Keycloak, Authentik, Okta, Auth0, Dex) is a drop-in swap. No vendor-specific SDK in the auth path.
- **S3-compatible object storage** (if/when needed for repo-tarball caching or artifact storage). GCS, S3, Azure Blob, Cloudflare R2, and MinIO all expose the S3 API — one client library covers all of them.
- **Env-var-only config.** No hardcoded Application Default Credentials flows, no cloud-specific metadata-server lookups baked into code. 12-factor throughout.
- **Multi-tenancy-ready schema.** Every table that holds engagement-scoped data carries a `tenant_id` FK from day one. Stage 0 has one tenant (Colaberry) — the column is a constant. Stage 2 (external tenants) becomes a seed script + middleware change, not a schema migration.
- **Plugin-agnostic data contract.** The webapp reads stable JSON outputs from named AADM scripts and recognized event-log entries. It does **not** parse skill prompt files or introspect `.claude/` internals. Any third-party skill, user-custom skill, or future AADM skill that conforms to the output contract becomes visible automatically; anything else is invisible without rendering support. This keeps the webapp decoupled from the skills layer and makes AADM's plug-and-play posture (documented in the method docs) the webapp's default too.
- **Explicit non-commitments.** No Pub/Sub, Firestore, BigQuery, Identity Platform, Cloud Tasks, or other GCP-specific managed services at any stage without a named cloud-agnostic fallback. Same rule for AWS-specific and Azure-specific services.

### 6.1 Performance expectations

- Dashboard page load: under 2 seconds for portfolio view of up to 20 engagements, using cached data.
- Engagement detail page: under 1 second, using cached data.
- **Refresh latency (on-demand):** when a user clicks "Refresh" or lands on a page whose data is >1hr stale, the backend pulls fresh state (subprocess or remote git fetch + script run) and returns within 30 seconds per engagement.
- **No background watcher.** No scheduled cron, no webhook-driven sync at v0. The UX contract is: every data view shows "Last refreshed: N min ago" + a refresh button, with auto-refresh only on page load if data is older than 1 hour. This preserves $0 idle cost on Cloud Run-style scale-to-zero and is the honest observer posture (the dashboard literally cannot drift from the repos because it doesn't watch them).
- None of these are SLA numbers — they're "good enough that tech leads actually use it" numbers.

- **Availability / uptime expectations:**
  - Best-effort internal tool. No SLA at v0. Business-hours availability (9–6 local time for the team's time zone) is the aspiration.
  - If the tool is down, engagements continue to operate normally — that's a hard requirement (see §3 anti-examples #3).

- **Security and compliance:**
  - **At rest:** Any cached data (failures-log content, intake documents, metric events) encrypted at rest on the VM disk.
  - **In transit:** HTTPS only.
  - **Authn:** SSO-gated. No anonymous access.
  - **Authz:** Per-engagement ACL — an engineer assigned to engagement A sees engagement A's data; an engineer on engagement B sees B's. Cross-engagement search (failures-log) is scoped to the engagements the user is assigned to. See §7.5 — Security.
  - **Audit logging:** Every data read is logged with user + engagement + timestamp. Retained for [UNKNOWN — see Q7] days.

- **Data residency:** [UNKNOWN — see Q8] — depends on individual client engagement contracts. If any active client has an EU/US-only residency clause, the control tower must honor it (easiest path: deploy in the matching region; hardest path: shard per region, which is out of scope for v0).

- **Scale expectations:**
  - v0: 3 active engagements, ~10 concurrent users, ~50 sprints of history.
  - 6-month horizon: 8–10 engagements, ~20 concurrent users, ~200 sprints of history.
  - If the webapp becomes a product: unbounded. Out of scope for v0 architecture decisions — rebuild is cheaper than premature scaling.

- **Support model post-delivery:**
  - v0: Builder also operates. Best-effort. Break/fix via internal Slack.
  - Post-v0: [UNKNOWN — see Q6].

---

## Section 7: Constraints `[REQUIRED]`

- **Non-negotiable technical constraints:**
  - Must read JSON outputs from AADM scripts — must not re-implement parsing of markdown artifacts. If the script schema changes, the webapp inherits it automatically; no drift.
  - **Cloud portability.** No GCP-specific, AWS-specific, or Azure-specific managed service without a cloud-agnostic abstraction. See §6.0 Portability Principles — non-negotiable because open-source positioning depends on it.
  - **Stage 0 localhost-first.** No cloud provisioning or spend before Stage 0 graduation criteria (§11.2) are met. Validate the product idea at $0 before paying the first cloud bill.
  - **Stack answered (Q9).** Python 3.11 + FastAPI backend; Next.js (TypeScript, React) frontend; Postgres 15+ via Docker in Stage 0 and managed Postgres in Stage 1+. API contract: OpenAPI schema generated from FastAPI → `openapi-typescript` generates TS types for the frontend. Single source of truth for the API; type-safe across the language boundary from day one.
  - **Three abstraction seams are load-bearing from Stage 0:** `RepoSource` interface (LocalFilesystemRepoSource vs. GitHubAppRepoSource), `AuthProvider` interface (DevBypassAuth vs. OIDCAuth), `SecretSource` interface (env vars vs. cloud secret manager). If Stage 0 conveniences leak past these seams — hardcoded paths, assumed-admin user objects, env-var-only secret reads — Stage 1 becomes a refactor rather than a deploy. Category E architecture-guard tests enforce the seams.

- **Non-negotiable process constraints:**
  - **This webapp's own development must run under AADM.** Design doc with stable IDs; sprints; `/dev-test` + `/dev-impl`; `/sprint-close`. The first test of the method is whether it works for the team building it.
  - Any feature that mutates repo state must be explicitly reviewed and rejected unless it can be proven to run through the existing scripts (e.g., a `/prd` form that produces a markdown file the engineer commits is fine; a "close sprint" button that writes `.lock` server-side is not).
  - Per-engagement ACL must be tested (Category E architecture-guard tests) from the first sprint.

- **Licensing constraints:** Open-source dependencies welcomed. If commercial licenses are needed, flag early. IP: Colaberry retains full ownership (internal build).

- **Timeline constraints that cannot flex:** None hard-imposed. See §1 target dates.

- **Known political constraints:** [UNKNOWN — see Q10] — if partners debate whether this becomes a commercial product now vs. later, that decision affects architecture (multi-tenancy, branding, auth flows). Surface early.

---

## Section 7.5: Completeness pass `[REQUIRED]`

Walked end-to-end. Every category below has either a captured requirement or an explicit "N/A because X."

- **Functional — primary user journeys:** Captured §3 and §4. Primary journey: tech lead opens portfolio dashboard → sees RAG list → drills into red/yellow engagement → sees specific flag → navigates to underlying repo in their terminal.
- **Functional — admin / operator journeys:** Someone must add a new engagement to the control tower when a pipeline engagement goes active. This is currently unspecified — to be added as a requirement in the design doc. Likely form: "admin pastes a repo URL; control tower clones it, runs scripts, surfaces in dashboard."
- **Functional — error-state UX:** What does the dashboard show when a repo is inaccessible (token expired, repo deleted, network issue, script timeout)? Concrete requirement needed: graceful degradation — show last-known-good state with staleness indicator; never show a false green.
- **Non-functional — performance:** Captured §6.
- **Non-functional — availability / SLA:** Captured §6 (best-effort, no SLA at v0).
- **Non-functional — scale:** Captured §6.
- **Security — authn / authz:** Authn via SSO (Q4). Authz via per-engagement ACL (see §6 and below). Two roles at v0: `engagement-member` (can see assigned engagements) and `portfolio-admin` (can see all engagements, can add/remove engagements). Avoid finer-grained RBAC until demonstrated need.
- **Security — data classification:** **Load-bearing.** Cached data includes client-confidential content (failures-log entries may describe client systems; intake documents contain SOW-adjacent info). Classification: treat all cached engagement data as client-confidential. No data from engagement A visible to engineer on engagement B unless both have explicit staffing.
- **Security — encryption in transit and at rest:** Captured §6. Algorithms: industry standard (TLS 1.3 in transit; AES-256 at rest on disk).
- **Security — audit logging:** Captured §6. Specific events logged: login, engagement detail view, cross-engagement search query, admin action (adding/removing engagements, adding/removing user ACLs).
- **Security — secrets management:** GitHub token for cloning/webhook validation, SSO client secret, cookie-signing key. Stored in the cloud provider's secret manager (AWS Secrets Manager / GCP Secret Manager), never in the repo. Rotation: 90-day for the GitHub token; on-breach for others.
- **Security — third-party / supply chain:** Standard open-source diligence. Semgrep runs on the webapp's own repo (dogfood). No banned vendors known.
- **Compliance — regulatory frameworks in scope:** None directly on the control tower. **Transitive:** if a Colaberry client is under HIPAA/SOC 2 and their failures log contains PHI/regulated data, caching it in the control tower extends scope. Mitigation: policy that failures-log entries do not contain regulated data (this should already be AADM discipline — failures logs describe patterns and prevention rules, not incident payloads). Confirm via design doc.
- **Compliance — data residency / cross-border:** See §6 and Q8. Default: match the region of the most restrictive client.
- **Compliance — retention and deletion:** When an engagement ends, what happens to its cached data? Requirement: on engagement decommission (explicit action by portfolio-admin), cache is purged within 30 days; audit logs about that engagement retained for 1 year per Colaberry's internal audit policy [UNKNOWN — confirm Q11].
- **Observability — logging:** Webapp's own structured logs go to stdout → cloud provider's log aggregation. Retained 90 days.
- **Observability — metrics:** Webapp's own operational metrics (request latency, sync success rate, DB size). Not to be confused with the AADM metrics the webapp displays.
- **Observability — tracing:** N/A because v0 is a monolith on one VM; tracing adds no information.
- **Observability — alerting:** Minimal at v0. One alert: sync job has not succeeded in >1 hour for any engagement. Channel: builder's Slack DM.
- **Failure modes — what happens when each external dependency is down:**
  - GitHub unreachable: sync job fails; dashboard shows last-known-good with staleness indicator.
  - SSO provider down: users cannot log in. Graceful: show a maintenance page, not a stack trace.
  - Script crash in a repo (e.g., `state-check.py` throws): surface the error in that engagement's detail page with the stderr; do not hide.
- **Failure modes — data loss tolerance:** RPO: 24 hours. All cached data can be regenerated by re-running scripts against the source repos. Loss of audit logs is more painful — RPO 1 hour for the audit log table.
- **Failure modes — recovery time:** RTO: 24 hours for the dashboard. Engagements continue operating independently — tech leads fall back to per-repo commands.
- **Failure modes — disaster recovery:** Nightly snapshot of the SQLite file + audit log to object storage. Restore drill quarterly.
- **Data — sources of truth:** The engagement repos are the sole sources of truth. The webapp is a cache. Any conflict resolves to "trust the repo, re-sync the cache." No write-back under any circumstance.
- **Data — migration from existing system:** None — there is no existing system to migrate from. First-time onboarding of the 3 active engagements is a one-time bulk clone + sync at deployment.
- **Data — schema evolution policy:** The webapp's own DB schema evolves via standard migrations. The AADM script JSON schemas are external and stable (documented in each script's README). If AADM adds a new flag or event type, the webapp tolerates it (displays it generically) until explicitly updated to render it. **Plugin-agnostic posture:** the webapp's only contract is with the JSON outputs of named scripts (`state-check.py --json`, `reconcile.py --json`, `gap.py --json`, `sprint_close.py --json`) and recognized `events.jsonl` entries. Third-party skills, user-custom skills, and future AADM skills all become visible via the same contract; the webapp does not inspect `.claude/skills/*.md` files or distinguish "AADM skill" from "third-party skill" when rendering activity. This preserves AADM's plug-and-play posture at the dashboard layer.
- **Operations — who deploys:** Stage 0 = Ram on his own laptop (`docker compose up`). Stage 1 = builder deploys via Terraform / container-platform CLI; post-Stage-1 operator handoff [see Q6].
- **Operations — who is on call:** No one at Stage 0 or Stage 1. Best-effort. If the tool is down on a weekend, it stays down until Monday. Alerting (and therefore paging) is a Stage 2 conversation.
- **Operations — runbooks:** Stage 0: a one-page README covering `docker compose up/down`, how to point it at a new local repo directory, how to reset the local DB. Stage 1: deployer README covering how to add an engagement, how to add a user in Zitadel, how to rotate the GitHub App key, how to restore from a snapshot, how to redeploy on a different cloud (prove portability).
- **Operations — capacity planning:** N/A at Stage 0 (one user, localhost, unconstrained laptop resources). Stage 1: three active engagements + ~20 users on the smallest Cloud Run / Cloud SQL tiers is ample. Revisit when engagement count crosses 30 or user count crosses 50.
- **Accessibility:** WCAG 2.1 AA for the dashboard. PMs are a target user and may include colleagues using assistive tech.
- **Internationalization / localization:** English-only for internal Colaberry use. N/A for other locales because users are Colaberry internal staff; revisit if this becomes a product sold externally.
- **Documentation deliverables:** (1) User README for tech leads / PMs / engineers; (2) Operator README for the deployer; (3) Architecture-decision records in `docs/decisions/` per AADM.
- **Training and handover:** N/A for v0 because the primary user (Ram) is also the primary builder. When a second tech lead onboards, a 30-min walkthrough + the user README.
- **Decommissioning / exit:** If Colaberry decides to stop using the control tower, all engagement data continues to live in the source repos (the webapp is a cache). Shutdown: purge the webapp's DB and volumes; nothing downstream breaks.

---

## Section 8: What the client gave us `[OPTIONAL but valuable]`

- **RFP or original request document:** The conversation thread that produced this intake. (Transcript lives in the Claude Code session log.)
- **Screenshots, wireframes, mockups:** None yet. To be produced during Phase 0b as low-fidelity sketches before the first sprint.
- **Existing system documentation:** The AADM repo itself (`method/`, `handbook/`, `state-check/DOCUMENTATION.md`, `tooling/README.md`, `metrics/docs/METRICS.md`) is the authority for what the webapp needs to display.
- **Sample data files:** The 3 active engagement repos are the live sample set.

---

## Section 9: Open questions `[REQUIRED to list; may remain unanswered]`

**Answered during intake (2026-04-23):**

- **Q1 — ANSWERED:** Internal-first with eventual productization. Stage 0 localhost single-user → Stage 1 Colaberry-internal cloud deploy → Stage 2 external tenants / open-source. **Architectural consequence:** Stage 1 is built single-tenant but every engagement-scoped table carries a `tenant_id` FK from day one. Stage 2 tenancy becomes a config flag + seed script, not a schema rewrite. Branding/white-labeling deferred to Stage 2.
- **Q4 — ANSWERED:** Stage 0 dev bypass (`AUTH_MODE=dev`). Stage 1 prod: Zitadel for authn (OIDC-compliant, self-hostable or Zitadel Cloud) + thin internal RBAC module (~200 lines) for authz. Stage 2: evaluate Permit.io (or OPA / Oso) **only when** actual policy complexity arrives — non-engineer policy editors, cross-tenant differential rules, audit-compliance requirements. Do not pre-optimize.
- **Q5 — ANSWERED:** Stage 0 `localhost` via Docker Compose. Stage 1 cloud-agnostic containers with GCP (Cloud Run + Cloud SQL) as the initial reference deployment; AWS (ECS/Fargate + RDS) as a proof-of-portability second deployment before Stage 2. Stage 2 ships Terraform modules (GCP/AWS/Azure) + `docker-compose.yml` for self-hosted. See §6.0 Portability Principles.
- **Q9 — ANSWERED:** Python 3.11 + FastAPI backend; Next.js (TypeScript) dashboard. OpenAPI-generated TS types across the boundary (`openapi-typescript`). Rationale: Python matches the AADM scripts (reuse / import directly where needed); TS dashboard preserves a future path to client-side interactivity if Stage 2 grows an action surface.

**Deferred / non-blocking (remain open after intake close):**

- **Q2:** Do client principals ever see a projection of this (client-facing dashboard)? — Owner: Ram + partners — Blocks: scope of UI components; ACL model. Deferred to post-Stage-1 ("no for Stage 0 and Stage 1").
- **Q3:** Clone-on-schedule vs. webhook-driven sync? — **Superseded** by the on-demand refresh decision (§6.1). Neither cron nor webhook is used at Stage 0 or Stage 1. Revisit if a Stage 2 alerting/digest use case arrives.
- **Q6:** Post-Stage-1 operator — builder continues, or handoff to a designated ops owner? — Owner: partners — Blocks: nothing immediately; answer before Stage 1 → Stage 2 gate.
- **Q7:** Audit-log retention duration — 90 days, 1 year, indefinite? — Owner: Colaberry internal audit / legal — Blocks: Stage 1 design-doc acceptance criterion. Default assumption: 90 days until answered.
- **Q8:** Do any of the 3 active clients have data-residency clauses that restrict where their cached data can live? — Owner: Ram (review each engagement SOW) — Blocks: Stage 1 deployment region choice. Default assumption: US region until answered.
- **Q10:** Is there a target date to productize this? — Owner: partners — Blocks: Stage 1 → Stage 2 gate timing. Default assumption: no externally-imposed date; gated on §11.3 graduation signals.
- **Q11:** Is there an existing Colaberry internal audit policy for retention / deletion that the webapp should conform to? — Owner: Colaberry internal — Blocks: nothing urgent; confirm before Stage 1 go-live.

---

## Section 10: Your team's context `[REQUIRED]`

- **Engagement team:** Ram (tech lead + sole engineer for v0, with Claude Code as primary collaborator). Additional engineers [UNKNOWN] if v0 lands and Stage 2 is greenlit.
- **Tech lead for this engagement:** Ram.
- **Similar work your team has done before:** The AADM scripts and skills themselves. This is the same tech-lead building meta-tooling he uses daily — unusually high domain expertise for this engagement.
- **Prevention rules from `docs/failures/` that apply:** [None yet — this is a fresh engagement repo; the AADM repo's own `docs/failures/` should be reviewed for lessons from prior AADM tooling work before the design doc is drafted.]
- **Skills gaps on this engagement:** Webapp UX design (tech-lead is strong on backend / method tooling, less so on frontend polish). If PM-usability becomes a sprint-critical constraint, consider contracting a designer for a one-off review.
- **Risk signals from this intake:**
  - Single-engineer team at v0 — bus factor is 1.
  - Builder = primary user = decision-maker. Feedback loop is tight (good) but lacks outside scrutiny (bad — might build features only Ram benefits from).
  - "Internal tool that might become a product" is the classic scope-ambiguity risk. Decide Q1 early or accept the re-architecture cost if the answer changes later.

---

## Section 11: Initial risk assessment `[REQUIRED]`

- **Top 3 risks, ranked:**
  1. **Per-client isolation bug leaks client A's failures-log data to an engineer on client B.** High impact (trust loss, potential contractual breach), medium likelihood if tested well from day 1. Mitigation: Category E architecture-guard test from sprint 1 asserting that `get_engagement_data(user, engagement_id)` raises for unauthorized combinations; manual security review before any multi-user access.
  2. **Scope creep into operational UI ("can we add a 'close sprint' button?").** High impact (the entire anti-goal), high likelihood (social pressure). Mitigation: this anti-example written into CLAUDE.md of the webapp repo as a never-do rule; architecture designed so the UI has no code path that writes to repos at all (not even a disabled button).
  3. **Method drifts faster than the webapp tracks.** Medium impact (dashboard shows outdated information), medium likelihood. Mitigation: webapp reads JSON outputs, not internal data structures. Adding a new state-check flag is invisible to the webapp until someone explicitly chooses to render it — and the webapp's "unknown flag" rendering path shows it generically rather than crashing.

- **What's the most likely reason this engagement fails?** Ram builds v0, uses it for 2 weeks, discovers he already has enough muscle memory for `state-check.py` that the dashboard doesn't change his behavior. Stage 1 → Stage 2 gate fails because the pain wasn't actually 10x the fix cost. Outcome: v0 stays deployed, gets minimal use, eventually bit-rots. Mitigation: be ruthless at the gate check — if Ram isn't opening the dashboard 5x/week unprompted after 2 weeks of use, kill it; don't sink Stage 2 engineering into a tool the builder himself doesn't need.

- **What would cause us to walk away?**
  - Partners decide to productize immediately (skip Stage 1 and jump to commercial launch). Walk away rather than accept that forced scope expansion.
  - A second, better tool emerges from the AADM community / GitHub issue tracker between now and v0 (unlikely but check before writing code).

### §11.2 Stage 0 → Stage 1 graduation signal (localhost → cloud)

Stage 0 is complete — and cloud investment earns its first dollar — when **all** of the following are true:

- Ram uses the localhost dashboard **at least 5x/week unprompted for 2 consecutive weeks**.
- At least one concrete moment where Ram wanted someone else to look at the dashboard (PM asking about engagement status, wanting to share a link instead of a screenshot).
- 2–3 UI shape iterations have been completed and the model feels stable enough to bother deploying.
- No crashes or data-corruption incidents in the last 7 days of actual use.

If at the 4-week mark Ram has not opened the dashboard 5x/week, **kill the initiative**. Do not deploy to cloud. The pain wasn't real enough to earn the cloud bill, and no amount of productization will rescue a tool its own builder doesn't use.

### §11.3 Stage 1 → Stage 2 graduation signal (internal cloud → external product)

Stage 1 ends and Stage 2 (external productization) begins when **all** of the following are true:

- At least one PM / partner uses the RAG view in **at least 2 engagement-review meetings** (unprompted — meaning Ram didn't open it for them).
- At least one documented "avoided incident" or "caught issue earlier than usual" anecdote attributable to the tool (e.g., cross-engagement failures-log search surfaced a prevention rule).
- At least one cross-engagement metric insight that would change AADM the method itself (e.g., "rework rate above X correlates with skipped `/gap`"). This is the commercialization-readiness signal: the tool has produced learnings that wouldn't have surfaced without it.
- Portability proof: the same container build has been deployed successfully on **at least two** of {GCP, AWS, Azure, self-hosted}. No open-source claim without it.
- Q6 (post-deploy operator), Q7 (audit retention), Q8 (data residency), Q10 (productization target), Q11 (Colaberry audit policy) are all answered.

If any of these are absent at the 12-week mark post-Stage-1, hold at Stage 1 — do not push to commercialization. Retrospective required before the next Stage 1 → Stage 2 review.

---

## Section 12: Commercial / contractual `[OPTIONAL at intake, REQUIRED before Phase 0 closes]`

N/A for v0 — internal engagement. If productization (Q1) resolves to "yes," a separate commercial SOW is drafted at that point. SOW acceptance criteria for v0 translate into internal milestones, tracked by the Stage 1 graduation signal in §11.3.

---

## Section 13: Handoff readiness `[REQUIRED before this intake is "closed"]`

- [x] All `[REQUIRED]` sections filled. Remaining `[UNKNOWN]` markers (Q2, Q6, Q7, Q8, Q10, Q11) are explicitly deferred in §9 with default assumptions documented — non-blocking for Stage 0 or first-sprint scope.
- [x] Section 7.5 completeness pass walked end to end — every category has a captured requirement or explicit "N/A because X."
- [x] Open questions list populated and owners assigned (11 questions; 4 resolved during intake, 7 deferred with defaults).
- [ ] Tech lead sign-off that the intake reflects what was actually discussed. (Pending Ram's final read.)
- [ ] Client champion review. (Same person as tech lead in this engagement — sign-off conflates.)
- [ ] SOW in draft form. **N/A** for Stage 0 and Stage 1 internal engagement; revisit at Stage 1 → Stage 2 gate if productization proceeds.
- [x] Initial risk assessment done (§11).
- [x] Intake document committed to the AADM repo at `method/intake/aadm-control-tower-2026-04-23.md` as a dogfood artifact. When the webapp's own repo is bootstrapped, this file also becomes the canonical `docs/intake/` entry there.

**Intake is ready to close.** Q1, Q4, Q5, Q9 (the four originally-blocking questions for first-sprint scope) are all answered. Q2, Q6, Q7, Q8, Q10, Q11 are deferred with explicit default assumptions that do not block Stage 0 or first-sprint implementation. Next step is design-doc drafting (`docs/aadm-control-tower.md`) once this intake file is moved into the bootstrapped webapp repo.

---

## Section 14: How to use this intake as LLM input

When ready, hand this intake to Claude Code with the prompt block from the template (Section 14 of the standard template). Expected output:

- A 10–15 page `docs/aadm-control-tower.md` design document with stable IDs (§1, §2, …, D1, D2, …, Q1, Q2, …).
- An ambiguity pass producing ~10–15 questions (many of which overlap with Section 9 of this intake — those are already captured).

**Proposed Stage 0 first-sprint scope (5–7 tasks):**

1. Repo bootstrap — monorepo scaffold: `backend/` (FastAPI + Pydantic), `frontend/` (Next.js + TypeScript), `docker-compose.yml` (Postgres), `.env.example`, initial `.claude/` skills directory consuming AADM's own templates.
2. `RepoSource` abstraction + `LocalFilesystemRepoSource` implementation — reads a configured list of local directories, subprocesses out to `state-check.py --json` and `reconcile.py --json` in each, returns parsed structs.
3. `AuthProvider` abstraction + `DevBypassAuth` implementation — always returns `{user: ram@colaberry.com, role: admin}`, wired into FastAPI dependency injection for every protected endpoint.
4. Postgres schema (with `tenant_id` FK on every engagement-scoped table from day one, even though Stage 0 has one hardcoded tenant) + migration tooling (Alembic).
5. Backend REST endpoints: `GET /engagements` (portfolio list), `GET /engagements/:id` (detail), `POST /engagements/:id/refresh` (on-demand refresh with rate limit).
6. OpenAPI schema export + `openapi-typescript` generation of frontend TS types.
7. Next.js dashboard: portfolio list page + engagement detail page. Each page shows "Last refreshed: N min ago" + a refresh button. Auto-refresh only if >1hr stale.

**Out of scope for Stage 0 first sprint:** Zitadel integration (Q4 Stage 1), GCP deployment (Q5 Stage 1), GitHub App integration (Stage 1 — Stage 0 reads from local filesystem directly), any alerting/notifications, cross-engagement failures-log search (second sprint), RAG color coding (second sprint after raw data view validates).

---

## Intake completion summary

- **Date intake opened:** 2026-04-23
- **Date intake closed:** 2026-04-23 (same-day close after Q1/Q4/Q5/Q9 were resolved through live dialogue)
- **Total time invested in intake:** ~2 hours across two drafting sessions, Claude-Code-assisted.
- **Number of open questions at intake close:** 7 (0 blocking Stage 0 or first sprint; all 7 have explicit default assumptions documented in §9).
- **Questions resolved during intake:** 4 (Q1 productization intent, Q4 authn stack, Q5 deployment target, Q9 language/framework).
- **Questions deferred with defaults:** 7 (Q2, Q3 superseded, Q6, Q7, Q8, Q10, Q11).
- **Link to resulting design doc:** `method/design-docs/aadm-control-tower-stage-0.md` (draft, co-located with this intake in the AADM repo until the webapp repo is bootstrapped).
- **Link to SOW:** N/A (internal engagement through Stage 1; SOW revisited at Stage 1 → Stage 2 commercialization gate).
