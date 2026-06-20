# Local PostgreSQL Migration 019 Verification Checklist

Tujuan checklist ini adalah memverifikasi migration `019_scope_import_fingerprints_by_workspace.sql` di environment local PostgreSQL tanpa menyentuh production/main database.

Catatan penting:

- Jangan jalankan checklist ini ke production tanpa backup.
- Migration runner project sudah menerapkan insert ke `schema_migrations` di transaksi yang sama dengan SQL migration. Jika migration gagal di tengah jalan, version migration tidak boleh tercatat sebagai applied.
- Migration 019 punya pre-check duplicate dan dirancang fail-fast sebelum unique index workspace-scoped dibuat.

## 1. Prasyarat install PostgreSQL local

Pastikan salah satu opsi berikut sudah siap:

- PostgreSQL server lokal terpasang dan running.
- Atau Docker Desktop tersedia untuk menjalankan container PostgreSQL lokal.

Minimum yang dibutuhkan:

- PostgreSQL 14+ direkomendasikan.
- User database lokal yang bisa membuat database baru.
- Akses shell untuk menjalankan command project.

## 2. Cara buat database local

Contoh dengan `psql`:

```bash
createdb finance_dashboard_local
```

Atau dari `psql`:

```sql
create database finance_dashboard_local;
```

Jika menggunakan Docker:

```bash
docker run --name finance-dashboard-pg ^
  -e POSTGRES_PASSWORD=postgres ^
  -e POSTGRES_USER=postgres ^
  -e POSTGRES_DB=finance_dashboard_local ^
  -p 5432:5432 ^
  -d postgres:16
```

## 3. Environment variable yang perlu di-set

Set minimal env berikut untuk backend local:

```env
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/finance_dashboard_local
DATABASE_MIGRATION_URL=postgresql://postgres:postgres@127.0.0.1:5432/finance_dashboard_local
DATABASE_SSL=false
DATABASE_SSL_REJECT_UNAUTHORIZED=false

DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=<local-password>
DASHBOARD_AUTH_TOKEN=<legacy-static-token>
JWT_SECRET=<jwt-secret>
TOKEN_ENCRYPTION_SECRET=<encryption-secret>
```

Jika project memakai file `.env`, pastikan values local tidak mengarah ke Supabase / production.

## 4. Command menjalankan migration dari awal

Dari root repo:

```bash
.\backend\venv\Scripts\python.exe backend\scripts\run_migrations.py
```

Expected behavior:

- Migration runner membuat `schema_migrations` bila belum ada.
- Seluruh file migration berjalan berurutan.
- Jika migration 019 gagal, process exit non-zero dan `019_scope_import_fingerprints_by_workspace.sql` tidak tercatat di `schema_migrations`.

## 5. Command menjalankan test setelah migration

Setelah migration selesai:

```bash
.\backend\venv\Scripts\python.exe -m unittest discover -s backend/tests -t .
npm --prefix apps/web run lint
npm --prefix apps/landing run lint
```

Optional targeted re-check:

```bash
.\backend\venv\Scripts\python.exe -m unittest backend.tests.imports.test_workspace_fingerprint_migration
.\backend\venv\Scripts\python.exe -m unittest backend.tests.test_migration_runner
```

## 6. SQL verifikasi kolom `workspace_id`

```sql
select
  column_name,
  is_nullable,
  data_type
from information_schema.columns
where table_schema = 'public'
  and table_name = 'import_transaction_registry'
  and column_name = 'workspace_id';
```

Expected:

- `workspace_id` ada
- `is_nullable = NO`
- `data_type = uuid`

## 7. SQL verifikasi composite key

```sql
select
  tc.constraint_name,
  kcu.column_name,
  kcu.ordinal_position
from information_schema.table_constraints tc
join information_schema.key_column_usage kcu
  on tc.constraint_name = kcu.constraint_name
 and tc.table_schema = kcu.table_schema
where tc.table_schema = 'public'
  and tc.table_name = 'import_transaction_registry'
  and tc.constraint_type = 'PRIMARY KEY'
order by kcu.ordinal_position;
```

Expected urutan kolom primary key:

1. `workspace_id`
2. `transaction_fingerprint`

## 8. SQL verifikasi duplicate fingerprint per workspace

Import fingerprint:

```sql
select
  workspace_id,
  import_transaction_fingerprint,
  count(*) as duplicate_count
from public.transactions
where import_transaction_fingerprint is not null
group by workspace_id, import_transaction_fingerprint
having count(*) > 1;
```

Canonical fingerprint:

```sql
select
  workspace_id,
  canonical_fingerprint,
  count(*) as duplicate_count
from public.transactions
where canonical_fingerprint is not null
group by workspace_id, canonical_fingerprint
having count(*) > 1;
```

Expected:

- Kedua query mengembalikan 0 row setelah migration sukses.

## 9. Cara rollback aman jika local migration gagal

Kalau migration gagal sebelum selesai:

1. Jangan lanjutkan aplikasi seolah migration sukses.
2. Cek apakah `019_scope_import_fingerprints_by_workspace.sql` tercatat di `schema_migrations`.
3. Jika tidak tercatat, perbaiki data/duplikasi penyebab failure lalu rerun migration.
4. Jika database local sudah terlanjur kotor dan lebih cepat untuk reset, drop database local lalu buat ulang database kosong, kemudian rerun seluruh migration dari awal.

Contoh reset local database:

```bash
dropdb finance_dashboard_local
createdb finance_dashboard_local
.\backend\venv\Scripts\python.exe backend\scripts\run_migrations.py
```

## 10. Catatan: jangan jalankan ke production tanpa backup

Sebelum production/main database:

- Ambil full backup.
- Jalankan duplicate pre-check query pada snapshot atau staging clone.
- Verifikasi jumlah row `legacy_unscoped_import_transaction_registry`.
- Siapkan rollback plan operasional.
- Pastikan aplikasi yang aktif sudah sesuai dengan schema target.

## Static Safety Notes for Migration 019

Hasil review statis saat ini:

1. Migration 019 sudah punya pre-check duplicate untuk:
   - `import_transaction_fingerprint` per `workspace_id`
   - `canonical_fingerprint` per `workspace_id`
2. Migration 019 mengarsipkan row registry lama yang tidak bisa dipetakan ke workspace ke `legacy_unscoped_import_transaction_registry`, bukan menebak workspace secara silent.
3. Migration runner menulis `schema_migrations` setelah SQL migration sukses di transaksi yang sama. Bila SQL migration meledak, version tidak boleh tercatat sebagai applied.
4. Sampai local PostgreSQL siap, Blu PDF import end-to-end tetap dianggap pending verification.
