# Week 5 Rule-Based Verification

Use this checklist on branch `feat/rule-based-classification`.

Do not run migrations automatically from this checklist. If the migration runner
is needed, run it explicitly:

```powershell
npm run db:migrate
```

Set the API token from the dashboard browser localStorage before endpoint checks:

```powershell
$token = "PASTE_TOKEN_DARI_LOCALSTORAGE"
```

## Migration Checklist

The Week 5 migration files must exist before database verification:

- `backend/db/migrations/007_add_week5_classification_columns.sql`
- `backend/db/migrations/008_add_week5_classification_rule_columns.sql`
- `backend/db/migrations/009_add_classification_performance_indexes.sql`
- `backend/db/migrations/010_add_workspace_insight_settings.sql`

## Environment Checklist

Rule-based classification must run without AI configuration:

```env
AI_CLASSIFICATION_ENABLED=false
AI_PROVIDER=rule_based
AI_MODEL=none
```

Insight severity defaults are fallback values only. Workspace settings in
`public.workspace_insight_settings` take priority.

## Data Source SQL

```sql
select count(*) as total_transactions
from public.transactions
where workspace_id = '9f11676e-90ca-4838-9c6a-e6ee2730b0d3';
```

```sql
select
  raw_payload->>'_sheet_name' as sheet_name,
  count(*) as rows,
  min(transaction_date) as min_date,
  max(transaction_date) as max_date,
  sum(amount) as total_amount
from public.transactions
where workspace_id = '9f11676e-90ca-4838-9c6a-e6ee2730b0d3'
group by 1
order by 1;
```

```sql
select count(*) as future_rows
from public.transactions
where workspace_id = '9f11676e-90ca-4838-9c6a-e6ee2730b0d3'
  and transaction_date > current_date;
```

Expected: synced totals look reasonable and `future_rows = 0`.

## Classification SQL

```sql
select count(*) as current_classifications
from public.transaction_classifications
where workspace_id = '9f11676e-90ca-4838-9c6a-e6ee2730b0d3'
  and is_current = true;
```

```sql
select count(*) as unclassified_rows
from public.transactions t
left join public.transaction_classifications c
  on c.transaction_id = t.id
 and c.workspace_id = t.workspace_id
 and c.is_current = true
where t.workspace_id = '9f11676e-90ca-4838-9c6a-e6ee2730b0d3'
  and c.id is null;
```

If `unclassified_rows` is not zero, run this endpoint repeatedly until the
backlog is cleared:

```text
POST /api/classifications/run?limit=500
```

```sql
select
  workspace_id,
  transaction_id,
  count(*) as current_rows
from public.transaction_classifications
where workspace_id = '9f11676e-90ca-4838-9c6a-e6ee2730b0d3'
  and is_current = true
group by workspace_id, transaction_id
having count(*) > 1;
```

Expected: no rows returned.

```sql
select
  c.financial_type,
  c.direction,
  c.category,
  c.method,
  count(*) as rows,
  sum(t.amount) as total_amount
from public.transaction_classifications c
join public.transactions t
  on t.id = c.transaction_id
where c.workspace_id = '9f11676e-90ca-4838-9c6a-e6ee2730b0d3'
  and c.is_current = true
group by c.financial_type, c.direction, c.category, c.method
order by rows desc;
```

Expected financial types: `need`, `want`, `saving`, `income`,
`uncategorized`.

## Classification Endpoint Checks

Summary:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/classifications/summary" `
  -Headers @{ Authorization = "Bearer $token" } |
ConvertTo-Json -Depth 10
```

Backfill run:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/classifications/run?limit=500" `
  -Headers @{ Authorization = "Bearer $token" } |
ConvertTo-Json -Depth 10
```

Grouped Uncategorized:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/classifications/uncategorized/groups" `
  -Headers @{ Authorization = "Bearer $token" } |
ConvertTo-Json -Depth 10
```

Suggestions:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/classifications/suggestions" `
  -Headers @{ Authorization = "Bearer $token" } |
