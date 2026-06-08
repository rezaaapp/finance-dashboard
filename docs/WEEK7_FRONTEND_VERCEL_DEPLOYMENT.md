# Week 7 Frontend Vercel Deployment

## Objective

This document prepares the React/Vite dashboard frontend for Vercel staging
deployment. It is deployment-prep-first: no deployment is performed here, no
real secrets are documented, and no backend business logic, frontend app
behavior, OAuth flow, Google Sheet sync, classification logic, workspace
invitation logic, dependency, or AI provider is changed.

## Current Frontend Architecture Summary

- Dashboard app: `apps/web`
- Framework: React with Vite
- Build output: `apps/web/dist`
- Root build script: `npm run build:web`
- Web build script: `node scripts/validate-env.mjs && vite build`
- Frontend API config: `apps/web/src/api/config.js`
- Production env validator: `apps/web/scripts/validate-env.mjs`
- Backend dependency: Render FastAPI base URL, for example
  `https://<render-backend>.onrender.com`

The dashboard is a browser-only SPA. Vercel must serve `index.html` for nested
routes such as `/dashboard`, `/analytics`, `/configuration`, and
`/settings/data-sources`.

## Existing Vercel Artifact Audit

| Artifact | Current role | Audit result | Decision |
| --- | --- | --- | --- |
| `vercel.json` | Root-level Vercel config. | Assumes repository root deployment and outputs `apps/web/dist`. It already had SPA rewrites and no hardcoded backend domain or localhost. Build command used `npm run build`, which works but is less explicit than `npm run build:web`. | Keep and align to `npm run build:web`. |
| `apps/web/vercel.json` | App-root Vercel config. | Assumed Vercel Root Directory `apps/web`, output `dist`, and SPA rewrites. It was valid for an alternate strategy but duplicated the root config and could cause root/build/output confusion. | Removed. Use root `vercel.json` as the single repository Vercel config. |
| Root `package.json` | Monorepo scripts. | Provides `build:web`, `build:landing`, `lint`, and security checks. `build:web` delegates to `apps/web`. | Keep. |
| `apps/web/package.json` | Dashboard package scripts. | `build` runs env validation before Vite build. Node engine is `22.x`. | Keep. |
| `apps/web/vite.config.js` | Vite React/Tailwind config. | No deployment-specific issue found. | Keep. |
| `apps/web/scripts/validate-env.mjs` | Production API URL guard. | Requires `VITE_API_URL` or `VITE_API_BASE_URL`, rejects localhost, validates URL, and prints the chosen API URL. | Keep. |
| `apps/web/src/api/config.js` | Browser API base URL resolver. | Uses `VITE_API_URL || VITE_API_BASE_URL`, normalizes to `/api/dashboard`, and derives other API roots. | Keep. |
| `apps/web/.env.example` | Local dashboard env template. | Localhost values are correct for local development but must not be used in Vercel production/preview env. | Keep. |

## Final Vercel Deployment Strategy

Use one canonical setup:

```text
Root Directory: .
Install Command: npm --prefix apps/web install --include=optional
Build Command: npm run build:web
Output Directory: apps/web/dist
Framework Preset: Vite, or Other with the custom commands above
```

Why this is the final recommendation:

- It matches the root `package.json` scripts.
- It uses the root `vercel.json` as the only active Vercel config.
- It avoids guessing whether Vercel should read repo-root or app-level config.
- Local verification already uses `npm run build:web`.
- The output directory is explicit and points to the dashboard build.

The alternate `apps/web` root strategy is still possible through manual Vercel
settings, but it is no longer represented by a checked-in app-level
`vercel.json` because keeping both configs made deployment attempts easier to
misconfigure.

## Root Directory Decision

Final:

```text
Root Directory: .
```

Do not set Vercel Root Directory to `apps/web` for the main dashboard staging
project unless you intentionally switch strategies and update the docs again.

## Build Command Decision

Final:

