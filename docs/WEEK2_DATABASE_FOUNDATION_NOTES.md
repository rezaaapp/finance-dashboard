# Week 2 Database Foundation Notes

Review ini dibuat untuk Task 2.1 pada branch `feat/database-foundation`.
Tujuannya mencatat kondisi fondasi database yang sudah ada sebelum perubahan
teknis Week 2 berikutnya.

## 1. Database Settings Yang Sudah Ada

- `backend/app/config.py` memuat environment dari `.env` root lalu
  `backend/.env` dengan `backend/.env` override nilai root.
- Settings database Python yang sudah tersedia:
  - `DATABASE_URL`
  - `DATABASE_SSL`
  - `DATABASE_SSL_REJECT_UNAUTHORIZED`
  - `DATABASE_POOL_MAX`
- `DATABASE_URL` saat ini wajib. Jika tidak tersedia, aplikasi FastAPI akan
  raise `ValueError("DATABASE_URL belum diset di .env")` saat startup.
- `backend/.env.example` sudah mendokumentasikan placeholder database:
  - `DATABASE_URL=postgresql://postgres:replace_with_password@localhost:5432/finance_dashboard`
  - `DATABASE_SSL=false`
  - `DATABASE_SSL_REJECT_UNAUTHORIZED=true`
  - `DATABASE_POOL_MAX=10`
  - `DATABASE_IDLE_TIMEOUT_MS=30000`
  - `DATABASE_CONNECTION_TIMEOUT_MS=10000`
- `docs/ENVIRONMENT.md` dan `README.md` sudah menyebut PostgreSQL sebagai arah
  penyimpanan production untuk user, workspace, token, transaksi, dan hasil
  klasifikasi.

## 2. DB Connection Helper atau Pool Yang Sudah Ada

- Python backend memiliki `backend/app/database.py`.
- Implementasi Python menggunakan `psycopg_pool.ConnectionPool` dari dependency
  `psycopg[binary,pool]==3.3.2`.
- Pool Python dibuat dengan:
  - `conninfo=settings.DATABASE_URL`
  - `min_size=0`
  - `max_size=settings.DATABASE_POOL_MAX`
  - SSL `verify-full` jika `DATABASE_SSL=true` dan
    `DATABASE_SSL_REJECT_UNAUTHORIZED=true`
  - SSL `require` jika `DATABASE_SSL=true` dan reject unauthorized dimatikan
- Helper Python yang tersedia:
  - `ensure_pool_open()`
  - `close_database_pool()`
  - `get_db_connection()` context manager
- Node scripts memiliki `backend/node/db.ts`.
- Implementasi Node menggunakan `pg.Pool` dengan:
  - `DATABASE_URL`
  - `DATABASE_POOL_MAX`
  - `DATABASE_IDLE_TIMEOUT_MS`
  - `DATABASE_CONNECTION_TIMEOUT_MS`
  - `DATABASE_SSL`
  - `DATABASE_SSL_REJECT_UNAUTHORIZED`
- Helper Node yang tersedia:
  - `pool`
  - `query()`
  - `withTransaction()`
  - `closeDatabase()`
- Folder `backend/app/db` tidak ada. Repository memakai
  `backend/app/database.py` untuk helper database Python.

## 3. Migration Files Yang Sudah Ada

Folder `backend/db/migrations` sudah ada dengan tiga file:

- `001_initial_multi_tenant_schema.sql`
  - Membuat extension `pgcrypto` dan `citext`.
  - Membuat function trigger `set_updated_at()`.
  - Membuat tabel:
    - `users`
    - `workspaces`
    - `workspace_members`
    - `workspace_configurations`
    - `user_tokens`
  - Membuat index untuk workspace membership dan token expiry.
  - Membuat trigger `updated_at` untuk tabel-tabel awal.
