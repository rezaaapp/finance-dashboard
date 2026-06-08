# Week 7 Environment Setup

## Objective

This document prepares safe environment and secret management for staging
deployment on Vercel, Render, Supabase, and Google OAuth. It is docs-first and
env-audit-first: no deployment happens here, no application behavior changes,
and no real secrets are documented.

## Environment Strategy

Use separate environment values for local, staging, and future production.
Committed files may contain placeholders only. Real values belong in:

- Render environment variables for backend secrets.
- Vercel environment variables for public dashboard build-time values.
- Supabase project settings for database connection strings.
- Google Cloud Console for OAuth client configuration.

Staging should start with platform default domains:

- Frontend: `https://<vercel-app>.vercel.app`
- Backend: `https://<render-backend>.onrender.com`
- OAuth callback:
  `https://<render-backend>.onrender.com/api/google/oauth/callback`

## Env Artifact Audit

| File/path | Purpose | Relevant env vars | Staging-ready? | Risk/issue | Recommendation |
| --- | --- | --- | --- | --- | --- |
| `.env.example` | Combined local template for backend, dashboard, and landing. | DB, auth, OAuth, CORS, AI guard, Vite URLs. | Mostly, as a placeholder reference. | Localhost values are correct for local but invalid for staging; legacy Gemini/service-account placeholders can confuse staging setup. | Keep. Use this doc for staging values and do not copy localhost values into platform env. |
| `backend/.env.example` | Backend-specific local template. | `DATABASE_URL`, OAuth, CORS, `TOKEN_ENCRYPTION_KEY`, classification env, insight thresholds. | Mostly, as backend placeholder reference. | Same legacy/service-account placeholders; staging needs Render-specific OAuth/CORS values. | Keep. Use Render env dashboard for real staging values. |
| `apps/web/.env.example` | Dashboard frontend local template. | `VITE_API_URL`, `VITE_API_BASE_URL`, `VITE_GUEST_MODE_MULTIPLIER`. | Yes for local, not staging values. | Localhost API values will fail production build validator. | Keep. In Vercel set both API vars to Render backend URL. |
| `backend/app/config.py` | Runtime backend settings loader. Loads repo `.env`, then `backend/.env` with override. | DB, OAuth, frontend URLs, CORS, auth, encryption, classification, insight thresholds. | Yes with correct env. | Requires `DASHBOARD_USERNAME`, `DASHBOARD_PASSWORD`, `DASHBOARD_AUTH_TOKEN`, `JWT_SECRET`/token fallback, and encryption secret fallback. | Document required Render env explicitly. |
| `apps/web/src/api/config.js` | Frontend API URL normalizer and endpoint derivation. | `VITE_API_URL`, `VITE_API_BASE_URL`. | Yes. | Uses `VITE_API_URL || VITE_API_BASE_URL`; only `VITE_` vars are browser-visible. | Set both Vite vars to the same Render backend base URL for compatibility. |
| `apps/web/scripts/validate-env.mjs` | Production build guard for dashboard. | `VITE_API_URL`, `VITE_API_BASE_URL`, optional local `.env` fallback. | Yes. | Accepts either API var but rejects localhost/invalid URLs. Missing env fails build. | Keep. This protects Vercel from accidentally building against localhost. |
| `render.yaml` | Existing Render Docker blueprint. | Old sheet registry/service-account env, `CORS_ALLOWED_ORIGINS`. | Partly. | Env list is legacy and CORS points to an old Vercel URL; OAuth/Supabase staging env is incomplete. | Do not change in Prompt B. Update/review in Week 7 Prompt C. |
| `vercel.json` | Root Vercel config for dashboard SPA. | Build uses env through `npm run build:web`. | Yes, final dashboard Vercel setup. | Must be paired with Vercel Root Directory `.` and output `apps/web/dist`. | Keep as the single checked-in dashboard Vercel config. |
| `apps/web/vercel.json` | Former app-root Vercel config for dashboard SPA. | N/A. | Removed in Prompt D. | Keeping both configs made root/build/output choices ambiguous. | Use root setup; configure app-root manually only if intentionally changing strategy later. |
| `docs/ENVIRONMENT.md` | General env reference. | Local/dev env, OAuth, DB, AI guard, frontend vars. | Useful but broad. | Not staging-specific. | Link this Week 7 staging doc from it. |
| `docs/GOOGLE_OAUTH.md` | OAuth setup reference. | OAuth client ID/secret/redirect, frontend URL, encryption key. | Useful but local/production generic. | Needs explicit staging link/checklist. | Link this Week 7 staging doc from it. |

