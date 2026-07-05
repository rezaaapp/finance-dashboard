# Replit + Supabase UAT Deployment Readiness Review

**Project:** Omon Dashboard  
**Baseline:** v0.9.6 - UAT Tester Provisioning  
**Review date:** 2026-07-05  
**Scope:** Static, audit-only review of the repository. No deployment, database connection, migration execution, seed, reset, or destructive command was performed.

## Executive conclusion

**Decision: NO-GO for external UAT in the current baseline.**

The single-app Replit architecture is present and internally coherent: Vite can build in same-origin mode, FastAPI can serve the built SPA, the server binds to `0.0.0.0`, Supabase-compatible PostgreSQL access is implemented, OAuth callbacks exist, and UAT provisioning is transactional. However, the environment model makes the intended combination impossible without a code/config correction:

1. `backend/app/config.py` accepts only `APP_ENV=local-dev|local-prod`.
2. Supabase is permitted only for `local-prod`.
3. UAT provisioning is blocked for `local-prod` and allowed for `local-dev|dev|uat`.
4. `dev` and `uat` cannot pass application startup validation.
5. `local-prod` requires `BACKEND_PORT=8001`, while Replit normally supplies its own `PORT`.
6. The Replit runbook does not set `APP_ENV`, `ENV_PROFILE`, `DB_TARGET`, or `BACKEND_PORT`, so its documented Supabase startup path defaults to `local-dev` and rejects the remote database host.

The Google Sheets permission contract is also unresolved: the Replit guide requests `spreadsheets.readonly`, but the backend contains a `worksheet.update(...)` path. Read-only access is suitable for importing a tester-owned sheet, but not for writing approved results back to it.

## 1. Environment configuration

### Observed behavior

| Area | Repository behavior | UAT assessment |
| --- | --- | --- |
| Profile loading | `ENV_PROFILE`, then `APP_ENV`, then `local-dev`; dotenv profile files are loaded only for `local-dev` and `local-prod`. | No deployable `uat` profile. Hosted secrets still work through process environment, but validation rejects `uat`. |
| `APP_ENV` | Strictly limited to `local-dev` and `local-prod`. | **Blocker** for a semantically correct UAT environment. |
| Database target | `local-dev` requires `postgres-local`; `local-prod` requires `supabase`. Host validation reinforces this. | Supabase cannot be combined with provisioning-safe `local-dev`. |
| Backend port | Derived from `BACKEND_PORT`, then `PORT`; validation requires exactly 8000 for `local-dev` and 8001 for `local-prod`. | **Blocker** when Replit injects another port. Binding itself is correct (`0.0.0.0`). |
| Frontend production build | Requires `VITE_API_URL`/`VITE_API_BASE_URL`, unless `VITE_API_MODE=same-origin`. | Correct for the recommended single-app Replit mode. Build-time variable must be present during build, not merely runtime. |
| Production fallback | Frontend throws if a production build has neither API URL nor same-origin mode. | Good fail-closed behavior. |
| Local behavior | `local-dev`: local PostgreSQL, port 8000. `local-prod`: Supabase simulation, port 8001. | Useful locally, but not a dev/UAT/prod deployment model. |
| `prod` behavior | No accepted `prod` value. | Production semantics are represented by `local-prod`, which is confusing and prevents a clean promotion path. |

### Required verification/fix

Introduce and test an explicit hosted `uat` configuration (and eventually `prod`) that permits Supabase, honors Replit's `PORT`, and keeps the provisioning gate enabled only in intended non-production environments. Align the runbook and example secrets with that model.

## 2. Database readiness

### Compatibility and connection behavior

- The backend uses `psycopg`/`psycopg_pool` and standard PostgreSQL SQL. Supabase aliases (`SUPABASE_DATABASE_URL`, `SUPABASE_MIGRATION_DATABASE_URL`) are supported.
- Runtime and migration URLs can be separated, which is appropriate for a pooled runtime URL and direct/session migration URL.
- Hosted SSL defaults to certificate verification (`verify-full`). This is the safe default; the exact Supabase URL and CA behavior must be smoke-tested from Replit.
- Pool maximum defaults to 10. Confirm this against the selected Supabase plan/pooler limits and Replit process count.

### Migration runner and migrations 001-022

- There are **25 SQL files**, named from `001` through `022`; prefixes `012` and `013` each have multiple files. This is not a collision in the current runner because the full filename is the migration version.
- Files are sorted lexicographically, tracked by full filename in `public.schema_migrations`, and applied one file per transaction. Already recorded filenames are skipped; execution stops on the first failure.
- `schema_migrations` is created automatically if absent. Migration 004 also creates it defensively.
- Extensions used include `pgcrypto`, `citext`, and `pg_trgm`, all expected to be available on Supabase, but they must be verified in the target project.
- Migration 019 performs data-sensitive fingerprint/workspace backfill and introduces workspace-scoped uniqueness. It should be validated first against a clone or clean UAT project; do not assume an existing shared database will migrate cleanly.
- There is no automatic migration step in the Replit run command. Migrations must be an explicit, controlled pre-deploy operation using the migration URL.
- Readiness acceptance should require exactly 25 rows in `schema_migrations`, with latest filename `022_add_user_password_credentials.sql`, and independently verify all expected filenames rather than relying only on `max(version)`.

