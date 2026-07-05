# Replit + Supabase Hosted UAT Hardening

## Background

The readiness audit found that Replit + Supabase + tester provisioning could
not boot under a truthful environment identity. The backend accepted only
`local-dev` and `local-prod`, local profiles enforced fixed ports, the Replit
runbook omitted environment selectors, and its read-only Google Sheets scope
contradicted the current write-back workflow.

This change introduces a first-class hosted `uat` profile. It does not deploy,
migrate a live database, or change product/business behavior.

## Blockers Addressed

- `APP_ENV=uat` and `ENV_PROFILE=uat` are accepted.
- Hosted UAT requires `DB_TARGET=supabase` and a Supabase database host.
- UAT honors Replit's arbitrary `PORT`; fixed port checks remain local.
- `prod` is accepted as Supabase-only and provisioning-blocked.
- `local-prod` remains a legacy local production simulation.
- Provisioning is allowed in `local-dev`, legacy `dev`, and `uat`, and blocked
  in `local-prod` and `prod`.
- `/api/system/info` reports sanitized UAT metadata.
- Frontend environment presentation recognizes `uat` and `prod`.
- Replit guidance uses the full Sheets scope required by write-back.

## Environment Matrix

| Environment | Runtime | Database | Port | Provisioning |
| --- | --- | --- | --- | --- |
| `local-dev` | Laptop | local PostgreSQL | exactly `8000` | Allowed |
| `uat` | Replit | Supabase UAT | Replit `PORT` | Allowed |
| `prod` | Future production | Supabase | provider port | Blocked |
| `local-prod` | Legacy local simulation | Supabase | exactly `8001` | Blocked |

`dev` remains recognized only by the existing provisioning gate for backward
compatibility; it is not a backend runtime profile.

## Required Replit Secrets

```env
APP_ENV=uat
ENV_PROFILE=uat
DB_TARGET=supabase
SUPABASE_DATABASE_URL=<pooled-runtime-url>
SUPABASE_MIGRATION_DATABASE_URL=<direct-or-session-migration-url>
DATABASE_SSL=true
DATABASE_SSL_REJECT_UNAUTHORIZED=true

DASHBOARD_USERNAME=<uat-super-admin-email>
DASHBOARD_PASSWORD=<strong-uat-password>
DASHBOARD_AUTH_TOKEN=<long-random-token>
JWT_SECRET=<long-random-secret>
TOKEN_ENCRYPTION_KEY=<stable-fernet-key>
TOKEN_ENCRYPTION_SECRET=<stable-random-secret>
SUPER_ADMIN_EMAILS=<uat-super-admin-email>

FRONTEND_URL=https://<replit-app-url>
FRONTEND_AUTH_REDIRECT_URL=https://<replit-app-url>/auth/callback
CORS_ALLOWED_ORIGINS=https://<replit-app-url>

GOOGLE_OAUTH_CLIENT_ID=<uat-google-client-id>
GOOGLE_OAUTH_CLIENT_SECRET=<uat-google-client-secret>
GOOGLE_OAUTH_REDIRECT_URI=https://<replit-app-url>/api/google/oauth/callback
GOOGLE_LOGIN_REDIRECT_URI=https://<replit-app-url>/api/auth/google/callback
GOOGLE_OAUTH_SCOPES=openid email profile https://www.googleapis.com/auth/spreadsheets

VITE_API_MODE=same-origin
```

Do not set `BACKEND_PORT`; Replit injects `PORT`. `VITE_API_MODE` must exist
during the frontend build. Never commit or print Replit Secrets.

## Supabase UAT Setup Checklist

- [ ] Create a dedicated empty Supabase UAT project.
- [ ] Confirm it has no personal or production data.
- [ ] Verify PostgreSQL extensions required by migration files.
- [ ] Apply every file in `backend/db/migrations`, including migration 022 and
      every later checked-in migration.
- [ ] Verify `schema_migrations` contains every migration filename.
- [ ] Verify `user_password_credentials` exists.
- [ ] Bootstrap the Super Admin safely from Replit Secrets.
- [ ] Run a two-user workspace-isolation smoke test.

## Google OAuth and Sheets Contract

The application writes to Sheets during delivery and retry, so hosted UAT
requires `https://www.googleapis.com/auth/spreadsheets`. Testers must use a
disposable spreadsheet or UAT copy. The app must not claim every action leaves
Sheets unchanged. Reset Synced Data and Factory Reset keep their existing
guarantee and do not modify the original Google Sheet.

A read-only/write-back feature toggle is deferred because no current safe flag
provides that split. Google Cloud must allow the exact Replit HTTPS origin and
documented callback URIs.

## Migration Procedure

Migrations are manual and must never run on app startup:

The migration runner supports hosted UAT directly. It prefers
`DATABASE_MIGRATION_URL`, then `SUPABASE_MIGRATION_DATABASE_URL`, before either
runtime URL. Explicit process/Replit environment values take precedence over
local dotenv files, and the selected migration URL is the URL validated during
migration-runner bootstrap.

1. Confirm the target is the dedicated empty Supabase UAT project.
2. Set the UAT selectors and migration URL in a controlled shell.
3. Run `python backend/scripts/run_migrations.py`.
4. Compare `schema_migrations` with every checked-in migration.
5. Verify migration 022 and `user_password_credentials`.
6. Start the app only after verification passes.

## Smoke Test Checklist

- [ ] `/api/health`, `/api/health/db`, and `/api/system/info` pass.
- [ ] System info reports `uat`, `supabase`, and Replit's port without secrets.
- [ ] Super Admin login and UAT provisioning work.
- [ ] Google connect, refresh, disconnect, and reconnect are controlled.
- [ ] A disposable Sheet supports one-row delivery and idempotent retry.
- [ ] Two users cannot access each other's unrelated workspaces.
- [ ] Dashboard, Search, Analytics, Budgeting, and Import smoke tests pass.

## Remaining Risks

- Replit sleep, timeout, rebuild, and resource limits require live validation.
- Supabase pool sizing and SSL behavior require validation from Replit.
- Provider configuration and redirect URIs cannot be verified from source.
- The import cleanup scheduler issue identified by the readiness audit is out of
  scope for this hardening task.
- External UAT remains blocked until Supabase setup and smoke tests pass.

## Tests Run

- Targeted backend config/migration/lifecycle/system-info tests: 32 passed.
- Full backend discovery after migration bootstrap hardening: 181 passed.
- Frontend utility tests: 18 passed.
- Web and landing lint: passed.
- Replit same-origin production build: passed; the existing large-chunk warning
  remains non-blocking.
- `git diff --check`: passed.
