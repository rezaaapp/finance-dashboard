# Task 3 - PostgreSQL As Source Of Truth

## Summary

Task 3 clarifies that approved transactions are finalized in PostgreSQL first, while Google Sheets is treated as an input layer plus export/projection destination.

No large logic changes were introduced. This task is limited to copy/UX semantics and documentation so the product no longer implies that approve + spreadsheet delivery is atomic.

## Files Changed

- `apps/web/src/pages/ImportTransactions.jsx`
- `apps/web/src/components/import/ImportReview.jsx`
- `apps/web/src/components/import/ImportHistory.jsx`
- `docs/smart-import/SPREADSHEET_SYNC.md`
- `docs/smart-import/IMPORT_HISTORY.md`
- `docs/smart-import/REVIEW_TABLE.md`
- `docs/project-audit/solving-reports/TASK_03_POSTGRES_SOURCE_OF_TRUTH.md`

## Copy And Documentation Clarified

- Approval success copy now states that transactions are stored in Omon first.
- Warning copy now states that spreadsheet delivery can fail after approval without undoing the final ledger.
- Import review guidance now explains that PostgreSQL is the source of truth and Google Sheets is only used for input/projection.
- Import history labels now distinguish approved ledger rows from spreadsheet delivery counts.
- Smart import docs now define separate approval state versus spreadsheet delivery state.
- Review-table docs now match the current implementation where approved drafts are promoted to final transactions and removed from draft storage.

## DB Vs Google Sheet Flow

1. User reviews draft transactions from import parsing.
2. On approval, final rows are written into PostgreSQL `transactions`.
3. Fingerprints are written into `import_transaction_registry`.
4. The system attempts to send a spreadsheet copy to the configured Google Sheet tab.
5. `sync_status` records spreadsheet delivery outcome separately from approval.
6. Approved draft rows are removed from draft storage.

## Remaining Mismatch Risks

- The approval flow still performs spreadsheet delivery in the same operational path, so runtime failures can still happen after ledger persistence and before spreadsheet delivery completes.
- Operators can still misread sync counters if they ignore the updated copy and look only at raw counts.
- Retry sync still depends on Google OAuth scope and sheet/tab availability, so spreadsheet delivery can remain behind even though PostgreSQL is already correct.

## Validation Run

- `npm --prefix apps/web run lint -- src/pages/ImportTransactions.jsx src/components/import/ImportReview.jsx src/components/import/ImportHistory.jsx`
- `python -m unittest discover -s backend/tests -t .`
- `python -m unittest discover -s backend/tests/imports -t .`

## Notes

- Migration 019 was not run to production.
- No approval logic or transaction semantics were changed in this task.
- `pytest` was not available in the local runtime, so backend validation used the repository's existing `unittest` suite instead.
