# Task 4 - Approval Sync Decoupling

## Summary

Approval import dan retry sync tidak lagi menahan final ledger transaction saat
memanggil Google Sheets. Jalur API sekarang dipisah menjadi:

1. prepare request
2. commit perubahan PostgreSQL
3. lakukan spreadsheet sync di luar transaction final ledger
4. catat `sync_status` dalam transaction terpisah

## Files Changed

- `backend/app/api/imports.py`
- `backend/app/imports/services/import_service.py`
- `backend/tests/test_migration_runner.py`
- `backend/tests/imports/test_workspace_fingerprint_migration.py`
- `docs/project-audit/solving-reports/CHECKPOINT_TASK_01_03_NO_DB_MIGRATION.md`
- `docs/project-audit/solving-reports/TASK_04_APPROVAL_SYNC_DECOUPLING.md`

## Outcome

- Final approved transactions commit ke PostgreSQL lebih dulu
- Spreadsheet append tidak lagi berada di transaction yang sama dengan final
  ledger persistence
- Jika spreadsheet sync gagal setelah commit, approval tetap sah dan
  `sync_status` dicatat sebagai `failed` atau `needs_reconnect`
- Retry sync mengikuti pola yang sama

## Validation

- `python -m unittest discover -s backend/tests -t .`
- `npm --prefix apps/web run lint`
- `npm --prefix apps/landing run lint`