- `002_add_workspace_google_sheet_sources.sql`
  - Menambah kolom `workspace_configurations.google_sheet_sources jsonb`.
  - Mengisi `google_sheet_sources` dari `google_sheet_id` existing jika ada.
- `003_add_global_user_roles.sql`
  - Menambah kolom `users.role`.
  - Menambah constraint role global:
    `super_admin`, `owner`, `member`, `user`.
  - Membuat index `users_role_idx`.

Belum terlihat tabel `schema_migrations` atau metadata migration lain untuk
melacak migration yang sudah dijalankan.

## 4. Script Database Yang Sudah Ada

Script root `package.json` yang terkait database:

- `npm run db:check`
  - Menjalankan `tsx backend/node/checkDatabaseConnection.ts`.
  - Script melakukan `select now()` untuk validasi koneksi PostgreSQL.
- `npm run db:seed`
  - Menjalankan `tsx backend/node/seedInitialWorkspace.ts`.
  - Script membuat atau memastikan user demo, workspace, membership owner, dan
    workspace configuration.
- `npm run db:backfill-workspaces`
  - Menjalankan `tsx backend/node/backfillUserWorkspaces.ts`.
  - Script membuat workspace default untuk user yang belum punya workspace.
- `npm run classify:financial-data`
  - Menjalankan `tsx backend/node/runSyncAndClassifyFinancialData.ts`.
  - Ini terkait sync dan klasifikasi data, bukan migration runner.

File di `backend/node` yang relevan:

- `db.ts`
- `checkDatabaseConnection.ts`
- `seedInitialWorkspace.ts`
- `backfillUserWorkspaces.ts`
- `repositories/workspaceRepository.ts`
- `syncAndClassifyFinancialData.ts`
- `runSyncAndClassifyFinancialData.ts`
- `monthlyAllocationRoute.ts`

File di `backend/scripts` saat review:

- `anomaly_detection.py`
- `data_processing.py`
- `generate_graph.py`
- `generate_pdf.py`
- `credentials.json`

Catatan keamanan: `credentials.json` ada di folder script. Isi file tidak
ditinjau atau disalin ke dokumen ini agar tidak memasukkan credential ke notes.

## 5. Gap Terhadap Target Week 2

- `schema_migrations`
  - Belum ada tabel `schema_migrations`.
  - Belum ada mekanisme pencatatan migration yang sudah dijalankan.
- `transactions`
  - Belum ada tabel PostgreSQL `transactions`.
  - Endpoint dashboard `/api/dashboard/transactions` masih mengambil data dari
    flow Google Sheets/service existing.
- `transaction_classifications`
  - Belum ada tabel untuk menyimpan hasil klasifikasi transaksi.
  - Flow AI classification masih berupa script dan output existing, belum write
    ke database.
- `classification_rules`
  - Belum ada tabel rules klasifikasi.
- `sync_jobs`
  - Belum ada tabel untuk tracking proses sync.
- Migration runner
  - Belum ada script runner migration resmi.
  - File SQL migration sudah ada, tetapi belum ada command seperti
    `db:migrate` yang membaca folder migration dan mengisi `schema_migrations`.
- `/api/health/db`
  - Belum ada endpoint database health check.
  - Endpoint yang ada baru `/api/health` dan hanya return `{"status": "ok"}`.
- `docs/DATABASE.md`
  - Belum ada dokumentasi database khusus.
  - Dokumentasi database saat ini tersebar di `README.md`,
    `docs/ENVIRONMENT.md`, dan migration SQL.

## Ringkasan

Repository sudah memiliki fondasi awal PostgreSQL untuk multi-tenant auth,
workspace, konfigurasi sumber Google Sheets, token user, connection pool Python,
connection pool Node, serta script check/seed/backfill. Gap utama Week 2 adalah
menjadikan migration dapat dijalankan secara resmi dan menambah schema inti
untuk transaksi, klasifikasi, rules, sync job tracking, database health check,
serta dokumentasi database khusus.
