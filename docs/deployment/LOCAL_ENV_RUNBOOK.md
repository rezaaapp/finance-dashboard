# Local Environment Runbook

Tanggal: 2026-06-27

## Kenapa Hanya local-dev dan local-prod

Fase pertama environment split Omon Dashboard hanya menargetkan dua environment lokal karena saat ini belum ada VPS, belum ada domain, dan staging belum dibutuhkan. Tujuannya adalah membuat fondasi yang jelas untuk menjalankan development lokal dan production simulation lokal secara terpisah tanpa mencampur database, port, API URL, CORS, temp upload storage, atau secret.

Environment yang aktif:

| Environment | Purpose | Database | Backend | Frontend |
| --- | --- | --- | --- | --- |
| `local-dev` | Development harian | PostgreSQL local | `http://127.0.0.1:8000` | `http://127.0.0.1:5173` |
| `local-prod` | Production simulation lokal | Supabase | `http://127.0.0.1:8001` | `http://127.0.0.1:5174` |

## File Env

Template yang boleh di-commit:

| Template | Copy lokal |
| --- | --- |
| `.env.local-dev.example` | `.env.local-dev` |
| `.env.local-prod.example` | `.env.local-prod` |
| `apps/web/.env.local-dev.example` | `apps/web/.env.local-dev` |
| `apps/web/.env.local-prod.example` | `apps/web/.env.local-prod` |

File lokal asli tidak boleh di-commit. `.gitignore` sudah meng-ignore `.env.*` dan mengizinkan hanya file `*.example`.

Backend akan mencoba memuat `.env.local-dev` secara default setelah `.env` dan `backend/.env`. Untuk memakai `local-prod`, set `APP_ENV=local-prod` atau `ENV_PROFILE=local-prod` sebelum backend start agar `.env.local-prod` ikut dimuat. Runner Phase 2 sudah mengatur ini otomatis lewat file `.bat`.

## Environment Identity

Backend sekarang mengenal tiga env identity:

| Env | local-dev | local-prod |
| --- | --- | --- |
| `APP_ENV` | `local-dev` | `local-prod` |
| `ENV_PROFILE` | `local-dev` | `local-prod` |
| `DB_TARGET` | `postgres-local` | `supabase` |
| `BACKEND_PORT` / `PORT` | `8000` | `8001` |

Guard dasar:

- `APP_ENV=local-dev` harus memakai `DB_TARGET=postgres-local`.
- `APP_ENV=local-prod` harus memakai `DB_TARGET=supabase`.
- Default backend port `local-dev` adalah `8000`.
- Default backend port `local-prod` adalah `8001`.

## Startup Summary Backend

Saat backend start, log akan menampilkan summary masked:

- `APP_ENV`
- `ENV_PROFILE`
- `DB_TARGET`
- backend port
- database host masked
- database name
- CORS origins
- frontend URL
- import temp directory

Summary tidak mencetak password, token, JWT secret, OAuth secret, atau connection string penuh.

## Upload Temp Storage

Upload temp storage dipisah dengan `IMPORT_TEMP_DIR`:

| Environment | Default value |
| --- | --- |
| `local-dev` | `backend/output/imports/temp/local-dev` |
| `local-prod` | `backend/output/imports/temp/local-prod` |

Ini mencegah dua backend lokal berbagi file upload sementara.

## Safety Rules

- Jangan commit `.env.local-dev`, `.env.local-prod`, `apps/web/.env.local-dev`, atau `apps/web/.env.local-prod`.
- Jangan commit credential JSON, token, private key, atau generated output.
- Jangan reset Supabase sebelum workflow reset Supabase punya safety guard dan confirmation phrase.
- Jangan seed Supabase tanpa script guarded dan approval eksplisit.
- Jangan menjalankan migration Supabase dari command umum yang tidak memvalidasi `APP_ENV` dan `DB_TARGET`.
- Pastikan frontend `local-dev` hanya mengarah ke backend `8000`.
- Pastikan frontend `local-prod` hanya mengarah ke backend `8001`.
- Pastikan Google OAuth redirect URI sesuai port backend environment yang sedang dipakai.

## Runner Scripts

Phase 2 menambahkan runner terpisah untuk setiap environment. Runner membaca file env target, memvalidasi identity/port/API URL, menampilkan banner aman tanpa secret, lalu menjalankan server.

