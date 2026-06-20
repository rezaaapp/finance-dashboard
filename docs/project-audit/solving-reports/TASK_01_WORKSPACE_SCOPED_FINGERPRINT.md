# Solving Report - Task 1

## Summary

Smart Import fingerprint registry, final transaction fingerprint, canonical
fingerprint, and sync-status mutation are now scoped by `workspace_id`.
Identical fingerprints can exist safely in different workspaces.

## Root Cause

The initial Smart Import implementation used global fingerprint identity:

- `import_transaction_registry.transaction_fingerprint` was the primary key.
- final transaction unique indexes contained only the fingerprint.
- registry lookups and sync-status updates did not filter by workspace.
- `get_existing_transaction_fingerprints` explicitly discarded
  `workspace_id`.

This allowed activity in one workspace to suppress or mutate transaction state
in another workspace.

## Impact Area

- Blu PDF duplicate detection
- Approved and rejected fingerprint registry
- Final imported transaction upsert
- Canonical duplicate detection constraint
- Spreadsheet sync delivery status
- Existing production/staging registry data

## Files Changed

- `backend/db/migrations/019_scope_import_fingerprints_by_workspace.sql`
- `backend/app/imports/repositories/fingerprint_registry_repository.py`
- `backend/app/imports/repositories/final_transaction_repository.py`
- `backend/app/imports/repositories/import_repository.py`
- `backend/app/imports/services/import_service.py`
- `backend/tests/imports/test_blu_pdf_parser.py`
- `backend/tests/imports/test_workspace_fingerprint_migration.py`

## Technical Changes

- Added `workspace_id` to `import_transaction_registry`.
- Changed registry primary key to:

  ```text
  (workspace_id, transaction_fingerprint)
  ```

- Replaced global transaction fingerprint unique index with:

  ```text
  (workspace_id, import_transaction_fingerprint)
  ```

- Replaced global canonical fingerprint unique index with:

  ```text
  (workspace_id, canonical_fingerprint)
  ```

- Added workspace filtering to all registry reads/writes.
- Added workspace filtering to fingerprint-based sync-status updates.
- Changed Smart Import final transaction conflict handling to use the composite
  workspace key.
- Added migration guards that stop safely if duplicate fingerprints already
  exist inside the same workspace.

### Existing Data Handling

Historical registry rows are backfilled from final imported transactions when
one unambiguous workspace can be resolved.

Rows without workspace provenance are moved to:

```text
legacy_unscoped_import_transaction_registry
```

They are removed from the active registry instead of being assigned to an
arbitrary workspace. This primarily affects historical rejected fingerprints
that have no surviving transaction or draft relationship.

## Validation

Commands:

```text
python -m unittest discover -s backend/tests -t .
python -m compileall -q backend/app backend/scripts
npm run lint
git diff --check
```

Results:

- Backend tests: `69` passed.
- Task-specific workspace fingerprint tests: `6` passed.
- Backend compile: passed.
- Dashboard and landing lint: passed.
- Diff whitespace validation: passed.
- Test verifies the same fingerprint is registered independently for two
  workspaces.
- Test verifies sync status SQL includes the workspace predicate.
- Migration contract tests verify composite keys, legacy archive behavior, and
  duplicate guards.

Database migration was not applied to a live database in this task. It must be
executed and inspected in staging before production.

## Result

Successful at source, migration, and automated-test level.

## Remaining Risk

- Unresolved historical rejected fingerprints are archived and no longer
  suppress future imports. A previously rejected transaction may reappear once
  and require review.
- Migration 019 intentionally fails if duplicate fingerprints already exist
  within one workspace. Those rows must be reconciled before retrying.
- A staging database backup and duplicate audit are required before migration.
- Google Sheet append still runs inside the database transaction; this remains
  Task 4.

## Commit

Message:

```text
fix(import): scope fingerprints by workspace
```

The commit hash is reported after the commit is created.

## Follow-up Findings

- The existing import test suite can delete its tracked PDF fixture when an
  unexpected exception occurs because mocked temp storage points at the
  fixture. The fixture was restored after validation. Test temp paths should be
  isolated in a future test-maintenance task.