```text
npm run build:web
```

Root `package.json` maps this to:

```text
npm --prefix apps/web run build
```

Then `apps/web/package.json` runs:

```text
node scripts/validate-env.mjs && vite build
```

This means every production build checks the API environment before producing
the Vite bundle.

## Output Directory Decision

Final:

```text
apps/web/dist
```

Using `dist` would be wrong for the root-directory strategy because Vite writes
inside `apps/web/dist`.

## SPA Routing and Rewrite Setup

Root `vercel.json` keeps the SPA fallback:

```json
{
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

This is required so direct visits or browser refreshes for nested frontend
routes serve the React app instead of returning 404.

Expected routes that should refresh safely:

- `/dashboard`
- `/analytics`
- `/configuration`
- `/settings/data-sources`
- OAuth result routes that land back in the frontend

## Environment Variables

Set these in Vercel Project Settings > Environment Variables:

```env
VITE_API_URL=https://<render-backend>.onrender.com
VITE_API_BASE_URL=https://<render-backend>.onrender.com
VITE_GUEST_MODE_MULTIPLIER=0.75
```

Rules:

- `VITE_API_URL` and `VITE_API_BASE_URL` should both point to the Render backend
  base URL.
- Do not include `/api/dashboard`; the frontend config appends the API path.
- Do not use localhost in Production or Preview env.
- Do not put backend secrets, database URLs, OAuth client secrets, JWT secrets,
  dashboard auth tokens, or encryption keys in Vercel env.
- Only `VITE_*` variables are exposed to the browser. Treat them as public.

## validate-env.mjs Behavior

`apps/web/scripts/validate-env.mjs` checks:

1. `process.env.VITE_API_URL`
2. `process.env.VITE_API_BASE_URL`
3. local `.env` fallback values when running locally

It fails the production build when:

- neither API variable is set,
- the selected API URL contains `localhost`, `127.0.0.1`, or `0.0.0.0`,
- the selected value is not a valid URL.

Expected Vercel value:

```text
https://<render-backend>.onrender.com
```

Example build failure:

```text
Missing VITE_API_URL or VITE_API_BASE_URL. Set it before building for production.
```

or:

```text
Production API URL must not point to localhost: http://127.0.0.1:8000
```

## Frontend API Config

`apps/web/src/api/config.js` uses:

```text
import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL
```

It normalizes these examples:

| Input | Dashboard API URL |
| --- | --- |
| `https://<render-backend>.onrender.com` | `https://<render-backend>.onrender.com/api/dashboard` |
| `https://<render-backend>.onrender.com/api` | `https://<render-backend>.onrender.com/api/dashboard` |
| `https://<render-backend>.onrender.com/api/dashboard` | unchanged |

Recommended Vercel env is the backend base URL without `/api`.

## Backend Render URL Dependency

The frontend depends on the Render backend URL:

```text
https://<render-backend>.onrender.com
```

Deploy or prepare Render first, then set Vercel env. If the Render service name
or URL changes, update both Vercel env variables and redeploy the frontend.

Render Free services may sleep. The first frontend API request can be slow or
temporarily fail while Render wakes the backend. Retry after the health endpoint
responds.

## Google OAuth Relationship

The frontend does not handle the Google OAuth callback directly for Google
Sheets connection. The relationship is:

1. Frontend calls the backend OAuth start endpoint.
2. Backend builds the Google authorization URL.
3. Google redirects to the Render backend callback:
   `https://<render-backend>.onrender.com/api/google/oauth/callback`.
4. Backend stores encrypted OAuth tokens.
5. Backend redirects the user back to `FRONTEND_URL`.

Required backend Render env:

```env
FRONTEND_URL=https://<vercel-app>.vercel.app
GOOGLE_OAUTH_REDIRECT_URI=https://<render-backend>.onrender.com/api/google/oauth/callback
CORS_ALLOWED_ORIGINS=https://<vercel-app>.vercel.app
```

