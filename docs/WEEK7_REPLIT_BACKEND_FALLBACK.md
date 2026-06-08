# Week 7 Replit Backend Fallback

## Objective

This document prepares a temporary Replit backend fallback for personal staging
when Render Free Web Service requires card/payment verification. It does not
deploy anything, does not change backend or frontend behavior, does not change
OAuth, sync, classification, workspace invitation logic, dependencies, or AI
configuration, and does not document real secrets.

Render remains the preferred/stable backend path when payment verification is
acceptable. Replit is a practical fallback for Reza/Divya personal staging, not
the final recommendation for public beta.

Current personal staging now uses the Replit single-app setup, where one Replit
URL serves both FastAPI `/api/*` and the built React frontend:

```text
docs/WEEK7_REPLIT_SINGLE_APP_STAGING.md
```

## Why Fallback From Render

The Week 7 preferred stack is still:

- Frontend: Vercel.
- Backend: Render Docker Web Service.
- Database: Supabase.
- OAuth: Google OAuth Web Client.

The fallback exists because Render may ask for a card even when a Free instance
is selected. If the goal is to avoid adding a card for now, Replit can host the
FastAPI backend temporarily while keeping the same Vercel frontend and Supabase
database.

## Where Replit Fits

Replit is:

- Temporary personal staging fallback.
- Useful when Render blocks setup on card/payment verification.
- Acceptable for internal testing by Reza and Divya.
- Good enough for validating API URL, CORS, OAuth callback, Supabase access,
  workspace switcher, sync, dashboard, analytics, and invitations at small
  scale.

Replit is not:

- The final recommendation for public beta.
- A replacement for the Render docs.
- A place to store committed `.env` files or real secrets.
- A reason to skip separate Supabase beta/staging database planning before
  external users are invited.

Before inviting external users from Threads/public interest, create a separate
Supabase beta/staging project and re-evaluate backend hosting stability.

## Replit Suitability And Limitations

| Area | Suitability | Limitation |
| --- | --- | --- |
| Personal staging | Good for quick backend hosting. | Free tier availability, sleep, and URL behavior may vary. |
| FastAPI app | Compatible with `uvicorn`. | Must bind to `0.0.0.0` and Replit's `$PORT`. |
| Supabase DB | Compatible through env secrets. | Wrong database URL can mutate personal/dev data. |
| Google OAuth | Compatible with HTTPS Replit URL. | Callback URL must be stable and exactly matched in Google Cloud. |
| Public beta | Not first choice. | Stability/limits should be proven before external testers. |

## Backend Architecture Summary

| Item | Current state | Replit impact | Recommendation |
| --- | --- | --- | --- |
| FastAPI app path | `backend/app/main.py` | Uvicorn module is `app.main:app` from backend directory. | Use `cd backend && uvicorn app.main:app ...` from repo root. |
| Requirements | `backend/requirements.txt` | Replit must install Python dependencies from this file. | Use `pip install -r backend/requirements.txt` from repo root. |
| Python version | Docker uses `python:3.12-slim`; requirements are pinned. | Replit Python image should be compatible with Python 3.12 or a close supported version. | Prefer Python 3.12 if configurable. |
| Runtime env | `backend/app/config.py` reads process env, then repo `.env`, then `backend/.env`. | Replit Secrets become process env and are enough. | Use Replit Secrets; do not commit `.env`. |
| Required auth env | `DASHBOARD_USERNAME`, `DASHBOARD_PASSWORD`, `DASHBOARD_AUTH_TOKEN`, `JWT_SECRET` fallback, encryption secret fallback. | Missing values can crash backend at startup. | Add all required backend secrets before running. |
| OAuth env | Code uses `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`, `GOOGLE_OAUTH_SCOPES`. | Generic names like `GOOGLE_CLIENT_ID` are not read by current code. | Use current `GOOGLE_OAUTH_*` names. |
| CORS | `CORS_ALLOWED_ORIGINS` is comma-separated. | Must include Vercel frontend URL. | Set exact Vercel URL, no wildcard if avoidable. |
| Health endpoint | `/api/health` exists and does not require auth. | Good for Replit smoke test. | Use as first backend check. |
| DB health endpoint | `/api/health/db` exists and does not require auth. | Confirms Supabase connection. | Use after `/api/health`. |
| Migrations | `backend/scripts/run_migrations.py` uses `DATABASE_MIGRATION_URL` or `DATABASE_URL`. | Can run from local or Replit shell if env is correct. | Do not auto-run on app start. |

