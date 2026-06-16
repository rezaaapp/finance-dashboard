# Review Table

## Review Lifecycle

The Smart Import review lifecycle in Sprint 5 is:

1. Upload statement
2. Parse and normalize transactions
3. Generate fingerprints
4. Skip transactions that already exist as previously approved fingerprints
5. Persist only new transactions into `import_draft_transactions`
6. Show those new draft rows in the review table
7. Approve or reject draft rows

Approved rows stay in the draft table with status `approved`.

Rejected rows are removed from the draft table.

## Filtering

The review UI supports these filters:

- `Semua`
- one filter per `review_group`
- `Perlu Review`

`review_group` is used only for UI grouping and filtering convenience.

It is never used for duplicate detection.

`Perlu Review` highlights rows that still have an empty category value in the draft review state.

## Approval Concept

Approval in Sprint 5 does not insert anything into the final transaction table.

Approval only updates the draft row:

- `status` -> `approved`
- `category` -> saved from the review UI
- `notes` -> saved from the review UI

This keeps the review step separate from later spreadsheet sync or final persistence work.

## Draft Lifecycle

Draft rows represent review candidates only.

Important rules:

- existing transactions are skipped before draft insert
- only new transactions appear in review
- approved rows remain as proof of previously reviewed fingerprints
- rejected rows are deleted from draft storage

This makes overlap imports deterministic while keeping the review surface focused only on genuinely new transactions.
