# Week 6 Security Hardening

This audit covers SaaS-oriented workspace isolation, sensitive data handling,
input validation, and operational security for the Week 6 backend/frontend.

## Scope

- Google OAuth and Google connection endpoints
- Google Sheet data sources and sync jobs
- Dashboard and Analytics endpoints
- Classification endpoints and user-defined rules
- Insight threshold settings
- Backend repositories, services, env defaults, and frontend API clients

No AI provider, local LLM, heavy dependency, OAuth rewrite, or sync engine
rewrite is part of this hardening pass.

## Auth And Workspace Rules

- Sensitive endpoints must require authenticated users.
- Workspace must be derived server-side from the auth context.
- Clients must not be trusted to provide `workspace_id`.
- Path IDs must be looked up or mutated with `workspace_id` filters.
- Public endpoints should only expose non-sensitive health/auth bootstrap
  behavior.

Observed endpoint pattern:

- `get_current_workspace` resolves the active workspace from the current user.
- Data source, sync job, classification, settings, Dashboard, and Analytics
  endpoints pass `workspace_id=str(workspace["id"])` or an equivalent
  server-derived workspace context into repositories.
- Admin endpoints are guarded by super-admin/owner checks.

## Endpoint Review Checklist

Google/OAuth:

- `/api/google/connection/status` and `/disconnect` require auth and filter
  OAuth connection by `workspace_id` plus `user_id`.
- `/api/google/oauth/start` requires auth and signs state with server-derived
  user/workspace IDs.
- `/api/google/oauth/callback` logs safe step codes only and stores encrypted
  access/refresh tokens.

Data Sources:

- `GET /api/data-sources` lists only active sources for the current workspace.
- Google Sheet test/create use the current user's OAuth connection and return
  spreadsheet metadata, not tokens.
- Sync and delete look up sources by `workspace_id` and `source_id`.
- Source status updates now also filter by `workspace_id`.
- Create source validates optional `year` in the `2000..2100` range.

Sync Jobs:

- `GET /api/sync-jobs/{job_id}` fetches by `workspace_id` and `job_id`.
- Sync responses include counts, tabs, safe reasons, and bounded samples only.

Dashboard/Analytics:

- Dashboard routes are auth protected.
- Workspace-aware routes call analytics repositories with server-derived
  `workspace_id`.
- Financial type, rule-based insight, anomaly, and personal analytics queries
  join classifications with `c.workspace_id = t.workspace_id`.
- Dashboard/Analytics responses do not include full `raw_payload`.

Classifications:

- Run, summary, low-confidence, manual correction, rules, groups, suggestions,
  and apply endpoints require auth and current workspace.
- Limits are clamped with API bounds.
- Manual correction validates direction, financial type, compatible pair,
  category, and confidence score.
- Rule mutations filter by `workspace_id` and rule ID.
- Transaction manual correction filters by `workspace_id` and transaction ID.

Settings:

- Insight thresholds require auth and current workspace.
- Ratios, counts, multipliers, and ordered thresholds are validated.
- Settings are upserted by `workspace_id`.

## Repository Checklist

- `google_oauth_repository.py`: queries and disconnect filter by workspace and
  user where relevant; encrypted token fields are not serialized to frontend.
- `google_sheet_source_repository.py`: list/get/delete/reactivate/status update
  operations are workspace-aware.
- `sync_job_repository.py`: external fetch uses workspace; internal job updates
  are created from already-owned sources/jobs.
- `transaction_repository.py`: transaction upserts and lookups use workspace and
  sheet source IDs.
- `classification_repository.py`: transaction/classification joins include
  workspace constraints and skip manual rows when required.
- `classification_rule_repository.py`: list/create/update/delete filter by
  workspace.
- `insight_settings_repository.py`: read/upsert by workspace.
- `analytics_repository.py`: dashboard/analytics data paths filter
  `t.workspace_id` and use current classification rows for financial-type
  endpoints.

## Sensitive Data Rules

Do not log or return:

- OAuth access tokens
- OAuth refresh tokens
- encrypted token values
- Authorization headers or bearer tokens
- service account JSON
- database URLs
- encryption keys
- full `raw_payload`
- stack traces or SQL query text in user-facing errors

Safe operational data:

- workspace ID
- source ID
- job ID
- counts
- duration
- safe reason codes
- bounded sheet/tab diagnostics without raw row content

OAuth callback logs only step/reason codes such as `invalid_state`,
`token_exchange_failed`, `database_upsert_failed`, and `encryption_failed`.

## Input Validation Rules

- Year: integer, recommended range `2000..2100`.
- Month: integer `1..12` where accepted by FastAPI query validation.
- Limit: clamp to bounded API maximums.
- IDs: must resolve under the active workspace before action.
- Google Sheet URL/ID: parse with `extract_spreadsheet_id`; spreadsheet access
  happens only through Google Sheets API using the authenticated OAuth token.
- Manual classification: validate direction, financial type, compatible pair,
  category, and confidence score.
- Insight thresholds: validate ratio/count/multiplier ranges and ordered pairs.

## Frontend Security Notes

- Frontend API clients read only the existing auth token from
  `localStorage.getItem("finance-dashboard-token")`.
- Frontend does not store Google access tokens, refresh tokens, encrypted
  tokens, service account JSON, or backend secrets.
- Frontend API clients do not send arbitrary `workspace_id`; backend derives it
  from auth context.
- No token logging was found in `apps/web/src/api`.

## Env And Gitignore Checklist

- `.env` files are ignored.
- backend/app env examples use placeholders.
- `credentials.json` and `*credentials*.json` are ignored.
- Service account JSON paths are documented as local-only.
- `TOKEN_ENCRYPTION_KEY`, OAuth client secret, JWT secret, and database URL
  examples are placeholders.
- Production secrets must live in provider environment variables.

## Manual Validation Steps

1. Login as User A and connect a Google Sheet.
2. Login as User B in another workspace.
3. Confirm User B cannot list, sync, delete, or inspect User A data source IDs.
4. Confirm `/api/sync-jobs/{job_id}` returns 404 for another workspace's job.
5. Confirm Dashboard and Analytics numbers differ by workspace when data differs.
6. Confirm classification rule IDs from another workspace return 404 on update
   and delete.
7. Confirm browser Network responses do not include OAuth token fields,
   encrypted token fields, or full raw payloads.
8. Confirm invalid `year`, invalid `month`, invalid confidence score, and
   incompatible direction/financial type return safe 400 responses.
9. Check backend logs during OAuth/sync/classification for token/header/raw row
   leakage.

## Known Limitations

- Dashboard keeps a legacy compatibility path for old auth mode. Modern
  multi-user/OAuth flows derive workspace server-side.
- Some internal sync job status updates mutate by job ID after the job is
  created under the active workspace. External reads are workspace-filtered.
- Legacy chart endpoints may use direction/category helpers rather than the
  financial-type contract; financial-type insights and KPI endpoints are
  classification-aware.
- This audit did not introduce row-level security policies or a new RBAC system.
