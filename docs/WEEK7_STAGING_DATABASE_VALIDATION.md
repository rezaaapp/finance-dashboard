# Week 7 Staging Database Validation

## Objective

This document prepares Supabase/PostgreSQL staging database migration and
validation before backend/frontend smoke tests. It does not run migrations,
deploy services, change schema SQL, change backend/frontend behavior, add
dependencies, or add any AI provider.

Use this guide after Render/Vercel environment variables are prepared and
before end-to-end staging smoke testing.

If the backend is temporarily hosted on Replit instead of Render, the same
Supabase migration and validation rules apply. See
`docs/WEEK7_REPLIT_BACKEND_FALLBACK.md` for the backend host-specific env and
smoke test notes.

## Staging Database Strategy

Option A: existing Supabase project for personal staging.

Pros:

- Faster.
- Existing data is already available.
- Good for personal verification.

Cons:

- Staging tests can affect development or personal data.
- Invite, sync, and classification tests can create noisy rows.
- Cleanup requires care.

Option B: separate Supabase staging project.

Pros:

- Cleaner and safer for limited beta/public testing.
- Full migration validation starts from a clean state.
- Test users and data are isolated.

Cons:

- More setup.
- Requires new `DATABASE_URL` and `DATABASE_MIGRATION_URL`.
- Requires migrations and seed/test data.

Recommendation:

- Personal test: existing Supabase is acceptable after backup.
- Limited beta/public test: separate Supabase staging is strongly recommended.

## Migration Inventory

| Filename | Purpose | Key tables/columns/indexes | Required before staging? | Notes |
| --- | --- | --- | --- | --- |
| `001_initial_multi_tenant_schema.sql` | Initial multi-tenant foundation. | `users`, `workspaces`, `workspace_members`, `workspace_configurations`, `user_tokens`, `set_updated_at()`, role/member indexes. | Yes | Creates `pgcrypto` and `citext`; required before all workspace-aware features. |
| `002_add_workspace_google_sheet_sources.sql` | Adds JSON source list to workspace configuration. | `workspace_configurations.google_sheet_sources`. | Yes for legacy/local compatibility | Keeps old `google_sheet_id` data as one JSON source. |
| `003_add_global_user_roles.sql` | Adds global MVP user role. | `users.role`, `users_role_check`, `users_role_idx`. | Yes | Workspace role still lives in `workspace_members.role`. |
| `004_add_ai_sync_database_foundation.sql` | Adds database foundation for OAuth, sources, sync, transactions, and legacy AI/classification tables. | `schema_migrations`, `google_oauth_connections`, `google_sheet_sources`, `transactions`, `transaction_classifications`, `classification_rules`, `sync_jobs`, many indexes. | Yes | Despite old "AI" naming, current staging keeps rule-based classification only. |
| `005_add_google_oauth_connection_unique_constraint.sql` | Ensures one OAuth connection per workspace/user for upsert. | Unique constraint `google_oauth_connections_workspace_user_unique`. | Yes | Required for stable Google OAuth connection upsert. |
| `006_add_google_sheet_source_title.sql` | Adds display title for Google Sheet sources. | `google_sheet_sources.spreadsheet_title`. | Yes | Used by data source UI. |
| `007_add_week5_classification_columns.sql` | Adds Week 5 rule-based classification columns. | `direction`, `financial_type`, `category`, `confidence_score`, `method`, `explanation`, `updated_at`, current unique index when safe. | Yes | Required for financial type dashboard and rule-based classification. |
| `008_add_week5_classification_rule_columns.sql` | Adds Week 5 user-defined rule columns. | `classification_rules.direction`, `financial_type`, `category`, `confidence_score`, `explanation`, related indexes. | Yes | Required for user-defined rule tuning. |
| `009_add_classification_performance_indexes.sql` | Adds classification/read performance indexes. | `transaction_classifications_workspace_transaction_current_idx`, `transactions_workspace_transaction_date_idx`. | Yes | Important for dashboard/classification performance. |
| `010_add_workspace_insight_settings.sql` | Adds workspace-level rule-based insight thresholds. | `workspace_insight_settings`, ratio/count/anomaly checks, workspace unique constraint, trigger. | Yes | Required for Configuration severity settings and backend severity highlights. |
| `011_add_workspace_invitations.sql` | Adds workspace invitation lifecycle. | `workspace_invitations`, pending invitation unique index, status/email/user indexes, trigger. | Yes | Required for pending/accept/decline/cancel invitation flow. |

Migration ordering risk: files are applied lexicographically by filename.
Preserve numeric prefixes. Do not rename migration files after they have been
applied to any shared database.

