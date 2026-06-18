# Spreadsheet Sync

## Overview

Smart Import approval has two related but separate outcomes:

1. reviewer approves draft transactions into final PostgreSQL ledger rows
2. the system attempts to deliver a spreadsheet copy for operational visibility/export

PostgreSQL is the system of record and source of truth for approved transactions.

Google Sheets has two roles only:

- input layer for import/parsing configuration and source connectivity
- export/projection layer for spreadsheet copies after approval

Approval success must never be interpreted as an atomic guarantee that PostgreSQL and Google Sheets both succeeded in the same commit.

## Approval Lifecycle

The approval pipeline is:

1. load selected draft transactions
2. merge reviewer updates such as category and notes
3. persist final transactions into `transactions`
4. register each `transaction_fingerprint`
5. attempt Google Spreadsheet append
6. update `sync_status`
7. delete approved draft rows

The important semantic boundary is:

- approval writes the final ledger state into PostgreSQL
- spreadsheet delivery records whether a copy was successfully sent afterward

If spreadsheet sync fails, the final transaction still exists in PostgreSQL and remains the authoritative record.

## Source Of Truth Rules

Use these rules consistently in code, docs, and UI copy:

- Final approved financial data lives in PostgreSQL `transactions`
- Duplicate prevention lives in `import_transaction_registry`
- Google Sheets does not define approval truth
- Google Sheets does not replace the final ledger
- Retry sync resends spreadsheet copies only; it does not recreate approved transactions

## State Model

Approval state and spreadsheet delivery state are intentionally tracked separately.

Typical interpretation:

- Approved in PostgreSQL + `sync_status = success`: ledger saved and spreadsheet copy delivered
- Approved in PostgreSQL + `sync_status = failed`: ledger saved, spreadsheet copy failed
- Approved in PostgreSQL + `sync_status = needs_reconnect`: ledger saved, spreadsheet write blocked by OAuth scope or reconnect issue
- Approved in PostgreSQL + `sync_status = pending`: ledger saved, spreadsheet delivery not yet confirmed

This separation is what prevents the UI from implying a false all-or-nothing outcome.

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

This is deliberate. PostgreSQL remains the source of truth even when spreadsheet delivery is behind.

Retry sync should be described as:

- retrying spreadsheet delivery for already-approved transactions
- not reopening approval
- not recreating final ledger rows
- not promising atomic recovery across PostgreSQL and Google Sheets
