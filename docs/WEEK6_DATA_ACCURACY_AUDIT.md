# Week 6 Data Accuracy Audit

Replace `workspace_id` with the active workspace when validating another
environment. Example workspace used below:

```text
9f11676e-90ca-4838-9c6a-e6ee2730b0d3
```

## Canonical Definitions

Financial types:

- `income`
- `saving`
- `need`
- `want`
- `uncategorized`

Direction values:

- `income`
- `expense`
- `saving_transfer`

Dashboard and Analytics financial-type metrics must use current
classification rows:

```sql
left join public.transaction_classifications c
  on c.transaction_id = t.id
 and c.workspace_id = t.workspace_id
 and c.is_current = true
```

Metric definitions:

- Spending / expense: `financial_type in ('need', 'want', 'uncategorized')`
- Saving: `financial_type = 'saving'`
- Income: `financial_type = 'income'`
- `uncategorized` is an official expense-like bucket.
- `income` and `saving` must not be counted as expense.
- Workspace filter and `t.transaction_date <= current_date` are required.

## Endpoint Contract

### GET /api/dashboard/summary

Required numeric fields:

- `total_expenses`
- `total_expenses_previous`
- `total_expenses_change_pct`
- `total_expenses_trend`
- `total_saving`
- `total_saving_previous`
- `total_saving_change_pct`
- `total_saving_trend`
- `total_income`
- `total_income_previous`
- `total_income_change_pct`
- `total_income_trend`
- `transaction_count`
- `net_cashflow`
- `saving_ratio`
- `comparison`

Selected month behavior: selected month compares to previous month. January
compares to December of the previous year.

All Month behavior: selected year total compares to previous year total.

Previous empty behavior: change percentage is `null`, trend is
`unavailable`, and comparison label is `no previous data`. If current and
previous are both zero, change is `0` and trend is `flat`.

### GET /api/dashboard/financial-types

Required response buckets:

- `need`
- `want`
- `saving`
- `income`
- `uncategorized`

Each item includes:

- `type`
- `amount`
- `count`

### GET /api/dashboard/monthly-financial-types

Required response per month:

- `month`
- `need`
- `want`
- `saving`
- `income`
- `uncategorized`

For the current year, future months are omitted.

### GET /api/dashboard/rule-based-insights

Required fields:

- `period`
- `summary`
- `highlights[]`
- `metrics`
- `metrics.settings_source`

Highlights are backend-severity-driven. The frontend must render severity; it
must not recompute severity.

### GET /api/dashboard/anomalies

Required safe fields:

- `transaction_id`
- `severity`
- `explanation`
- `amount`
- `category`
- `title`
- legacy display aliases such as `Kategori`, `Nama Transaksi`, and `Harga`

The endpoint must not expose full `raw_payload`.

### GET /api/dashboard/personal-analytics

Required fields:

- `users`, including `{ "label": "All Data", "value": "all" }`
- `kpis.all`
- `kpis[person]` for every person shown in `users`
- KPI fields for income, spending, saving, and saving rate
- trend fields for each KPI
- `comparison_period`
- `comparison`
- `top_categories`

Person identity uses:

```sql
coalesce(nullif(t.raw_payload->>'Nama', ''), 'Unknown')
```

Saving rate may stay in the API response, but it is not rendered as a main
Analytics KPI card.

## MoM Formula

Amount trend:

```text
percentage_change = ((current_value - previous_value) / previous_value) * 100
```

Saving rate:

```text
saving_rate = total_saving / total_income * 100
saving_rate_change = current_saving_rate - previous_saving_rate
```

Do not render or return `NaN` or `Infinity`.

## SQL Comparators

### Financial Type Total By Selected Year/Month

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
  and extract(month from t.transaction_date)::int = 5
  and t.transaction_date <= current_date
group by 1
order by total_amount desc;
```

### Dashboard Summary

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
where t.workspace_id = '9f11676e-90ca-4838-9c6a-e6ee2730b0d3'
  and extract(year from t.transaction_date)::int = 2026
  and extract(month from t.transaction_date)::int = 5
  and t.transaction_date <= current_date;
```

### MoM Current Vs Previous

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
where t.workspace_id = '9f11676e-90ca-4838-9c6a-e6ee2730b0d3'
  and (
    (extract(year from t.transaction_date)::int = 2026 and extract(month from t.transaction_date)::int in (4, 5))
  )
  and t.transaction_date <= current_date
group by 1, 2
order by 1, 2;
```

### All Month Summary Current Vs Previous Year

```sql
select
  extract(year from t.transaction_date)::int as year,
  sum(case when coalesce(c.financial_type, 'uncategorized') in ('need', 'want', 'uncategorized') then t.amount else 0 end) as total_expenses,
  sum(case when coalesce(c.financial_type, 'uncategorized') = 'saving' then t.amount else 0 end) as total_saving,
  sum(case when coalesce(c.financial_type, 'uncategorized') = 'income' then t.amount else 0 end) as total_income
