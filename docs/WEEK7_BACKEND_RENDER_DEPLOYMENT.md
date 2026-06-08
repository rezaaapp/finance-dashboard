# Week 7 Backend Render Deployment

## Objective

This document prepares the FastAPI backend for a Render Free Web Service
deployment. It is preparation-first: no deployment is performed here, no real
secrets are documented, and no backend business logic, OAuth flow, Google Sheet
sync, rule-based classification, workspace invitation logic, or dependency set
is changed.

## Current Backend Architecture Summary

- Backend app: `backend/app/main.py`
- FastAPI object: `app.main:app` when running from the `backend` directory.
- API health endpoint: `GET /api/health`
- Database health endpoint: `GET /api/health/db`
- Database: PostgreSQL/Supabase through `psycopg` and `psycopg_pool`.
- Google Sheets production direction: per-user/workspace Google OAuth.
- OAuth callback route: `/api/google/oauth/callback`
- Runtime configuration: `backend/app/config.py`
- Migrations: SQL files under `backend/db/migrations` run by
  `backend/scripts/run_migrations.py`.

The backend currently imports settings at startup. Render must provide the
required auth, database, encryption, OAuth, frontend, and CORS environment
variables before the service can boot reliably.

## Existing Render and Docker Artifact Audit

| Artifact | Audit result | Decision |
| --- | --- | --- |
| `backend/Dockerfile` | Uses `python:3.12-slim`, installs from `requirements.txt`, copies the backend context, and starts `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`. | Keep. It is suitable for Render Docker deployment when the Docker context is `backend`. |
| `render.yaml` | Existing blueprint used Docker but listed legacy service-account variables and an old Vercel CORS URL. | Updated to OAuth/Supabase staging placeholders and non-secret defaults. |
| `backend/requirements.txt` | Contains FastAPI, uvicorn, dotenv, pandas, gspread, google-auth, cryptography, httpx, PyJWT, psycopg, scikit-learn, and openpyxl. | Keep. No dependency change is needed for this prompt. |
| `DEPLOY_RENDER_VERCEL.md` | Older service-account oriented Render/Vercel guide. | Mark as legacy and link to this Week 7 guide. |

## Dockerfile Audit

Current file:

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Line-by-line findings:

| Area | Result |
| --- | --- |
| Base image | `python:3.12-slim`, acceptable for staging. |
| Working directory | `/app`, correct when Render Docker context is `backend`. |
| Dependency install | Installs `build-essential`, upgrades pip, and installs `-r requirements.txt`. |
| Requirements path | Correct only when Docker context is `backend`; it expects `backend/requirements.txt` to appear as `requirements.txt` inside the context. |
| Copy strategy | `COPY . .` copies the backend directory. It should not copy repo-root `.env` if context is `backend`, but a local `backend/.env` could be copied if present. Keep `.env` ignored and do not place secrets in the image. |
| Exposed port | No `EXPOSE`. This is acceptable on Render because the process binds to `$PORT`; `EXPOSE` is informational only. |
| Start command | Starts `uvicorn app.main:app`. Correct module path from backend root. |
| Render `$PORT` | Uses `${PORT:-8000}`, so Render can inject its assigned port. |
| Host binding | Uses `0.0.0.0`, required for Render. |
| `PYTHONPATH` | Not needed because `/app` contains the `app` package. |
| Secret safety | No secret values are embedded. Risk depends on keeping `backend/.env` and credential files out of the Docker context. |

Dockerfile decision: keep as-is. It is cleaner than the native Python option
for this repo because it pins the backend runtime path inside the image and
does not rely on Render guessing a Python monorepo layout.

## render.yaml Audit

Current blueprint decision:

- Service type: Render Web Service.
- Runtime: Docker.
- Service name: `finance-dashboard-api`.
- Root directory: `backend`.
- Docker context: `backend`.
- Dockerfile path: `backend/Dockerfile`.
- Health check path: `/api/health`.
- Environment variables: placeholder/synced entries only, plus safe non-secret
  defaults.

The old blueprint had these issues:

- Service-account variables were listed as if they were the staging path.
- `CORS_ALLOWED_ORIGINS` pointed to an old Vercel URL.
- OAuth, Supabase, encryption, and JWT variables were incomplete.
- It could mislead a manual Render dashboard setup.

The updated blueprint intentionally does not include real values. Any `sync:
false` value must be entered in Render's environment variable dashboard or via
Render secret management.

If Render's UI setup conflicts with the blueprint, use manual dashboard setup
for the first staging deployment and keep `render.yaml` as the later automation
candidate.

## Recommended Render Deployment Strategy

### Option A: Docker Render Web Service

Settings:

```text
Service type: Web Service
Runtime: Docker
Root Directory: backend
Docker Context: backend
Dockerfile Path: backend/Dockerfile
Health Check Path: /api/health
```

Pros:

- Uses the existing Dockerfile.
- Keeps the FastAPI import path stable.
- Uses Render `$PORT` correctly through the Dockerfile command.
- Avoids Render auto-detecting the repository as the wrong app type.

Cons:

