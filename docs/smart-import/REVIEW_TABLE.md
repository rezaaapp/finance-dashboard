# Review Table

## Review Lifecycle

The current Smart Import review lifecycle is:

1. Upload statement
2. Parse and normalize transactions
3. Generate fingerprints
4. Skip transactions that already exist as previously approved fingerprints
5. Persist only new transactions into `import_draft_transactions`
6. Show those new draft rows in the review table
7. Approve or reject draft rows

Approved rows are promoted into final `transactions`, registered in
`import_transaction_registry`, and then removed from the draft table.

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

Approval inserts the reviewed result into the final PostgreSQL ledger.

Approval also keeps spreadsheet delivery as a separate downstream concern:

- `transactions` is the final ledger
- `import_transaction_registry` is the duplicate-prevention registry
- Google Sheets receives a copy after approval when delivery succeeds
- spreadsheet delivery failure does not undo final ledger approval

## Draft Lifecycle

Draft rows represent review candidates only.

Important rules:

- existing transactions are skipped before draft insert
- only new transactions appear in review
- approved rows do not remain in draft storage after final persistence
- proof of prior approval lives in final `transactions` and `import_transaction_registry`
- rejected rows are deleted from draft storage

This makes overlap imports deterministic while keeping the review surface focused only on genuinely new transactions.
