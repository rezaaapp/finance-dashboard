# Week 7 Replit Single-App Staging

## Objective

This document describes the current personal staging path where one Replit URL
serves both the FastAPI backend and the React/Vite frontend:

```text
https://<replit-app-url>
```

Routing target:

- `/api/*` -> FastAPI backend.
- `/*` -> React SPA from `apps/web/dist`.

This is the hosted UAT path. It must use a dedicated, empty Supabase UAT
project; never point it at personal or production data.

## Why Single-App Replit

Render Free requested card verification, and the immediate goal is to keep
personal staging moving without adding a card. Replit single-app staging avoids
separate Vercel frontend env during personal testing because the browser calls
the backend through the same origin.

Before inviting external users, use a separate Supabase beta project and choose
a more stable backend host.

## Architecture

```text
https://<replit-app-url>/api/health
  -> FastAPI

https://<replit-app-url>/dashboard
  -> FastAPI serves apps/web/dist/index.html

https://<replit-app-url>/assets/*
  -> FastAPI serves apps/web/dist/assets/*
```

## Code And Config Changes

- `backend/app/main.py` serves `apps/web/dist` when the frontend build exists.
- `/api/*` routes remain API routes and are not swallowed by the SPA fallback.
- `apps/web/src/api/config.js` supports `VITE_API_MODE=same-origin`.
- `apps/web/scripts/validate-env.mjs` allows production builds when
  `VITE_API_MODE=same-origin`.
- `backend/app/config.py` supports Replit-friendly aliases:
  `SUPABASE_DATABASE_URL` and `SUPABASE_MIGRATION_DATABASE_URL`.
- Root `package.json` includes `build:replit` and `start:replit`.
- `.replit.example` provides a copyable Replit run config.

## Build Command

For Replit single-app staging:

```bash
VITE_API_MODE=same-origin npm run build:replit
```

PowerShell equivalent for local verification:

```powershell
$env:VITE_API_MODE="same-origin"
npm run build:replit
```

## Run Command

From repository root:

```bash
npm run start:replit
```

This runs:

```bash
cd backend && python3 -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

If using Replit's `.replit` file, copy `.replit.example` to `.replit` in the
Replit project if needed.

## Replit Secrets

Use Replit Secrets. Do not commit `.env`.

Backend/database:

```env
APP_ENV=uat
ENV_PROFILE=uat
DB_TARGET=supabase
SUPABASE_DATABASE_URL=<supabase-runtime-or-pooled-connection-string>
SUPABASE_MIGRATION_DATABASE_URL=<supabase-direct-or-session-connection-string>
DATABASE_SSL=true
DATABASE_SSL_REJECT_UNAUTHORIZED=true
DATABASE_POOL_MAX=10
```

Auth/encryption:

```env
DASHBOARD_USERNAME=<staging-admin-email>
DASHBOARD_PASSWORD=<staging-admin-password>
DASHBOARD_AUTH_TOKEN=<long-random-token>
JWT_SECRET=<long-random-jwt-secret>
TOKEN_ENCRYPTION_KEY=<fernet-key>
TOKEN_ENCRYPTION_SECRET=<long-random-token-secret>
SUPER_ADMIN_EMAILS=<staging-admin-email>
```

Single-app frontend/backend URL:

```env
FRONTEND_URL=https://<replit-app-url>
FRONTEND_AUTH_REDIRECT_URL=https://<replit-app-url>/auth/callback
CORS_ALLOWED_ORIGINS=https://<replit-app-url>
```

Google OAuth:

```env
GOOGLE_OAUTH_CLIENT_ID=<google-oauth-client-id>.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=<google-oauth-client-secret>
GOOGLE_OAUTH_REDIRECT_URI=https://<replit-app-url>/api/google/oauth/callback
GOOGLE_LOGIN_REDIRECT_URI=https://<replit-app-url>/api/auth/google/callback
GOOGLE_OAUTH_SCOPES=openid email profile https://www.googleapis.com/auth/spreadsheets
```

Rule-based only:

```env
AI_CLASSIFICATION_ENABLED=false
AI_PROVIDER=rule_based
AI_MODEL=none
AI_ONLY_LOW_CONFIDENCE=true
AI_CONFIDENCE_THRESHOLD=0.75
AI_MAX_TRANSACTIONS_PER_RUN=500
```

Frontend build env:

```env
VITE_API_MODE=same-origin
VITE_GUEST_MODE_MULTIPLIER=0.75
```

Important: Replit may reserve or manage `DATABASE_URL`, so use
`SUPABASE_DATABASE_URL` and `SUPABASE_MIGRATION_DATABASE_URL` for this staging
path.

Do not set `BACKEND_PORT` in hosted UAT. Replit supplies `PORT`, and the UAT
profile accepts that managed port. `VITE_API_MODE=same-origin` must be present
when the frontend build runs, not only when the server starts.

The full Sheets scope is required because the current approval/retry workflow
can write rows back to the configured destination. Testers must connect only a
disposable spreadsheet or a copy prepared for UAT. Do not promise that every
application action leaves that spreadsheet unchanged. Reset Synced Data and
Factory Reset retain their existing contract and do not modify the original
Google Sheet.

## Google OAuth Setup

If Replit URL is:

```text
https://<replit-app-url>
```

Google Cloud Console:

```text
Authorized JavaScript origin:
https://<replit-app-url>

