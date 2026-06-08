# Week 6 Release Readiness

This document is the final release readiness checklist for closing Week 6. It
is documentation-focused and does not introduce code behavior, migrations, OAuth
changes, sync changes, classification changes, AI providers, or new
dependencies.

## Overview

Week 6 moved the finance dashboard closer to production readiness across data
accuracy, dashboard/analytics UX, workspace isolation, onboarding, and
workspace collaboration flows.

Week 6 completed:

- Dynamic Month-over-Month trend for Dashboard summary cards.
- Dashboard visual polish.
- Rule-based Financial Insights retained.
- Legacy AI insight card removed.
- Analytics performance trend for All Data and person-specific views.
- Saving Rate removed from the main Analytics KPI cards.
- Data accuracy and endpoint contract audit.
- Workspace isolation and frontend logging hardening.
- Onboarding and empty states.
- Workspace switcher.
- Active workspace header `X-Workspace-Id`.
- Workspace invitation pending/accept/decline/cancel flow.
- Existing workspace member compatibility.

Reference docs:

```text
docs/WEEK6_DASHBOARD_QA.md
docs/WEEK6_ANALYTICS_QA.md
docs/WEEK6_DATA_ACCURACY_AUDIT.md
docs/WEEK6_SECURITY_HARDENING.md
docs/WEEK6_ONBOARDING_EMPTY_STATE.md
docs/WEEK6_WORKSPACE_SWITCHER.md
docs/WEEK6_WORKSPACE_INVITATIONS.md
```

## Migration Checklist

Required migrations:

- `007_add_week5_classification_columns.sql`
- `008_add_week5_classification_rule_columns.sql`
- `009_add_classification_performance_indexes.sql`
- `010_add_workspace_insight_settings.sql`
- `011_add_workspace_invitations.sql`

Run migrations:

```powershell
.\backend\venv\Scripts\python.exe backend\scripts\run_migrations.py
```

Validate applied migration records:

```sql
select version as filename, applied_at
from public.schema_migrations
where version in (
  '007_add_week5_classification_columns.sql',
  '008_add_week5_classification_rule_columns.sql',
  '009_add_classification_performance_indexes.sql',
  '010_add_workspace_insight_settings.sql',
  '011_add_workspace_invitations.sql'
)
order by version;
```

Validate required tables:

```sql
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in (
    'transaction_classifications',
    'classification_rules',
    'workspace_insight_settings',
    'workspace_invitations'
  )
order by table_name;
```

Migration acceptance:

- All required migrations are applied exactly once.
- Tables above exist in `public`.
- Existing `workspace_members` rows remain intact.
- Migration 011 is additive and should not remove existing access.

## Environment Checklist

Backend minimum:

- `DATABASE_URL`
- `DATABASE_MIGRATION_URL` if the environment uses a separate migration URL
- `FRONTEND_URL`
- `GOOGLE_OAUTH_CLIENT_ID` or deployment-specific `GOOGLE_CLIENT_ID` alias
- `GOOGLE_OAUTH_CLIENT_SECRET` or deployment-specific `GOOGLE_CLIENT_SECRET`
  alias
- `GOOGLE_OAUTH_REDIRECT_URI` or deployment-specific `GOOGLE_REDIRECT_URI`
  alias
- `TOKEN_ENCRYPTION_KEY`
- `AI_CLASSIFICATION_ENABLED=false`
- `AI_PROVIDER=rule_based`
- `AI_MODEL=none`

Frontend minimum:

- `VITE_API_URL`
- `VITE_API_BASE_URL` if used by the deployment environment

Security checks:

- Do not use localhost API URLs in production builds.
- Do not commit `.env` files.
- Do not commit credentials, bearer tokens, OAuth tokens, service account JSON,
  private keys, or generated local financial output.
- `TOKEN_ENCRYPTION_KEY` must be strong and different per environment.
- Google OAuth redirect URI must exactly match the environment URL configured in
  Google Cloud.

## Backend Verification Checklist

Compile backend files when backend code changed:

```powershell
.\backend\venv\Scripts\python.exe -m compileall backend\app backend\scripts
```

Core backend checks:

- Health endpoint returns ok.
- DB health endpoint returns connected.
- Google connection status is safe and token-free.
- Data sources list is workspace-aware.
- Dashboard summary returns expected contract.
- Financial types return official buckets.
- Monthly financial types return trend buckets.
- Rule-based insights return structured severity.
- Anomalies return bounded response data.
- Personal analytics returns All Data and person-specific metrics.
- Classifications summary is workspace-aware.
- Insight thresholds are workspace-aware.
- Workspaces list returns active memberships only.
- Pending workspace invitations are filtered by current user email.
- Sync job status is workspace-aware.

PowerShell examples:

```powershell
$token = "PASTE_TOKEN_DARI_LOCALSTORAGE"

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/workspaces" `
  -Headers @{ Authorization = "Bearer $token" } |
  ConvertTo-Json -Depth 10
```

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/dashboard/summary?year=2026&month=5" `
  -Headers @{
    Authorization = "Bearer $token"
    "X-Workspace-Id" = "PASTE_WORKSPACE_ID"
  } |
  ConvertTo-Json -Depth 10
