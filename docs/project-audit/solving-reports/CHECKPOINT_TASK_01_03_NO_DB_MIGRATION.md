# Checkpoint Task 1-3 (No DB Migration)

## Scope

Checkpoint ini memvalidasi Task 1 sampai Task 3 tanpa menjalankan migration `019`
ke production, main database, maupun environment staging/dev yang belum tersedia.

Metode validasi yang dipakai:

- SQL review untuk migration `019`
- unit test / contract test
- migration safety analysis
- full backend unittest
- frontend lint
- landing lint

## Checkpoint Result

Task 1-3 aman untuk lanjut ke Task 4 tanpa menjalankan migration database.

## Migration 019 Review

File:

- `backend/db/migrations/019_scope_import_fingerprints_by_workspace.sql`

SQL review memastikan hal berikut:

- `workspace_id` ditambahkan ke `import_transaction_registry`
- primary key registry diubah menjadi `(workspace_id, transaction_fingerprint)`
- unique index final transaction diubah menjadi `(workspace_id, import_transaction_fingerprint)`
- unique index canonical fingerprint diubah menjadi `(workspace_id, canonical_fingerprint)`
- legacy registry row yang tidak bisa dipetakan ke satu workspace tunggal diarsipkan ke `legacy_unscoped_import_transaction_registry`
- duplicate within workspace diblok via `raise exception`

## Duplicate Pre-check

Migration `019` punya duplicate pre-check eksplisit untuk dua area:

- duplicate `import_transaction_fingerprint` dalam workspace yang sama
- duplicate `canonical_fingerprint` dalam workspace yang sama

Contract test juga memastikan guard tersebut muncul sebelum pembuatan unique index
workspace-scoped.

## Safe Failure Analysis

Safe failure dinilai aman berdasarkan dua lapis proteksi:

1. Migration `019` sendiri melakukan `raise exception` jika duplicate within
   workspace ditemukan.
2. `backend/scripts/run_migrations.py` menjalankan tiap migration di dalam
   `connection.transaction()`, sehingga kegagalan SQL akan menggagalkan whole
   migration transaction dan mencegah pencatatan `schema_migrations` versi itu.

Tambahan unit test memverifikasi:

- migration yang berhasil baru mencatat versi setelah SQL selesai
- migration yang gagal tidak mencatat versi schema migration
- skip path tidak menjalankan SQL migration ulang

## Workspace-Scoped Test Coverage

Coverage lintas dua workspace sudah ada dan tervalidasi:

- fingerprint registry bisa menyimpan fingerprint yang sama untuk
  `workspace-1` dan `workspace-2`
- sync status update dibatasi oleh `workspace_id`
- migration contract test memverifikasi composite key dan index workspace-scoped

## Validation Run

- `python -m unittest discover -s backend/tests -t .`
- `npm --prefix apps/web run lint`
- `npm --prefix apps/landing run lint`

Results:

- backend unittest: `83` tests passed
- web lint: passed
- landing lint: passed

## Remaining Limits

- Migration `019` belum dieksekusi ke database nyata mana pun
- Duplicate audit terhadap data existing masih perlu dilakukan saat staging/dev
  database tersedia
- Validasi runtime plan untuk migration tetap perlu dilakukan sebelum production

## Decision

Checkpoint Task 1-3 dinyatakan aman untuk melanjutkan Task 4.
