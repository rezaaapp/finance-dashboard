# Fingerprint Engine

## Why Fingerprint Exists

The transaction fingerprint exists to make imported transactions deterministic before any persistence or review workflow is introduced.

It prepares Smart Import for future incremental import logic by ensuring the same parsed transaction always produces the same identifier.

## Normalization Strategy

Fingerprint generation depends on rule-based merchant normalization so small statement suffixes do not create false differences.

Current normalization rules:

- trim leading and trailing spaces
- collapse duplicated spaces
- remove trailing reference numbers
- remove obvious QR or QRIS suffixes
- remove obvious reference labels such as `REF`, `REFERENCE`, `ID`, `INV`, and `TRX`
- preserve the original merchant string separately as `merchant_original`

Examples:

- `Fore Coffee 61715` -> `Fore Coffee`
- `SUPERINDO BCY QR` -> `SUPERINDO`
- `jajanan ahmadi 000885` -> `jajanan ahmadi`

## Fingerprint Fields

The fingerprint uses:

- `source_dana`
- `datetime`
- `merchant_normalized`
- `amount`

It is generated as a SHA256 hash from a canonical string payload.

## Why Review Group Is Excluded

`review_group` is only parser metadata derived from Blu section headers.

It is intentionally excluded from the fingerprint because:

- section labels are not the actual financial transaction identity
- the same transaction should keep the same fingerprint even if review grouping changes later
- fingerprinting should stay focused on deterministic transaction identity fields

## Why Normalized Merchant Is Used

`merchant_normalized` is used instead of raw merchant text because statement noise such as trailing numeric references or QR suffixes should not change transaction identity.

This reduces accidental fingerprint drift while still preserving `merchant_original` for review and debugging.
