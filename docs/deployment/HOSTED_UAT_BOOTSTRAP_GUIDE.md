# Omon Dashboard — Hosted UAT Bootstrap Guide

| Field | Value |
|---|---|
| **Project** | Omon Dashboard |
| **Document** | Hosted UAT Bootstrap Guide |
| **Current Release** | v0.9.8 |
| **Status** | Official Deployment Runbook |
| **Owner** | Project Team |

> Dokumen permanen ini adalah source of truth operasional untuk bootstrap, deployment, verifikasi, dan onboarding Hosted UAT. Jangan menaruh credential asli, access token, connection string, atau Spreadsheet ID di dokumen, issue, log, maupun repository.

## Table of Contents

1. [Introduction](#1-introduction)
2. [Environment Architecture](#2-environment-architecture)
3. [Deployment Philosophy](#3-deployment-philosophy)
4. [Hosted UAT Architecture](#4-hosted-uat-architecture)
5. [Supabase UAT Bootstrap](#5-supabase-uat-bootstrap)
6. [Runtime Environment](#6-runtime-environment)
7. [Migration Procedure](#7-migration-procedure)
8. [Migration Verification](#8-migration-verification)
9. [Replit Setup](#9-replit-setup)
10. [Replit Secrets](#10-replit-secrets)
11. [Google OAuth Setup](#11-google-oauth-setup)
12. [First Hosted Deployment](#12-first-hosted-deployment)
13. [Provision Tester](#13-provision-tester)
14. [Tester Onboarding](#14-tester-onboarding)
15. [Smoke Test Checklist](#15-smoke-test-checklist)
16. [Two User Isolation Test](#16-two-user-isolation-test)
17. [Troubleshooting](#17-troubleshooting)
18. [Security Checklist](#18-security-checklist)
19. [GO / NO-GO Checklist](#19-go--no-go-checklist)
20. [Future Improvements](#20-future-improvements)

## 1. Introduction

Hosted UAT adalah environment permanen untuk User Acceptance Testing oleh tester melalui URL yang dapat diakses dari internet. Tujuannya adalah memvalidasi alur nyata—authentication, Google OAuth, Google Sheets sync, dashboard, budgeting, search, dan PDF import—sebelum perubahan dipertimbangkan untuk Production.

- **Local Development** berjalan di workstation developer, memakai PostgreSQL lokal, dan ditujukan untuk implementasi serta automated test yang cepat.
- **Hosted UAT** berjalan di Replit, memakai dedicated Supabase UAT project, dan ditujukan untuk acceptance test dengan data sintetis/disposable.
- **Production** kelak memakai runtime, database, OAuth client, secrets, monitoring, dan data policy Production yang sepenuhnya terpisah.

Dokumen ini menjelaskan cara membangun Hosted UAT dari nol, melakukan migration secara aman, deploy ke Replit, menyiapkan OAuth dan tester, lalu menentukan status GO atau NO-GO tanpa bergantung pada riwayat chat.

## 2. Environment Architecture

```text
Developer workstation                 Hosted platform                    Future platform
┌─────────────────────┐              ┌──────────────────────────┐       ┌─────────────────────┐
│ Local app runtime   │              │ Replit Hosted UAT        │       │ Production runtime  │
│          │          │              │          │               │       │          │          │
│ Local PostgreSQL    │              │ Dedicated Supabase UAT   │       │ Production database │
└─────────────────────┘              └──────────────────────────┘       └─────────────────────┘
```

| Environment | Runtime | Database | Purpose |
|---|---|---|---|
| Local Dev | Developer workstation | Local PostgreSQL | Development, debugging, automated test |
| Hosted UAT | Replit | Dedicated Supabase UAT | Persistent acceptance testing oleh tester |
| Production | Dedicated Production runtime (future) | Dedicated Production database (future) | Live service setelah seluruh release gate lulus |

> **Boundary wajib:** Hosted UAT bukan Production, tidak boleh berisi data pribadi/keuangan asli, dan harus memakai database yang terpisah secara fisik/logis dari Production.

## 3. Deployment Philosophy

- [ ] Semua perubahan schema dibuat sebagai file SQL versioned di `backend/db/migrations/`.
- [ ] Schema tidak diedit manual melalui Supabase SQL Editor atau dashboard sebagai shortcut.
- [ ] Hosted UAT tidak pernah diarahkan ke Production database.
- [ ] Setiap tester memakai copy Spreadsheet khusus UAT, bukan dokumen pribadi atau source asli.
- [ ] Secrets hanya disimpan di secret manager platform atau process environment; tidak di-commit.
- [ ] Hosted UAT diperlakukan sebagai environment permanen: konfigurasi stabil, perubahan dapat diaudit, dan migration idempotent.
- [ ] Migration dijalankan sebagai langkah operator terpisah, bukan otomatis setiap startup.
- [ ] Deployment harus repeatable dari repository dan runbook ini.

## 4. Hosted UAT Architecture

```text
Developer
    ↓ push reviewed change
GitHub
    ↓ import / deploy branch
Replit
    ↓ runtime PostgreSQL connection (SSL)
Supabase UAT
    ↑ encrypted OAuth tokens and workspace data
Google OAuth
    ↓ grants scoped access
Google Sheet (disposable tester copy)
    ↕ sync/test connection
Tester
```

GitHub adalah source code source of truth. Replit membangun frontend dan menjalankan FastAPI pada port yang diinjeksi platform. Backend berkomunikasi dengan dedicated Supabase UAT dan Google OAuth; tester hanya berinteraksi melalui Hosted UAT URL dan Spreadsheet copy.

## 5. Supabase UAT Bootstrap

### 5.1 Create Project

1. Masuk ke Supabase organization milik project team.
2. Pilih **New project**.
3. Gunakan nama yang eksplisit, misalnya `omon-dashboard-uat`.
4. Pilih organization dan billing plan yang telah disetujui.
5. Pilih region terdekat dengan Replit runtime dan mayoritas tester. Region tidak mudah diubah; catat keputusan tersebut di deployment record.
6. Generate database password yang panjang dan unik. Simpan di password manager; jangan menaruhnya di repository atau chat.
7. Tunggu provisioning selesai, lalu catat **Project Reference** (`<SUPABASE_PROJECT_REF>`) dari dashboard URL/Project Settings.

### 5.2 Connection Methods

Ambil connection string dari tombol **Connect** di Supabase Dashboard. Jangan menyusun host atau username berdasarkan ingatan.

| Connection | Contoh placeholder | Use case |
|---|---|---|
| Direct | `postgresql://postgres:<DB_PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres` | Migration, backup, native Postgres tools, persistent host dengan IPv6 |
| Shared Pooler — Session | `postgresql://postgres.<PROJECT_REF>:<DB_PASSWORD>@aws-<REGION>.pooler.supabase.com:5432/postgres` | Migration atau persistent runtime dari jaringan IPv4-only |
| Shared Pooler — Transaction | `postgresql://postgres.<PROJECT_REF>:<DB_PASSWORD>@aws-<REGION>.pooler.supabase.com:6543/postgres` | Runtime transient/serverless; hindari untuk migration dan prepared statements |

**Direct Connection** adalah pilihan utama migration karena memiliki session Postgres native. Gunakan **Session Pooler** jika mesin operator tidak dapat mencapai endpoint Direct. Windows/network ISP sering hanya mempunyai jalur IPv4 yang berfungsi, sedangkan Direct endpoint Supabase umumnya IPv6 kecuali project memakai IPv4 add-on; Session Pooler menyediakan endpoint IPv4.

Untuk Replit runtime yang persistent, gunakan Direct bila IPv6 tersedia dan teruji; gunakan Session Pooler sebagai fallback IPv4. Transaction Pooler cocok untuk traffic transient, tetapi port `6543` dan keterbatasan prepared statements harus diuji dengan driver aplikasi.

- [ ] Project name dan Project Reference telah diverifikasi dua orang/dua sumber.
- [ ] Region telah dicatat.
- [ ] Database password tersimpan di password manager.
- [ ] Runtime URL dan migration URL menunjuk project reference UAT yang sama.
- [ ] SSL diwajibkan.

## 6. Runtime Environment

Process environment (termasuk Replit Secrets dan PowerShell operator) memiliki precedence atas dotenv files. Jangan membuat `.env.uat` berisi nilai asli di repository.

### 6.1 Core and Database

| Variable | Required | Hosted UAT value / purpose |
|---|---:|---|
| `APP_ENV` | Yes | `uat`; mengaktifkan validation dan UAT provisioning gate |
| `ENV_PROFILE` | Yes | `uat`; memilih environment profile |
| `DB_TARGET` | Yes | `supabase`; UAT akan menolak target lain |
| `PORT` | Platform | Diinjeksi Replit; jangan hard-code `BACKEND_PORT` |
| `DATABASE_URL` | Conditional | Primary runtime URL bila tidak dikelola/reserved platform |
| `SUPABASE_DATABASE_URL` | Yes* | Runtime fallback alias; gunakan bila `DATABASE_URL` reserved |
| `DATABASE_MIGRATION_URL` | Optional | Highest-precedence migration URL |
| `SUPABASE_MIGRATION_DATABASE_URL` | Recommended | Direct atau Session Pooler URL khusus migration |
| `DATABASE_SSL` | Yes | `true` |
| `DATABASE_SSL_REJECT_UNAUTHORIZED` | Yes | `true`; downgrade sementara hanya untuk diagnosis terkontrol |
| `DATABASE_POOL_MAX` | No | `10` default; sesuaikan terhadap connection limit |
| `DATABASE_IDLE_TIMEOUT_MS` | No | `30000` default |
| `DATABASE_CONNECTION_TIMEOUT_MS` | No | `10000` default |

`*` Salah satu `DATABASE_URL` atau `SUPABASE_DATABASE_URL` wajib tersedia. Precedence runtime adalah `DATABASE_URL` → `SUPABASE_DATABASE_URL`. Precedence migration adalah `DATABASE_MIGRATION_URL` → `SUPABASE_MIGRATION_DATABASE_URL` → `DATABASE_URL` → `SUPABASE_DATABASE_URL`.

### 6.2 Authentication, Security, and OAuth

| Variable | Required | Placeholder / purpose |
|---|---:|---|
| `DASHBOARD_USERNAME` | Yes | `<UAT_SUPER_ADMIN_EMAIL>` |
| `DASHBOARD_PASSWORD` | Yes | `<STRONG_UAT_ADMIN_PASSWORD>` |
| `DASHBOARD_AUTH_TOKEN` | Yes | `<LONG_RANDOM_AUTH_TOKEN>`; legacy/internal authentication fallback |
| `JWT_SECRET` | Yes | `<LONG_RANDOM_JWT_SECRET>`; independent secret |
| `JWT_EXPIRES_IN_MINUTES` | No | `10080` default; review against UAT session policy |
| `TOKEN_ENCRYPTION_KEY` | Yes | `<FERNET_KEY>` generated once and kept stable |
| `TOKEN_ENCRYPTION_SECRET` | Yes | `<LONG_RANDOM_TOKEN_SECRET>` independent from JWT secret |
| `SUPER_ADMIN_EMAILS` | Yes | `<UAT_SUPER_ADMIN_EMAIL>`; comma-separated when multiple |
| `GOOGLE_AUTH_MODE` | Yes | `oauth` |
| `GOOGLE_OAUTH_CLIENT_ID` | Yes | `<GOOGLE_CLIENT_ID>.apps.googleusercontent.com` |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Yes | `<GOOGLE_CLIENT_SECRET>` |
| `GOOGLE_OAUTH_REDIRECT_URI` | Yes | `https://<REPLIT_HOST>/api/google/oauth/callback` |
| `GOOGLE_LOGIN_REDIRECT_URI` | Yes | `https://<REPLIT_HOST>/auth/google/callback` |
| `GOOGLE_OAUTH_SCOPES` | Yes | `openid email profile https://www.googleapis.com/auth/spreadsheets` or approved least-privilege variant |
| `FRONTEND_URL` | Yes | `https://<REPLIT_HOST>` |
| `FRONTEND_AUTH_REDIRECT_URL` | Yes | `https://<REPLIT_HOST>/auth/google/callback` |
| `CORS_ALLOWED_ORIGINS` | Yes | `https://<REPLIT_HOST>`; exact origin, no trailing path |

> `GOOGLE_CLIENT_ID` dan `GOOGLE_CLIENT_SECRET` adalah istilah umum; variable yang benar-benar dibaca project adalah `GOOGLE_OAUTH_CLIENT_ID` dan `GOOGLE_OAUTH_CLIENT_SECRET`.

### 6.3 Application and Frontend

| Variable | Required | Hosted UAT value / purpose |
|---|---:|---|
| `VITE_API_MODE` | Yes (build) | `same-origin`; harus tersedia saat frontend build |
| `VITE_API_URL` / `VITE_API_BASE_URL` | No | Jangan set untuk same-origin kecuali ada deployment split yang disengaja |
| `VITE_GUEST_MODE_MULTIPLIER` | No | UI guest/demo multiplier, default sesuai app |
| `USE_MOCK_DATA` | Yes | `false` |
| `GOOGLE_SHEET_ID` | No | `<DISPOSABLE_SHEET_ID>` hanya jika default legacy diperlukan |
| `MAX_GOOGLE_SHEET_SOURCES` | No | `5` default |
| `GOOGLE_SHEET_REGISTRY_JSON` | No | `{"2026":{"id":"<SHEET_ID>","name":"UAT 2026"}}` |
| `IMPORT_TEMP_DIR` | No | Default profile-specific path; pastikan runtime dapat menulis |
| `AI_CLASSIFICATION_ENABLED` | No | `false` untuk rule-based default |
| `AI_PROVIDER` | No | `rule_based` |
| `AI_MODEL` | No | `none` |
| `GEMINI_API_KEY` | No | Hanya jika AI flow secara eksplisit diaktifkan |

Insight thresholds dan AI tuning lain tersedia di `backend/.env.example`; pertahankan default kecuali test plan meminta nilai tertentu. Jangan simpan service-account JSON pada Hosted UAT OAuth flow.

## 7. Migration Procedure

Migration harus dijalankan dari clean checkout pada branch/tag yang sama dengan deployment. Stop deployment promotion bila target tidak dapat diverifikasi.

```powershell
# Jalankan dari repository root. Nilai hanya berlaku untuk shell aktif.
$env:APP_ENV = "uat"
$env:ENV_PROFILE = "uat"
$env:DB_TARGET = "supabase"
$env:DATABASE_SSL = "true"
$env:DATABASE_SSL_REJECT_UNAUTHORIZED = "true"
$env:SUPABASE_DATABASE_URL = "postgresql://postgres.<PROJECT_REF>:<DB_PASSWORD>@aws-<REGION>.pooler.supabase.com:5432/postgres"
$env:SUPABASE_MIGRATION_DATABASE_URL = "postgresql://postgres:<DB_PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres"

backend\venv\Scripts\python.exe backend\scripts\run_migrations.py
if ($LASTEXITCODE -ne 0) { throw "Hosted UAT migration failed" }
```

Jika Direct Connection gagal karena IPv6, ganti hanya `SUPABASE_MIGRATION_DATABASE_URL` dengan Session Pooler URL dari dashboard. Jangan memakai URL dari project lain dan jangan menampilkan nilainya di screenshot/log.

Runner membuat `schema_migrations` bila belum ada, mengurutkan semua file `.sql` berdasarkan filename, melewati migration yang sudah tercatat, dan menjalankan setiap migration dalam transaction. **Jangan** menambahkan migration command ke Replit startup.

- [ ] Branch/tag deployment benar.
- [ ] `<PROJECT_REF>` pada runtime dan migration URL adalah UAT project.
- [ ] Runner melaporkan `Found 25 migration file(s).` untuk release v0.9.8.
- [ ] Exit code `0`.
- [ ] Tidak ada credential tercetak.

## 8. Migration Verification

Release v0.9.8 memiliki **25 migration files**. Angka ini adalah release baseline; pada release berikutnya, expected count harus dibandingkan dengan jumlah file aktual di repository.

Jalankan melalui Supabase SQL Editor pada **UAT project** atau `psql` dengan migration URL:

```sql
-- 1. Total dan uniqueness migration
select
  count(*) as migration_count,
  count(distinct version) as distinct_migration_count
from public.schema_migrations;

-- Expected untuk v0.9.8:
-- migration_count = 25
-- distinct_migration_count = 25

-- 2. Urutan migration yang tercatat
select version, applied_at
from public.schema_migrations
order by version;

-- Expected: setiap filename di backend/db/migrations muncul tepat sekali.

-- 3. Latest required credential migration
select exists (
  select 1 from public.schema_migrations
  where version = '022_add_user_password_credentials.sql'
) as credential_migration_applied;

-- Expected: true

-- 4. Credential table dan update trigger
select to_regclass('public.user_password_credentials') as credential_table;

select trigger_name
from information_schema.triggers
where event_object_schema = 'public'
  and event_object_table = 'user_password_credentials'
  and trigger_name = 'set_user_password_credentials_updated_at';

-- Expected: credential_table = user_password_credentials; satu trigger ditemukan.

-- 5. Pastikan password yang tersimpan berupa hash, tanpa menampilkan nilainya
select count(*) as credential_rows,
       count(*) filter (where password_hash is null or password_hash = '') as invalid_hash_rows
from public.user_password_credentials;

-- Expected: invalid_hash_rows = 0. credential_rows boleh 0 sebelum provisioning.
```

Verifikasi juga endpoint ter-sanitasi setelah runtime aktif:

```powershell
Invoke-RestMethod "https://<REPLIT_HOST>/api/system/info"
```

Expected: `app_env=uat`, `env_profile=uat`, `db_target=supabase`, `migration_table_found=true`, `migration_count=25`, dan `latest_migration=022_add_user_password_credentials.sql`.

## 9. Replit Setup

1. Buat Repl/App baru melalui **Import from GitHub** dan pilih repository Omon Dashboard.
2. Pilih branch release/UAT yang disetujui; jangan deploy branch developer acak.
3. Pastikan runtime menyediakan Node.js dan Python yang kompatibel dengan lockfile/requirements project.
4. Gunakan [`.replit.example`](../../.replit.example) sebagai referensi. Konfigurasi saat ini:

   ```toml
   run = "npm run build:replit && npm run start:replit"

   [deployment]
   run = ["sh", "-c", "npm run build:replit && npm run start:replit"]
   ```

5. Replit menginjeksi `PORT`; backend bind ke `0.0.0.0` dan port tersebut. Jangan set `BACKEND_PORT` untuk Hosted UAT.
6. Set `VITE_API_MODE=same-origin` **sebelum build** agar browser memanggil API pada host yang sama.
7. Install dependencies sesuai project workflow, lalu build dan deploy.
8. Jangan menjalankan migration otomatis dalam `run` atau startup lifecycle. Migration adalah release gate manual pada Bagian 7.

## 10. Replit Secrets

Masukkan nilai melalui Replit Secrets, bukan file committed. Daftar berikut adalah baseline Hosted UAT.

### Application

```dotenv
APP_ENV=uat
ENV_PROFILE=uat
DB_TARGET=supabase
DASHBOARD_USERNAME=<UAT_SUPER_ADMIN_EMAIL>
DASHBOARD_PASSWORD=<STRONG_UAT_ADMIN_PASSWORD>
DASHBOARD_AUTH_TOKEN=<LONG_RANDOM_AUTH_TOKEN>
SUPER_ADMIN_EMAILS=<UAT_SUPER_ADMIN_EMAIL>
USE_MOCK_DATA=false
```

### Database

```dotenv
SUPABASE_DATABASE_URL=<SUPABASE_UAT_RUNTIME_CONNECTION_URL>
SUPABASE_MIGRATION_DATABASE_URL=<SUPABASE_UAT_DIRECT_OR_SESSION_CONNECTION_URL>
DATABASE_SSL=true
DATABASE_SSL_REJECT_UNAUTHORIZED=true
DATABASE_POOL_MAX=10
DATABASE_IDLE_TIMEOUT_MS=30000
DATABASE_CONNECTION_TIMEOUT_MS=10000
```

### Security

```dotenv
JWT_SECRET=<LONG_RANDOM_JWT_SECRET>
JWT_EXPIRES_IN_MINUTES=10080
TOKEN_ENCRYPTION_KEY=<STABLE_FERNET_KEY>
TOKEN_ENCRYPTION_SECRET=<LONG_RANDOM_TOKEN_ENCRYPTION_SECRET>
```

### OAuth

```dotenv
GOOGLE_AUTH_MODE=oauth
GOOGLE_OAUTH_CLIENT_ID=<GOOGLE_OAUTH_CLIENT_ID>.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=<GOOGLE_OAUTH_CLIENT_SECRET>
GOOGLE_OAUTH_REDIRECT_URI=https://<REPLIT_HOST>/api/google/oauth/callback
GOOGLE_LOGIN_REDIRECT_URI=https://<REPLIT_HOST>/auth/google/callback
GOOGLE_OAUTH_SCOPES=openid email profile https://www.googleapis.com/auth/spreadsheets
FRONTEND_URL=https://<REPLIT_HOST>
FRONTEND_AUTH_REDIRECT_URL=https://<REPLIT_HOST>/auth/google/callback
CORS_ALLOWED_ORIGINS=https://<REPLIT_HOST>
```

### Frontend (must exist at build time)

```dotenv
VITE_API_MODE=same-origin
```

`PORT` tidak dimasukkan karena dikelola Replit. Jangan menaruh server secrets pada variable `VITE_*`, karena variable tersebut dapat masuk ke browser bundle.

## 11. Google OAuth Setup

1. Buat/pilih Google Cloud project khusus Omon Dashboard UAT.
2. Enable Google Sheets API.
3. Konfigurasi OAuth consent screen. Gunakan **Testing mode** selama Hosted UAT belum dipublikasikan.
4. Tambahkan seluruh tester dan operator yang diizinkan sebagai **Test users**. Email harus sama dengan Google account yang dipakai ketika consent.
5. Buat **OAuth Client ID → Web application**.
6. Tambahkan Authorized JavaScript Origin:

   ```text
   https://<REPLIT_HOST>
   ```

7. Tambahkan Authorized Redirect URI secara exact:

   ```text
   https://<REPLIT_HOST>/api/google/oauth/callback
   https://<REPLIT_HOST>/auth/google/callback
   ```

8. Salin Client ID dan Client Secret ke Replit Secrets.
9. Gunakan scope yang disetujui. Project default mendukung identity scopes dan Google Sheets; bila write-back diuji, `https://www.googleapis.com/auth/spreadsheets` diperlukan. Jika seluruh skenario benar-benar read-only, evaluasi `spreadsheets.readonly` sebagai least privilege.
10. Deploy ulang setelah perubahan build-time/runtime secrets, lalu uji consent flow dengan tester account.

- [ ] Origin hanya scheme + host, tanpa path/trailing slash yang tidak perlu.
- [ ] Redirect URI cocok karakter demi karakter dengan secret aplikasi.
- [ ] Tester email terdaftar pada Testing mode.
- [ ] Spreadsheet yang dipakai adalah disposable copy dan dimiliki/dibagikan kepada tester tersebut.

## 12. First Hosted Deployment

Ikuti urutan ini setelah deployment pertama:

1. Buka `https://<REPLIT_HOST>/api/health`.
   - Expected: HTTP `200`, `{"status":"ok"}`.
2. Buka `https://<REPLIT_HOST>/api/health/db`.
   - Expected: HTTP `200`, database `connected`.
3. Buka `https://<REPLIT_HOST>/api/system/info`.
   - Expected: environment UAT, target Supabase, migration count sesuai release, host tersamarkan.
4. Periksa Replit logs untuk startup environment summary yang tersanitasi; pastikan tidak ada URL/password/token.
5. Login menggunakan Super Admin UAT.
6. Verifikasi menu/endpoint admin tersedia dan role Super Admin dikenali.
7. Jangan melanjutkan provisioning bila health, database, atau migration status gagal.

## 13. Provision Tester

Provisioning hanya diizinkan pada environment non-Production yang didukung, termasuk `uat`, dan endpoint memerlukan Super Admin bearer token.

1. Tentukan email sintetis/non-pribadi, nama tester, password unik sementara, role, dan workspace name.
2. Login sebagai Super Admin dan ambil access token dari response/session secara aman.
3. Panggil endpoint berikut (jangan menyimpan token/password dalam shell history atau screenshot):

   ```http
   POST /api/admin/users/provision-test-user
   Authorization: Bearer <SUPER_ADMIN_ACCESS_TOKEN>
   Content-Type: application/json

   {
     "email": "tester-a@example.test",
     "name": "Tester A",
     "role": "owner",
     "password": "<UNIQUE_TEMPORARY_PASSWORD>",
     "workspace_name": "UAT Workspace A"
   }
   ```

4. Expected: HTTP `201`, `created=true`, serta `user_id` dan `workspace_id` baru.
5. Kirim URL, email, dan password melalui channel aman yang disetujui. Jangan menyalin database credential, Super Admin token, atau Google Client Secret.
6. Minta tester mengonfirmasi login. Rotate password/credential bila channel pengiriman diragukan.

Provision tester kedua dengan email dan workspace berbeda untuk isolation test. Password disimpan sebagai one-way hash di `user_password_credentials`; operator tidak boleh membaca hash sebagai metode pemulihan password.

## 14. Tester Onboarding

Tester menerima tiga hal melalui channel aman:

- Hosted UAT URL: `https://<REPLIT_HOST>`
- Tester email: `<TESTER_EMAIL>`
- Temporary password: `<TEMPORARY_PASSWORD>`

Prosedur tester:

1. Buka Hosted UAT URL dan login dengan email/password yang diberikan.
2. Pastikan nama workspace milik tester tampil dengan benar.
3. Pilih **Connect Google**.
4. Login dengan Google account yang sudah ditambahkan sebagai OAuth Test user dan setujui scope.
5. Buat copy Spreadsheet template UAT; hapus/anonimkan seluruh data pribadi.
6. Pilih **Tambah Spreadsheet / Add Spreadsheet** dan masukkan URL/ID copy tersebut.
7. Pilih tab/worksheet yang benar.
8. Jalankan **Test Connection** dan pastikan berhasil.
9. Pilih **Save Source**.
10. Pilih **Sync Now** dan tunggu status sukses.
11. Buka Dashboard dan cocokkan sample totals/transactions dengan Spreadsheet copy.
12. Catat issue beserta timestamp, tester, workspace, browser, langkah reproduksi, dan screenshot yang tidak mengandung secrets/data pribadi.

## 15. Smoke Test Checklist

### Authentication and OAuth

- [ ] Super Admin login berhasil.
- [ ] Tester password login berhasil.
- [ ] Invalid password ditolak tanpa membocorkan detail.
- [ ] Google OAuth consent dan callback berhasil.
- [ ] Refresh/relogin mempertahankan koneksi yang diharapkan.

### Spreadsheet and Sync

- [ ] Tambah Spreadsheet copy berhasil.
- [ ] Test Connection berhasil pada tab yang benar.
- [ ] Save Source berhasil dan tetap ada setelah reload.
- [ ] Sync Now selesai tanpa error.
- [ ] Duplicate/repeated sync tidak menggandakan transaksi secara salah.
- [ ] Dashboard totals, charts, dan transaction list sesuai sample data.

### Product Flows

- [ ] Blu PDF Smart Import menerima PDF UAT yang valid.
- [ ] Import review, approve/reject, history, dan duplicate handling berfungsi.
- [ ] Budget create/edit/save/reload/reset period berfungsi.
- [ ] Search menemukan transaksi yang diharapkan.
- [ ] Workspace yang aktif dan role user tampil benar.
- [ ] Reset Synced Data hanya menghapus data hasil sync source terpilih.
- [ ] Reset Synced Data tidak mengubah Google Sheet.
- [ ] Error states dan validation copy dapat dipahami tester.

### Operational

- [ ] `/api/health` dan `/api/health/db` HTTP `200`.
- [ ] `/api/system/info` menunjukkan UAT/Supabase dan migration lengkap.
- [ ] Replit logs tidak membocorkan credential/token.
- [ ] Tidak ada request API yang salah origin atau mixed content.

## 16. Two User Isolation Test

Gunakan Tester A dan Tester B, masing-masing dengan account Google, Spreadsheet copy, dan workspace berbeda.

| Step | Tester A | Tester B | Expected isolation |
|---:|---|---|---|
| 1 | Login dan buat Source A | Login dan buat Source B | Masing-masing hanya melihat source sendiri |
| 2 | Sync dataset A dengan marker unik | Sync dataset B dengan marker unik | Marker A tidak muncul pada B; marker B tidak muncul pada A |
| 3 | Buat Budget A | Buat Budget B | Budget tidak tercampur |
| 4 | Import PDF A | Import PDF B | Draft/history/registry terisolasi |
| 5 | Search marker A/B | Search marker A/B | Hasil hanya berasal dari workspace aktif |
| 6 | Reset Synced Data Source A | Tetap membuka dashboard B | Data A terhapus sesuai scope; data B tidak berubah |
| 7 | Reload dan relogin | Reload dan relogin | Isolation tetap konsisten |

- [ ] Catat jumlah transaksi A dan B sebelum reset.
- [ ] Jalankan reset hanya dari Tester A pada Source A.
- [ ] Pastikan deletion dibatasi `workspace_id`, `sheet_source_id`, dan Google Sheet origin.
- [ ] Pastikan Spreadsheet A sendiri tidak berubah akibat reset.
- [ ] Pastikan seluruh count, source, budget, import, dan dashboard Tester B identik sebelum/sesudah reset A.
- [ ] Bila satu data lintas workspace terlihat, status deployment langsung **NO-GO** dan test dihentikan.

## 17. Troubleshooting

| Symptom / issue | Diagnosis | Resolution |
|---|---|---|
| **Wrong Supabase Project** | Project Reference pada URL runtime/migration tidak sama dengan UAT record | Stop segera. Jangan migrate/reset. Ambil ulang kedua URL melalui tombol Connect pada UAT project dan verifikasi masked host di `/api/system/info`. |
| **APP_ENV validation** | Startup menolak profile/target/host | Hosted UAT wajib `APP_ENV=uat`, `ENV_PROFILE=uat`, `DB_TARGET=supabase`, dan host Supabase. Jangan gunakan `dev` atau local host. |
| **dotenv override** | Nilai `.env` lokal tampak mengalahkan secret | Process environment yang sudah ada sengaja memiliki precedence. Periksa Replit Secrets/operator shell, hapus nilai stale, restart process; jangan commit `.env.uat`. |
| **Migration URL precedence** | Runner menuju host yang tidak diharapkan | Periksa urutan: `DATABASE_MIGRATION_URL`, `SUPABASE_MIGRATION_DATABASE_URL`, `DATABASE_URL`, `SUPABASE_DATABASE_URL`. Unset nilai precedence lebih tinggi yang stale. |
| **Migration Diagnostics** | Migration gagal namun detail target tidak jelas | Baca safe diagnostics: masked host, port, SSL flags, exception chain. Cocokkan dengan UAT project. Jangan menyalin full URL ke issue. |
| **IPv6 Direct Connection** | Timeout/name resolution/no route dari Windows | Direct endpoint biasanya IPv6. Gunakan Shared Session Pooler port `5432` dari Supabase Connect atau approved IPv4 add-on. |
| **Session Pooler** | Authentication failed pada pooler | Gunakan username persis dari generated string (`postgres.<PROJECT_REF>`), host/region, password URL-encoded, dan port `5432`. Jangan memakai username Direct. |
| **Windows root certificate** | SSL certificate verification gagal walau credential benar | Update Windows/Python CA store dan ambil server root certificate dari Supabase dashboard bila driver memerlukannya. Pertahankan verification; `false` hanya diagnosis sementara, bukan steady state. |
| **`sslmode=require`** | Driver menolak parameter/query atau tetap gagal verify | Pastikan `DATABASE_SSL=true`. Gunakan generated connection string dan driver-supported SSL config. `sslmode=require` mengenkripsi koneksi tetapi tidak menggantikan verifikasi identity yang benar. |
| **Google OAuth redirect mismatch** | Google mengembalikan `redirect_uri_mismatch` | Samakan scheme, host, path, port, dan trailing slash antara Google Console dan `GOOGLE_OAUTH_REDIRECT_URI`. Redeploy setelah secret berubah. |
| **Replit PORT** | Deploy health check timeout/connection refused | Jangan set `BACKEND_PORT`; gunakan `PORT` yang diinjeksi Replit, bind `0.0.0.0`, dan jalankan `npm run start:replit`. |
| **Large Vite Chunk** | Build memberi chunk-size warning | Warning bukan otomatis failure. Pastikan build exit `0` dan app berfungsi; catat backlog code-splitting/lazy loading. Investigasi bila size memengaruhi load time atau deployment limit. |

### Fast triage commands

```powershell
Invoke-RestMethod "https://<REPLIT_HOST>/api/health"
Invoke-RestMethod "https://<REPLIT_HOST>/api/health/db"
Invoke-RestMethod "https://<REPLIT_HOST>/api/system/info"

# Tampilkan hanya nama variable, bukan nilainya
Get-ChildItem Env: | Where-Object Name -Match 'APP_ENV|ENV_PROFILE|DB_TARGET|DATABASE|SUPABASE|GOOGLE|VITE_API_MODE' | Select-Object Name
```

## 18. Security Checklist

- [ ] Tidak ada secrets, database URL, tokens, passwords, OAuth credentials, atau Spreadsheet IDs asli di Git.
- [ ] `git diff` diperiksa sebelum setiap push/deploy.
- [ ] Credential yang sempat tampil di log/chat/screenshot segera di-rotate.
- [ ] Supabase UAT dedicated dan tidak mempunyai akses ke Production database.
- [ ] Google OAuth client UAT terpisah dari Production.
- [ ] Setiap tester memakai dedicated disposable Spreadsheet copy tanpa data pribadi.
- [ ] Production secrets dan UAT secrets berbeda.
- [ ] `JWT_SECRET`, `TOKEN_ENCRYPTION_KEY`, dan `TOKEN_ENCRYPTION_SECRET` kuat, independen, dan stabil antar-redeploy.
- [ ] TLS aktif dan certificate verification tetap aktif.
- [ ] Tidak ada server secret pada `VITE_*` variable/browser bundle.
- [ ] Super Admin access dibatasi dan diaudit.
- [ ] Password hanya disimpan sebagai secure hash; OAuth tokens terenkripsi at rest oleh aplikasi.
- [ ] Database backup/recovery boundary tidak pernah mencampur UAT dan Production.

## 19. GO / NO-GO Checklist

Deployment hanya boleh berstatus **GO** jika semua item berikut PASS. Satu item FAIL atau UNKNOWN berarti **NO-GO**.

### Infrastructure and Configuration

- [ ] Replit deploy berasal dari branch/tag yang disetujui.
- [ ] Supabase Project Reference terverifikasi sebagai dedicated UAT.
- [ ] Environment summary adalah `uat / uat / supabase`.
- [ ] Replit menggunakan injected `PORT` dan same-origin frontend.
- [ ] Secrets lengkap, tidak committed, dan tidak bocor di logs.

### Database

- [ ] Migration runner exit `0`.
- [ ] `schema_migrations` berisi 25 unique rows untuk v0.9.8.
- [ ] Latest required migration `022_add_user_password_credentials.sql` tersedia.
- [ ] Credential table dan trigger tersedia.
- [ ] `/api/health/db` PASS.

### Identity and Product

- [ ] Super Admin login PASS.
- [ ] Tester provisioning dan tester login PASS.
- [ ] Google OAuth PASS untuk approved test user.
- [ ] Spreadsheet connect/save/sync PASS menggunakan disposable copy.
- [ ] Seluruh Smoke Test Checklist PASS.
- [ ] Two User Isolation Test PASS, termasuk reset isolation.

### Decision Record

| Field | Value |
|---|---|
| Release / commit | `<RELEASE_OR_COMMIT_SHA>` |
| Replit deployment | `<DEPLOYMENT_ID>` |
| Supabase UAT project ref (non-secret) | `<PROJECT_REF>` |
| Operator | `<NAME>` |
| Reviewer | `<NAME>` |
| Test date (UTC) | `<YYYY-MM-DD HH:MM>` |
| Decision | `GO / NO-GO` |
| Evidence location | `<LINK_TO_APPROVED_TEST_RECORD>` |

## 20. Future Improvements

- [ ] Production Deployment runbook dan production release gate.
- [ ] CI/CD dengan build, test, security scanning, dan controlled promotion.
- [ ] Automated Migration sebagai gated release job dengan approval dan target verification (bukan startup side effect).
- [ ] In-app **Take a Tour** onboarding.
- [ ] Production Branding dan environment badge yang jelas.
- [ ] RLS Hardening dan database security review untuk seluruh exposed schema/table.
- [ ] Deployment Monitoring dengan deploy status dan rollback signal.
- [ ] Health Monitoring untuk API, database, OAuth, dan sync dependencies.
- [ ] Backup Strategy dengan retention, encryption, dan restore testing.
- [ ] Recovery Procedure termasuk RTO/RPO, incident roles, rollback, dan credential rotation.
- [ ] Frontend code-splitting untuk mengurangi Large Vite Chunk warning dan initial load time.

---

**Maintenance rule:** setiap perubahan environment variable, migration mechanism, endpoint, provider, atau release baseline wajib memperbarui runbook ini pada pull request yang sama. Jangan mengubah nilai historis v0.9.8 tanpa menjelaskan release baru dan expected migration count baru.