## Migration Runner Documentation

Runner:

```text
backend/scripts/run_migrations.py
```

How it works:

- Discovers `*.sql` files in `backend/db/migrations`.
- Sorts migration files by filename.
- Ensures `schema_migrations` exists.
- Uses each migration filename as `schema_migrations.version`.
- Skips already applied versions.
- Runs each migration inside a transaction.
- Inserts the migration version after successful execution.
- Hides detailed database errors to avoid leaking connection information.

Database URL selection:

- Uses `DATABASE_MIGRATION_URL` when present.
- Falls back to `DATABASE_URL`.
- SSL behavior follows `DATABASE_SSL` and
  `DATABASE_SSL_REJECT_UNAUTHORIZED`.

Run from repository root:

```powershell
.\backend\venv\Scripts\python.exe backend\scripts\run_migrations.py
```

Alternative:

```powershell
python backend\scripts\run_migrations.py
```

Do not run migrations automatically on every Render boot. Run them manually
before smoke testing. If using an existing Supabase database, backup first. If
using a separate Supabase staging project, run the full migration set from a
clean state.

## schema_migrations Validation

The current runner stores filenames in the `version` column. These queries
alias `version` as `filename` for readability.

All applied migrations:

```sql
select version as filename, applied_at
from public.schema_migrations
order by version;
```

Required Week 5/6 migrations:

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

Expected:

- All required files appear once.
- `applied_at` is not null.
- No duplicate filename/version.

Duplicate check:

```sql
select version as filename, count(*) as rows
from public.schema_migrations
group by version
having count(*) > 1;
```

Expected: 0 rows.

## Core Schema Validation

Required tables:

```sql
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in (
    'users',
    'workspaces',
    'workspace_members',
    'google_oauth_connections',
    'google_sheet_sources',
    'sync_jobs',
    'transactions',
    'transaction_classifications',
    'classification_rules',
    'workspace_insight_settings',
    'workspace_invitations'
  )
order by table_name;
```

Expected: all tables exist.

Important columns:

```sql
select table_name, column_name, data_type, is_nullable
from information_schema.columns
where table_schema = 'public'
  and table_name in (
    'workspace_invitations',
    'workspace_insight_settings',
    'transaction_classifications',
    'transactions',
    'google_sheet_sources'
  )
order by table_name, ordinal_position;
```

## Workspace And Membership Validation

All memberships:

```sql
select
  w.id as workspace_id,
  w.name as workspace_name,
  u.email,
  wm.role,
  wm.created_at
from public.workspace_members wm
join public.workspaces w
  on w.id = wm.workspace_id
join public.users u
  on u.id = wm.user_id
order by w.name, u.email;
```

Specific user membership check:

```sql
select
  wm.workspace_id,
  w.name as workspace_name,
  u.email,
  wm.role,
  wm.created_at
from public.workspace_members wm
join public.workspaces w
  on w.id = wm.workspace_id
join public.users u
  on u.id = wm.user_id
where lower(u.email) in (
  'rezaaapp@gmail.com',
  'divyakoemala@gmail.com'
)
order by w.name, u.email;
```

Expected for the existing compatibility test data, when present:

- Reza owns workspace Reza.
- Divya owns workspace Divya.
- Divya is a member of workspace Reza if that compatibility scenario exists in
  the target database.

## Workspace Invitations Validation

Invitation rows:

```sql
select
  id,
  workspace_id,
  email,
  role,
  status,
  invited_by_user_id,
  invited_user_id,
  created_at,
  responded_at
from public.workspace_invitations
order by created_at desc;
```

Pending duplicate check:

```sql
select
  workspace_id,
  lower(email) as email,
  count(*) as pending_count
from public.workspace_invitations
where status = 'pending'
group by workspace_id, lower(email)
having count(*) > 1;
```

Expected: 0 rows.

Status distribution:

```sql
select status, count(*) as rows
from public.workspace_invitations
group by status
order by status;
```

## Google OAuth, Sources, And Sync Validation

Google OAuth status without exposing tokens:

```sql
select
  workspace_id,
  user_id,
  google_email,
  status,
  scopes,
  created_at,
  updated_at
from public.google_oauth_connections
order by updated_at desc;
```

Do not select `access_token_encrypted` or `refresh_token_encrypted`.

Google Sheet sources:

```sql
select
  id,
  workspace_id,
  spreadsheet_title,
  sheet_name,
  year,
  status,
  last_synced_at,
  created_at,
  updated_at
from public.google_sheet_sources
order by created_at desc;
```

Sync jobs:

```sql
select
  id,
  workspace_id,
  sheet_source_id,
  job_type,
  status,
  total_rows,
  inserted_rows,
  updated_rows,
  skipped_rows,
  failed_rows,
  error_message,
  started_at,
  finished_at,
  created_at
from public.sync_jobs
order by created_at desc
limit 20;
```

`error_message` should not expose secrets, tokens, OAuth codes, or database
connection strings.

## Transactions Validation

Transactions summary by workspace:

```sql
select
  workspace_id,
  count(*) as total_transactions,
  min(transaction_date) as min_date,
  max(transaction_date) as max_date,
  sum(amount) as total_amount
from public.transactions
group by workspace_id
order by total_transactions desc;
```

Transaction date/null readiness:

```sql
select
  workspace_id,
  count(*) filter (where transaction_date is null) as missing_transaction_date,
  count(*) filter (where title is null or title = '') as missing_title,
  count(*) filter (where amount is null) as missing_amount
from public.transactions
group by workspace_id
order by workspace_id;
```

## Classification Validation

Classification summary:

```sql
select
  t.workspace_id,
  coalesce(c.financial_type, 'uncategorized') as financial_type,
  count(*) as rows,
  sum(t.amount) as total_amount
from public.transactions t
left join public.transaction_classifications c
  on c.transaction_id = t.id
 and c.workspace_id = t.workspace_id
 and c.is_current = true
group by t.workspace_id, coalesce(c.financial_type, 'uncategorized')
order by t.workspace_id, total_amount desc;
```

Current classification duplicate check:

```sql
select
  workspace_id,
  transaction_id,
  count(*) as current_rows
from public.transaction_classifications
where is_current = true
group by workspace_id, transaction_id
having count(*) > 1;
```

Expected: 0 rows.

Classification rules:

```sql
select
  workspace_id,
  match_type,
  financial_type,
  direction,
  category,
  is_active,
  count(*) as rows
from public.classification_rules
group by workspace_id, match_type, financial_type, direction, category, is_active
order by workspace_id, rows desc;
```

Low-confidence/current method distribution:

```sql
select
  workspace_id,
  method,
  financial_type,
  count(*) as rows,
  min(confidence_score) as min_confidence,
  max(confidence_score) as max_confidence
from public.transaction_classifications
where is_current = true
group by workspace_id, method, financial_type
order by workspace_id, rows desc;
```

## Dashboard And Analytics Readiness

Replace `<workspace_id>` with the active workspace id for the environment.
Example workspace id used in previous local validation:

```text
9f11676e-90ca-4838-9c6a-e6ee2730b0d3
```

Dashboard selected month comparator:

```sql
select
  sum(case when coalesce(c.financial_type, 'uncategorized') in ('need', 'want', 'uncategorized') then t.amount else 0 end) as total_expenses,
  sum(case when coalesce(c.financial_type, 'uncategorized') = 'saving' then t.amount else 0 end) as total_saving,
  sum(case when coalesce(c.financial_type, 'uncategorized') = 'income' then t.amount else 0 end) as total_income
from public.transactions t
left join public.transaction_classifications c
  on c.transaction_id = t.id
 and c.workspace_id = t.workspace_id
 and c.is_current = true
where t.workspace_id = '<workspace_id>'
  and extract(year from t.transaction_date)::int = 2026
  and extract(month from t.transaction_date)::int = 5
  and t.transaction_date <= current_date;
```

All Month comparator:

```sql
select
  sum(case when coalesce(c.financial_type, 'uncategorized') in ('need', 'want', 'uncategorized') then t.amount else 0 end) as total_expenses,
  sum(case when coalesce(c.financial_type, 'uncategorized') = 'saving' then t.amount else 0 end) as total_saving,
  sum(case when coalesce(c.financial_type, 'uncategorized') = 'income' then t.amount else 0 end) as total_income
from public.transactions t
left join public.transaction_classifications c
  on c.transaction_id = t.id
 and c.workspace_id = t.workspace_id
 and c.is_current = true
where t.workspace_id = '<workspace_id>'
  and extract(year from t.transaction_date)::int = 2026
  and t.transaction_date <= current_date;
```

Personal analytics person comparator:

```sql
select
  coalesce(nullif(t.raw_payload->>'Nama', ''), 'Unknown') as person,
  sum(case when coalesce(c.financial_type, 'uncategorized') in ('need', 'want', 'uncategorized') then t.amount else 0 end) as total_spending,
  sum(case when coalesce(c.financial_type, 'uncategorized') = 'saving' then t.amount else 0 end) as total_saving,
  sum(case when coalesce(c.financial_type, 'uncategorized') = 'income' then t.amount else 0 end) as total_income
from public.transactions t
left join public.transaction_classifications c
  on c.transaction_id = t.id
 and c.workspace_id = t.workspace_id
 and c.is_current = true
where t.workspace_id = '<workspace_id>'
  and extract(year from t.transaction_date)::int = 2026
  and extract(month from t.transaction_date)::int = 5
  and t.transaction_date <= current_date
group by coalesce(nullif(t.raw_payload->>'Nama', ''), 'Unknown')
order by total_spending desc;
```

