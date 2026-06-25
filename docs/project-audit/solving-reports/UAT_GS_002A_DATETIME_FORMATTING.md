# UAT-GS-002A — Spreadsheet Datetime Formatting Fix

## Status

PASS

## Bug

UAT-GS-002 delivered one transaction successfully, but Google Sheets displayed column B (`Waktu Transaksi`) as a raw serial value:

```text
46175.90139
```

Expected display:

```text
2026-06-01 13:28
```

or another human-readable date/time format.

## Root cause

Spreadsheet delivery appended datetime values with `USER_ENTERED`, then copied formatting from the nearest template row. The target template row did not reliably provide a datetime number format for column B, so Google Sheets could display the parsed datetime as a serial number.

## Fix summary

- Kept existing A–G mapping unchanged.
- Kept amount as numeric.
- After append, applies an explicit Google Sheets `DATE_TIME` number format to column B for the appended row range.
- Uses format pattern `yyyy-mm-dd hh:mm`.
- Keeps template row format/data validation copy as best-effort for other columns.
- Does not change ledger logic, fingerprint logic, delivery routing, or bulk sync behavior.

## Files changed

- `backend/app/services/google_sheets_client.py`
- `backend/app/imports/services/spreadsheet_sync_service.py`
- `backend/tests/imports/test_blu_pdf_parser.py`

## Manual UAT evidence

Transaction tested:

- `LEGE COFFEE & TOASTIE-H`
- Target spreadsheet: `Omon-UAT-Spreadsheet`
- Target sheet: `Start 1 Juni`

Spreadsheet verification:

- Rows before/after: 3 → 4
- Appended count: 1
- Column B display: `2026-06-01 13:28`
- Column E amount remained numeric.
- Mapping A–G remained unchanged.

## Ledger verification

- Final transactions: 25
- Total expense: Rp1.867.169
- Approved registry: 25
- Rejected registry: 11
- Sync success: 1 → 2
- Pending delivery: 24 → 23

## Test results

- Targeted formatter tests: PASS.
- Targeted import suite via unittest: PASS.
- Combined targeted backend validation: 74 PASS.
- Web lint: PASS.

## Non-blocking notes

- `smart_import.sheet_validation.warning` for missing/ unreadable Nama and Source Dana dropdown validation is a separate setup/data-validation issue and not a blocker for UAT-GS-002A.
- `PythonFinalizationError` observed after manual helper output was shutdown cleanup noise after successful JSON output.