## Backend Render Environment Variables

Use Render Project/Service environment variables. Do not commit real values.

| Variable | Used by | Local value example | Staging value example | Required? | Secret? | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `DATABASE_URL` | Backend runtime and current Node DB scripts | `postgresql://postgres:...@localhost:5432/finance_dashboard` | `<supabase-runtime-or-pooled-connection-string>` | Yes | Yes | Backend only. Never expose to frontend. |
| `DATABASE_MIGRATION_URL` | Migration runner | blank or local direct URL | `<supabase-direct-or-session-connection-string>` | If used | Yes | Useful when Supabase migration/direct connection differs from runtime URL. |
| `DATABASE_SSL` | Backend DB config | `false` | `true` | Recommended | No | Hosted Supabase/PostgreSQL should use SSL. |
| `DATABASE_SSL_REJECT_UNAUTHORIZED` | Backend DB config | `true` | `true` | Recommended | No | Keep strict unless a known provider/proxy requires otherwise. |
| `DATABASE_POOL_MAX` | Backend DB pool | `10` | `10` | Optional | No | Tune later if Render/Supabase limits require it. |
| `DATABASE_IDLE_TIMEOUT_MS` | Backend DB pool | `30000` | `30000` | Optional | No | Existing config supports this. |
| `DATABASE_CONNECTION_TIMEOUT_MS` | Backend DB pool | `10000` | `10000` | Optional | No | Existing config supports this. |
| `FRONTEND_URL` | OAuth callback redirect UX | `http://127.0.0.1:5173` | `https://<vercel-app>.vercel.app` | Yes | No | Must point to dashboard staging frontend. |
| `FRONTEND_AUTH_REDIRECT_URL` | Auth redirect if used | `http://localhost:5173/auth/google/callback` | `https://<vercel-app>.vercel.app/auth/google/callback` | If used | No | Keep aligned with frontend routes. |
| `GOOGLE_OAUTH_CLIENT_ID` | Google OAuth | `<local-client-id>.apps.googleusercontent.com` | `<staging-client-id>.apps.googleusercontent.com` | Yes | No | Some planning docs may say `GOOGLE_CLIENT_ID`; current code uses `GOOGLE_OAUTH_CLIENT_ID`. |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google OAuth | `<local-client-secret>` | `<staging-client-secret>` | Yes | Yes | Store only in Render/secret manager. |
| `GOOGLE_OAUTH_REDIRECT_URI` | Google OAuth callback | `http://127.0.0.1:8000/api/google/oauth/callback` | `https://<render-backend>.onrender.com/api/google/oauth/callback` | Yes | No | Must match Google Console exactly. |
| `GOOGLE_LOGIN_REDIRECT_URI` | Legacy Google login if used | `http://127.0.0.1:8000/auth/google/callback` | `https://<render-backend>.onrender.com/auth/google/callback` | If used | No | Separate from Google Sheets connection callback. |
| `GOOGLE_OAUTH_SCOPES` | Google OAuth | `openid email profile https://www.googleapis.com/auth/spreadsheets.readonly` | same | Yes | No | Keep minimal. |
| `TOKEN_ENCRYPTION_KEY` | OAuth token encryption | `<generate-secure-fernet-key>` | `<generate-secure-fernet-key>` | Yes | Yes | Stable per environment. Changing it can break decrypting stored OAuth tokens. |
| `TOKEN_ENCRYPTION_SECRET` | Backend token crypto fallback/secret | `<long-random-secret>` | `<long-random-secret>` | Recommended | Yes | Existing config falls back to `JWT_SECRET` or `DASHBOARD_AUTH_TOKEN` if missing. |
| `JWT_SECRET` | App auth tokens | `<long-random-jwt-secret>` | `<long-random-jwt-secret>` | Yes | Yes | Different per environment. |
| `JWT_EXPIRES_IN_MINUTES` | App auth token lifetime | `10080` | `10080` | Optional | No | Existing default is one week. |
| `DASHBOARD_USERNAME` | Legacy/local login compatibility | `local_admin@example.com` | `<staging-admin-email>` | Yes currently | Yes-ish | Required by current config validation. |
| `DASHBOARD_PASSWORD` | Legacy/local login compatibility | `<local-password>` | `<staging-password>` | Yes currently | Yes | Required by current config validation. |
| `DASHBOARD_AUTH_TOKEN` | Legacy/static token fallback | `<long-random-token>` | `<long-random-token>` | Yes currently | Yes | Required by current config validation and JWT fallback. |
| `SUPER_ADMIN_EMAILS` | Admin role bootstrap | `local_admin@example.com` | `<staging-admin-email>` | Recommended | No | Use staging admin email(s). |
| `CORS_ALLOWED_ORIGINS` | Backend CORS | `http://localhost:5173,http://127.0.0.1:5173` | `https://<vercel-app>.vercel.app` | Yes | No | Comma-separated list. Do not use wildcard for staging if avoidable. |
| `USE_MOCK_DATA` | Backend runtime | `false` | `false` | Recommended | No | Staging should test real integration with safe data. |
| `MAX_GOOGLE_SHEET_SOURCES` | Workspace source limit | `5` | `5` | Optional | No | Existing default is 5. |
| `GOOGLE_SHEET_ID` | Legacy/local single sheet | fake local placeholder | blank or safe placeholder | Legacy/local only | No | Not required for OAuth data-source staging flow. |
| `GOOGLE_SHEET_REGISTRY_JSON` | Legacy/local registry | fake JSON | `{}` or safe placeholder | Legacy/local only | No | Not required for OAuth data-source staging flow. |
| `AI_CLASSIFICATION_ENABLED` | Rule-based classification guard | `false` | `false` | Yes | No | Keep disabled. |
| `AI_PROVIDER` | Classification provider marker | `rule_based` | `rule_based` | Yes | No | No external AI provider. |
| `AI_MODEL` | Classification model marker | `none` | `none` | Yes | No | No local LLM/API. |
| `AI_ONLY_LOW_CONFIDENCE` | Future AI guard | `true` | `true` | Optional | No | Existing config supports this. |
| `AI_CONFIDENCE_THRESHOLD` | Low confidence threshold | `0.75` | `0.75` | Optional | No | Existing config supports this. |
| `AI_MAX_TRANSACTIONS_PER_RUN` | Classification batch limit | `500` | `500` | Optional | No | Keep bounded. |
| `INSIGHT_*` thresholds | Rule-based insight defaults | example ratios/counts | same defaults or tuned values | Optional | No | Workspace DB settings override defaults. |

