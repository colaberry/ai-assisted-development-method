# Design Doc — AADM Control Tower, Stage 0 (localhost)

| | |
|---|---|
| **Initiative** | AADM Control Tower — portfolio-level dashboard over active AADM engagements. |
| **Stage scoped by this doc** | **Stage 0 only** (localhost, single user, `AUTH_MODE=dev`, zero cloud spend). Stage 1 (cloud-internal) and Stage 2 (external tenants / OSS) have their own design docs, authored at their respective graduation gates. |
| **Intake** | [`internal-mode/engagements/aadm-control-tower/intake.md`](./intake.md) — this doc cites intake IDs as `intake §X`. |
| **Mode** | AADM Internal Product Mode (dogfood). Mode stages documented in [`internal-mode/Internal_Product_Mode.md`](../../Internal_Product_Mode.md). |
| **Created** | 2026-04-23 |
| **Author** | Ram Kotamaraja (with Claude Code) |
| **Status** | **Draft** — pending ambiguity-pass Qn resolution (§11) and Ram's sign-off. |

> **Reader's note on stable IDs.** Every section gets `§X.Y`. Every decision gets `Dn`. Every question resolved during authorship gets `Qn`. **Once assigned, IDs do not change** — they propagate into sprint PRDs, task `Satisfies:` lines, and `/gap` audit reports. The Qn numbering in this doc continues from the intake: Q1/Q4/Q5/Q9 are already resolved at intake close; this doc adds Q12+ for design-phase ambiguities.

---

## §1 Intent

### §1.1 What Stage 0 is

A single-user, localhost webapp that gives Ram an at-a-glance **portfolio view** of the 3 active AADM engagements, rendered from the existing AADM scripts' JSON outputs. Runs entirely on his laptop via `docker compose up`. No cloud, no SSO, no tenant model exposed in the UI, no multi-user concerns, no alerting.

### §1.2 What Stage 0 is not

