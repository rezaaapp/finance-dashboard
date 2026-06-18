# Omon Dashboard Pre-Production Technical Audit

Audit date: 2026-06-18  
Baseline: `main` at `6dcdcb9`  
Audit branch: `audit/pre-production-review`  
Mode: source read-only; documentation output only

## Executive Summary

Omon Dashboard has a coherent MVP architecture, broad workspace filtering, parameterized SQL, useful database constraints, and mature Smart Import recovery states. Frontend lint passes. However, it is **not production-ready for multi-user SaaS** because tenant identity is missing from the import deduplication keys, workspace-role authorization is inconsistent, and database/external spreadsheet writes are not protected by a durable consistency pattern.

The most exposed areas are Smart Import, legacy authentication compatibility, workspace configuration authorization, dashboard query fan-out, and migration governance. The highest business risk is silent transaction suppression or cross-workspace status mutation caused by globally unique fingerprints. The highest operational risk is a Google Sheet append succeeding while the surrounding database transaction later rolls back.

Production recommendation: **No-Go** until all Critical findings and the first five High findings are fixed and verified against a staging database.

## Pre-Check

### Repository State

```text
Active branch before audit: main
Active branch during audit: audit/pre-production-review
Working tree before audit: clean
main / origin/main: 6dcdcb9
Newest local branch by commit timestamp: main
```

Last 10 commits:

```text
6dcdcb9 Feat/blu pdf smart import (#30)
dbf0add Feat/budgeting alerts foundation (#29)
d4c045e fix: logout-in-mobile (#28)
b1758db Fix/hide amount chart axis (#27)
43a008d feat: add omon inquiry engine foundation (#26)
690ce51 feat: add omon icon and enhance styling with new animations and color scheme (#25)
d7a544e fix(auth): update Google auth callback routes for consistency (#24)
c46c137 fix(auth): persist google callback token handoff (#23)
08b2a32 feat(deploy): support replit single app staging (#22)
f97633d docs(deploy): add week 7 staging architecture plan (#21)
```

### Inventory

| Metric | Count |
|---|---:|
| Backend routes | 89 |
| Frontend pages | 8 |
| SQL migration files | 21 |
| Database tables declared | 19 |
| Backend automated test files | 2 |

Main structure:

```text
apps/landing/       public landing page
apps/web/           authenticated React/Vite dashboard
backend/app/api/    FastAPI routes
backend/app/services/
backend/app/repositories/
backend/app/imports/
backend/db/migrations/
backend/tests/
docs/
```

Tables:

```text
users, workspaces, workspace_members, workspace_configurations, user_tokens,
google_oauth_connections, google_sheet_sources, transactions,
transaction_classifications, classification_rules, sync_jobs,
workspace_insight_settings, workspace_invitations, budgets,
budget_category_ignores, import_jobs, import_draft_transactions,
import_transaction_registry, schema_migrations
```

Environment variable names are listed in `SECURITY_AUDIT.md`; values and local secrets were not copied.

## Verification Performed

- Frontend and landing ESLint: **passed**.
- Tracked secret-like filenames: no tracked `.env`, `.env_backup`, private key, or credential file found.
- Backend tests: **not executed** because the repository venv executable was denied by the sandbox and no system Python was available.
- Database runtime verification, migration dry run, query plans, OAuth callback, Google API calls, and browser QA: **Need Verification**.

## Critical Findings

### C-01 — Import deduplication is global across all workspaces

| Field | Detail |
|---|---|
| Severity | Critical |
| Area | Data Integrity / Multi-tenancy |
| File | `backend/db/migrations/015_add_import_transaction_registry.sql`; `backend/app/imports/repositories/fingerprint_registry_repository.py`; `backend/app/imports/repositories/import_repository.py` |
| Function | registry PK, `get_registered_transaction_fingerprint_statuses`, `get_existing_transaction_fingerprints` |
| Issue | `import_transaction_registry` is keyed only by `transaction_fingerprint`; `workspace_id` is absent and repository code explicitly discards it. |
| Root cause | Single-user fingerprint model was carried into a multi-workspace schema. |
| Impact | Approval or rejection in Workspace A can mark an identical transaction as existing/rejected in Workspace B. Valid transactions can disappear from review. |
| Recommendation | Add `workspace_id`, use `(workspace_id, transaction_fingerprint)` as PK/unique key, scope every registry read/write, and backfill with an explicit conflict policy. |
| Effort | 3–5 days including repair and tests |
| Priority | P0 |
| Sprint | Sprint 0 |