## Frontend Vercel Environment Variables

Only `VITE_*` variables are exposed to the browser. Never put backend secrets,
database URLs, OAuth client secrets, bearer tokens, or encryption keys in Vercel
frontend env.

Required for dashboard staging:

| Variable | Used by | Local value example | Staging value example | Required? | Secret? | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `VITE_API_URL` | Frontend API base URL | `http://127.0.0.1:8000` | `https://<render-backend>.onrender.com` | Yes | No | `apps/web/src/api/config.js` checks this first. |
| `VITE_API_BASE_URL` | Frontend API base URL fallback | `http://127.0.0.1:8000` | `https://<render-backend>.onrender.com` | Recommended/Yes for compatibility | No | Keep both names set to the same Render URL. |
| `VITE_GUEST_MODE_MULTIPLIER` | Privacy/guest UI | `0.75` | `0.75` | Optional | No | Demo masking only. |

Actual usage:

- `apps/web/src/api/config.js` uses
  `import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL`.
- `apps/web/scripts/validate-env.mjs` accepts either value but fails build if
  neither exists.
- `validate-env.mjs` rejects `localhost`, `127.0.0.1`, and `0.0.0.0` for
  production builds.

Vercel setup:

1. Open Vercel Project Settings > Environment Variables.
2. Add `VITE_API_URL`.
3. Add `VITE_API_BASE_URL`.
4. Apply to Production and Preview as needed.
5. Redeploy after changing env values.

## Supabase Environment Setup

Variables:

- `DATABASE_URL`
- `DATABASE_MIGRATION_URL`

Checklist:

1. Decide existing Supabase project vs separate staging Supabase project.
2. For personal staging, existing Supabase is acceptable.
3. For beta users, separate staging Supabase is safer.
4. Copy connection strings from Supabase project settings.
5. Use backend/Render env only; never expose DB URLs to frontend.
6. Run migrations before smoke test.
7. Validate `schema_migrations`.
8. Backup/export before applying migrations to shared databases.

Migration command:

```powershell
.\backend\venv\Scripts\python.exe backend\scripts\run_migrations.py
```

Validation SQL:

```sql
select filename, applied_at
from public.schema_migrations
order by filename;
```

## Google OAuth Staging Setup

Google Cloud Console:

1. Open the existing OAuth client or create a staging OAuth Web Client.
2. Add Authorized JavaScript origin:

```text
https://<vercel-app>.vercel.app
```

3. Add Authorized redirect URI:

```text
https://<render-backend>.onrender.com/api/google/oauth/callback
```

4. Keep local redirect URI for local development:

```text
http://127.0.0.1:8000/api/google/oauth/callback
```

Backend Render env:

```env
GOOGLE_OAUTH_CLIENT_ID=<staging-oauth-client-id>.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=<staging-oauth-client-secret>
GOOGLE_OAUTH_REDIRECT_URI=https://<render-backend>.onrender.com/api/google/oauth/callback
FRONTEND_URL=https://<vercel-app>.vercel.app
```

Frontend Vercel env:

```env
VITE_API_URL=https://<render-backend>.onrender.com
VITE_API_BASE_URL=https://<render-backend>.onrender.com
```

Important:

- Redirect URI must match exactly.
- `http` vs `https` mismatch will fail.
- Host mismatch will fail.
- Trailing slash mismatch can fail.
- Google Sheets OAuth callback is different from legacy Google login callback.

## CORS and Frontend URL Rules

Backend config currently treats these separately:

- `FRONTEND_URL`: frontend destination for OAuth user experience redirects.
- `FRONTEND_AUTH_REDIRECT_URL`: optional auth redirect URL for legacy login.
- `CORS_ALLOWED_ORIGINS`: comma-separated origins allowed by FastAPI CORS.

Staging required:

```env
FRONTEND_URL=https://<vercel-app>.vercel.app
CORS_ALLOWED_ORIGINS=https://<vercel-app>.vercel.app
```

Local required:

```env
FRONTEND_URL=http://127.0.0.1:5173
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Do not use wildcard CORS in staging if avoidable. If multiple frontend origins
are needed, add them as a comma-separated list in `CORS_ALLOWED_ORIGINS`.

## TOKEN_ENCRYPTION_KEY Rules

`TOKEN_ENCRYPTION_KEY` protects stored OAuth tokens. It must be:

- Fernet-compatible.
- Strong.
- Secret.
- Stable per environment.
- Different between local, staging, and future production.

Placeholder:

```env
TOKEN_ENCRYPTION_KEY=<generate-secure-fernet-key>
```

Generate locally with existing backend dependencies:

```powershell
.\backend\venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Important:

- Never commit the real key.
- Store staging key in Render env variables.
- If changed after OAuth tokens are stored, encrypted refresh tokens may become
  undecryptable.
- Rotation requires users to reconnect Google OAuth or a deliberate migration
  strategy.

## AI / Rule-Based Classification Env

Week 7 staging uses rule-based classification only.

Required safe values:

```env
AI_CLASSIFICATION_ENABLED=false
AI_PROVIDER=rule_based
AI_MODEL=none
```

Optional existing guards:

```env
AI_ONLY_LOW_CONFIDENCE=true
AI_CONFIDENCE_THRESHOLD=0.75
AI_MAX_TRANSACTIONS_PER_RUN=500
```

No external AI API key is required for staging. Legacy `GEMINI_*` placeholders
may exist in `.env.example`, but they are not required for the current Week 7
staging path.

## Workspace / Multi-User Env Considerations

- Workspace switcher depends on authenticated API requests.
- Frontend sends `X-Workspace-Id`.
- Backend validates workspace membership server-side.
- No extra env is required for workspace switcher beyond normal auth/API URL.
- Invitation flow does not require email delivery yet.
- No SMTP or email provider env is required for Week 7 staging.

## Secret Management Rules

- Do not commit `.env`, real credentials, tokens, service account JSON, PEM/key
  files, or generated private output.
- Use Render env dashboard for backend secrets.
- Use Vercel env dashboard only for public `VITE_*` values.
- Use Supabase dashboard to copy DB connection strings into Render, not
  frontend.
- Do not paste secrets into docs, issues, screenshots, logs, or chat.
- If a secret is exposed, rotate it and redeploy.

## Secret Rotation Notes

| Secret | Rotation impact | Recommended action |
| --- | --- | --- |
| `DATABASE_URL` | Backend DB connection changes. | Rotate in Supabase, update Render env, redeploy, check `/api/health/db`. |
| `GOOGLE_OAUTH_CLIENT_SECRET` | OAuth start/token exchange can fail until env is updated. | Update Google Cloud and Render together, redeploy, test OAuth start. |
| `TOKEN_ENCRYPTION_KEY` | Existing encrypted OAuth tokens can fail to decrypt. | Avoid routine rotation. If required, plan reconnect or token migration. |
| `JWT_SECRET` | Existing sessions become invalid. | Rotate during maintenance window; users may need to login again. |
| `DASHBOARD_AUTH_TOKEN` | Legacy/static API access changes. | Update clients/scripts that still use it. |