Authorized redirect URI:
https://<replit-app-url>/api/google/oauth/callback
```

Replit Secrets:

```env
FRONTEND_URL=https://<replit-app-url>
FRONTEND_AUTH_REDIRECT_URL=https://<replit-app-url>/auth/callback
CORS_ALLOWED_ORIGINS=https://<replit-app-url>
GOOGLE_OAUTH_REDIRECT_URI=https://<replit-app-url>/api/google/oauth/callback
GOOGLE_LOGIN_REDIRECT_URI=https://<replit-app-url>/api/auth/google/callback
```

Keep local OAuth redirect URI in Google Cloud if local development still needs
it.

For Google login, keep the backend callback and frontend token handoff route
separate:

- `GOOGLE_LOGIN_REDIRECT_URI` is the backend callback route:
  `https://<replit-app-url>/api/auth/google/callback`.
- `FRONTEND_AUTH_REDIRECT_URL` is the frontend token handoff route:
  `https://<replit-app-url>/auth/callback`.
- Do not use `/auth/google/callback` as `FRONTEND_AUTH_REDIRECT_URL` in
  Replit single-app staging if that route conflicts with the backend.

## Supabase UAT Safety Checklist

- Create a dedicated empty Supabase UAT project with no personal/production data.
- Run every checked-in migration manually before sharing the UAT link. Do not
  add migration execution to application startup.
- Verify `schema_migrations`, migration 022, and `user_password_credentials`.
- Verify all PostgreSQL extensions required by the migration files.
- Bootstrap the first Super Admin using the documented static-admin path and
  keep its credentials in Replit Secrets.
- Provision testers only after confirming `/api/system/info` reports `uat` and
  `supabase`.
- Run a two-user workspace-isolation smoke test before external UAT.

Database validation doc:

```text
docs/WEEK7_STAGING_DATABASE_VALIDATION.md
```

## Smoke Test

After build/run:

1. Open `https://<replit-app-url>/api/health`.
2. Open `https://<replit-app-url>/api/health/db`.
3. Open `https://<replit-app-url>/`.
4. Refresh `/dashboard`.
5. Refresh `/analytics`.
6. Login.
7. Connect Google OAuth.
8. Confirm OAuth callback returns to the same Replit URL.
9. Confirm workspace switcher loads.
10. Confirm Dashboard loads.
11. Confirm Analytics loads.
12. Confirm Configuration loads.
13. Confirm Data Sources display.
14. Run Sync Now only after verifying OAuth and Supabase target.
15. Logout and login again.

## Common Issues

| Issue | Likely cause | Fix |
| --- | --- | --- |
| `/dashboard` returns 404 | Frontend build missing. | Run `VITE_API_MODE=same-origin npm run build:replit`. |
| `/api/health` returns frontend HTML | SPA fallback is catching API routes. | Ensure catch-all excludes `api/`. |
| Frontend calls localhost | `VITE_API_MODE` was not set during build. | Build with `VITE_API_MODE=same-origin`. |
| Build fails due missing API URL | External API mode validation is active. | Set `VITE_API_MODE=same-origin`. |
| OAuth redirects to Vercel | `FRONTEND_URL` still points to Vercel. | Set Replit URL in Replit Secrets. |
| `redirect_uri_mismatch` | Google Console URI differs. | Match Replit `GOOGLE_OAUTH_REDIRECT_URI` exactly. |
| DB health fails | Supabase URL or SSL env wrong. | Check `SUPABASE_DATABASE_URL` and SSL flags. |
| Token decrypt failed | `TOKEN_ENCRYPTION_KEY` changed. | Restore stable key or reconnect Google OAuth. |
| Replit `DATABASE_URL` conflict | Replit reserved env name. | Use `SUPABASE_DATABASE_URL`. |

## Exit Path

Replit single-app is the current personal staging path. For beta/paid hosting:

1. Keep Vercel + Render docs available.
2. Pick stable backend hosting.
3. Create separate Supabase beta database.
4. Update Google OAuth redirect URI.
5. If splitting frontend/backend again, set Vercel `VITE_API_URL` and
   `VITE_API_BASE_URL` to the stable backend URL.
6. Re-run migration validation and end-to-end smoke tests.

## Known Limitations

- Replit resource limits and sleep behavior may affect reliability.
- Same-origin build must be rebuilt if switching back to split Vercel/Render.
- This path still uses existing Supabase for personal staging unless changed.
- No automatic migration job is configured.