### Password credentials and provisioning schema

Migration 022 creates `user_password_credentials` with one row per user, a cascade FK to `users`, a one-way password hash, timestamps, and the existing `set_updated_at()` trigger. This is compatible with the provisioning/login repositories. Migration 022 is mandatory before provisioning.

### Workspace isolation

- Core repositories and reset paths visibly use `workspace_id`, and import fingerprint uniqueness was explicitly migrated to workspace scope in migration 019.
- Workspace membership/manager checks exist at API boundaries, and reset operations are workspace-scoped.
- No migration enables PostgreSQL Row Level Security. Isolation therefore depends primarily on application queries and API authorization. If Supabase's generated REST/GraphQL API or public keys are enabled, verify grants/RLS so public-schema tables cannot be accessed outside FastAPI. This is a **High** defense-in-depth risk.
- A focused two-user/two-workspace leakage test is still required across dashboard, analytics, search, budgets, imports, data sources, sync history, invitations, and reset endpoints.

### Seed/admin requirement

No seed is required for a provisioned tester, but a first Super Admin path is required. Replit must have `DASHBOARD_USERNAME`, `DASHBOARD_PASSWORD`, and `SUPER_ADMIN_EMAILS` aligned so static admin login creates/updates a database user with `super_admin`. `DASHBOARD_AUTH_TOKEN` is also mandatory at startup and is treated as a legacy super-admin bearer token; protect and rotate it like a privileged credential.

## 3. Replit readiness

### Working pieces

- Root scripts provide `build:replit` and `start:replit`.
- The backend starts with Uvicorn on `0.0.0.0` and a supplied port.
- FastAPI serves `apps/web/dist/index.html`, `/assets`, and SPA fallback routes; `/api/*` is protected from SPA fallback.
- `VITE_API_MODE=same-origin` produces relative `/api/...` calls and avoids CORS for normal browser traffic.
- A split frontend/backend mode remains possible using `VITE_API_URL`, with explicit `CORS_ALLOWED_ORIGINS`.

### Gaps

- The checked-in file is `.replit.example`, not an active `.replit`; the actual Replit configuration must be created/configured in the service.
- The example run command builds on every start, increasing cold-start time. Verify Replit build/deploy lifecycle and persistent artifact behavior.
- The documented secret list omits the environment/DB target variables required by backend validation.
- There is no migration or release health gate in startup. This avoids unsafe automatic schema mutation, but operations must deliberately migrate before starting the app.
- Replit sleep/resource behavior may interrupt long imports or sync jobs. Confirm plan limits and timeout behavior before external testing.
- `start_import_cleanup_scheduler()` appears after a `return` in `/api/system/info`, so it is unreachable and is not started by the startup handler. This is not a boot blocker, but temporary import cleanup will not run as intended.

### Recommended serving mode

Use the documented **single-app/same-origin** mode for UAT. It minimizes URL and CORS drift. Use split mode only if Replit is configured as backend-only and the frontend origin/API URL/CORS/OAuth settings are all updated together.

## 4. Google OAuth readiness

Two distinct OAuth flows exist:

- Google login callback: `https://<replit-host>/api/auth/google/callback`.
- Workspace Google connection callback: `https://<replit-host>/api/google/oauth/callback`.

Google Cloud must contain the exact HTTPS authorized redirect URI for every flow that UAT will exercise, with no path/trailing-slash mismatch. The authorized JavaScript origin should be `https://<replit-host>`. `FRONTEND_URL` must be the same host so the connection callback returns to `/settings/data-sources`; `FRONTEND_AUTH_REDIRECT_URL` must match the frontend route used for login token handoff.

The authorization flow requests offline access and consent, stores encrypted access/refresh tokens, and scopes the workspace connection through signed state. Keep `TOKEN_ENCRYPTION_KEY` stable across restarts/deploys or testers will need to reconnect.

### Scope decision

- For read/import-only access to tester-owned sheets: use `https://www.googleapis.com/auth/spreadsheets.readonly`.
- For the current workflow that writes approved data back through `worksheet.update(...)`: use `https://www.googleapis.com/auth/spreadsheets` and make the write behavior explicit to testers.

