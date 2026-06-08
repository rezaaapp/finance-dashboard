# Week 7 Staging Architecture

## Objective

Week 7 starts with a docs-first and audit-first staging plan. This prompt does
not deploy anything and does not change backend logic, frontend behavior, OAuth,
sync, classification, workspace invitations, dependencies, migrations, or AI
configuration.

The goal is to make the next deployment attempt cleaner by documenting the
current hosting artifacts, recommended free/low-cost staging architecture, and
the exact roadmap for future deployment prompts.

## Current Project Architecture Summary

The project is a multi-app repository:

- `apps/web`: React/Vite dashboard application.
- `apps/landing`: React/Vite landing page.
- `backend/app`: FastAPI backend application, app entrypoint
  `app.main:app`.
- `backend/db/migrations`: PostgreSQL schema migrations.
- `backend/scripts`: backend migration and local data processing utilities.
- `backend/node`: Node/TypeScript database and legacy utility scripts.
- `docs`: operational and QA documentation.

Production direction after Weeks 4-6:

- Google OAuth per user/workspace.
- Google Sheet sources stored in PostgreSQL.
- Google Sheet sync writes normalized transactions to PostgreSQL.
- Rule-based classification writes current classifications to PostgreSQL.
- Dashboard and Analytics read workspace-aware PostgreSQL data.
- Workspace switcher sends `X-Workspace-Id`.
- Workspace invitations use pending/accept/decline/cancel lifecycle.

## Recommended Staging Stack

Recommended first staging stack:

- Frontend: Vercel Hobby/Free.
- Backend: Render Free Web Service.
- Database: existing Supabase project for personal testing, or a separate
  Supabase staging project before inviting additional users.
- Domain: default Vercel and Render subdomains first.
- OAuth: Google OAuth Web Client with staging redirect URI.

Alternative:

- Frontend: Netlify Free if Vercel remains confusing.
- Backend: Railway or Fly.io only if Render is blocked.
- Backend paid small instance later if Render Free sleep/spin-up is too
  disruptive.

Important notes:

- Render Free services may spin down when idle; first request can be slow.
- Vercel should host frontend only in this architecture.
- FastAPI backend should not be forced into Vercel serverless unless the project
  is intentionally adapted for that runtime.
- Supabase remains the database for Week 7A.
- Use platform environment variables. Do not commit production/staging `.env`
  files.

## Why Free/Low-Cost First

Free/low-cost staging is appropriate because the immediate goal is validating
architecture, environment variables, OAuth callback URLs, CORS, migrations, and
workspace-aware behavior before paying for always-on infrastructure.

Move to paid services only after:

- OAuth staging works end-to-end.
- Sync and classification run reliably.
- Workspace switcher and invitations pass smoke tests.
- Render Free cold starts become a real usage problem.

## Frontend Hosting Plan

The dashboard app is Vite/React and builds to `apps/web/dist`.

Recommended Vercel setup: Option 1.

Option 1: repository root project

```text
Root Directory: .
Install Command: npm --prefix apps/web install --include=optional
Build Command: npm run build:web
Output Directory: apps/web/dist
```

Why Option 1 is recommended:

- Root `package.json` already has `build:web`.
- Root `vercel.json` already targets `apps/web/dist`.
- It keeps root-level scripts such as `security:check` and future monorepo
  commands visible.

Option 2: `apps/web` project

```text
Root Directory: apps/web
Install Command: npm install --include=optional
Build Command: npm run build
Output Directory: dist
```

This remains viable through manual Vercel settings, but the checked-in
app-level `apps/web/vercel.json` has been removed so the repository has one
canonical dashboard Vercel config.

Frontend environment variables:

```env
VITE_API_URL=https://<render-backend>.onrender.com
VITE_API_BASE_URL=https://<render-backend>.onrender.com
```

The production build validator rejects localhost API URLs, so staging must use
the Render backend URL.

Detailed frontend Vercel audit and setup guidance lives in:

```text
docs/WEEK7_FRONTEND_VERCEL_DEPLOYMENT.md
```

## Backend Hosting Plan

The backend is FastAPI with app path:

