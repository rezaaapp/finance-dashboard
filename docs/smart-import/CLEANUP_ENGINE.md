# Cleanup Engine

## Overview

Sprint 7 adds an hourly cleanup engine for Smart Import.

The goal is simple:

- uploaded PDFs are temporary
- review drafts expire
- final transactions and fingerprint registry stay intact

## PDF Lifecycle

The expected lifecycle is:

1. upload file
2. save file into temporary storage
3. parse and create review draft
4. approve and sync
5. delete temporary PDF

If the user never reviews the import, the temporary file is eligible for cleanup after 24 hours.

## Draft Lifecycle

Drafts are used only for review.

If an import job is not completed and has passed its expiration window, cleanup removes all remaining draft rows for that job.

The cleanup targets import jobs whose status is:

- `uploaded`
- `review`
- `expired`

After cleanup completes, the job status becomes `cleanup_completed`.

## Retry Sync

Retry sync only targets final transactions whose `sync_status` is:

- `failed`
- `needs_reconnect`

Retry sync does not:

- recreate final transactions
- recreate fingerprints
- reopen the parser

It only retries spreadsheet append for already-approved final rows.

## Preservation Rules

Cleanup never deletes:

- final `transactions`
- `import_transaction_registry`
- `import_jobs`

This preserves import history and duplicate-prevention state even when temporary review artifacts are removed.
