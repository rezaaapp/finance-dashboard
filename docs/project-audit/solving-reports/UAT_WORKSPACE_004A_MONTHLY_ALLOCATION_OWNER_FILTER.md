# UAT-WORKSPACE-004A — Monthly Allocation Owner Filter

## Status

PASS

## Severity

High

## Root cause

`analytics_repository.get_monthly_allocation(..., name=...)` accepted an owner filter, but it delegated to `get_monthly_totals(...)` without passing the owner name.

Additionally, `get_monthly_totals(...)` did not expose a `name` parameter, so monthly allocation always aggregated the whole workspace even when the API was called with `name=Divya`.

Observed failing behavior:

- `GET /api/dashboard/monthly-allocation?year=2026&month=6&name=Divya`
- Returned `Needs: 1,867,169`
- Expected empty/zero because Divya has no final transactions in the current UAT dataset.

## Fix summary

- Added optional `name` support to `get_monthly_totals(...)`.
- Forwarded `name` from `get_monthly_allocation(...)` into `get_monthly_totals(...)`.
- Reused the existing owner filter normalization in `_filters(...)`.
- Did not change ledger/import/registry data.
- Did not change owner data.
- Did not alter workspace isolation behavior.

## Files changed

- `backend/app/repositories/analytics_repository.py`
- `backend/tests/test_analytics_date_filters.py`

## Backend/API behavior

After the fix:

- No owner filter returns workspace total.
- `name=Reza` returns Reza total.
- `name=Divya` returns empty/zero for the current dataset.
- Non-member access remains blocked by workspace membership.

## Manual verification

Endpoint:

- `/api/dashboard/monthly-allocation?year=2026&month=6`

Results:

- Owner `ALL`: `200`, `Needs: 1,867,169`
- Owner `Reza`: `200`, `Needs: 1,867,169`
- Owner `Divya`: `200`, empty list
- Non-member with `name=Divya`: `403`, `Workspace access denied`

## Ledger verification

- Final transactions: 25
- Total expense: Rp1.867.169
- Owner `Reza`: 25 transactions / Rp1.867.169
- Owner `Divya`: 0 transactions / Rp0
- Approved registry: 25
- Rejected registry: 11

No ledger/import/registry data was mutated.

## Test results

- Targeted backend tests:
  - `backend.tests.test_analytics_date_filters`
  - `backend.tests.test_workspace_permissions`
  - Result: 15 PASS

Full backend unittest discovery was attempted:

- 130 tests executed
- 127 passed
- 3 existing errors in `test_google_token_service`
- Failure reason: test harness patches `app.services.google_token_service.httpx.post`, but the loaded `httpx` module in this environment does not expose `post`.
- This is unrelated to the monthly allocation owner-filter change.

## Notes

No frontend files changed, so web lint was not required for this backend-only fix.