```text
backend/app/main.py
```

Python import path from `backend` root:

```text
app.main:app
```

Recommended Render setup using existing Dockerfile:

```text
Service type: Web Service
Runtime: Docker
Root Directory: backend
Dockerfile Path: backend/Dockerfile
Health Check Path: /api/health
```

The existing Dockerfile runs:

```text
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Alternative Render setup using Python runtime:

```text
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

If Render root is repository root instead:

```text
Build Command: pip install -r backend/requirements.txt
Start Command: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Recommendation: use the existing Docker setup first. It is already represented
by `backend/Dockerfile` and `render.yaml`.

Detailed backend Render audit and setup guidance lives in:

```text
docs/WEEK7_BACKEND_RENDER_DEPLOYMENT.md
```

## Database/Supabase Plan

Option A: use existing Supabase project for staging.

Pros:

- Fastest.
- No schema setup from scratch.

Cons:

- Staging and development data can mix.
- Testing can mutate real/personal data.

Option B: create separate Supabase staging project.

Pros:

- Safer for public beta.
- Migration state can be validated cleanly.

Cons:

- Requires new connection strings.
- Requires running all migrations.
- Requires separate seed/test data.

Recommendation:

- Personal/internal smoke test: existing Supabase is acceptable.
- Inviting other users or public beta: use a separate Supabase staging project.

Migration command:

```powershell
.\backend\venv\Scripts\python.exe backend\scripts\run_migrations.py
```

Staging env:

```env
DATABASE_URL=postgresql://...
DATABASE_MIGRATION_URL=postgresql://...
```

Before running migrations against a shared or real project:

- Backup/export current database.
- Confirm target database URL.
- Confirm `schema_migrations` table state.
- Run migration validation SQL from `docs/WEEK6_RELEASE_READINESS.md`.

## Google OAuth Staging Plan

Render backend callback URL:

```text
https://<render-backend>.onrender.com/api/google/oauth/callback
```

Vercel frontend URL:

```text
https://<vercel-frontend>.vercel.app
```

Backend env must match exactly:

```env
FRONTEND_URL=https://<vercel-frontend>.vercel.app
GOOGLE_OAUTH_REDIRECT_URI=https://<render-backend>.onrender.com/api/google/oauth/callback
CORS_ALLOWED_ORIGINS=https://<vercel-frontend>.vercel.app
```

Google Cloud Console checklist:

1. Open OAuth Web Client used for staging.
2. Add authorized redirect URI:
   `https://<render-backend>.onrender.com/api/google/oauth/callback`.
3. Add authorized JavaScript origin if needed:
   `https://<vercel-frontend>.vercel.app`.
4. Ensure backend `GOOGLE_OAUTH_REDIRECT_URI` matches the redirect URI exactly.
5. Ensure backend `FRONTEND_URL` points to the Vercel staging URL.

## Environment Variable Matrix

Detailed Week 7 staging env and secret management guidance lives in:

```text
docs/WEEK7_ENVIRONMENT_SETUP.md
```