Required Google Cloud Console setup:

- Authorized redirect URI:
  `https://<render-backend>.onrender.com/api/google/oauth/callback`
- Authorized JavaScript origin if needed:
  `https://<vercel-app>.vercel.app`

## Common Vercel Deployment Failures

| Failure | Symptom | Fix |
| --- | --- | --- |
| Wrong Root Directory | Vercel cannot find root scripts or builds the wrong app. | Use Root Directory `.` for this staging strategy. |
| Wrong Build Command | Script not found or landing app/web app confusion. | Use `npm run build:web`. |
| Wrong Output Directory | Deploy succeeds but page is blank or 404. | Use `apps/web/dist`. |
| Missing API env | Build fails in `validate-env.mjs`. | Add `VITE_API_URL` and `VITE_API_BASE_URL`. |
| API env points to localhost | Build fails or browser cannot call backend. | Use Render backend URL. |
| SPA route refresh 404 | Refreshing `/analytics` returns 404. | Keep root `vercel.json` rewrite to `/index.html`. |
| Backend CORS error | Frontend loads but API requests are blocked. | Add Vercel URL to backend `CORS_ALLOWED_ORIGINS`. |
| OAuth redirects to localhost | Backend callback completes but user lands locally. | Set backend `FRONTEND_URL` to Vercel URL. |
| OAuth redirect mismatch | Google shows `redirect_uri_mismatch`. | Match Google Console and backend `GOOGLE_OAUTH_REDIRECT_URI`. |
| Render cold start | First API request is slow or briefly fails. | Wait for `/api/health`, retry, or use a paid always-on backend later. |

## Step-by-Step Vercel Setup From Scratch

1. Open Vercel.
2. Import the GitHub repository.
3. Choose the dashboard project.
4. Set Root Directory to `.`.
5. Use Framework Preset `Vite` if detected, or keep custom commands below.
6. Set Install Command:

```text
npm --prefix apps/web install --include=optional
```

7. Set Build Command:

```text
npm run build:web
```

8. Set Output Directory:

```text
apps/web/dist
```

9. Add env variables:

```env
VITE_API_URL=https://<render-backend>.onrender.com
VITE_API_BASE_URL=https://<render-backend>.onrender.com
VITE_GUEST_MODE_MULTIPLIER=0.75
```

10. Deploy.
11. Open the Vercel frontend URL.
12. Confirm the app loads.
13. Confirm browser Network requests call the Render backend URL.
14. Refresh a nested route such as `/analytics`.
15. Test login and dashboard data after the backend is configured.
16. Test Google OAuth after Render env and Google Cloud redirect URI are set.

## Post-Deploy Frontend Smoke Test

Checklist:

- Open `https://<vercel-app>.vercel.app`.
- Login page or authenticated dashboard renders.
- Browser console has no fatal runtime error.
- Network tab calls `https://<render-backend>.onrender.com`.
- `GET /api/health` on Render responds.
- Dashboard summary loads after auth.
- Workspace switcher renders.
- Financial Insights and charts render when data exists.
- Refresh `/dashboard`, `/analytics`, and `/configuration`.
- Start Google OAuth and verify the callback returns to Vercel.

## Known Limitations

- Render Free cold starts can make the first frontend API request feel slow.
- Vercel preview deployments may have different URLs; add preview origins to
  backend CORS only when needed.
- `validate-env.mjs` checks build-time env, but runtime browser behavior still
  depends on the deployed bundle being rebuilt after env changes.
- Landing page deployment is separate from the dashboard deployment.

## Follow-Up Tasks

- Deploy Render backend or confirm the final Render URL.
- Configure Vercel env with the actual Render URL.
- Run Week 7 database migration validation before full smoke testing.
- Run end-to-end staging smoke test for auth, OAuth, sync, dashboard,
  analytics, workspace switcher, invitations, and classification.
- Decide later whether landing page needs its own Vercel project.
