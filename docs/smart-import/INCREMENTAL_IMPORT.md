# Incremental Import

## Concept

Incremental import exists to support overlapping statement uploads without sending the same transaction into review multiple times.

The engine compares each parsed transaction against previously approved or completed imports and marks whether that transaction already exists.

## Fingerprint Strategy

Duplicate detection uses only `transaction_fingerprint`.

The fingerprint already captures deterministic transaction identity from:

- `source_dana`
- canonicalized `datetime`
- `merchant_normalized`
- canonicalized `amount`

Because that identity is already normalized and hashed, the incremental engine does not compare merchant text, datetime, or amount separately.

## Overlap Upload

Example:

- Upload statement for `1-15 June` -> all transactions are new
- Later upload statement for `1-30 June`
- Transactions from `1-15 June` become `existing`
- Transactions from `16-30 June` remain `new`

This lets the system prepare only the new transactions for the next review step.

## Why Duplicate Uses Fingerprint Only

Fingerprint-only duplicate detection is intentional because:

- it keeps incremental logic deterministic
- it avoids repeated heuristic comparisons
- it prevents `review_group` or other parser metadata from affecting identity

`review_group` remains persisted in the draft table only for future review convenience, not for duplicate detection.