| Variable | Used by | Local value example | Staging value example | Required? | Notes |
| --- | --- | --- | --- | --- | --- |
| `DATABASE_URL` | Backend, Node DB scripts | `postgresql://postgres:...@localhost:5432/finance_dashboard` | Supabase pooled/runtime connection | Yes | Runtime app connection. |
| `DATABASE_MIGRATION_URL` | Migration runner | blank or local direct URL | Supabase direct/session connection | Recommended | Use when provider requires a separate migration URL. |
| `DATABASE_SSL` | Backend DB config | `false` | `true` | Yes for hosted DB | Existing examples include this flag. |
| `DATABASE_SSL_REJECT_UNAUTHORIZED` | Backend DB config | `true` | `true` | Recommended | Set false only for known local/proxy SSL issues. |
| `FRONTEND_URL` | Backend OAuth redirects | `http://127.0.0.1:5173` | `https://<vercel-frontend>.vercel.app` | Yes | Must match staging frontend. |
| `FRONTEND_AUTH_REDIRECT_URL` | Backend/auth redirects | `http://localhost:5173/auth/google/callback` | `https://<vercel-frontend>.vercel.app/auth/google/callback` | If used | Keep aligned with frontend routes. |
| `GOOGLE_OAUTH_CLIENT_ID` | Backend OAuth | local Google OAuth client | staging Google OAuth client | Yes | Some notes may call this `GOOGLE_CLIENT_ID`; existing code/examples use `GOOGLE_OAUTH_CLIENT_ID`. |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Backend OAuth | local secret | staging secret | Yes | Store in Render env only. |
| `GOOGLE_OAUTH_REDIRECT_URI` | Backend OAuth | `http://127.0.0.1:8000/api/google/oauth/callback` | `https://<render-backend>.onrender.com/api/google/oauth/callback` | Yes | Must match Google Console exactly. |
| `GOOGLE_OAUTH_SCOPES` | Backend OAuth | `openid email profile https://www.googleapis.com/auth/spreadsheets.readonly` | same | Yes | Keep minimal scopes. |
| `TOKEN_ENCRYPTION_KEY` | Backend token encryption | generated local Fernet key | generated staging Fernet key | Yes | Strong, environment-specific. Do not rotate casually after tokens exist. |
| `JWT_SECRET` | Backend auth | local random string | staging random string | Yes | Different per environment. |
| `DASHBOARD_AUTH_TOKEN` | Legacy/static auth | local random token | staging random token if legacy path remains | If legacy path used | Keep secret. |
| `SUPER_ADMIN_EMAILS` | Backend roles | `local_admin@example.com` | staging admin email(s) | Yes for admin setup | Comma-separated if supported by config. |
| `CORS_ALLOWED_ORIGINS` | Backend CORS | `http://localhost:5173,http://127.0.0.1:5173` | `https://<vercel-frontend>.vercel.app` | Yes | Must include staging frontend. |
| `AI_CLASSIFICATION_ENABLED` | Backend classification config | `false` | `false` | Yes | Rule-based only. |
| `AI_PROVIDER` | Backend classification config | `rule_based` | `rule_based` | Yes | No AI provider deployment. |
| `AI_MODEL` | Backend classification config | `none` | `none` | Yes | No local LLM/API. |
| `AI_MAX_TRANSACTIONS_PER_RUN` | Backend classification limits | `500` | `500` | Recommended | Keep bounded. |
| `MAX_GOOGLE_SHEET_SOURCES` | Backend data source limit | `5` | `5` | Recommended | Controls workspace data source count. |
| `USE_MOCK_DATA` | Backend runtime | `false` | `false` | Recommended | Staging should test real integration with safe data. |
| `VITE_API_URL` | Frontend dashboard | `http://127.0.0.1:8000` | `https://<render-backend>.onrender.com` | Yes | Must not be localhost in production build. |
| `VITE_API_BASE_URL` | Frontend dashboard | `http://127.0.0.1:8000` | `https://<render-backend>.onrender.com` | Yes for compatibility | Keep both frontend env names. |
| `VITE_GUEST_MODE_MULTIPLIER` | Frontend privacy UI | `0.75` | `0.75` | Optional | Demo masking only. |
| `VITE_DASHBOARD_URL` | Landing app | `http://127.0.0.1:5173` | `https://<vercel-frontend>.vercel.app` | Landing only | Needed if landing is deployed. |

Security notes:

- Do not commit real env values.
- Use Render and Vercel environment variable dashboards.
- Use a strong `TOKEN_ENCRYPTION_KEY`.
- Use different keys/secrets per environment.

## Existing Vercel/Deployment Artifact Audit

