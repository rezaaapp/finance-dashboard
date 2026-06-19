# Task 5.6 — Local PostgreSQL Migration 019 Verification

## Migration execution result

PASS

Migration dijalankan ke local PostgreSQL target:

- host: `127.0.0.1`
- port: `5432`
- database: `finance_dashboard_local`
- SSL: `false`
- migration URL: local PostgreSQL

Catatan:

- Verifikasi ini **tidak** menggunakan production database.
- File `backend/.env_prod` terdeteksi sebagai backup env prod user dan **tidak** dipakai dalam task ini.

## Migration order

Semua migration berjalan dari awal dan **tidak ada yang skipped**.

Urutan eksekusi:

1. `001_initial_multi_tenant_schema.sql`
2. `002_add_workspace_google_sheet_sources.sql`
3. `003_add_global_user_roles.sql`
4. `004_add_ai_sync_database_foundation.sql`
5. `005_add_google_oauth_connection_unique_constraint.sql`
6. `006_add_google_sheet_source_title.sql`
7. `007_add_week5_classification_columns.sql`
8. `008_add_week5_classification_rule_columns.sql`
9. `009_add_classification_performance_indexes.sql`
10. `010_add_workspace_insight_settings.sql`
11. `011_add_workspace_invitations.sql`
12. `012_add_budgets.sql`
13. `012_add_import_jobs.sql`
14. `012_add_inquiry_search_support.sql`
15. `013_add_budget_category_ignores.sql`
16. `013_add_import_draft_transactions.sql`
17. `014_add_import_review_fields.sql`
18. `015_add_import_transaction_registry.sql`
19. `016_add_import_history_and_cleanup.sql`
20. `017_add_import_registry_status.sql`
21. `018_add_import_owner_and_canonical_fingerprint.sql`
22. `019_scope_import_fingerprints_by_workspace.sql`

Observed result:

- total migration file ditemukan: `22`
- total migration applied: `22`
- duplicate version di `schema_migrations`: `0`
- `019_scope_import_fingerprints_by_workspace.sql`: tercatat sebagai applied

## Schema verification

PASS

Verifikasi hasil schema:

- `public.import_transaction_registry.workspace_id` ada
- type: `uuid`
- nullable: `NO`

Hasil primary key registry:

- constraint: `import_transaction_registry_pkey`
- column order:
  1. `workspace_id`
  2. `transaction_fingerprint`

## Constraint verification

PASS

Verifikasi index/constraint fingerprint:

- `transactions_workspace_import_fingerprint_unique`
  - unique on `(workspace_id, import_transaction_fingerprint)`
  - partial where fingerprint is not null

- `transactions_workspace_canonical_fingerprint_unique`
  - unique on `(workspace_id, canonical_fingerprint)`
  - partial where fingerprint is not null

- `import_transaction_registry_workspace_status_idx`
  - index on `(workspace_id, status)`

## Fingerprint verification

PASS

Evidence:

1. Migration 019 berhasil applied di database kosong local tanpa error.
2. Unit test suite tetap hijau, termasuk coverage import/fingerprint/workspace migration safety.
3. Runtime smoke test membuktikan:
   - upload pertama di workspace A menghasilkan `29` transaksi baru
   - reject terhadap 29 draft mencatat fingerprint rejected
   - upload file yang sama lagi di workspace A menghasilkan:
     - `new_transactions = 0`
     - `existing_transactions = 29`
     - `rejected_transactions = 29`
     - `no_new_transactions = true`
   - upload file yang sama di workspace B tetap menghasilkan:
     - `new_transactions = 29`
     - `existing_transactions = 0`
     - `rejected_transactions = 0`

Interpretasi:

- duplicate detection dalam workspace berjalan
- fingerprint registry tidak bocor lintas workspace
- objective Task 1 + migration 019 benar-benar terkonfirmasi di runtime local

## Workspace verification

PASS

Runtime verification memakai dua workspace baru yang dibuat di local DB:

- Workspace A:
  - upload pertama: `29` new
  - upload kedua file yang sama: seluruh transaksi terbaca sebagai existing/rejected