```

## Frontend Verification Checklist

Commands:

```powershell
npm run lint
npm run build:web
npm run security:check
git diff --check
```

If production build rejects localhost:

```powershell
$env:VITE_API_URL="https://api.example.com"
$env:VITE_API_BASE_URL="https://api.example.com"
npm run build:web
```

Browser checklist:

- Login page works.
- Google OAuth connect flow starts and returns safely.
- Configuration page loads.
- Data sources load.
- Sync Now starts and returns safe status.
- Dashboard loads.
- Analytics loads.
- Workspace switcher loads.
- Invitation notification appears only when pending invitations exist.
- Dark/light mode remains readable.
- Mobile layout is responsive.
- Console has no critical error.
- Network tab has no unexpected 500 responses.

## Dashboard Smoke Test

- Summary cards load.
- MoM trend is not stuck at `0%`.
- All Month summary works.
- Selected month summary works.
- Financial Insights render.
- Financial Type chart renders.
- Monthly Financial Type trend renders.
- Legacy AI Financial Insight card is not shown.
- Empty state works for a workspace without data.
- Switching workspace refetches Dashboard data.

## Analytics Smoke Test

- All Data KPI cards render:
  - Total Income
  - Total Spending
  - Total Saving
- Saving Rate card is not shown as a main KPI.
- Person-specific KPI trend works.
- All Month behavior works.
- Selected month trend works.
- Empty person state works.
- Switching workspace refetches Analytics.
- No stale previous workspace data remains visible.

## Workspace Switcher Smoke Test

- Login as a user with multiple workspaces.
- Workspace switcher shows all active memberships.
- Pending invitations do not appear as active workspace.
- Selecting workspace updates `X-Workspace-Id` on workspace-aware requests.
- Dashboard changes after switch.
- Analytics changes after switch.
- Configuration and Data Sources change after switch.
- Invalid workspace id returns `403`.
- Invalid localStorage workspace id is cleared or falls back safely.

## Invitation Flow Smoke Test

- Owner invites new email.
- Invite appears under Pending Invitations.
- Invited user sees notification after login.
- Accept adds active membership.
- Accepted workspace appears in switcher.
- Decline does not add membership.
- Cancel invite removes pending invite.
- Existing active member does not need to accept invitation.
- Duplicate pending invite is blocked.
- Already active member invite is blocked.
- Non-owner/member cannot invite or cancel.

## Security Checklist

- No token or secret in frontend logs.
- No raw Axios error object logging.
- No OAuth token exposed.
- No encrypted token exposed.
- No credentials in repo.
- Workspace access is validated server-side.
- User cannot access a workspace where they are not a member.
- User cannot accept invitation for another email.
- User cannot cancel invitation without permission.
- Data source update/delete is filtered by workspace.
- Dashboard/Analytics queries are workspace-aware.
- No stack trace is exposed to frontend responses.

Reference:

```text
docs/WEEK6_SECURITY_HARDENING.md
docs/SECURITY_CHECKLIST.md
```

## Data Accuracy Checklist

Reference:

```text
docs/WEEK6_DATA_ACCURACY_AUDIT.md
```

Checklist:

- Dashboard summary vs SQL.
- Financial type vs SQL.
- Monthly financial type vs SQL.
- Rule-based insight metrics vs SQL.
- Anomaly comparator.
- Analytics All Data vs SQL.
- Analytics person-specific vs SQL.
- All Month contract.
- MoM selected month contract.

## Deployment Steps

Suggested deployment flow:

1. Pull the latest release branch or main branch candidate.
2. Install or update dependencies only if package files changed.
3. Verify backend and frontend environment variables.
4. Run database migrations.
5. Start or deploy backend.
6. Build or deploy frontend.
7. Run backend smoke tests.
8. Run frontend smoke tests.
9. Run workspace switcher and invitation smoke tests.
10. Monitor backend and frontend logs.

This checklist intentionally avoids assuming a specific vendor beyond the
existing project deployment docs.

## Post-Deployment Validation

- `/api/health` returns ok.
- `/api/health/db` returns connected.
- Login succeeds.
- `GET /api/workspaces` returns expected memberships.
- Dashboard summary loads with the active workspace.
- Analytics loads with the active workspace.
- Configuration Data Sources load with the active workspace.
- Insight thresholds load and save per workspace.
- Sync Now can be tested in a controlled workspace.
- Pending invitation notification appears only for invited users.
- Invalid `X-Workspace-Id` returns `403`.
- Browser console has no critical errors.
- Backend logs do not show token, credential, raw payload, or stack trace leaks.

## Rollback Plan

If deployment fails:

1. Stop the new deployment.
2. Revert application runtime to the previous known-good commit or tag.
3. Do not rollback database migrations automatically unless a destructive issue
   occurs.
4. Migration 011 is additive and should be safe to keep.
5. If invitation UI causes an issue, temporarily hide or disable the Workspace
   Invitation UI path while preserving backend data.
6. Preserve existing `workspace_members`.
7. Check logs for spikes in workspace access `403` responses.
8. Record incident notes, including environment, commit, migration state,
   symptoms, and follow-up owner.

## Known Limitations

- Invitation email delivery is not implemented yet.
- Automatic invitation expiry is not implemented yet.
- Workspace role model is still MVP-level.
- Detailed RBAC for admin/member actions can be expanded.
- Vite chunk size warning still appears during production build.
- Legacy auth compatibility path remains documented.
- Production observability and rate limiting can be improved.

## Next Recommended Work

- Add email delivery for workspace invitations.
- Add automatic invitation expiry handling.
- Expand workspace RBAC beyond MVP owner/member behavior.
- Add production observability dashboards and alerting.
- Add rate limiting for auth, invitation, sync, and classification mutation
  endpoints.
- Add deeper automated integration tests for workspace isolation and invitation
  flows.
