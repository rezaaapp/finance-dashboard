# UAT-BUDGET-001A — Budget Edit Persistence & Save UX

## Bug

- ID: UAT-BUDGET-001A
- Severity: High
- Scope: Editing an existing monthly category budget

## Root cause

Editing a budget input only updated the local `draftBudgets` React state. The
`PUT /api/budgets/{budget_id}` request was only sent after
`handleSaveCategory` ran.

The existing Save action was placed in the far-right action column. It was not
visually associated with the edited input and could be outside the visible
table area. The UI also had no dirty-state indicator. As a result, changing
Food from Rp500.000 to Rp550.000 looked like a saved change even though no
request had been sent. Reload correctly fetched the unchanged Rp500.000 value
from PostgreSQL.

The backend update repository and the reload/forecast endpoint use the same
budget record. No backend persistence defect was found.

## Fix summary

- Detect existing budget rows whose draft amount differs from the persisted
  amount.
- Show `Belum disimpan` beside the changed budget.
- Show a page-level warning listing categories with unsaved changes.
- Place `Simpan Perubahan` directly below the related budget input on desktop
  and mobile layouts.
- Disable the save button when the draft matches the persisted amount.
- Show `Menyimpan...` while the request is running.
- Register a browser unload warning while unsaved budget changes exist.
- Keep create, delete, reset, transaction, registry, and forecast behavior
  unchanged.

## Files changed

- `apps/web/src/pages/BudgetingAlerts.jsx`
- `docs/project-audit/solving-reports/UAT_BUDGET_001A_BUDGET_EDIT_PERSISTENCE.md`

## Manual verification

June 2026:

- Initial Food budget: Rp500.000
- Initial Groceries budget: Rp1.200.000
- Changed Food input to Rp550.000.
- `Belum disimpan: Food` warning appeared.
- `Simpan Perubahan` became enabled next to the Food input.
- Save completed without browser console errors.
- Reload retained Food at Rp550.000.
- PostgreSQL Food budget: Rp550.000.
- Total budget: Rp1.750.000.
- Actual spending: Rp1.867.169.
- Remaining budget: -Rp117.169.
- Food actual spending: Rp463.400.
- Food remaining: Rp86.600.
- Food utilization: 84.25% (displayed as 84.3%).
- Food alert/status changed from `Hampir habis` to `Perlu dipantau`.

Data-integrity guard:

- Final transactions remained 25 / Rp1.867.169.
- Approved registry remained 25.
- Rejected registry remained 11.
- Reset Budget Bulan Ini was not executed.

## Test results

- Web lint: PASS.
- Full backend regression: PASS.
- Manual UI edit/save/reload: PASS.
- PostgreSQL persistence and forecast cross-check: PASS.

## Deferred backlog

The copy `Sumber kategori mengikuti transaksi dari spreadsheet` is no longer
fully accurate because local Blu PDF transactions also provide category
options. This copy change is intentionally out of scope for UAT-BUDGET-001A.