## Replit Project Setup Options

### Option A: Import Full GitHub Repository

Replit root is repository root.

Install command:

```bash
pip install -r backend/requirements.txt
```

Run command:

```bash
cd backend && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Pros:

- Repository structure stays intact.
- Easier to sync with GitHub.
- Matches current monorepo documentation.

Cons:

- Commands must `cd backend`.
- Replit must not accidentally run frontend or landing app commands.

### Option B: Backend-Only Replit Project

Project root is the backend folder.

Install command:

```bash
pip install -r requirements.txt
```

Run command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Pros:

- Simpler runtime layout.

Cons:

- Easier to drift from the GitHub monorepo.
- Manual copy/import can lose docs, scripts, or future changes.

Final recommendation: use Option A first. Import the full GitHub repository and
run the backend from the `backend` directory. Avoid manual copying if possible.

## Recommended Replit Run Command

If Replit project root is repository root:

```bash
cd backend && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

If Replit project root is `backend`:

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Rules:

- Bind to `0.0.0.0`, not localhost.
- Use `$PORT` when Replit provides it.
- Fallback `8000` is fine for local/Replit preview if supported.
- Keep `app.main:app` as the module path when running from backend root.

## Replit Secrets And Environment Variables

Set backend secrets in Replit Secrets. Do not commit `.env`. Do not put Vite
frontend variables in Replit backend secrets.

Required backend env:

```env
DATABASE_URL=<supabase-runtime-or-pooled-connection-string>
DATABASE_MIGRATION_URL=<supabase-direct-or-session-connection-string-if-used>
DATABASE_SSL=true
DATABASE_SSL_REJECT_UNAUTHORIZED=true
DATABASE_POOL_MAX=10

DASHBOARD_USERNAME=<staging-admin-email>
DASHBOARD_PASSWORD=<staging-admin-password>
DASHBOARD_AUTH_TOKEN=<long-random-token>
JWT_SECRET=<long-random-jwt-secret>
JWT_EXPIRES_IN_MINUTES=10080
TOKEN_ENCRYPTION_KEY=<fernet-key>
TOKEN_ENCRYPTION_SECRET=<long-random-token-secret>
SUPER_ADMIN_EMAILS=<staging-admin-email>

FRONTEND_URL=https://finance-dashboard-rezaaapp.vercel.app
FRONTEND_AUTH_REDIRECT_URL=https://finance-dashboard-rezaaapp.vercel.app/auth/google/callback
CORS_ALLOWED_ORIGINS=https://finance-dashboard-rezaaapp.vercel.app

GOOGLE_OAUTH_CLIENT_ID=<google-oauth-client-id>.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=<google-oauth-client-secret>
GOOGLE_OAUTH_REDIRECT_URI=https://<replit-backend>.replit.app/api/google/oauth/callback
GOOGLE_LOGIN_REDIRECT_URI=https://<replit-backend>.replit.app/auth/google/callback
GOOGLE_OAUTH_SCOPES=openid email profile https://www.googleapis.com/auth/spreadsheets.readonly

MAX_GOOGLE_SHEET_SOURCES=5
USE_MOCK_DATA=false

AI_CLASSIFICATION_ENABLED=false
AI_PROVIDER=rule_based
AI_MODEL=none
AI_ONLY_LOW_CONFIDENCE=true
AI_CONFIDENCE_THRESHOLD=0.75
AI_MAX_TRANSACTIONS_PER_RUN=500
```

Optional insight defaults:

