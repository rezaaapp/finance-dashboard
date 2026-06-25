# UAT-WORKSPACE-003 — Member Permission / Transaction Access

## Status

PASS

## Severity

High

## Root cause

The workspace membership setup was valid, but several read-only dashboard endpoints still required the global `require_premium_role` dependency.

That made Divya, a valid member of `Admin's Household` with global role `user`, receive:

- HTTP 403
- `Premium access required`

The failure was not caused by missing workspace membership. It was caused by a global role guard being applied before the workspace-scoped access policy could serve member-readable transaction data.

## Fix summary

- Removed the global premium-role dependency from workspace read-only dashboard endpoints.
- Kept the existing workspace membership dependency via `get_active_sheet_context`.
- Preserved non-member blocking through `get_workspace_for_user`.
- Did not change mutation endpoints, ledger logic, imports, registry, or Google Sheet sync behavior.

## Access policy after fix

- Workspace owner/member can read workspace dashboard transaction data.
- Non-member remains blocked with workspace access denial.
- Mutation/configuration endpoints remain protected by the existing workspace manager policy.

## Files changed

- `backend/app/api/dashboard.py`
- `backend/tests/test_workspace_permissions.py`

## Backend/API behavior

Read-only dashboard endpoints now authorize through workspace access instead of global premium role:

- `/api/dashboard/transactions`
- `/api/dashboard/category-heatmap`
- `/api/dashboard/category-trends`
- `/api/dashboard/source-dana-analytics`
- `/api/dashboard/monthly-allocation`
- `/api/dashboard/personal-analytics`
- `/api/dashboard/grocery-vs-food`
- `/api/dashboard/anomalies`
- `/api/dashboard/latest-insight`
- `/api/dashboard/budget-forecast`

## Validation evidence

In-process FastAPI validation against the current source:

- Admin: dashboard transactions `200`, 25 rows.
- Google Reza: dashboard transactions `200`, 25 rows.
- Divya: dashboard transactions `200`, 25 rows.
- Non-member: dashboard transactions `403`, `Workspace access denied`.
- Divya category heatmap: `200`, 4 categories.
- Divya budget forecast: `200`, current spending `1,867,169`.

## Ledger verification

- Final transactions: 25
- Total expense: Rp1.867.169
- Approved registry: 25
- Rejected registry: 11

No ledger/import/registry data was mutated.

## Test results

- Targeted workspace permission tests: PASS.
- Dashboard read endpoint guard regression test: PASS.

## Notes

During audit, a stale local dev server process still returned the old `Premium access required` response over HTTP. The source-level FastAPI validation used the updated app directly and confirmed the fix. A clean backend restart is recommended before browser retest.
