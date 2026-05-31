# Database

Finance Dashboard memakai Supabase PostgreSQL sebagai database provider saat
ini. Nama environment variable sengaja dibuat provider-neutral agar aplikasi
tetap bisa berjalan di PostgreSQL compatible provider lain jika diperlukan.

## Environment Variables

Konfigurasi database utama:

- `DATABASE_URL`: runtime connection string untuk FastAPI dan helper database.
- `DATABASE_MIGRATION_URL`: optional direct/session connection untuk migration
  runner jika provider membutuhkan URL berbeda.
- `DATABASE_SSL`: aktifkan SSL. Gunakan `true` untuk hosted Supabase.
- `DATABASE_SSL_REJECT_UNAUTHORIZED`: kontrol verifikasi sertifikat SSL.
  Gunakan sesuai mode SSL yang dipakai.
- `DATABASE_POOL_MAX`: maksimum connection pool runtime.
- `DATABASE_IDLE_TIMEOUT_MS`: idle timeout untuk helper/script Node.
- `DATABASE_CONNECTION_TIMEOUT_MS`: connection timeout untuk helper/script Node.

Jangan commit nilai asli dari connection string, password, token, atau credential
ke repository.

## Role In Target Architecture

Database menjadi fondasi resmi untuk:

- `users` dan `workspaces`
- Google OAuth connections
- Google Sheet sources per workspace
- synced transactions
- AI classification results
- classification rules
- sync job status

Week 2 hanya menyiapkan fondasi database. Week 2 belum melakukan sync transaksi
Google Sheets ke PostgreSQL. Google Sheet sync masuk Week 4, dan AI
classification write ke database masuk Week 5.

## Supabase Setup

Langkah setup dasar:

1. Buat Supabase project.
2. Copy PostgreSQL connection string dari Supabase.
3. Set `DATABASE_URL` di `backend/.env`.
4. Set `DATABASE_SSL=true` untuk hosted Supabase.
5. Set `DATABASE_SSL_REJECT_UNAUTHORIZED` sesuai mode SSL yang digunakan.
6. Isi `DATABASE_MIGRATION_URL` hanya jika perlu direct/session connection
   terpisah untuk migration.

Contoh placeholder aman:

```env
DATABASE_URL=postgresql://postgres:replace_with_password@localhost:5432/finance_dashboard
DATABASE_MIGRATION_URL=
DATABASE_SSL=true
DATABASE_SSL_REJECT_UNAUTHORIZED=true
DATABASE_POOL_MAX=10
DATABASE_IDLE_TIMEOUT_MS=30000
DATABASE_CONNECTION_TIMEOUT_MS=10000
```

## Migrations

Jalankan migration dari root repository:

```powershell
npm run db:migrate
```

Atau jalankan direct Python command:

```powershell
.\backend\venv\Scripts\python.exe backend\scripts\run_migrations.py
```

Runner membaca file SQL dari:

```text
backend/db/migrations
```

Migration diurutkan berdasarkan nama file. Migration yang sudah tercatat di
`schema_migrations` akan dilewati saat command dijalankan ulang.

## Health Check

Endpoint database health check:

```text
GET /api/health/db
```

Response sukses:

```json
{
  "status": "ok",
  "database": "connected"
}
```

Response gagal:

```json
{
  "status": "error",
  "database": "unavailable",
  "message": "database connection failed"
}
```

Response gagal sengaja tidak mengekspos `DATABASE_URL`, username, password,
host Supabase, token, atau credential lain.

## Troubleshooting

### `DATABASE_URL` Missing

Pastikan `backend/.env` ada dan berisi `DATABASE_URL`. Untuk deployment Render,
set nilai ini sebagai provider environment variable, bukan di file repo.

### Connection Refused

Cek apakah host database dapat diakses dari environment backend. Untuk lokal,
pastikan PostgreSQL berjalan. Untuk hosted Supabase, cek allowlist/network mode
dan connection string yang dipakai.

### SSL Required

Hosted Supabase umumnya membutuhkan SSL. Set:

```env
DATABASE_SSL=true
```

Jika sertifikat tidak bisa diverifikasi karena mode lokal/proxy tertentu, cek
apakah `DATABASE_SSL_REJECT_UNAUTHORIZED=false` memang diperlukan. Jangan
menonaktifkan verifikasi tanpa alasan operasional yang jelas.

### Migration Already Applied

Ini normal. Runner akan skip migration yang versinya sudah ada di
`schema_migrations`.

### Permission Denied

Pastikan user database punya permission untuk membuat extension, table, index,
trigger, dan menjalankan migration. Jika runtime user dibatasi, gunakan
`DATABASE_MIGRATION_URL` dengan connection yang punya permission migration.

### `psycopg` Missing

Install dependency backend:

```powershell
cd backend
.\venv\Scripts\python.exe -m pip install -r requirements.txt
cd ..
```

## Security

- Jangan commit `DATABASE_URL` asli.
- Jangan commit Supabase password.
- Jangan commit credential Google/service account.
- Jangan commit file `.env`.
- Gunakan environment variables di Render untuk secret production.
- Rotate secret jika pernah ter-commit atau muncul di log publik.

## Week 2 Definition Of Done

- Settings DB tersedia.
- Connection helper tersedia.
- Migration `004_add_ai_sync_database_foundation.sql` tersedia.
- Migration runner tersedia.
- `/api/health/db` tersedia.
- Dokumentasi database tersedia.