| Script | Membuka |
| --- | --- |
| `scripts/start-local-dev-backend.bat` | Backend local-dev di `127.0.0.1:8000` |
| `scripts/start-local-dev-frontend.bat` | Frontend local-dev di `127.0.0.1:5173` |
| `scripts/start-local-prod-backend.bat` | Backend local-prod di `127.0.0.1:8001` |
| `scripts/start-local-prod-frontend.bat` | Frontend local-prod di `127.0.0.1:5174` |
| `scripts/start-local-dev.bat` | Backend dan frontend local-dev |
| `scripts/start-local-prod.bat` | Backend dan frontend local-prod |
| `scripts/start-all-local.bat` | Empat terminal: local-dev backend/frontend dan local-prod backend/frontend |

Helper reusable:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local-env-runner.ps1 -Target local-dev -Service backend -ValidateOnly
```

Gunakan `-UseExample` untuk validasi template tanpa membuat file env asli:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local-env-runner.ps1 -Target local-dev -Service backend -ValidateOnly -UseExample
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local-env-runner.ps1 -Target local-prod -Service frontend -ValidateOnly -UseExample
```

## Cara Menjalankan local-dev

1. Copy template backend dan frontend:

```powershell
Copy-Item .env.local-dev.example .env.local-dev
Copy-Item apps/web/.env.local-dev.example apps/web/.env.local-dev
```

2. Isi secret dan koneksi PostgreSQL local di `.env.local-dev`.
3. Jalankan dua service:

```bat
scripts\start-local-dev.bat
```

Atau jalankan terpisah:

```bat
scripts\start-local-dev-backend.bat
scripts\start-local-dev-frontend.bat
```

## Cara Menjalankan local-prod

1. Copy template backend dan frontend:

```powershell
Copy-Item .env.local-prod.example .env.local-prod
Copy-Item apps/web/.env.local-prod.example apps/web/.env.local-prod
```

2. Isi secret dan koneksi Supabase di `.env.local-prod`.
3. Jalankan dua service:

```bat
scripts\start-local-prod.bat
```

Atau jalankan terpisah:

```bat
scripts\start-local-prod-backend.bat
scripts\start-local-prod-frontend.bat
```

## Cara Menjalankan Keduanya Bersamaan

Setelah `.env.local-dev`, `.env.local-prod`, dan env frontend masing-masing tersedia:

```bat
scripts\start-all-local.bat
```

Script ini membuka empat terminal:

- local-dev backend
- local-dev frontend
- local-prod backend
- local-prod frontend

## Port Mapping

| Environment | Backend | Frontend | Expected API URL di frontend |
| --- | --- | --- | --- |
| `local-dev` | `http://127.0.0.1:8000` | `http://127.0.0.1:5173` | `http://127.0.0.1:8000` |
| `local-prod` | `http://127.0.0.1:8001` | `http://127.0.0.1:5174` | `http://127.0.0.1:8001` |

## Cara Memastikan Frontend Tidak Cross-Connect

- Banner frontend runner harus menampilkan `VITE_API_URL` dan `VITE_API_BASE_URL` sesuai target.
- Untuk local-dev, keduanya harus `http://127.0.0.1:8000`.
- Untuk local-prod, keduanya harus `http://127.0.0.1:8001`.
- Browser devtools Network tab harus menunjukkan request local-dev ke port `8000` dan local-prod ke port `8001`.
- Jika salah satu runner menolak start karena API URL tidak sesuai, perbaiki file env frontend target sebelum menjalankan ulang.

## Database Lifecycle Phase 3

Phase 3 menyediakan runner terpisah untuk setiap target. Semua runner memuat file env target, memvalidasi `APP_ENV`, `ENV_PROFILE`, `DB_TARGET`, host database, dan nama database sebelum membuka koneksi. Output hanya menampilkan host yang sudah di-mask dan tidak mencetak URL, password, token, atau secret.

| Operasi | local-dev | local-prod |
| --- | --- | --- |
| Migrate | `scripts\migrate-local-dev.bat` | `scripts\migrate-local-prod.bat` |
| Reset | `scripts\reset-local-dev-db.bat` | `scripts\reset-local-prod-supabase-db.bat` |
| Seed | `scripts\seed-local-dev.bat` | `scripts\seed-local-prod.bat` |
| Verify | `scripts\verify-local-dev-db.bat` | `scripts\verify-local-prod-db.bat` |

Urutan untuk membuat baseline fresh adalah reset, migrate, seed, lalu verify. Seed bersifat idempotent untuk owner dan workspace, tetapi tidak menghapus data bisnis yang sudah ada. Karena itu, nilai transaksi/import/draft/fingerprint/budget nol hanya dijamin pada database yang baru di-reset.

### Migrate local-dev

```bat
scripts\migrate-local-dev.bat
```

Runner hanya menerima loopback `localhost`, `127.0.0.1`, atau `::1` dengan database `finance_dashboard_local`.

### Migrate local-prod