```env
INSIGHT_NEED_WARNING_RATIO=0.80
INSIGHT_NEED_DANGER_RATIO=0.90
INSIGHT_WANT_WARNING_RATIO=0.30
INSIGHT_WANT_DANGER_RATIO=0.45
INSIGHT_SAVING_WARNING_RATIO=0.10
INSIGHT_SAVING_GOOD_RATIO=0.20
INSIGHT_UNCATEGORIZED_WARNING_COUNT=1
INSIGHT_UNCATEGORIZED_DANGER_COUNT=20
INSIGHT_ANOMALY_WARNING_MULTIPLIER=2.0
INSIGHT_ANOMALY_DANGER_MULTIPLIER=3.0
```

Important:

- Current backend code uses `GOOGLE_OAUTH_CLIENT_ID`,
  `GOOGLE_OAUTH_CLIENT_SECRET`, and `GOOGLE_OAUTH_REDIRECT_URI`. Do not rely on
  `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, or `GOOGLE_REDIRECT_URI` aliases
  unless code is explicitly changed later.
- `TOKEN_ENCRYPTION_KEY` must stay stable. If it differs from the key used for
  already stored tokens, users may need to reconnect Google OAuth.
- Replit secrets are backend-only. Vercel needs its own `VITE_*` env values.

## Google OAuth Setup For Replit

If Replit backend URL is:

```text
https://<replit-backend>.replit.app
```

Google Cloud Console Authorized redirect URI must include:

```text
https://<replit-backend>.replit.app/api/google/oauth/callback
```

Authorized JavaScript origin should include the Vercel frontend:

```text
https://finance-dashboard-rezaaapp.vercel.app
```

Rules:

- Redirect URI must exactly match `GOOGLE_OAUTH_REDIRECT_URI`.
- Use HTTPS.
- Avoid trailing slash mismatch.
- Keep local redirect URI for local development.
- If the Replit URL changes, update Replit secrets, Google Cloud Console, and
  Vercel frontend env.

## Vercel Frontend Env For Replit Backend

When using Replit as backend, update Vercel env:

```env
VITE_API_URL=https://<replit-backend>.replit.app
VITE_API_BASE_URL=https://<replit-backend>.replit.app
VITE_GUEST_MODE_MULTIPLIER=0.75
```

Then redeploy Vercel.

Rules:

- Frontend should not point to Render URL while using Replit backend.
- Do not include `/api/dashboard`; frontend config appends API paths.
- Browser CORS requires Replit `CORS_ALLOWED_ORIGINS` to include the Vercel
  frontend URL.
- Vercel env is public if prefixed with `VITE_`; never put backend secrets
  there.

## Supabase Existing Database Notes

For personal staging, existing Supabase is acceptable after backup. Do not
treat existing Supabase as the public beta database.

Before public beta:

- Create a separate Supabase beta/staging project.
- Run all migrations from a clean state.
- Use separate `DATABASE_URL`, `DATABASE_MIGRATION_URL`, OAuth client/redirect
  settings, and test data.

Use the SQL validation pack:

```text
docs/WEEK7_STAGING_DATABASE_VALIDATION.md
```

Do not run destructive queries against the existing Supabase project.

## Migration Strategy On Replit

Do not run migrations automatically on Replit app start.

Recommended:

1. Run migrations manually from local machine using known-good env.
2. Or run from Replit shell only after confirming Replit Secrets point to the
   intended Supabase project.
3. Validate `schema_migrations`.
4. Validate tables and indexes with the Week 7 database validation doc.

Commands:

From local or Replit full repo root:

```bash
python backend/scripts/run_migrations.py
```

From Replit backend root:

```bash
python scripts/run_migrations.py
```

Warning: confirm `DATABASE_MIGRATION_URL` before running. Existing Supabase may
contain local/personal data.

## Post-Deploy Backend Smoke Test

Health:

```powershell
Invoke-RestMethod `
  -Uri "https://<replit-backend>.replit.app/api/health"
```

