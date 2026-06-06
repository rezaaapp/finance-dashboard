# Week 6 Analytics QA

## Personal Finance Performance Trend

Analytics Personal Finance Performance uses:

```text
GET /api/dashboard/personal-analytics?year=YYYY&month=M
```

The endpoint returns KPI and trend fields for `all` plus every person found in
`raw_payload->>'Nama'`. The frontend switches between All Data and person tabs
locally from the same response.

## Comparison Contract

Month-specific filters compare the selected month to the previous month:

- May 2026 -> April 2026
- April 2026 -> March 2026
- January 2026 -> December 2025

All Month compares the selected year to the previous year:

- 2026 All Month -> 2025 All Month

If no previous value exists and the current value is greater than zero, the
trend is `null` with `trend = "unavailable"` and the UI displays `N/A` /
`no previous data`.

## KPI Fields

Each `kpis[userKey]` entry includes:

```json
{
  "income": 12145927,
  "income_previous": 10000000,
  "income_change_pct": 21.4,
  "income_trend": "up",
  "spending": 8514693,
  "spending_previous": 9000000,
  "spending_change_pct": -5.4,
  "spending_trend": "down",
  "saving": 112401,
  "saving_previous": 200000,
  "saving_change_pct": -43.8,
  "saving_trend": "down",
  "saving_rate": 0.9,
  "saving_rate_previous": 2.0,
  "saving_rate_change_pct": -1.1,
  "saving_rate_trend": "down"
}
```

Saving rate trend is a percentage-point delta, rendered as `pp` in the UI.

## Metric Definition

Personal analytics is classification-aware:

- Spending: `financial_type in ('need', 'want', 'uncategorized')`
- Saving: `financial_type = 'saving'`
- Income: `financial_type = 'income'`

Queries are workspace-aware, actual-data only, and use:

```sql
t.transaction_date <= current_date
```

## Endpoint Check

```powershell
$token = "PASTE_TOKEN_DARI_LOCALSTORAGE"

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/dashboard/personal-analytics?year=2026&month=5" `
  -Headers @{ Authorization = "Bearer $token" } |
ConvertTo-Json -Depth 10
```

Validate:

- `comparison_period.current_year/current_month` match the selected period.
- `comparison_period.previous_year/previous_month` match the previous period.
- `kpis.all` has trend fields for income, spending, saving, and saving rate.
- Every person key in `users` has matching `kpis[user.value]`.

## SQL Comparator

All Data spending for May 2026 vs April 2026:

```sql
select
  extract(year from t.transaction_date)::int as year,
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
  and extract(month from t.transaction_date)::int in (4, 5)
  and t.transaction_date <= current_date
  and coalesce(c.financial_type, 'uncategorized') in (
    'need', 'want', 'uncategorized'
  )
group by 1, 2, 3
order by 1, 2, 3;
```

Person-specific spending:

```sql
select
  extract(year from t.transaction_date)::int as year,
  extract(month from t.transaction_date)::int as month,
  coalesce(t.raw_payload->>'Nama', 'Unknown') as person,
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
  and extract(month from t.transaction_date)::int in (4, 5)
  and t.transaction_date <= current_date
  and coalesce(c.financial_type, 'uncategorized') in (
    'need', 'want', 'uncategorized'
  )
  and coalesce(t.raw_payload->>'Nama', 'Unknown') = 'PERSON_NAME'
group by 1, 2, 3, 4
order by 1, 2, 3, 4;
```

## Regression Matrix

- All Data + May 2026 -> April 2026
- All Data + April 2026 -> March 2026
- All Data + January 2026 -> December 2025
- Person A + May 2026 -> Person A April 2026
- Person B + May 2026 -> Person B April 2026
- Person with no previous data -> `N/A` / `no previous data`
- All Month + selected year -> previous year

Expected:

- Total Income trend changes by selected month/year/person.
- Total Spending trend changes by selected month/year/person.
- Total Saving trend changes by selected month/year/person.
- Saving Rate trend changes by selected month/year/person.
- No `NaN`, `Infinity`, raw `null`, or misleading `0%`.
