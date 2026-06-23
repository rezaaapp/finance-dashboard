# UAT-GS-001A — Persist Default Destination Tab

## Status

PASS

## Root Cause

- Source configuration only submitted `spreadsheet_url`.
- Detected worksheets were displayed but could not be selected as a persistent default.
- Saving an existing active source returned a duplicate conflict instead of updating `sheet_name`.
- Import Review's filename suggestion took priority over the persisted source default.

## Fix Summary

- Added a default destination-tab selector to source configuration.
- Source save now submits and persists `sheet_name`.
- Saving an existing source updates its configuration without creating a duplicate.
- Import Review and Retry Sync prioritize the source's persisted `sheet_name`.
- Users may still override the destination tab before delivery.
- Spreadsheet delivery, ledger, fingerprint, and routing behavior remain unchanged.

## Files Changed

- `apps/web/src/pages/Configuration.jsx`
- `apps/web/src/pages/ImportTransactions.jsx`
- `backend/app/repositories/google_sheet_source_repository.py`
- `backend/tests/test_google_sheet_source_repository.py`

## Validation

- Targeted backend tests: 74 PASS.
- Web lint: PASS.
- Manual UAT: PASS.
- Persisted `sheet_name`: `Start 1 Juni`.
- Configuration persistence after reload: PASS.
- Retry Sync default destination: `Start 1 Juni` — PASS.
- Ledger unchanged: 25 transactions / Rp1.867.169.
- Fingerprint registry unchanged: 25 approved / 11 rejected.
- Spreadsheet sync jobs: 0.

The full backend suite was not rerun because the environment rejected the
tool escalation after its usage/tool-approval limit was reached. The targeted
backend suite, web lint, database verification, and manual UAT above were used
as the replacement validation set.

## Out of Scope

- Spreadsheet fingerprint column.
- Multi-month routing.
- Spreadsheet delivery behavior changes.
- Ledger logic changes.
- Spreadsheet transaction sync.