ConvertTo-Json -Depth 10
```

Apply suggestion sample:

```powershell
$body = @{
  pattern_type = "raw_category_equals"
  pattern = "Laundry"
  target_direction = "expense"
  target_financial_type = "need"
  target_category = "Household"
  apply_to_existing = $true
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/classifications/suggestions/apply" `
  -Headers @{
    Authorization = "Bearer $token"
    "Content-Type" = "application/json"
  } `
  -Body $body |
ConvertTo-Json -Depth 10
```

Expected:

- Summary reports classified/unclassified/low-confidence/manual/rule counters.
- Backfill is bounded and does not overwrite manual classifications.
- Suggestions are deterministic and do not call external AI services.
- Apply suggestion creates or updates a user-defined rule and only reclassifies
  matching non-manual rows.

## Financial Type Endpoint

SQL comparator:

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
where t.workspace_id = '9f11676e-90ca-4838-9c6a-e6ee2730b0d3'
  and extract(year from t.transaction_date)::int = 2026
  and t.transaction_date <= current_date
group by 1
order by total_amount desc;
```

PowerShell endpoint check:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/dashboard/financial-types?year=2026" `
  -Headers @{ Authorization = "Bearer $token" } |
ConvertTo-Json -Depth 10
```

Expected: endpoint totals match SQL and always include `need`, `want`,
`saving`, `income`, and `uncategorized`.

## Monthly Financial Type Endpoint

SQL comparator:

```sql
select
  extract(month from t.transaction_date)::int as month,
  coalesce(c.financial_type, 'uncategorized') as financial_type,
  sum(t.amount) as total_amount
from public.transactions t
left join public.transaction_classifications c
  on c.transaction_id = t.id
 and c.workspace_id = t.workspace_id
 and c.is_current = true
where t.workspace_id = '9f11676e-90ca-4838-9c6a-e6ee2730b0d3'
  and extract(year from t.transaction_date)::int = 2026
  and t.transaction_date <= current_date
group by 1, 2
order by 1, 2;
```

PowerShell endpoint check:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/dashboard/monthly-financial-types?year=2026" `
  -Headers @{ Authorization = "Bearer $token" } |
ConvertTo-Json -Depth 10
```

Expected: current year excludes future months, past years can return Jan-Dec,
future years return empty, and `uncategorized` stays present as a field.

## Rule-Based Insight Endpoint

```powershell
$response = Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/dashboard/rule-based-insights?year=2026" `
  -Headers @{ Authorization = "Bearer $token" }

$response | ConvertTo-Json -Depth 10
```

Expected:

- Response has `period`, `summary`, `highlights`, and `metrics`.
- Highlights are objects with `type`, `label`, `severity`, and `message`.
- Severity is one of `positive`, `neutral`, `info`, `warning`, `danger`.
- Metrics include `need_ratio`, `want_ratio`, `saving_rate`,
  `uncategorized_count`, and `settings_source`.
- `settings_source = workspace` after settings are saved.

## Insight Severity Settings

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/settings/insight-thresholds" `
  -Headers @{ Authorization = "Bearer $token" } |
ConvertTo-Json -Depth 10
```

```powershell
$body = @{
  need_warning_ratio = 0.80
  need_danger_ratio = 0.90
  want_warning_ratio = 0.30
  want_danger_ratio = 0.45
  saving_warning_ratio = 0.10
  saving_good_ratio = 0.20
  uncategorized_warning_count = 1
  uncategorized_danger_count = 20
  anomaly_warning_multiplier = 2.0
  anomaly_danger_multiplier = 3.0
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Put `
  -Uri "http://127.0.0.1:8000/api/settings/insight-thresholds" `
  -Headers @{
    Authorization = "Bearer $token"
    "Content-Type" = "application/json"
  } `
  -Body $body
```

Invalid PUT cases should return HTTP 400:

- `need_warning_ratio > need_danger_ratio`
- `want_warning_ratio > want_danger_ratio`
- `saving_warning_ratio > saving_good_ratio`
- `uncategorized_warning_count > uncategorized_danger_count`
- `anomaly_warning_multiplier > anomaly_danger_multiplier`
- negative count
- anomaly multiplier `< 1`

DB check:

```sql
select *
from public.workspace_insight_settings
where workspace_id = '9f11676e-90ca-4838-9c6a-e6ee2730b0d3';
```

## Anomaly Endpoint

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/dashboard/anomalies?year=2026" `
  -Headers @{ Authorization = "Bearer $token" } |
ConvertTo-Json -Depth 10
```

Expected: status 200, income/saving excluded, explanations present, severity
uses workspace anomaly thresholds, no raw payload is exposed, and there is no
division by zero.

## Dashboard UI Checks

- Summary cards render.
- Financial Insights render Want, Need, Saving, Income, Uncategorized, and Top
  Category when available.
- Severity badges are readable in light and dark mode.
- Severity changes after Configuration settings are saved and Dashboard is
  revisited or refreshed.
- Financial Type Breakdown and Monthly Financial Type Trend charts render.
- Tooltips and legends are readable.
- No horizontal overflow or clipped chart content.
- Network status is 200 for rule-based insights, financial types, and monthly
  financial types.

## Configuration UI Checks

- Insight Severity Settings card renders.
- Source shows `default` or `workspace`.
- Need, Want, and Saving sliders sync with numeric inputs.
- Decimal percentage input such as `37.5` works.
- Save Settings persists values across refresh.
- Reset to Defaults loads default values and requires Save Settings.
- Invalid threshold ordering shows an error or disables save.
- Light, dark, and mobile layouts are readable without horizontal overflow.

## Final Static Checks

Run from the repository root:

```powershell
git branch --show-current
git status --short
```

Python compile for relevant backend modules:

```powershell
python -m py_compile `
  backend/app/repositories/analytics_repository.py `
  backend/app/repositories/classification_repository.py `
  backend/app/repositories/insight_settings_repository.py `
  backend/app/services/financial_insight_service.py `
  backend/app/api/dashboard.py `
  backend/app/api/classifications.py `
  backend/app/api/settings.py
```

If local Python is not available, use the bundled Codex Python runtime and note
that in the final report.

Frontend/static/security checks:

```powershell
npm run lint
npm run build:web
npm run security:check
git diff --check
```

If production build env validation rejects localhost, use:

```powershell
$env:VITE_API_URL='https://api.example.com'
$env:VITE_API_BASE_URL='https://api.example.com'
npm run build:web
```

Expected: all checks pass. CRLF warnings from Git and Vite chunk-size warnings
are acceptable if the commands exit successfully.