Do not advertise original-sheet immutability while enabling the write-back flow. Prefer a dedicated test spreadsheet/copy and a dedicated UAT OAuth client/consent configuration. Verify Google app publishing/test-user rules and add every tester if the consent screen remains in Testing mode.

## 5. UAT tester provisioning readiness

### Implemented correctly

- Endpoint: `POST /api/admin/users/provision-test-user`.
- Entire admin router requires Super Admin authorization.
- Input validates email, name, workspace name, role, and password policy through hashing.
- Provisioning is wrapped in a database transaction.
- It creates the user, one-way password credential, workspace, owner membership, and default workspace configuration.
- Membership is always `owner`, even when the user's global role is `member` or `user`; this appears intentional for a tester-owned workspace but should be documented.
- Duplicate emails return a conflict and plaintext password is not returned by the API.

### Blocking gate mismatch

The service allows provisioning only when `APP_ENV` or `ENV_PROFILE` is `local-dev`, `dev`, or `uat`. Backend startup rejects `dev`/`uat`, while `local-dev` rejects Supabase. Consequently, Replit + Supabase cannot both boot and expose provisioning under the intended configuration. This is the primary UAT blocker.

## 6. Data safety

### Reset Synced Data

`POST /api/data-sources/{source_id}/reset-synced-data` resolves the source through the current workspace and deletes only rows matching `workspace_id`, `sheet_source_id`, and `source_origin='google_sheet'`. It does not call Google Sheets and reports `google_sheet_untouched=true`. This design is appropriate, subject to live two-workspace authorization testing.

### Factory Reset

`POST /api/workspace/factory-reset-data` is owner/Super Admin protected and available only when `APP_ENV == local-dev`. It deletes selected operational rows by workspace while preserving users, workspace, memberships, Google source configuration, and OAuth connections. It is therefore unavailable in the desired UAT environment and should not be enabled casually; decide explicitly whether UAT needs it and add a safe UAT-specific policy if so.

### Google Sheet content protection

Reset operations do not mutate Google Sheets. Normal sync/write-back can mutate a selected worksheet. UAT must use a disposable copy, confirm the selected tab and expected headers, and test that updates cannot target an unintended sheet/tab. “Original content protected” is true for resets, not universally true for all application actions.

### Leakage risks

Application-level workspace scoping is substantial, but the absence of database RLS and the breadth of repository/query surface mean static review is insufficient. Run adversarial tests with two users and distinct sheet sources, including guessed UUIDs and switched `X-Workspace-Id` values. Never share a Supabase project that contains production/personal data with external testers.

## 7. Operational checklist

### Replit secrets

- [ ] `APP_ENV`, `ENV_PROFILE`, `DB_TARGET`, and port behavior set according to a corrected hosted-UAT model.
- [ ] `SUPABASE_DATABASE_URL` (pooled/runtime) and `SUPABASE_MIGRATION_DATABASE_URL` (direct/session where required).
- [ ] `DATABASE_SSL=true`, certificate verification retained, and pool size reviewed.
- [ ] `DASHBOARD_USERNAME`, strong `DASHBOARD_PASSWORD`, random `DASHBOARD_AUTH_TOKEN`.
- [ ] Strong independent `JWT_SECRET` and appropriate session lifetime.
- [ ] Stable `TOKEN_ENCRYPTION_KEY` and `TOKEN_ENCRYPTION_SECRET`.
- [ ] `SUPER_ADMIN_EMAILS` contains the bootstrap admin email.
- [ ] Exact `FRONTEND_URL`, `FRONTEND_AUTH_REDIRECT_URL`, and `CORS_ALLOWED_ORIGINS`.
- [ ] Google client ID/secret, both redirect URIs, and deliberately selected Sheets scope.
- [ ] `VITE_API_MODE=same-origin` available during the build.
- [ ] No secret placed in any `VITE_*` variable or committed env file.

### Supabase setup

- [ ] Dedicated UAT project with no production/personal data.
- [ ] Runtime and migration connection strings tested from Replit without printing credentials.
- [ ] Extensions `pgcrypto`, `citext`, and `pg_trgm` available.
- [ ] Public schema grants/RLS reviewed; generated APIs cannot bypass FastAPI isolation.
- [ ] Connection/pool limits reviewed.
- [ ] Backup/restore point established before migration.

### Google Cloud setup

- [ ] Dedicated UAT OAuth client or isolated redirect configuration.
- [ ] Exact Replit HTTPS JavaScript origin.
- [ ] Exact connection and login callback URIs as applicable.
- [ ] Sheets API enabled.
- [ ] Consent screen configured; external test users allowlisted while in Testing mode.
- [ ] Scope matches read-only versus write-back promise.
- [ ] Testers instructed to use disposable sheet copies.

### Migrations