from public.transactions t
left join public.transaction_classifications c
  on c.transaction_id = t.id
 and c.workspace_id = t.workspace_id
 and c.is_current = true
where t.workspace_id = '9f11676e-90ca-4838-9c6a-e6ee2730b0d3'
  and extract(year from t.transaction_date)::int in (2025, 2026)
  and t.transaction_date <= current_date
group by 1
order by 1;
```

### Monthly Financial Type

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
where t.workspace_id = '9f11676e-90ca-4838-9c6a-e6ee2730b0d3'
  and extract(year from t.transaction_date)::int = 2026
  and t.transaction_date <= current_date
group by 1, 2
order by 1, 2;
```

### Rule-Based Insights Metrics

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
  where t.workspace_id = '9f11676e-90ca-4838-9c6a-e6ee2730b0d3'
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

### Anomaly Comparator

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
  where t.workspace_id = '9f11676e-90ca-4838-9c6a-e6ee2730b0d3'
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

### Analytics All Data

```sql
select
  extract(year from t.transaction_date)::int as year,
  extract(month from t.transaction_date)::int as month,
  sum(case when coalesce(c.financial_type, 'uncategorized') in ('need', 'want', 'uncategorized') then t.amount else 0 end) as total_spending,
  sum(case when coalesce(c.financial_type, 'uncategorized') = 'saving' then t.amount else 0 end) as total_saving,
  sum(case when coalesce(c.financial_type, 'uncategorized') = 'income' then t.amount else 0 end) as total_income
from public.transactions t
left join public.transaction_classifications c
  on c.transaction_id = t.id
 and c.workspace_id = t.workspace_id
 and c.is_current = true
where t.workspace_id = '9f11676e-90ca-4838-9c6a-e6ee2730b0d3'
  and extract(year from t.transaction_date)::int = 2026
  and extract(month from t.transaction_date)::int in (4, 5)
  and t.transaction_date <= current_date
group by 1, 2
order by 1, 2;
```

### Analytics Person-Specific

```sql
select
  coalesce(nullif(t.raw_payload->>'Nama', ''), 'Unknown') as person,
  extract(year from t.transaction_date)::int as year,
  extract(month from t.transaction_date)::int as month,
  sum(case when coalesce(c.financial_type, 'uncategorized') in ('need', 'want', 'uncategorized') then t.amount else 0 end) as total_spending,
  sum(case when coalesce(c.financial_type, 'uncategorized') = 'saving' then t.amount else 0 end) as total_saving,
  sum(case when coalesce(c.financial_type, 'uncategorized') = 'income' then t.amount else 0 end) as total_income
from public.transactions t
left join public.transaction_classifications c
  on c.transaction_id = t.id
 and c.workspace_id = t.workspace_id
 and c.is_current = true
where t.workspace_id = '9f11676e-90ca-4838-9c6a-e6ee2730b0d3'
  and extract(year from t.transaction_date)::int = 2026
  and extract(month from t.transaction_date)::int in (4, 5)
  and t.transaction_date <= current_date
group by 1, 2, 3
order by 1, 2, 3;
```

## Endpoint Smoke Tests

```powershell
$token = "PASTE_TOKEN_DARI_LOCALSTORAGE"

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/dashboard/summary?year=2026&month=5" `
  -Headers @{ Authorization = "Bearer $token" } |
ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/dashboard/financial-types?year=2026&month=5" `
  -Headers @{ Authorization = "Bearer $token" } |
ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/dashboard/monthly-financial-types?year=2026" `
  -Headers @{ Authorization = "Bearer $token" } |
ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/dashboard/rule-based-insights?year=2026&month=5" `
  -Headers @{ Authorization = "Bearer $token" } |
ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/dashboard/anomalies?year=2026&month=5" `
  -Headers @{ Authorization = "Bearer $token" } |
ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/dashboard/personal-analytics?year=2026&month=5" `
  -Headers @{ Authorization = "Bearer $token" } |
ConvertTo-Json -Depth 10
```

## Audit Notes

- `/api/dashboard/summary` is classification-aware for selected month and All
  Month. All Month uses selected year vs previous year.
- `/api/dashboard/financial-types`,
  `/api/dashboard/monthly-financial-types`, `/api/dashboard/rule-based-insights`,
  `/api/dashboard/anomalies`, and `/api/dashboard/personal-analytics` use
  current classification rows with an uncategorized fallback.
- Legacy chart endpoints such as monthly spending, category trends, category
  heatmap, source-dana analytics, and top spending use the existing direction
  and category helpers. They remain safe for workspace/month/person filters and
  actual-data-only checks, but their contract is legacy expense-category based.
- No endpoint should return full `raw_payload` for Dashboard cards/charts.