Rollback notes:

- If an env update breaks staging, restore the previous Render/Vercel env value
  from a secure password manager or deployment notes.
- Do not recover secrets from Git history.
- If `TOKEN_ENCRYPTION_KEY` was changed and OAuth breaks, restore the previous
  key if available; otherwise users must reconnect Google OAuth.

## Validation Commands

Docs/env-only verification:

```powershell
git diff --check
npm run lint
$env:VITE_API_URL="https://api.example.com"
$env:VITE_API_BASE_URL="https://api.example.com"
npm run build:web
npm run security:check
```

Backend smoke checks after env is deployed:

```powershell
Invoke-RestMethod -Uri "https://<render-backend>.onrender.com/api/health"
Invoke-RestMethod -Uri "https://<render-backend>.onrender.com/api/health/db"
```

Frontend build check:

- Confirm Vercel build log prints a non-localhost API URL.
- Confirm frontend Network tab calls the Render backend URL.

## Common Deployment Env Mistakes

| Mistake | Symptom | Fix |
| --- | --- | --- |
| Vercel frontend still points to localhost | Browser network/API calls fail. | Set `VITE_API_URL` and `VITE_API_BASE_URL` to Render backend URL. |
| `GOOGLE_OAUTH_REDIRECT_URI` mismatch | Google shows `redirect_uri_mismatch`. | Match Google Cloud Console exactly. |
| `FRONTEND_URL` wrong | OAuth callback redirects to the wrong frontend. | Set `FRONTEND_URL` to Vercel staging URL. |
| CORS missing Vercel URL | Browser shows CORS error. | Add exact Vercel URL to `CORS_ALLOWED_ORIGINS`. |
| `TOKEN_ENCRYPTION_KEY` changed | Google token decrypt fails or connection appears broken. | Restore previous key or reconnect Google OAuth. |
| `DATABASE_URL` wrong | DB health or migrations fail. | Validate Supabase connection string and SSL flags. |
| Missing `VITE_API_BASE_URL` | Build or compatibility path can fail later. | Set both Vite API env vars. |
| Backend secret placed in Vercel env | Secret becomes browser-exposed if prefixed with `VITE_`. | Remove secret from frontend env and rotate if exposed. |

## Pre-Deployment Checklist

- Pick staging frontend URL.
- Pick staging backend URL.
- Choose existing Supabase or separate staging Supabase.
- Configure Render backend env.
- Configure Vercel frontend env.
- Configure Google OAuth redirect URI and origin.
- Generate and store `TOKEN_ENCRYPTION_KEY`.
- Confirm `CORS_ALLOWED_ORIGINS` includes Vercel URL.
- Run migrations.
- Validate `/api/health` and `/api/health/db`.
- Run frontend build with staging API URL.
- Confirm no real `.env` or secret files are staged.

## Known Limitations

- `render.yaml` still needs a Week 7 Prompt C review for OAuth/Supabase staging
  env completeness.
- Prompt D chose repository root `.` as the canonical Vercel setup and removed
  the redundant app-level Vercel config.
- Email delivery for workspace invitations is not implemented, so no SMTP env
  is needed yet.
- Legacy service-account/Gemini placeholders remain in examples for historical
  compatibility but are not required for Week 7 staging.

## Next Prompt Roadmap

Prompt C - Backend Render Deployment Preparation:

- Review/update Render settings and `render.yaml` if approved.
- Confirm Docker runtime and backend health checks.
- Prepare Render env entry checklist.

Current backend Render deployment guidance:

```text
docs/WEEK7_BACKEND_RENDER_DEPLOYMENT.md
```

Prompt D - Frontend Vercel Deployment Preparation:

- Use root `.` as the final dashboard Vercel setup.
- Keep root `vercel.json` as the single checked-in Vercel config.
- Prepare final Vercel build/output/env settings.

Current frontend Vercel deployment guidance:

```text
docs/WEEK7_FRONTEND_VERCEL_DEPLOYMENT.md
```

Prompt E - Staging Database Migration & Validation:

- Run migrations against selected Supabase target.
- Validate schema, workspaces, classifications, settings, and invitations.

Prompt F - End-to-End Staging Smoke Test:

- Test login, OAuth, data source connect, sync, dashboard, analytics, workspace
  switcher, and invitations.