- **Not a cloud deploy.** Stage 1 decisions (Cloud Run vs. ECS, Zitadel integration, managed Postgres) are explicitly out of scope for this doc.
- **Not a product.** Stage 0's job is to **prove the pain is real** (intake §3 success criteria: "tech lead checks the dashboard ≥5x/week unprompted"). If Stage 0 fails that, cloud work never starts — see Stage 0 → 1 graduation signal (intake §11.2).
- **Not a skills-integration layer.** The webapp reads stable JSON outputs (`state-check.py --json`, `reconcile.py --json`, `gap.py --json`, `events.jsonl`). It does not parse skill prompts or introspect `.claude/` internals (intake §6.0 plugin-agnostic data contract).
- **Not an operational UI.** No "close sprint" button, no task-mutation affordances (intake §3 anti-example #1).

### §1.3 Why Stage 0 matters disproportionately

If Ram — the builder, primary user, and decision-maker — does not use the localhost dashboard after 2 weeks, the portfolio-pain hypothesis is falsified at $0. That is the most expensive signal the initiative can produce, and it must be produced **before** any cloud dollars are spent. Stage 0 is the hypothesis-validation phase dressed up as a product increment.

---

## §2 Primary user journeys

### §2.1 Daily portfolio glance (primary — drives success metric)

1. Ram opens `http://localhost:3000/`.
2. Portfolio page renders a list of the 3 active engagements, each showing: name, last-refreshed timestamp, sprint state (active sprint id or "between sprints"), last reconcile result, count of open gap findings, count of events in the last 7 days.
3. If any field is stale >1h, it auto-refreshes on page load. Otherwise, a "Refresh" button triggers an explicit pull.
4. Ram scans the list in <10 seconds. If anything looks off, he clicks into the engagement detail page.

**Success signal:** this journey is completed unprompted ≥5x/week for 2 consecutive weeks (intake §11.2).

### §2.2 Engagement detail drill-in

1. From portfolio, Ram clicks an engagement row.
2. Detail page shows: full `state-check` output, latest `reconcile` status, open gap-analysis items (if `/gap` has run), last 20 entries from `events.jsonl` reverse-chronological.
3. "Refresh" button available per-engagement.
4. No edit affordances anywhere on the page.

### §2.3 Cross-engagement failures-log search (deferred from Stage 0 sprint v1)

Intake §10 risk signals flag this as a wanted-but-not-load-bearing feature. Deferred to Stage 0 sprint v2 — see §12 Out of Scope.

---

## §3 Architecture overview

### §3.1 Component diagram (Stage 0)

```
┌─────────────────────────────────────────────────────────────┐
│ Ram's laptop                                                │
│                                                             │
│  ┌──────────────────┐      ┌──────────────────────────────┐ │
│  │  Next.js         │ HTTP │  FastAPI                     │ │
│  │  (frontend)      │◀────▶│  (backend, Python 3.11)      │ │
│  │  :3000           │      │  :8000                       │ │
│  │                  │      │                              │ │
│  │  - portfolio     │      │  - RepoSource abstraction    │ │
│  │  - detail        │      │  - AuthProvider abstraction  │ │
│  │  - (refresh UI)  │      │  - SecretSource abstraction  │ │
│  └──────────────────┘      └──────────────────────────────┘ │
│         ▲                            │                      │
│         │                            │ subprocess           │
│         │                            ▼                      │
│         │               ┌──────────────────────────────┐    │
│         │               │ Local repo checkouts         │    │
│         │               │  ~/engagements/client-a/     │    │
│         │               │  ~/engagements/client-b/     │    │
│         │               │  ~/engagements/client-c/     │    │
│         │               │ (python3 state-check.py etc) │    │
│         │               └──────────────────────────────┘    │
│         │                            │                      │
│         │                            ▼                      │
│         │               ┌──────────────────────────────┐    │
│         │               │ Postgres 15 (container)      │    │
│         │               │  - cached script outputs     │    │
│         │               │  - tenant_id FK on every row │    │
│         └───────────────│  - audit_log (append-only)   │    │
│                         └──────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### §3.2 Request lifecycle

1. Browser → Next.js → calls FastAPI (same machine, CORS open to `localhost:3000` only).
2. FastAPI endpoint authn-check via `AuthProvider.current_user()` → in Stage 0, `DevBypassAuth` returns `{user: "ram@colaberry.com", role: "portfolio-admin", tenant_id: "colaberry"}` unconditionally.
3. FastAPI reads from Postgres cache. If row timestamp older than TTL (§8), trigger refresh via `RepoSource.refresh(engagement_id)` synchronously.
4. `RepoSource.refresh` subprocesses `python3 <engagement_repo>/state-check/scripts/state-check.py --json`, parses stdout, upserts into Postgres with fresh timestamp.
5. FastAPI returns JSON to Next.js. Next.js renders.

### §3.3 Local filesystem layout (Stage 0 dev convenience)

```
~/engagements/
  client-a/         # git clone of engagement A repo
  client-b/
  client-c/
```

Paths configured via `REPO_SOURCE_LOCAL_DIRS=~/engagements/client-a,~/engagements/client-b,~/engagements/client-c` in `.env`. No symlinks, no read-only bind mounts required — Stage 0 assumes Ram owns the directories and trusts his own filesystem.

---

## §4 Load-bearing abstractions (non-negotiable from Stage 0 code)

These three seams are what make Stage 0 → Stage 1 a **deploy, not a rewrite**. If any of them is bypassed ("I'll just read the path directly from an env var right here"), Stage 1 becomes a refactor sprint. Category E architecture-guard tests enforce each seam from sprint v1.

### §4.1 `RepoSource` interface

```python
class RepoSource(Protocol):
    def list_engagements(self) -> list[Engagement]: ...
    def refresh(self, engagement_id: str) -> EngagementSnapshot: ...
    def get_snapshot(self, engagement_id: str) -> EngagementSnapshot: ...
```

**Stage 0 impl:** `LocalFilesystemRepoSource` — reads from `REPO_SOURCE_LOCAL_DIRS`, subprocesses out to `state-check.py --json` etc.

**Stage 1 impl (future, not in this doc):** `GitHubAppRepoSource` — clones-on-demand to a tmpfs, runs the same scripts, caches to Postgres. Drop-in behind the same interface.

**Category E guard:** no file I/O outside `RepoSource` subclasses. Enforced via a `grep` test that any `open(` or `subprocess` call in `backend/` other than inside `backend/repo_source/` fails the build.

### §4.2 `AuthProvider` interface

```python
class AuthProvider(Protocol):
    def current_user(self, request: Request) -> User: ...
    def require_role(self, user: User, role: str) -> None: ...
```

**Stage 0 impl:** `DevBypassAuth` — always returns `ram@colaberry.com` with `portfolio-admin` role. Wired via FastAPI dependency injection on every protected endpoint. `AUTH_MODE=dev` is the only accepted value at Stage 0.

**Stage 1 impl (future):** `OIDCAuth` — validates bearer tokens against Zitadel (or any OIDC IdP). Same interface.

**Category E guard:** no endpoint handler reads `request.headers['x-user']` or any other auth-shaped header directly. All auth flows through `AuthProvider`. Enforced via test that greps every `@app.<method>` handler and asserts `user: User = Depends(auth_provider.current_user)` is present.

### §4.3 `SecretSource` interface

```python
class SecretSource(Protocol):
    def get(self, key: str) -> str: ...
```

**Stage 0 impl:** `EnvVarSecretSource` — reads from `os.environ`, loaded from `.env` via `python-dotenv`.

**Stage 1 impl (future):** `GCPSecretManagerSecretSource`, `AWSSecretsManagerSecretSource`, etc. Same interface.

**Category E guard:** no `os.environ[...]` or `os.getenv(...)` outside `backend/secret_source/`. Forces all secrets through the seam even when env vars are the only impl.

### §4.4 Decision D1 — no code-side multi-cloud abstractions beyond these three seams at Stage 0

**D1.** Stage 0 ships **only** `RepoSource`, `AuthProvider`, `SecretSource`. No `ObjectStorage`, no `MessageQueue`, no `Cache`, no `BackgroundJob` interface. Reasoning: Stage 0 has exactly zero use cases for object storage, queues, or background jobs (intake §6.1 on-demand refresh, §7.5 no alerting). Building abstractions for work we're not doing is surface-area inflation. Stage 1 introduces them **only if** the Stage 1 design doc requires them.

**Rationale for listing D1 here:** the temptation during Stage 0 build will be to "pre-abstract" more seams "because we'll need them anyway." D1 says no — three seams is the floor; four or more requires a Stage 1 design-doc amendment.

---

## §5 Data model

### §5.1 Schema — all Stage 0 tables

```sql
-- Every engagement-scoped table carries tenant_id from day one (intake §6.0).
-- Stage 0 has one hardcoded tenant; this is not optional even at single-user scale.

CREATE TABLE tenants (
  id          TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- Seeded: ('colaberry', 'Colaberry')

CREATE TABLE users (
  id          TEXT PRIMARY KEY,       -- email at Stage 0; opaque id at Stage 1
  tenant_id   TEXT NOT NULL REFERENCES tenants(id),
  role        TEXT NOT NULL,          -- 'engagement-member' | 'portfolio-admin'
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE engagements (
  id          TEXT PRIMARY KEY,       -- slug: 'client-a', 'client-b', ...
  tenant_id   TEXT NOT NULL REFERENCES tenants(id),
  display_name TEXT NOT NULL,
  repo_url    TEXT,                   -- NULL at Stage 0 (local filesystem)
  local_path  TEXT,                   -- Stage 0 only; NULL at Stage 1+
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  decommissioned_at TIMESTAMPTZ       -- retention countdown starts from this
);

CREATE TABLE engagement_user_acl (
  tenant_id     TEXT NOT NULL REFERENCES tenants(id),
  engagement_id TEXT NOT NULL REFERENCES engagements(id),
  user_id       TEXT NOT NULL REFERENCES users(id),
  granted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (engagement_id, user_id)
);

CREATE TABLE engagement_snapshots (
  tenant_id     TEXT NOT NULL REFERENCES tenants(id),
  engagement_id TEXT NOT NULL REFERENCES engagements(id),
  source        TEXT NOT NULL,        -- 'state-check' | 'reconcile' | 'gap' | 'events'
  payload       JSONB NOT NULL,       -- raw script stdout, parsed
  refreshed_at  TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (engagement_id, source)
);

CREATE TABLE audit_log (
  id          BIGSERIAL PRIMARY KEY,
  tenant_id   TEXT NOT NULL REFERENCES tenants(id),
  user_id     TEXT NOT NULL,
  action      TEXT NOT NULL,          -- 'view_portfolio' | 'view_engagement' | 'refresh' | ...
  engagement_id TEXT,                 -- NULL for portfolio-level actions
  ts          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  extra       JSONB
);
CREATE INDEX idx_audit_ts ON audit_log(ts DESC);
CREATE INDEX idx_audit_tenant ON audit_log(tenant_id, ts DESC);
```

### §5.2 Decision D2 — `tenant_id` FK even at single-tenant Stage 0

**D2.** Every engagement-scoped table carries `tenant_id TEXT NOT NULL REFERENCES tenants(id)`. Stage 0 has one tenant row (`colaberry`); it is not nullable, not defaulted, not added later. Rationale: intake §6.0 multi-tenancy-ready schema is non-negotiable because retrofitting `tenant_id` into live tables is a migration, not a config flip. The cost at Stage 0 is one extra column and a seed row. The cost of waiting is a Stage 2-blocking migration on live data.

### §5.3 Decision D3 — snapshot cache uses JSONB, not typed columns

**D3.** `engagement_snapshots.payload` is `JSONB`, not a typed column-per-field breakdown. Rationale: the AADM scripts' JSON schemas evolve (intake §7.5 schema-evolution policy). Typed columns would force a migration every time a script adds a field; JSONB lets the webapp render new fields generically without a schema change. Cost: queries that need to filter on payload fields use `payload->>'field'` indexing — acceptable at Stage 0's scale (3 engagements).

---

## §6 Backend API

### §6.1 Endpoints (Stage 0)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/health` | none | Liveness probe for `docker compose` |
| `GET` | `/api/engagements` | `portfolio-admin` OR `engagement-member` (filtered) | Portfolio list, cached rows |
| `GET` | `/api/engagements/:id` | ACL check | Engagement detail, cached |
| `POST` | `/api/engagements/:id/refresh` | ACL check + rate limit (1/min/engagement) | Force-refresh a single engagement |
| `POST` | `/api/engagements/refresh-all` | `portfolio-admin` + rate limit (1/5min) | Refresh every engagement the caller can see |
| `GET` | `/api/audit` | `portfolio-admin` | Recent audit log (Stage 0 — for debugging ACL; Stage 1 → operator surface) |

### §6.2 Response contract

All `/api/*` endpoints return JSON. OpenAPI schema generated from FastAPI → `openapi-typescript` generates TypeScript types consumed by the frontend (intake §7 non-negotiable constraint). No hand-written API types on the frontend — type drift is structurally prevented.

### §6.3 Error model

```json
{
  "error": {
    "code": "engagement_not_found",
    "message": "Engagement 'client-x' does not exist or caller lacks access.",
    "correlation_id": "01J..."
  }
}
```

`engagement_not_found` is returned for both "does not exist" AND "caller lacks ACL" at Stage 0, to avoid leaking engagement existence to unauthorized callers. This is a paranoid default — Stage 0 has one user so it's theoretical, but it's the posture Stage 1 will need anyway.

---

## §7 Frontend

### §7.1 Pages

- `/` — portfolio list. Table: engagement | last-refreshed | active sprint | reconcile status | open gaps | events 7d. Row click → `/engagements/:id`.
- `/engagements/:id` — engagement detail. Tabs: State Check | Reconcile | Gap Analysis | Events. Refresh button per-tab and per-page.

### §7.2 Staleness UX contract (non-negotiable)

Every data view renders:
- "Last refreshed: `N min ago`" in the page header.
- A manual "Refresh" button.
- Auto-refresh on page load if last refresh > 1h.

This is intake §6.1's honest-observer posture: the dashboard literally cannot show phantom-green because it doesn't watch the repos, it pulls.

### §7.3 Decision D4 — no client-side routing magic, no SSR data fetching at Stage 0

**D4.** All data fetching on the frontend is plain `useEffect` + `fetch` against `/api/*`. No Next.js `getServerSideProps`, no React Server Components, no SWR / React Query at Stage 0. Rationale: Stage 0 is a single-user tool with negligible traffic; complex data-fetching frameworks add Stage-1-deploy-time questions ("where does SSR run? Cloud Run cold starts? SSG?") that we don't need to answer yet. Revisit at Stage 1 design doc if the tab-switching UX degrades.

---

## §8 Refresh semantics

### §8.1 Cache TTL

- Snapshot is considered stale when `NOW() - refreshed_at > 1 hour`.
- Stale reads on `GET /api/engagements/:id` trigger a synchronous refresh before returning. First request pays the latency (intake §6.1: ≤30s per engagement); subsequent requests within the TTL are instant.

### §8.2 Explicit-refresh rate limits

- `POST /api/engagements/:id/refresh` — max 1/min per engagement, returns 429 otherwise.
- `POST /api/engagements/refresh-all` — max 1/5min globally, returns 429 otherwise.

### §8.3 Decision D5 — no background refresh, no scheduler, no worker

**D5.** Stage 0 has **zero** background processes. No APScheduler, no Celery, no cron inside the container, no webhook consumer. Every refresh is caller-initiated (user click or TTL-triggered on a user request). Rationale: intake §6.1 explicit anti-example — the honest-observer posture is load-bearing, not incidental. It also preserves $0 idle cost when Stage 1 lands on scale-to-zero serverless (Cloud Run / Fargate-Spot). A scheduler would defeat scale-to-zero.

---

## §9 Non-functional surface (Stage 0 only)

Intake §6 is the authority; this section captures only what Stage 0 code must respect.

- **Perf:** portfolio load <2s cached; refresh <30s/engagement (§8.1). No other perf commitments.
- **Availability:** Ram's laptop. No SLA. `docker compose down` = "the app is down." Fine.
- **Security:** HTTPS **not required** at Stage 0 (localhost only). Cookie secret still required (DevBypassAuth still issues a session cookie for CSRF posture; value is constant but signed). TLS becomes mandatory at Stage 1.
- **Audit logging:** every `GET /api/engagements`, `GET /api/engagements/:id`, `POST */refresh`, and admin action writes one row to `audit_log`. Stage 0 retention = forever (Ram's laptop, no volume concerns). Stage 1 introduces retention policy (intake Q7 deferred).
- **Observability:** backend logs to stdout → `docker compose logs`. No structured log shipping at Stage 0.

---

## §10 Decisions (D-index)

| ID | Decision | §ref |
|---|---|---|
| **D1** | Stage 0 ships exactly 3 abstraction seams (`RepoSource`, `AuthProvider`, `SecretSource`); no pre-abstracted object storage / queue / cache / worker interfaces. | §4.4 |
| **D2** | Every engagement-scoped table carries `tenant_id` FK from day one, even at single-tenant Stage 0. | §5.2 |
| **D3** | `engagement_snapshots.payload` is JSONB, not typed columns. | §5.3 |
| **D4** | No SSR / React Server Components / SWR at Stage 0; plain `useEffect` + `fetch`. | §7.3 |
| **D5** | No background refresh / scheduler / worker at Stage 0; all refreshes are caller-initiated. | §8.3 |
| **D6** | Errors collapse "not found" and "not authorized" into a single `engagement_not_found` response to prevent existence-leaking. | §6.3 |
| **D7** | Frontend TS types are generated from the FastAPI OpenAPI schema; never hand-written. | §6.2 |

**ID stability rule:** once a D-number is written in this table, it never changes. Re-decisions produce a **new** Dn with a `Supersedes: Dm` annotation — never an edit-in-place.

---

## §11 Resolved questions (Q-index)

Continued from the intake's Q-index. Intake Q1/Q4/Q5/Q9 are already resolved there; this doc adds Q12+.

| ID | Question | Resolution | §ref |
|---|---|---|---|
| **Q12** | Do we need a `Cache` abstraction at Stage 0 in case we swap Postgres for Redis later? | **No.** Postgres is the cache. See D1. | §4.4 |
| **Q13** | Should the portfolio page show aggregated RAG color at Stage 0, or raw counts only? | **Raw counts only.** Intake §3 anti-example #4: no health labels without earned thresholds. RAG revisited at Stage 0 sprint v2 once ≥3 weeks of data exists. | §7.1 |
| **Q14** | Should `POST /refresh-all` be fire-and-forget or synchronous? | **Synchronous at Stage 0.** 3 engagements × 30s = 90s worst case, tolerable for a rare admin action. Stage 1 revisits once N grows. | §8.2 |
| **Q15** | Do we need CSRF protection at Stage 0 if there's one user on localhost? | **Yes.** DevBypassAuth still issues a signed session cookie; CSRF token middleware runs normally. Rationale: Stage 1 lights up CSRF requirements, and testing the middleware against a dev flow from day one catches integration bugs at $0 cost. | §9 |

### §11.1 Unresolved (new deferred questions raised during design)

- **Q16:** What does the engagement-detail "Events" tab show when `events.jsonl` doesn't exist in a repo (e.g., an engagement that predates events logging)? Default: empty-state message "Events logging not yet enabled for this engagement." Ram to confirm. Non-blocking for sprint v1.
- **Q17:** Should Stage 0's `audit_log` writes be synchronous (in the request path) or deferred to a background buffer? Stage 0 default: synchronous. Revisit if p99 regression observed. Non-blocking.

---

## §12 Out of scope for Stage 0

Explicit deferrals, each marked with the target stage where they re-enter scope:

- **Cross-engagement failures-log search** → Stage 0 sprint v2 (after portfolio+detail prove usage).
- **RAG color coding on portfolio** → Stage 0 sprint v2 (after Q13-dependent data accrues).
- **Zitadel OIDC integration** → Stage 1.
- **Cloud deployment (GCP / AWS / Azure / self-hosted)** → Stage 1.
- **GitHub App-based repo access** → Stage 1.
- **Multi-tenant UI (tenant switcher, per-tenant branding)** → Stage 2.
- **Alerting / notifications / digests** → Stage 2 (with explicit re-review of intake §3 anti-example #5).
- **Skill-manifest / plugin-aware rendering** → gated on extension-framework roadmap §4 graduation signal; see [`docs/roadmap/extension-framework.md`](../../../docs/roadmap/extension-framework.md).

---

## §13 Sprint v1 handoff

Proposed sprint v1 scope (mirrors intake §14 with design-doc IDs attached):

| # | Task | Satisfies |
|---|---|---|
| 1 | Repo bootstrap — monorepo scaffold (`backend/`, `frontend/`, `docker-compose.yml`, `.env.example`, AADM `.claude/` skills). | §3.1, §3.3 |
| 2 | `RepoSource` abstraction + `LocalFilesystemRepoSource` impl + Category E guard. | §4.1, D1 |
| 3 | `AuthProvider` abstraction + `DevBypassAuth` impl + Category E guard. | §4.2, D1 |
| 4 | `SecretSource` abstraction + `EnvVarSecretSource` impl + Category E guard. | §4.3, D1 |
| 5 | Postgres schema + Alembic migration for §5.1 tables + seed row for `colaberry` tenant. | §5.1, D2 |
| 6 | Backend endpoints `/health`, `GET /api/engagements`, `GET /api/engagements/:id`, `POST /api/engagements/:id/refresh` with ACL + rate limit. | §6.1, §8.2, D6 |
| 7 | OpenAPI schema export + `openapi-typescript` codegen step in `frontend/`. | §6.2, D7 |
| 8 | Next.js portfolio page + engagement detail page + staleness UX (§7.2). | §7.1, §7.2, D4 |

**Out of scope for v1 (carries to v2):** `/api/engagements/refresh-all`, `/api/audit`, cross-engagement search, RAG, Q13 resolution.

**Sprint v1 Category E guard suite (must exist before v1 `/sprint-close`):**

- No file I/O in `backend/` outside `backend/repo_source/`.
- No `os.environ` reads outside `backend/secret_source/`.
- No endpoint handler without `Depends(auth_provider.current_user)`.
- No hand-written TS types in `frontend/` under a `types/api/` path (must be generated).

---

## §14 Cross-references

- `internal-mode/engagements/aadm-control-tower/intake.md` — intake (upstream source of truth for problem, users, constraints).
- `method/AI_Assisted_Development_Method_v3_2_1.md` — parent method; design-doc conventions from §1 and §3 of this doc derive from §3 of the method doc.
- `internal-mode/Internal_Product_Mode.md` — mode governing this initiative; Stage 0/1/2 nomenclature in this doc maps to exploration/validation/commercialization stages there.
- `docs/roadmap/extension-framework.md` — roadmap for third-party skill integration; §5 non-goals of that doc constrain what this webapp is allowed to render per §1.2 of this doc.
- `tooling/scripts/sprint_gate.py`, `state-check/scripts/state-check.py`, `reconcile.py`, `gap.py` — the scripts whose JSON outputs this webapp consumes.

---

## §15 Pre-handoff checks (run before sprint v1 `/prd`)

Per method §3 (design-document pre-sprint checks):

- [ ] **Spec-lint.** No vague words (fast, intuitive, seamless, robust, leverage, optimize). This doc's pass is pending Ram's read.
- [ ] **Ambiguity pass.** Qn enumeration (§11) is the current pass output. Additional ambiguities raised during Ram's read become Q18+.
- [ ] **Failures-log cross-check.** Read `docs/failures/` in this repo (and any present in each engagement repo) and flag any past failure in a domain this initiative touches (webapp sec, data caching, script-subprocess patterns). Prevention rules restated in this doc or explicitly marked N/A.
- [ ] **Ram sign-off.** Tech lead (who is also the client champion) reads end-to-end and either approves or lists changes.

**Design doc is not handed to `/prd` until all four boxes are checked.**

---

## §16 Change log

| Date | Change | Author |
|---|---|---|
| 2026-04-23 | Draft created; Qn enumeration seeded from intake; D1–D7 captured. | Ram Kotamaraja (with Claude Code) |