### C-02 — Final transaction fingerprint uniqueness is global

| Field | Detail |
|---|---|
| Severity | Critical |
| Area | Database / Data Integrity |
| File | `backend/db/migrations/015_add_import_transaction_registry.sql`; `backend/db/migrations/018_add_import_owner_and_canonical_fingerprint.sql`; `backend/app/imports/repositories/final_transaction_repository.py` |
| Function | unique indexes; `create_import_transactions`; `update_import_transaction_sync_status` |
| Issue | Both `import_transaction_fingerprint` and `canonical_fingerprint` are globally unique, and sync-status updates filter only by fingerprint. |
| Root cause | Tenant key omitted from identity constraints and mutations. |
| Impact | Cross-workspace insert conflicts, wrong row returned by `ON CONFLICT`, and sync status updates affecting another tenant. |
| Recommendation | Replace with partial unique indexes on `(workspace_id, fingerprint)` and add workspace filters to all mutation paths. |
| Effort | 3–5 days |
| Priority | P0 |
| Sprint | Sprint 0 |

### C-03 — Google Sheets append occurs inside an open database transaction

| Field | Detail |
|---|---|
| Severity | Critical |
| Area | Import / Distributed Consistency |
| File | `backend/app/api/imports.py`; `backend/app/imports/services/import_service.py` |
| Function | approve and retry endpoints; `approve_review_transactions` |
| Issue | DB rows and registry records are written, then a remote Google API append runs before the DB transaction commits. |
| Root cause | A local transaction is being used as if it could atomically include an external system. |
| Impact | Long-held DB connections/locks; sheet append may succeed and a later DB error may roll back, causing duplicate append on retry. |
| Recommendation | Use an outbox/idempotency design: commit approved DB rows first, enqueue append, append with a durable delivery key, then update delivery status in a separate transaction. |
| Effort | 5–10 days |
| Priority | P0 |
| Sprint | Sprint 0–1 |

### C-04 — Workspace member configuration authorization checks the wrong role

| Field | Detail |
|---|---|
| Severity | Critical |
| Area | Authorization |
| File | `backend/app/api/dashboard.py` |
| Function | `update_workspace_configuration` |
| Issue | The endpoint checks `current_user["role"] == "member"`, but user role is global (`user`/`super_admin`) while workspace role lives on the resolved workspace. |
| Root cause | Global account role and workspace membership role are conflated. |
| Impact | A normal workspace member can likely modify Google Sheet configuration for the workspace. |
| Recommendation | Authorize using `workspace["role"]` and a centralized workspace permission policy. Add owner/member integration tests. |
| Effort | <1 day plus tests |
| Priority | P0 |
| Sprint | Sprint 0 |

## High Findings

### H-01 — Legacy static bearer token bypasses user/workspace identity

`backend/app/auth.py` accepts `DASHBOARD_AUTH_TOKEN` on all `require_auth` routes and returns `True`. Dashboard endpoints then enter legacy behavior without a workspace. `/api/auth/login` returns the same shared token and labels the caller super admin. This prevents per-user revocation, accountability, tenant attribution, and safe SaaS operation.

Recommendation: disable static-token auth outside local development, issue short-lived user tokens, and remove the shared credential path from production.

### H-02 — Session token is stored in `localStorage`

`apps/web/src/App.jsx` and all API clients read the JWT from `localStorage`. Any XSS can exfiltrate a seven-day bearer token, including impersonation state.

Recommendation: use Secure, HttpOnly, SameSite cookies or a hardened short-lived access-token pattern with CSP and refresh rotation.

### H-03 — Upload has no explicit size limit or early PDF validation

`receive_upload` writes the entire upload to disk before enforcing a maximum size, content type, signature, page count, or decompression/resource limit.

Impact: disk exhaustion and parser resource DoS. Add reverse-proxy and application limits, PDF magic-byte validation, bounded page/text extraction, and quotas per user/workspace.

### H-04 — Temporary file deletion lacks directory containment

`delete_temp_import_file` unlinks the path stored in the database without confirming it resolves under `backend/output/imports/temp`.

Impact: a corrupted or malicious DB path could delete another writable file. Resolve and enforce containment before unlink.

### H-05 — Canonical uniqueness can be silently absent