Financial type readiness:

```sql
select
  coalesce(c.financial_type, 'uncategorized') as financial_type,
  count(*) as rows,
  sum(t.amount) as total_amount
from public.transactions t
left join public.transaction_classifications c
  on c.transaction_id = t.id
 and c.workspace_id = t.workspace_id
 and c.is_current = true
where t.workspace_id = '<workspace_id>'
  and extract(year from t.transaction_date)::int = 2026
  and t.transaction_date <= current_date
group by coalesce(c.financial_type, 'uncategorized')
order by total_amount desc;
```

## Data Accuracy SQL Pack

Month-over-month current vs previous:

```sql
select
  extract(year from t.transaction_date)::int as year,
  extract(month from t.transaction_date)::int as month,
  sum(case when coalesce(c.financial_type, 'uncategorized') in ('need', 'want', 'uncategorized') then t.amount else 0 end) as total_expenses,
  sum(case when coalesce(c.financial_type, 'uncategorized') = 'saving' then t.amount else 0 end) as total_saving,
  sum(case when coalesce(c.financial_type, 'uncategorized') = 'income' then t.amount else 0 end) as total_income
from public.transactions t
left join public.transaction_classifications c
  on c.transaction_id = t.id
 and c.workspace_id = t.workspace_id
 and c.is_current = true
where t.workspace_id = '<workspace_id>'
  and (
    (extract(year from t.transaction_date)::int = 2026 and extract(month from t.transaction_date)::int in (4, 5))
  )
  and t.transaction_date <= current_date
group by 1, 2
order by 1, 2;
```

Monthly financial type:

```sql
select
  extract(month from t.transaction_date)::int as month,
  coalesce(c.financial_type, 'uncategorized') as financial_type,
  sum(t.amount) as total_amount,
  count(*) as rows
from public.transactions t
left join public.transaction_classifications c
  on c.transaction_id = t.id
 and c.workspace_id = t.workspace_id
 and c.is_current = true
where t.workspace_id = '<workspace_id>'
  and extract(year from t.transaction_date)::int = 2026
  and t.transaction_date <= current_date
group by 1, 2
order by 1, 2;
```

Rule-based insight metrics:

```sql
with ft as (
  select
    coalesce(c.financial_type, 'uncategorized') as financial_type,
    sum(t.amount) as amount,
    count(*) as rows
  from public.transactions t
  left join public.transaction_classifications c
    on c.transaction_id = t.id
   and c.workspace_id = t.workspace_id
   and c.is_current = true
  where t.workspace_id = '<workspace_id>'
    and extract(year from t.transaction_date)::int = 2026
    and extract(month from t.transaction_date)::int = 5
    and t.transaction_date <= current_date
  group by 1
)
select
  coalesce(sum(amount) filter (where financial_type = 'need'), 0) as need,
  coalesce(sum(amount) filter (where financial_type = 'want'), 0) as want,
  coalesce(sum(amount) filter (where financial_type = 'saving'), 0) as saving,
  coalesce(sum(amount) filter (where financial_type = 'income'), 0) as income,
  coalesce(sum(amount) filter (where financial_type = 'uncategorized'), 0) as uncategorized,
  coalesce(sum(rows) filter (where financial_type = 'uncategorized'), 0) as uncategorized_count
from ft;
```

Anomaly comparator:

```sql
with base as (
  select
    t.id as transaction_id,
    t.transaction_date,
    t.title,
    coalesce(c.category, c.category_normalized, t.raw_payload->>'_category_normalized', t.raw_category, 'Uncategorized') as category,
    t.amount,
    coalesce(c.financial_type, 'uncategorized') as financial_type
  from public.transactions t
  left join public.transaction_classifications c
    on c.transaction_id = t.id
   and c.workspace_id = t.workspace_id
   and c.is_current = true
  where t.workspace_id = '<workspace_id>'
    and extract(year from t.transaction_date)::int = 2026
    and extract(month from t.transaction_date)::int = 5
    and t.transaction_date <= current_date
),
scored as (
  select
    *,
    avg(amount) over (partition by category) as avg_amount,
    stddev_pop(amount) over (partition by category) as stddev_amount
  from base
  where financial_type in ('need', 'want', 'uncategorized')
)
select *
from scored
where amount > avg_amount + (2 * stddev_amount)
order by amount desc;
```