DB health:

```powershell
Invoke-RestMethod `
  -Uri "https://<replit-backend>.replit.app/api/health/db"
```

Auth-protected workspaces after frontend login:

```powershell
$token = "PASTE_TOKEN_FROM_FRONTEND_AFTER_LOGIN"

Invoke-RestMethod `
  -Uri "https://<replit-backend>.replit.app/api/workspaces" `
  -Headers @{ Authorization = "Bearer $token" } |
ConvertTo-Json -Depth 10
```

Dashboard with workspace:

```powershell
Invoke-RestMethod `
  -Uri "https://<replit-backend>.replit.app/api/dashboard/summary?year=2026" `
  -Headers @{
    Authorization = "Bearer $token"
    "X-Workspace-Id" = "PASTE_WORKSPACE_ID"
  } |
ConvertTo-Json -Depth 10
```

## Vercel And Replit End-To-End Smoke Test

Manual browser flow:

1. Open the Vercel frontend.
2. Confirm Network tab calls the Replit backend URL.
3. Login.
4. Start Google OAuth connect.
5. Confirm OAuth callback returns to Vercel frontend.
6. Confirm workspace switcher loads.
7. Confirm Dashboard loads.
8. Confirm Analytics loads.
9. Confirm Configuration loads data sources.
10. Test Sync Now only when Google OAuth and Supabase target are correct.
11. Test Reza/Divya workspace switching.
12. Test invitation notification only if needed.
13. Logout and login again.

## Common Replit Issues And Fixes

| Issue | Symptom | Fix |
| --- | --- | --- |
| Backend starts but API is unreachable | Replit page opens but `/api/health` fails. | Bind to `0.0.0.0` and use `${PORT:-8000}`. |
| `ModuleNotFoundError: app` | Uvicorn cannot import `app.main`. | Run from backend root or use `cd backend && uvicorn app.main:app ...`. |
| Missing dependency | Import error at startup. | Run `pip install -r backend/requirements.txt` from repo root. |
| Env missing | Backend crashes on startup. | Add required Replit Secrets. |
| CORS error | Vercel loads but API calls are blocked. | Set `CORS_ALLOWED_ORIGINS` to Vercel URL. |
| OAuth redirect mismatch | Google shows `redirect_uri_mismatch`. | Match Google Cloud Console and Replit `GOOGLE_OAUTH_REDIRECT_URI`. |
| Token decrypt failed | Google connection exists but sync fails. | Restore stable `TOKEN_ENCRYPTION_KEY` or reconnect Google. |
| DB connection failed | `/api/health/db` returns unavailable. | Check Supabase URL, SSL flags, and database target. |
| Replit URL changed | Frontend/OAuth suddenly points to old backend. | Update Google Cloud redirect URI and Vercel `VITE_API_URL`/`VITE_API_BASE_URL`. |

## Exit Plan From Replit

Replit is temporary.

When moving to a stable backend:

1. Keep Render docs as the preferred deployment path.
2. Choose stable hosting before public beta.
3. Create a separate Supabase beta project for external testers.
4. Configure dedicated OAuth client or staging redirect URI.
5. Deploy backend to Render or another stable host.
6. Update Vercel env from Replit backend URL to the stable backend URL.
7. Update Google OAuth redirect URI.
8. Run database validation and end-to-end smoke tests again.

## Known Limitations

- Replit availability, sleep behavior, URL stability, and resource limits may
  vary by plan.
- Replit is less production-like than Render Docker hosting for this app.
- Existing Supabase personal staging can mix test and personal data.
- No automatic migration job is configured.
- This plan does not deploy or test the app from Codex.

## Next Prompt Roadmap

- Configure Replit manually if choosing this fallback.
- Update Vercel env after the Replit backend URL is known.
- Run Week 7 database validation.
- Run end-to-end staging smoke test for Vercel + Replit + Supabase + Google
  OAuth.
- Before public beta, move from Replit fallback to stable backend hosting and a
  separate Supabase beta project.
