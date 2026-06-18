# Spreadsheet Sync

## Overview

Sprint 6 completes the Smart Import approval pipeline for Blu imports:

1. reviewer approves draft transactions
2. approved drafts become final `transactions` rows
3. transaction fingerprints are registered in `import_transaction_registry`
4. approved rows are appended to Google Spreadsheet
5. sync status is recorded on final transactions
6. draft rows are removed after approval

This keeps import review separate from the final ledger while still making spreadsheet sync part of the approval flow.

## Approval Lifecycle

The approval pipeline is:

1. load selected draft transactions
2. merge reviewer updates such as category and notes
3. persist final transactions into `transactions`
4. register each `transaction_fingerprint`
5. attempt Google Spreadsheet append
6. update `sync_status`
7. delete approved draft rows

Spreadsheet sync is intentionally downstream from final persistence. If spreadsheet sync fails, the final transaction still exists in the database.

## Fingerprint Registry

`import_transaction_registry` is the incremental import registry.

It stores:

- `transaction_fingerprint`
- `provider`
- `created_at`
- `approved_at`

The registry is the only source used to decide whether a parsed transaction has already been approved before. `review_group` is never part of the registry and never part of duplicate detection.

## Sync Status

Final imported transactions track spreadsheet delivery through `transactions.sync_status`.

Available values:

- `pending`
- `success`
- `failed`
- `needs_reconnect`

`sync_error_message` stores the latest sync failure detail when the append step fails.

## OAuth Write Scope

Spreadsheet append needs the Google Sheets write scope:

- `https://www.googleapis.com/auth/spreadsheets`

If the active Google OAuth token only has:

- `https://www.googleapis.com/auth/spreadsheets.readonly`

then sync returns `needs_reconnect` and does not attempt any spreadsheet write. This prevents partial failures caused by an outdated token scope.

## Retry Strategy

Spreadsheet sync failure does not roll back:

- final transaction persistence
- fingerprint registry insertion

This is deliberate. The database remains the source of truth, and a future sprint can add explicit retry actions for rows with `sync_status = failed`.