| File/path | Current purpose | Still relevant? | Risk/issue | Recommendation |
| --- | --- | --- | --- | --- |
| `vercel.json` | Root-level Vercel config for dashboard SPA. Installs `apps/web`, builds root `npm run build:web`, outputs `apps/web/dist`, rewrites to `index.html`. | Yes, final dashboard Vercel setup. | Must be paired with Vercel Root Directory `.`. | Keep as the single canonical dashboard Vercel config. |
| `apps/web/vercel.json` | Former app-level Vercel config for `apps/web` root setup. | No longer checked in after Prompt D. | Keeping both root and app configs made root/build/output selection ambiguous. | Removed; use root setup or configure app-root manually in Vercel only if intentionally switching strategy later. |
| `apps/web/scripts/validate-env.mjs` | Prevents production frontend build when API env is missing, localhost, or invalid. | Yes. | Build fails if Vercel env is missing or still localhost. | Keep. Document `VITE_API_URL` and `VITE_API_BASE_URL` as required. |
| `apps/web/vite.config.js` | Vite React/Tailwind config. | Yes. | No deployment issue found. | Keep. |
| `apps/landing/vite.config.js` | Landing Vite config. | Yes if landing deployed. | Separate app can be confused with dashboard in Vercel. | Keep; deploy landing as separate project later if needed. |
| `package.json` | Root scripts for web/landing build, lint, security check, DB utilities. | Yes. | `build` currently aliases web only; platform users may assume it builds all apps. | Use explicit `build:web` for dashboard staging docs. |
| `apps/web/package.json` | Dashboard app scripts and Node engine `22.x`. | Yes. | Vercel project must use compatible Node version. | Keep; confirm Vercel Node 22 support/settings. |
| `apps/landing/package.json` | Landing app scripts and Node engine `22.x`. | Yes. | Only relevant if landing is deployed. | Keep. |
| `render.yaml` | Render Blueprint for Docker web service. | Partly. | Env list is legacy/service-account oriented and CORS points to an old Vercel URL. It may not include all OAuth/Supabase env needed now. | Do not delete. Treat as cleanup/update candidate in Week 7 Prompt C. |
| `backend/Dockerfile` | Docker image for FastAPI backend from `backend` context. | Yes. | Needs Render config to use `backend` root/context correctly. | Recommended backend staging path. |
| `backend/requirements.txt` | Python dependencies for FastAPI backend. | Yes. | Includes heavier packages such as pandas/scikit-learn; acceptable for existing backend but affects cold build/start. | Keep; no dependency changes in Week 7A. |
| `DEPLOY_RENDER_VERCEL.md` | Older Render/Vercel deployment guide. | Partly. | It is service-account oriented and references old Vercel URL/CORS. Week 6 production direction prefers OAuth. | Keep as historical doc; update or supersede after Week 7 deployment prompts. |
| `.env.example` | Root env template for local/staging reference. | Yes. | Contains legacy Gemini placeholders and service account examples; could confuse staging users. | Keep; staging doc clarifies rule-based/no AI and OAuth direction. |
| `backend/.env.example` | Backend env template. | Yes. | Contains legacy Gemini/service-account placeholders. | Keep; document OAuth env as required for staging. |
| `apps/web/.env.example` | Dashboard env template. | Yes. | Localhost values are correct for local but invalid for production build. | Keep; staging doc specifies platform env values. |
| `scripts/security-check.ps1` | Prevents staged secret-like files from being committed. | Yes. | Only checks staged files; unstaged local secrets can still exist. | Keep and run before commits. |
| `start-local*.bat` | Local development start helpers. | Yes for local only. | Not deployment scripts. | Keep; do not use as hosting commands. |
| `.github/workflows` | CI/CD workflow folder. | Not present in current audit. | No auto-deploy workflow found. | No action. |
| `netlify.toml` | Netlify config. | Not present. | Netlify setup would need manual configuration or a new file later. | Add only if Netlify is selected later. |
| `railway.json` | Railway config. | Not present. | Railway setup would need manual configuration later. | Add only if Railway is selected later. |
| `Procfile` | Procfile hosting config. | Not present. | Not needed for Docker Render path. | No action. |
| `docker-compose.yml` | Compose config. | Not present. | Not needed for initial staging. | No action. |

Cleanup candidates for later prompts:

- `render.yaml`: update env list for OAuth/Supabase staging and remove old CORS
  default.
- `DEPLOY_RENDER_VERCEL.md`: supersede service-account guidance with OAuth
  staging guidance.
- Root `vercel.json`: now uses `buildCommand: npm run build:web`.
- Vercel project root is now documented as repo root `.` for the dashboard.

