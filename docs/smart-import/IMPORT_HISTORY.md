# Import History

## Overview

Sprint 7 completes the operational layer for Smart Import by keeping import job metadata after review and after temporary PDF cleanup.

Import history stores metadata only. The original uploaded PDF is treated as temporary processing input and is not kept as permanent storage.

## What History Shows

Each import job exposes:

- filename
- provider
- import time
- transactions found
- new transactions
- existing transactions
- approved transactions in PostgreSQL
- rejected transactions
- spreadsheet copies delivered
- spreadsheet copies pending or failed
- import status

History also exposes whether the PDF is still available or already deleted.

## Why History Survives Cleanup

Cleanup only removes:

- temporary PDF files
- expired review drafts

Cleanup never removes:

- `import_jobs`
- final `transactions`
- `import_transaction_registry`

This keeps the audit trail available even after temporary artifacts are gone.

## Detail View

History detail is designed as an operational summary for one import job:

- import metadata
- review summary
- PostgreSQL approval outcome
- spreadsheet delivery outcome
- PDF lifecycle state
- retryable sync state

If any final transactions still have `sync_status = failed` or `needs_reconnect`, the job remains retryable from history without recreating transactions.

History should be read with these semantics:

- approval counts represent rows already saved into PostgreSQL
- sync counts represent spreadsheet delivery only
- a non-zero sync failure count does not mean approval was rolled back