Migration 018 creates `transactions_canonical_fingerprint_unique` only when no duplicate currently exists. If duplicates exist, migration succeeds but leaves the database without the expected guard.

Recommendation: fail migration with a diagnostic or run a mandatory repair migration before adding the constraint.

### H-06 — Dashboard performs high request fan-out, largely sequential

`fetchDashboardData` performs six sequential requests, three parallel requests, then up to seven more sequential premium requests. Analytics view repeats eight of those requests.

Impact: slow first render, high DB/API load, stale partial state, and poor mobile experience. Add aggregate/BFF endpoints, parallelize independent calls, cancel stale requests, and cache by workspace/period.

### H-07 — Analytics filters often make the date index unusable

`analytics_repository.py` repeatedly uses `extract(year/month from transaction_date)`. The existing B-tree indexes on `transaction_date` and `(workspace_id, transaction_date)` are less useful than range predicates.

Recommendation: use half-open date ranges and validate with `EXPLAIN (ANALYZE, BUFFERS)`.

### H-08 — Migration naming has duplicate numeric versions

There are three `012_*` files and two `013_*` files. The runner uses full filenames, so current ordering is deterministic, but numeric-version semantics are ambiguous for humans, external tooling, cherry-picks, and future branches.

Recommendation: adopt timestamp or globally unique monotonically increasing versions and add CI validation.

### H-09 — No database Row-Level Security defense

Tenant isolation relies entirely on application filters. One missing predicate becomes a data breach.

Recommendation: for production Supabase/PostgreSQL, add RLS or a restricted DB role plus tenant-context policies after the application key model is corrected.

### H-10 — Import history and review lists are unbounded

History loads all jobs for a workspace; review can load all new drafts. Large import volume will increase response size and rendering cost.

Recommendation: add cursor pagination and explicit maximum upload transaction count.

## Medium Findings

- `workspace_invitations.expires_at` is nullable and automatic expiry is absent.
- Invitation email delivery is not implemented, leaving discovery dependent on in-app polling.
- Registration is not a distinct product flow; Google login auto-provisions a user/workspace. Copy and onboarding should state this clearly.
- OAuth state nonce is signed but not persisted/consumed; replay protection relies mostly on Google’s one-time authorization code.
- `extract_email_from_id_token` disables signature and audience verification. It is a fallback in the connection flow and should be replaced with verified claims or userinfo-only behavior.
- JWT lifetime defaults to seven days with no revocation list, token version, or device/session management.
- Import draft `datetime` is stored as text, weakening validation, sorting guarantees, and timezone semantics.
- `user_tokens.refresh_token` is declared `NOT NULL` in migration 001 while OAuth code permits a missing refresh token. Existing schema evolution must be verified.
- Several status mutations are scoped only by job ID after an earlier ownership lookup. Defense-in-depth workspace predicates are preferable.
- Search uses offset pagination and a second full count query; this degrades on deep pages.
- Dashboard and configuration pages are 1,640 and 1,783 lines, respectively; import service is about 1,300 lines and analytics repository about 1,600 lines.
- Loading is often page-global; one failed dashboard request can replace the whole dashboard with an error.
- No frontend component/unit tests were found.
- Backend tests are concentrated in Smart Import and reconciliation; auth, workspace RBAC, budgets, analytics contracts, invitations, and sync concurrency lack equivalent coverage.
- Cleanup scheduler is process-local. Multiple replicas can execute cleanup concurrently; downtime pauses cleanup.
- Logging is inconsistent (`print` remains in finance service), and correlation/request IDs are absent.

## Low Findings

- Custom pathname routing makes route ownership and 404 behavior harder to reason about.
- Duplicate chart/component names exist in separate folders, increasing maintenance ambiguity.
- Environment aliases and legacy paths increase deployment configuration surface.
- Error copy mixes English and Indonesian.
- Some documented architecture statements are stale relative to the current implementation.

## Data Integrity Risk

| Risk | Rating | Notes |
|---|---|---|
| Duplicate transaction | Critical | Cross-workspace fingerprint constraints and external append retry window |
| Wrong owner | High | Owner is normalized text, not a stable workspace member/entity FK |
| Wrong category | Medium | Free-text category remains possible; classification and import category sources can diverge |
| Wrong workspace | Critical | Registry/unique keys omit workspace |
| Wrong period | Medium | PDF datetime is text in drafts; timezone policy is implicit |
| Spreadsheet mismatch | Critical | DB and sheet cannot commit atomically |
| Import inconsistency | Critical | External success can precede DB rollback |
| Sync inconsistency | High | Status update by fingerprint lacks workspace |
| Budget mismatch | Medium | Category uniqueness is case-sensitive; analytics category normalization may differ |