## Deployment Risk List

| Risk | Mitigation |
| --- | --- |
| Vercel wrong root directory | Choose one canonical setup before deployment. Recommended: root directory `.` with `npm run build:web`. |
| Vercel wrong output directory | Use `apps/web/dist` for root setup or `dist` for `apps/web` root setup. |
| Vercel env still localhost | Set `VITE_API_URL` and `VITE_API_BASE_URL` to Render URL; validator should catch localhost. |
| Render wrong start command | Prefer Docker setup already encoded in `backend/Dockerfile`. |
| Render Free cold start/spin down | Expect slow first request; use manual warm-up or move to paid instance later. |
| Google OAuth redirect mismatch | Copy exact Render callback URL into Google Cloud and backend env. |
| CORS blocked frontend | Set `CORS_ALLOWED_ORIGINS` to exact Vercel URL. |
| Supabase connection string wrong | Verify DB health endpoint and `schema_migrations` before smoke test. |
| Migrations not applied | Run migration command and validation SQL before frontend smoke test. |
| `TOKEN_ENCRYPTION_KEY` changed accidentally | Generate once per environment and keep stable; changing it can break stored token decrypt. |
| Workspace switcher stale localStorage | Test invalid stored workspace ID and switching between workspaces after deploy. |
| Frontend talks to wrong backend | Inspect Network tab and confirm API host is Render staging URL. |

## Decision Log

| Decision | Status | Rationale |
| --- | --- | --- |
| Use Vercel for dashboard staging frontend first | Recommended | Existing config/scripts already support Vite static hosting. |
| Use Render for backend staging first | Recommended | Existing Dockerfile and Render blueprint exist; FastAPI suits a web service. |
| Avoid Vercel serverless for FastAPI backend | Recommended | Current backend is a conventional long-running FastAPI app. |
| Keep Supabase as database | Recommended | Current app already targets PostgreSQL/Supabase. |
| Use default platform subdomains first | Recommended | Reduces domain/DNS complexity during staging. |
| Do not cleanup old deployment files in Week 7A | Accepted | This prompt is audit/plan only. |

## Step-by-Step Next Prompts

Prompt B - Environment & Secret Management Preparation:

- Produce exact staging env list for Render, Vercel, Supabase, and Google Cloud.
- Generate/check secret requirements without committing real values.
- Decide existing Supabase vs separate staging Supabase.

Prompt C - Backend Render Deployment Preparation:

- Update/confirm Render settings.
- Decide Docker vs Python runtime.
- Prepare Render env checklist and health checks.
- Audit `backend/Dockerfile`, update `render.yaml` placeholders if safe, and
  document the final Render backend strategy.

Prompt D - Frontend Vercel Deployment Preparation:

- Use repository root `.` as the final dashboard Vercel setup.
- Keep root `vercel.json` as the single checked-in Vercel config.
- Prepare exact Vercel build/output/env settings.

Prompt E - Staging Database Migration & Validation:

- Run migrations against chosen staging database.
- Validate `schema_migrations` and required tables.
- Confirm workspace/classification/settings/invitation schema.

Prompt F - End-to-End Staging Smoke Test:

- Test auth, OAuth, data source connect, sync, dashboard, analytics, workspace
  switcher, and invitations against staging URLs.

Prompt G - Limited Public Beta Checklist:

- Finalize limitations, monitoring, support workflow, invite policy, rollback
  path, and data privacy notice for limited testers.

## Manual Checklist Before Actual Deployment

- Pick canonical frontend hosting setup: root `.` or `apps/web`.
- Pick database strategy: existing Supabase or separate staging Supabase.
- Confirm Render backend URL.
- Confirm Vercel frontend URL.
- Configure Google OAuth redirect URI and frontend origin.
- Configure Render env variables.
- Configure Vercel env variables.
- Run migrations.
- Run `npm run lint`.
- Run `npm run build:web` with staging API env.
- Run `npm run security:check`.
- Run `git diff --check`.
- Verify no real `.env`, credential JSON, token, private key, or generated
  private output is staged.
- Run backend health and DB health checks.
- Run workspace/invitation smoke tests.