```bat
scripts\migrate-local-prod.bat
```

Runner wajib melihat host Supabase dan meminta phrase persis:

```text
MIGRATE SUPABASE OMON
```

Migration memakai `DATABASE_MIGRATION_URL` bila tersedia. Fallback ke `DATABASE_URL` hanya dilakukan setelah URL lolos guard target.

### Reset local-dev

Hentikan backend port `8000`, lalu jalankan:

```bat
scripts\reset-local-dev-db.bat
```

Reset ditolak bila identity bukan `local-dev`, target bukan `postgres-local`, host bukan loopback, nama database bukan `finance_dashboard_local`, host mengandung `supabase`, atau backend masih aktif.

### Reset local-prod Supabase

```bat
scripts\reset-local-prod-supabase-db.bat
```

Runner menampilkan warning besar dan meminta phrase persis:

```text
RESET SUPABASE OMON
```

Operasi ini menghapus dan membuat ulang schema `public`; lanjutkan dengan migrate dan seed. Backup/dump sengaja di-skip karena Supabase saat ini adalah production simulation fresh tanpa user production asli. Keputusan ini harus ditinjau ulang sebelum ada data production nyata.

### Seed baseline

Pastikan env berikut terisi:

```text
SEED_USER_EMAIL
SEED_USER_NAME
SEED_WORKSPACE_NAME
```

Kemudian jalankan runner target. Seed membuat atau memperbarui satu user owner dan workspace. Pada baseline fresh, transaksi, import jobs, drafts, fingerprint registry, dan budgets tetap nol.

```bat
scripts\seed-local-dev.bat
scripts\seed-local-prod.bat
```

### Verify baseline

```bat
scripts\verify-local-dev-db.bat
scripts\verify-local-prod-db.bat
```

Summary mencakup identity, target, host masked, nama database, jumlah/latest migration, user, workspace, transaction, import job, draft, fingerprint registry, dan budget.

### Safety checklist Supabase

- Pastikan terminal dan env file adalah `local-prod`.
- Pastikan `APP_ENV=local-prod`, `ENV_PROFILE=local-prod`, dan `DB_TARGET=supabase`.
- Pastikan banner menunjukkan host Supabase masked dan database yang diharapkan.
- Pastikan tidak ada user production asli; backup memang di-skip hanya untuk baseline saat ini.
- Tutup backend local-prod sebelum reset.
- Ketik confirmation phrase secara manual dan hentikan bila ada nilai yang tidak sesuai.
- Jangan memakai runner local-dev untuk URL Supabase atau sebaliknya.

### Dry-run guard

Mode berikut hanya memvalidasi template dan berhenti sebelum koneksi database:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/database-lifecycle-runner.ps1 -Target local-dev -Action reset -ValidateOnly -UseExample
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/database-lifecycle-runner.ps1 -Target local-prod -Action reset -Confirm "RESET SUPABASE OMON" -ValidateOnly -UseExample
```

### Troubleshooting

- `Required env file is missing`: copy file `.example` target ke file lokal yang di-ignore.
- `APP_ENV`, `ENV_PROFILE`, atau `DB_TARGET must be`: perbaiki identity pada env target.
- `database host must be loopback`: local-dev tidak menunjuk PostgreSQL lokal.
- `database host must be Supabase`: local-prod menunjuk host yang salah.
- `Confirmation phrase must be exactly`: ulangi dan ketik phrase tanpa perubahan.
- `database error. Connection details hidden`: cek konektivitas, credential, SSL, dan akses database pada env lokal; runner sengaja menyembunyikan detail koneksi.

## Belum Dikerjakan Setelah Phase 3

- Concurrent run full test untuk dua environment sekaligus.
- UI environment badge.
- Perubahan Google OAuth flow.
- Perubahan business logic import Blu PDF.
- Perubahan dashboard analytics logic.

## Cek Cepat Manual

Sebelum menjalankan backend, pastikan env aktif sesuai target:

```powershell
APP_ENV=local-dev
ENV_PROFILE=local-dev
DB_TARGET=postgres-local
BACKEND_PORT=8000
```

atau:

```powershell
APP_ENV=local-prod
ENV_PROFILE=local-prod
DB_TARGET=supabase
BACKEND_PORT=8001
```

Jika summary startup mencetak target database atau frontend URL yang tidak sesuai, hentikan proses dan perbaiki env sebelum melanjutkan.

## Catatan Operasional

Script Phase 3 sudah tersedia, tetapi pembuatan script bukan izin untuk menjalankan reset, migration, atau seed Supabase. Operasi Supabase tetap harus diminta secara eksplisit dan confirmation phrase tidak boleh dilewati.