## Performance Risk

See `PERFORMANCE_AUDIT.md`.

## Architecture Risk

See `TECH_DEBT.md`.

## UX Risk

- Dashboard blocks on a large request chain.
- A single rejected request can hide otherwise valid widgets.
- Workspace fallback can select a primary workspace without an explicit user decision.
- Register is implicit and not explained as account provisioning.
- Invitation delivery and expiry are incomplete.
- Import approval allows DB success with sheet failure, but the mental model and recovery wording need stronger separation.
- Delete/disconnect/bulk budget actions require consistent confirmation review in browser QA.
- Need Verification: keyboard navigation, focus management, screen reader labels, chart alternatives, reduced motion, and mobile overflow.

## Security Risk

See `SECURITY_AUDIT.md`.

## Quick Wins (<1 day each)

1. Fix configuration authorization to use workspace membership role.
2. Add upload size and PDF signature checks.
3. Add temp-path containment.
4. Parallelize existing independent dashboard requests.
5. Add request cancellation on workspace/period changes.
6. Add migration filename uniqueness CI check.
7. Add workspace predicates to fingerprint status updates.
8. Replace unverified ID-token fallback.
9. Add pagination limits to import review/history.
10. Standardize user-facing error language.

## Long-Term Improvement for 1,000+ Users

- Durable job queue and outbox for sync/import/classification.
- Tenant-scoped keys plus RLS.
- Aggregate dashboard API and precomputed/materialized analytics.
- Short-lived sessions with rotation/revocation.
- Object storage for uploads with malware/content scanning.
- Central RBAC policy.
- Structured logs, traces, metrics, SLOs, audit log, and alerting.
- Idempotency keys for all mutation endpoints.
- Database load testing, query-plan regression tests, and partition/retention strategy.

## Recommended Timeline

### Sprint 0 — Data Audit and Safety

- Freeze import rollout.
- Measure duplicate fingerprints by workspace.
- Repair schema and constraints.
- Fix workspace RBAC.
- Define DB-vs-Sheet source-of-truth and reconciliation procedure.

### Sprint 1 — Critical Bug Fix

- Outbox/idempotent spreadsheet delivery.
- Static-token production removal.
- Upload and temp-file hardening.
- Cross-workspace integration tests.

### Sprint 2 — Performance Optimization

- Aggregate dashboard endpoint.
- Range-based date filters and query-plan review.
- Pagination and caching.

### Sprint 3 — UX Polish

- Partial widget errors, skeletons, confirmations, recovery copy, accessibility.

### Sprint 4 — Architecture Refactor

- Split god modules and introduce background worker boundaries.

### Sprint 5 — Test Coverage

- RBAC, OAuth, import consistency, budgets, analytics contracts, concurrency, browser E2E.

## Do Not Fix Yet

- Do not add more bank providers before import identity is tenant-safe.
- Do not introduce microservices before the outbox/job boundary is stable.
- Do not add AI classification providers before deterministic data contracts and observability are complete.
- Do not optimize minor component rendering before API/query fan-out is addressed.
- Do not create destructive down migrations for additive historical migrations.

## Final Score

| Area | Score | Reason |
|---|---:|---|
| Business Flow | 68 | Major flows exist, but registration, invite delivery, recovery, and source-of-truth semantics remain unclear |
| Architecture | 58 | Sensible layers, but large modules and synchronous external work weaken boundaries |
| Database | 52 | Good basic constraints/indexes; tenant keys and migration governance have critical gaps |
| Performance | 47 | High request/query fan-out and non-sargable date filters |
| Security | 50 | Workspace filtering is widespread, but static token, localStorage JWT, RBAC bug, no RLS, and upload risks remain |
| UX | 66 | Strong states in newer flows; dashboard blocking and incomplete collaboration flows remain |
| Maintainability | 55 | Very large modules, duplicated compatibility paths, limited tests |
| Scalability | 42 | Process-local jobs, synchronous sync, unbounded lists, no tenant DB guard |
| Production Readiness | 40 | Critical multi-tenant and distributed consistency blockers |
| **Overall** | **52/100** | Promising MVP, not yet safe for production SaaS |