- Workspace B:
  - upload file yang sama tetap diproses sebagai `29` transaksi baru

Ini menunjukkan isolasi fingerprint dan import state benar-benar workspace-scoped setelah migration 019.

## Blu Import compatibility

PASS

Yang tervalidasi di schema terbaru:

- PDF upload valid: PASS
- review payload: PASS
- reject flow: PASS
- import history: PASS
- retry sync pada job tanpa transaksi retryable: PASS
- duplicate detection dalam workspace: PASS
- workspace isolation: PASS

Approve flow result:

- endpoint approve tidak crash oleh schema mismatch
- pada workspace tanpa target Google Sheet/tab, endpoint mengembalikan controlled response:
  - status: `409`
  - error code: `missing_target_sheet`
  - message: `Pilih target spreadsheet dan tab tujuan sebelum approve.`

Interpretasi teknis:

- approve path sekarang **compatible** dengan schema terbaru
- failure yang terjadi bersifat operasional/configuration, **bukan** schema/runtime blocker

## Remaining risk

1. Happy path approve + spreadsheet sync ke Google Sheet nyata belum diverifikasi pada task ini karena workspace local yang dipakai tidak punya source/tab target yang aktif.
2. Satu instance backend lama di port `8001` sempat menunjukkan perilaku stale terhadap schema lama. Setelah backend baru di-start ulang pada port `8002`, smoke test local berjalan normal. Ini mengindikasikan verifikasi runtime sebaiknya dilakukan pada process yang start **setelah** migration selesai.
3. Working tree saat task dimulai memiliki file untracked `backend/.env_prod`, tetapi file itu adalah backup env prod dan tidak dipakai oleh task ini.

## Test result

### Runtime verification

PASS

Ringkasan smoke test di backend fresh setelah migration:

| Area | Result | Notes |
|---|---|---|
| Login local | PASS | session JWT local valid |
| Blu PDF upload | PASS | 29 transaksi terdeteksi |
| Import review | PASS | 29 draft transaction terbaca |
| Approve | PASS | controlled `409 missing_target_sheet`, tidak ada schema crash |
| Reject | PASS | 29 draft rejected |
| Retry sync | PASS | `skipped` ketika tidak ada transaksi retryable |
| Import history | PASS | job tercatat sebagai `completed` |
| Duplicate detection | PASS | upload ulang di workspace sama tidak membuat transaksi baru |
| Workspace isolation | PASS | upload file yang sama di workspace lain tetap dianggap transaksi baru |

### Validation commands

Command yang dijalankan:

```bash
.\backend\venv\Scripts\python.exe backend\scripts\run_migrations.py
.\backend\venv\Scripts\python.exe -m unittest discover -s backend/tests -t .
npm --prefix apps/web run lint
npm --prefix apps/landing run lint
```

Hasil:

- migration runner: PASS
- backend unittest: PASS (`Ran 96 tests`)
- web lint: PASS
- landing lint: PASS

## Final recommendation

### Apakah migration 019 aman?

PASS

Alasan teknis:

- migration berhasil dijalankan end-to-end pada database kosong local
- `schema_migrations` konsisten
- schema final sesuai target
- fingerprint dan duplicate behavior tervalidasi di runtime antar workspace

### Apakah Blu Import sekarang compatible dengan schema terbaru?

PASS

Alasan teknis:

- blocker `workspace_id does not exist` sudah tidak muncul pada backend fresh pasca-migration
- upload, review, reject, history, retry, duplicate detection, dan workspace isolation berjalan di schema terbaru
- approve path gagal secara terkontrol karena belum ada target sheet, bukan karena incompatibility schema

### Apakah aman lanjut Task 6 Dashboard Aggregation?

YES

Alasan teknis:

1. Blocker utama migration/schema compatibility sudah tertutup.
2. Local runtime membuktikan flow import tidak lagi pecah karena `workspace_id`.
3. Test suite dan lint tetap hijau setelah migration diverifikasi.
4. Remaining risk yang tersisa berada pada external integration path Google Sheet target nyata, bukan pada fondasi schema PostgreSQL untuk Task 6.