- [ ] Run the migration runner manually against the dedicated UAT migration URL.
- [ ] Confirm all 25 filenames are recorded in `schema_migrations` and 022 is present.
- [ ] Confirm `user_password_credentials` and its update trigger exist.
- [ ] Validate migration 019 constraints/backfill and workspace-scoped fingerprint indexes.
- [ ] Run the staging SQL validation pack and archive sanitized results.

### Smoke tests before sharing

- [ ] Build succeeds in same-origin mode; `/`, `/dashboard`, and refresh routes serve the SPA.
- [ ] `/api/health`, `/api/health/db`, and `/api/system/info` return expected sanitized status.
- [ ] Startup summary shows UAT, Supabase, correct host mask, frontend URL, and migration status.
- [ ] Super Admin login works; static bearer token is not exposed to the browser/testers.
- [ ] Provision tester; verify password login, owner membership, empty/default workspace config.
- [ ] Connect tester-owned disposable Google Sheet; refresh/reconnect survives restart.
- [ ] Verify the precise read-only or write-back workflow and expected tab behavior.
- [ ] Run two-user/two-workspace isolation and guessed-ID tests.
- [ ] Reset Synced Data removes only the selected source's PostgreSQL rows and leaves the sheet byte-for-byte/functionally unchanged.
- [ ] Confirm Factory Reset is unavailable unless explicitly approved for UAT.
- [ ] Restart/redeploy and verify secrets, token decryption, SPA build, and login persist.
- [ ] Observe logs for credential/URL/token leakage and confirm acceptable sleep/timeouts.

## 8. Risks and blockers

| Severity | Finding | Suggested fix or verification |
| --- | --- | --- |
| **Blocker** | No valid environment combination supports Replit + Supabase + UAT provisioning. | Add/validate a hosted `uat` profile, map it to Supabase, and permit provisioning only there/non-prod. |
| **Blocker** | Strict backend port validation conflicts with Replit-managed `PORT`. | Honor injected `PORT` for hosted profiles; test with the actual Replit port. |
| **Blocker** | Replit runbook omits required environment selector/DB target values and defaults lead to Supabase rejection. | Update secrets/runbook together with the environment model and perform a clean boot test. |
| **Blocker** | Google scope/runbook says read-only while application write-back calls `worksheet.update`. | Decide UAT contract; either disable write-back for read-only scope or request full Sheets scope with explicit tester consent. |
| **High** | No database RLS is defined; isolation relies on every application query and Supabase grants. | Disable unnecessary generated API access and/or add RLS; execute two-workspace adversarial tests. |
| **High** | Existing Supabase is documented as personal staging and not recommended for external users. | Use a dedicated UAT project containing no personal/production data. |
| **High** | Migration 019 is data-sensitive and migrations are not automated. | Rehearse on a clone/clean UAT DB, validate all 25 filenames, and capture sanitized evidence. |
| **High** | Privileged static `DASHBOARD_AUTH_TOKEN` is accepted as legacy Super Admin. | Keep server-only, use a long random value, rotate before UAT, and verify it never enters frontend/logs. |
| **High** | Google write-back can modify tester sheets; reset safety does not imply global sheet immutability. | Require disposable copies and verify destination/tab selection and scope. |
| **Medium** | Factory Reset is unavailable outside `local-dev`; UAT recovery expectations are unclear. | Define an operator-led recovery process or a separately guarded UAT reset policy before testing. |
| **Medium** | Import cleanup scheduler call is unreachable. | Fix after readiness blockers; meanwhile monitor/clean temporary files operationally. |
| **Medium** | Replit sleep/resource limits can interrupt sync/import and rebuild-on-start increases cold start. | Validate the selected plan under realistic imports, restart, and idle wake-up. |
| **Medium** | Config only models local environments; promotion semantics are ambiguous. | Define dev/UAT/prod matrix and add automated configuration tests. |
| **Low** | Duplicate numeric migration prefixes can confuse manual operators although filenames are unique. | Document full-filename ordering and validate the exact manifest, not numeric count alone. |

## 9. Recommended go/no-go and next step

**NO-GO.** Do not share the Replit link with external testers yet.

The next implementation step should be a small deployment-configuration hardening change: introduce a first-class hosted `uat` environment, honor Replit's port, align the provisioning safety gate, and update the Replit secret/runbook matrix. In the same change set, decide and enforce the Google Sheets permission contract. Then deploy to a dedicated empty Supabase UAT project, apply all 25 migrations, and complete the smoke/isolation checklist before reconsidering go-live.

## Audit verification notes

- Frontend unit tests: **16 passed**.
- Backend migration-runner unit tests that did not require FastAPI executed, but the combined backend suite could not complete in the available audit runtime because `fastapi` was not installed there. Three requested backend modules failed at import for that tooling reason; this is not evidence of application test failure.
- No live Replit, Supabase, or Google Cloud state was inspected. All provider-specific setup remains an operational verification item.
