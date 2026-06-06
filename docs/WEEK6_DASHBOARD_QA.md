# Week 6 Dashboard QA

See also: [Week 6 Analytics QA](WEEK6_ANALYTICS_QA.md).

## Summary Month-over-Month Trend

Dashboard summary cards call:

```text
GET /api/dashboard/summary?year=YYYY&month=M
```

When `year` and `month` are provided, the backend compares the selected month
against the immediately previous month:

- May 2026 -> April 2026
- April 2026 -> March 2026
- January 2026 -> December 2025

Summary totals are classification-aware:

- Expenses: `financial_type in ('need', 'want', 'uncategorized')`
- Saving: `financial_type = 'saving'`
- Income: `financial_type = 'income'`

The response keeps legacy fields and adds explicit comparison fields:

```json
{
  "total_pengeluaran": 21365653,
  "trend_pengeluaran": 18.7,
  "total_expenses_previous": 18000000,
  "total_expenses_change_pct": 18.7,
  "total_expenses_trend": "up",
  "comparison": {
    "current_year": 2026,
    "current_month": 5,
    "previous_year": 2026,
    "previous_month": 4,
    "label": "vs last month"
  }
}
```

If previous data is unavailable and the current value is greater than zero,
`*_change_pct` is `null`, `*_trend` is `unavailable`, and the UI displays `N/A`
with `no previous data`. The UI must not display `NaN`, `Infinity`,
`undefined`, raw `null`, or a misleading `0%`.

## Endpoint Check

```powershell
$token = "PASTE_TOKEN_DARI_LOCALSTORAGE"

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/dashboard/summary?year=2026&month=5" `
  -Headers @{ Authorization = "Bearer $token" } |
ConvertTo-Json -Depth 10
```

Validate:

- `comparison.current_year/current_month` match the selected period.
- `comparison.previous_year/previous_month` match the previous period.
- `total_expenses_change_pct`, `total_saving_change_pct`, and
  `total_income_change_pct` are calculated when previous values exist.
- January selected periods compare against December of the previous year.

## SQL Comparator

Example for May 2026 vs April 2026 expenses:

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

Example for January 2026 vs December 2025:

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
  and (
    (
      extract(year from t.transaction_date)::int = 2026
      and extract(month from t.transaction_date)::int = 1
    )
    or (
      extract(year from t.transaction_date)::int = 2025
      and extract(month from t.transaction_date)::int = 12
    )
  )
  and t.transaction_date <= current_date
  and coalesce(c.financial_type, 'uncategorized') in (
    'need', 'want', 'uncategorized'
  )
group by 1, 2, 3
order by 1, 2, 3;
```

## Regression Matrix

- May 2026 -> April 2026
- April 2026 -> March 2026
- March 2026 -> February 2026
- January 2026 -> December 2025
- February 2025 -> January 2025
- First available month -> safe `N/A` / `no previous data`

Dashboard visual QA:

- Summary card numbers and trend text are not clipped.
- Financial Insights cards do not overlap.
- Financial Type Breakdown and Monthly Financial Type Trend remain readable.
- No horizontal overflow on mobile.