- Docker builds can be slower on Free tier.
- The Docker context must stay clean and must not include local secret files.

### Option B: Native Python Render Web Service

If choosing repository root:

```text
Build Command: pip install -r backend/requirements.txt
Start Command: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

If choosing `backend` root:

```text
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Pros:

- Simpler to understand for small Python apps.
- No Docker image build layer.

Cons:

- Path settings are easier to misconfigure in this monorepo.
- A wrong root/start command can cause import errors or Render serving the
  wrong service.

Final recommendation: use Docker for the first Render staging backend. The
current Dockerfile is small, the module path is correct, and it already listens
on Render's `$PORT`.

## Backend Dependency Audit

Dependency source:

```text
backend/requirements.txt
```

Deployment relevance:

- FastAPI and `uvicorn[standard]` are present.
- `python-dotenv` supports local env loading.
- `psycopg[binary,pool]` supports Supabase/PostgreSQL runtime and migrations.
- `cryptography` supports token encryption.
- `httpx`, `PyJWT`, and Google libraries support OAuth and Google API flows.
- `pandas`, `openpyxl`, and `scikit-learn` are existing heavier dependencies.
  They are not changed in this prompt, but they may affect build time and cold
  start on Render Free.

No dependency changes are required.

## Render Service Settings

Use these for manual setup:

```text
Name: finance-dashboard-api
Service type: Web Service
Runtime: Docker
Branch: main or the deployment branch selected for staging
Root Directory: backend
Dockerfile Path: backend/Dockerfile
Health Check Path: /api/health
Auto Deploy: optional for personal staging; disabled is safer while testing
```

If Render asks for Docker context separately, use:

```text
Docker Context: backend
```

## Required Environment Variables

Set real values only in Render, never in Git.

```env
DATABASE_URL=<supabase-runtime-or-pooled-connection-string>
DATABASE_MIGRATION_URL=<supabase-direct-or-session-connection-string>
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

FRONTEND_URL=https://<vercel-app>.vercel.app
FRONTEND_AUTH_REDIRECT_URL=https://<vercel-app>.vercel.app/auth/google/callback
CORS_ALLOWED_ORIGINS=https://<vercel-app>.vercel.app

GOOGLE_OAUTH_CLIENT_ID=<google-oauth-client-id>.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=<google-oauth-client-secret>
GOOGLE_OAUTH_REDIRECT_URI=https://<render-backend>.onrender.com/api/google/oauth/callback
GOOGLE_LOGIN_REDIRECT_URI=https://<render-backend>.onrender.com/auth/google/callback
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

Optional insight defaults may also be set in Render, although workspace DB
settings override them when configured:

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

Legacy service-account variables are not required for the OAuth staging path:

- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `GOOGLE_SERVICE_ACCOUNT_JSON_BASE64`
- `GOOGLE_APPLICATION_CREDENTIALS`
- `GOOGLE_SHEET_REGISTRY_JSON`

## TOKEN_ENCRYPTION_KEY

Generate one Fernet key per environment and keep it stable:

```powershell
.\backend\venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Changing `TOKEN_ENCRYPTION_KEY` after users connect Google OAuth can make stored
refresh tokens undecryptable. If the key is lost, users may need to reconnect
Google OAuth.

## Health Check Setup

Recommended Render health check:

```text
/api/health
```

Why:

- It is lightweight.
- It does not require auth.
- It does not open a database connection.
- It returns `{"status":"ok"}`.

Use deeper manual DB smoke testing after deployment:

```text
/api/health/db
```

`/api/health/db` opens a database connection and returns `503` when the
database is unavailable. It should not be the Render health check on Free tier
because a temporary database issue could restart an otherwise healthy web
service.

## Google OAuth Callback Setup

Backend callback URL:

```text
https://<render-backend>.onrender.com/api/google/oauth/callback
```

Rules:

- Must exactly match `GOOGLE_OAUTH_REDIRECT_URI` in Render env.
- Must exactly match an Authorized redirect URI in Google Cloud Console.
- Must use HTTPS for staging.
- Must not use localhost.
- Must pair with `FRONTEND_URL=https://<vercel-app>.vercel.app`.

Common OAuth failures:

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `redirect_uri_mismatch` | Render env and Google Console URI differ. | Copy the exact Render callback URL into both places. |
| Callback redirects to localhost | `FRONTEND_URL` is still local. | Set `FRONTEND_URL` to Vercel URL and redeploy. |
| OAuth start fails as unconfigured | Missing client ID, secret, redirect URI, or scopes. | Fill all Google OAuth env vars in Render. |
| Token exchange fails | Wrong client secret or redirect URI. | Check Google Cloud client and Render env values. |

## CORS and FRONTEND_URL Setup

Backend config treats these separately:

- `FRONTEND_URL`: where OAuth callbacks redirect users after backend work.
- `FRONTEND_AUTH_REDIRECT_URL`: optional legacy auth redirect destination.
- `CORS_ALLOWED_ORIGINS`: comma-separated browser origins allowed by FastAPI
  CORS middleware.

Staging values:

```env
FRONTEND_URL=https://<vercel-app>.vercel.app
FRONTEND_AUTH_REDIRECT_URL=https://<vercel-app>.vercel.app/auth/google/callback
CORS_ALLOWED_ORIGINS=https://<vercel-app>.vercel.app
```

If both a Vercel preview URL and production Vercel URL must call the backend,
add both origins separated by commas. Do not use wildcard CORS for staging if a
specific origin list is available.

## Migration Strategy

Do not run migrations automatically on every Render boot unless that behavior is
deliberately designed later.

Recommended staging sequence:

1. Choose the Supabase staging target.
2. Back up/export if using an existing database with real data.
3. Confirm `DATABASE_URL` and `DATABASE_MIGRATION_URL`.
4. Run migrations manually before smoke testing.
5. Confirm the `schema_migrations` table.
6. Verify required schema through Week 6 release readiness checks.

Command from repository root:

```powershell
.\backend\venv\Scripts\python.exe backend\scripts\run_migrations.py
```

Alternative if running from a Render shell after deployment:

```bash
python scripts/run_migrations.py
```

Migration 011 is required for workspace invitations. Confirm all migration
files are applied before testing dashboard, classification, settings, workspace
switcher, or invitation flows.

## Step-by-Step Render Setup From Scratch

1. Open Render.
2. Create a new Web Service.
3. Connect the GitHub repository.
4. Choose the deployment branch.
5. Select Docker runtime.
6. Set root directory to `backend`.
7. Set Dockerfile path to `backend/Dockerfile`.
8. Set Docker context to `backend` if Render exposes the field.
9. Set health check path to `/api/health`.
10. Add Render environment variables from this document.
11. Deploy.
12. Check build logs for dependency install and uvicorn start.
13. Open `/api/health`.
14. Open `/api/health/db`.
15. Add the Render callback URL to Google Cloud Console.
16. Update Vercel frontend env to use the Render URL.

## Post-Deploy Smoke Test

Health:

```powershell
Invoke-RestMethod `
  -Uri "https://<render-backend>.onrender.com/api/health"
```

DB health:

```powershell
Invoke-RestMethod `
  -Uri "https://<render-backend>.onrender.com/api/health/db"
```

Auth-protected example:

```powershell
$token = "PASTE_TOKEN_FROM_FRONTEND_AFTER_LOGIN"

Invoke-RestMethod `
  -Uri "https://<render-backend>.onrender.com/api/workspaces" `
  -Headers @{ Authorization = "Bearer $token" } |
ConvertTo-Json -Depth 10
```

Dashboard example with workspace:

```powershell
Invoke-RestMethod `
  -Uri "https://<render-backend>.onrender.com/api/dashboard/summary?year=2026" `
  -Headers @{
    Authorization = "Bearer $token"
    "X-Workspace-Id" = "PASTE_WORKSPACE_ID"
  } |
ConvertTo-Json -Depth 10
```

## Common Render Deployment Failures

| Failure | Symptom | Fix |
| --- | --- | --- |
| Wrong runtime auto-detected | `/api/health` is missing or a non-FastAPI page appears. | Use Docker runtime and `backend/Dockerfile`. |
| Wrong Docker context | Build cannot find `requirements.txt`. | Use Docker context `backend`. |
| Wrong module path | Uvicorn cannot import `app.main`. | Start from backend context; keep `app.main:app`. |
| App binds wrong host | Render cannot route traffic. | Ensure `--host 0.0.0.0`. |
| App ignores `$PORT` | Service fails health check. | Keep `--port ${PORT:-8000}` in Dockerfile. |
| Missing auth env | Backend crashes on startup. | Set dashboard/JWT/token env required by `config.py`. |
| Missing DB env | `/api/health/db` fails and DB-backed endpoints fail. | Set Supabase connection strings and SSL flags. |
| CORS blocked | Browser requests fail from Vercel. | Set exact Vercel URL in `CORS_ALLOWED_ORIGINS`. |
| OAuth mismatch | Google shows redirect mismatch. | Align Google Console and Render `GOOGLE_OAUTH_REDIRECT_URI`. |
| Free tier cold start | First request is slow. | Wait for spin-up or move to paid instance later. |

## Known Limitations

- Render Free services can sleep; first request may be slow.
- `backend/requirements.txt` includes heavier existing packages, so builds may
  take longer.
- `render.yaml` is now safer, but the first staging deployment can still be
  done manually in the Render dashboard to avoid blueprint confusion.
- Native Python runtime remains a fallback, not the recommended first attempt.
- No automatic migration job is configured yet.

## Follow-Up Tasks

- After Render backend is deployed, update Vercel env using
  `docs/WEEK7_FRONTEND_VERCEL_DEPLOYMENT.md`.
- In Week 7 Prompt E, run and validate migrations against the staging Supabase
  target.
- In Week 7 Prompt F, run end-to-end staging smoke tests.
- Consider a one-off Render job for migrations after the manual staging process
  is proven.
- Consider splitting or slimming heavy backend dependencies only if Render build
  time becomes a real blocker.