## Index And Constraint Validation

Important indexes:

```sql
select
  schemaname,
  tablename,
  indexname,
  indexdef
from pg_indexes
where schemaname = 'public'
  and tablename in (
    'transactions',
    'transaction_classifications',
    'classification_rules',
    'workspace_invitations',
    'google_sheet_sources',
    'sync_jobs'
  )
order by tablename, indexname;
```

Important constraints:

```sql
select
  conrelid::regclass as table_name,
  conname,
  contype,
  pg_get_constraintdef(oid) as definition
from pg_constraint
where connamespace = 'public'::regnamespace
  and conrelid::regclass::text in (
    'workspace_invitations',
    'transaction_classifications',
    'classification_rules',
    'workspace_insight_settings'
  )
order by table_name, conname;
```

## Backup And Rollback Notes

- For an existing Supabase project, export/backup before migration.
- Migrations are mostly additive, but validate first in staging when possible.
- Do not manually delete rows from `schema_migrations`.
- Rollback should usually be application rollback first, not database rollback.
- Migration 011 is additive and safe to keep if app rollback happens.
- If invitation behavior causes issues, disable the UI/API path rather than
  dropping `workspace_invitations`.
- If `TOKEN_ENCRYPTION_KEY` changes, OAuth tokens may become undecryptable and
  users may need to reconnect Google.

## Common Migration And Database Issues

| Issue | Symptom | Fix |
| --- | --- | --- |
| `DATABASE_URL` points to the wrong Supabase project | Data looks empty or belongs to another environment. | Confirm Render/local env and Supabase project id. |
| `DATABASE_MIGRATION_URL` missing or wrong | Migration runner cannot connect or lacks permission. | Use direct/session URL when Supabase pooling mode is not suitable for DDL. |
| Migration marked applied but table missing | Manual DB edits or wrong database target. | Stop, verify target DB, restore from backup if needed, and avoid editing `schema_migrations` blindly. |
| Duplicate current classifications | Classification queries double count rows. | Run duplicate check before relying on dashboard totals. |
| Duplicate pending invitation | Insert/upsert fails for pending invite. | Expected unique index behavior; cancel/resolve old pending invite. |
| Workspace exists but user is not a member | Dashboard or workspace API returns 403/empty. | Validate `workspace_members`. |
| OAuth connection exists but token decrypt fails | Google sync fails after deploy. | Check stable `TOKEN_ENCRYPTION_KEY`; reconnect Google if key changed. |
| Sync jobs failed | Data source has no fresh transactions. | Inspect `sync_jobs.error_message` without exposing secrets. |
| Dashboard empty | Active workspace has no transactions or wrong workspace selected. | Validate active `workspace_id` and transaction counts. |
| Analytics person mismatch | Person totals differ from UI expectations. | Validate `raw_payload->>'Nama'` and use `Unknown` fallback. |

## Step-By-Step Staging DB Validation Flow

1. Choose existing Supabase or a separate staging Supabase project.
2. Backup/export if using an existing project.
3. Confirm `DATABASE_URL`, `DATABASE_MIGRATION_URL`, `DATABASE_SSL`, and
   `DATABASE_SSL_REJECT_UNAUTHORIZED`.
4. Run migrations manually from local or a controlled shell.
5. Validate `schema_migrations`.
6. Validate core tables and important columns.
7. Validate indexes and constraints.
8. Validate workspace memberships and invitations.
9. Validate OAuth connections without selecting encrypted tokens.
10. Validate Google Sheet sources and latest sync jobs.
11. Validate transactions and current classifications.
12. Run dashboard/analytics SQL comparators for the active workspace.
13. Proceed to backend Render smoke tests.
14. Proceed to frontend Vercel smoke tests.

## Known Limitations

- This pack does not run migrations automatically.
- SQL examples use year `2026` and month `5`; adjust for the target smoke test.
- Workspace examples include personal email addresses only for known local
  compatibility checks.
- Supabase RLS is not validated here because current backend authorization is
  application-enforced.
- This pack does not validate Google OAuth token decryptability directly; that
  requires backend service smoke tests.

## Next Prompt Roadmap

- Prompt F: end-to-end staging smoke test across Render, Vercel, Supabase, and
  Google OAuth.
- Limited beta checklist: decide test users, support process, rollback path,
  monitoring, and data privacy notes.
- Future hardening: optional migration job/runbook, observability, stricter
  database role separation, and deeper automated integration tests.
