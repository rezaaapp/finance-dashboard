# Finance Dashboard Operations Guide

Dokumen ini adalah panduan operasional project Financial Dashboard agar kamu bisa menjalankan, merawat, dan mengupdate data tanpa perlu meminta instruksi manual setiap kali.

## Production Direction Notice

Project ini masih dalam tahap development. Instruksi lokal di dokumen ini tetap
valid untuk menjalankan project saat ini, termasuk penggunaan:

- service account credentials untuk local development, personal testing, demo
  internal, atau controlled testing
- `GOOGLE_SHEET_REGISTRY_JSON` sebagai registry spreadsheet lokal/tahunan
- generated legacy classification JSON lokal di `backend/output/`

Arah production yang lebih aman bukan memakai shared service account sebagai
default onboarding user publik. Target arsitektur production adalah:

- Google OAuth per user/workspace
- refresh token disimpan terenkripsi
- sumber Google Sheet disimpan di PostgreSQL
- transaksi disinkronkan ke PostgreSQL
- hasil rule-based classification disimpan di PostgreSQL
- dashboard analytics membaca data dari PostgreSQL

Panduan database Supabase/PostgreSQL tersedia di
`docs/DATABASE.md`.
Panduan validasi database staging Week 7 tersedia di
`docs/WEEK7_STAGING_DATABASE_VALIDATION.md`.

Bagian-bagian di bawah masih mempertahankan command lokal yang berguna untuk
development saat ini. Jika ada perbedaan antara workflow lokal dan arah
production, ikuti notice ini sebagai arah desain production.

Panduan setup Google OAuth ada di:

```text
docs/GOOGLE_OAUTH.md
```

## 1. Ringkasan Project

Project ini terdiri dari:

- Frontend: React + Vite + Tailwind CSS + Recharts
- Backend: FastAPI + Python + Pandas + Google Sheets
- Week 5 classification pipeline: deterministic rule-based engine, no AI
  provider/API/local LLM by default
- Data source utama: Google Spreadsheet laporan keuangan tahunan
- Deployment umum:
  - Frontend: Vercel
  - Backend API: Render

Folder penting:

```text
backend/app                 FastAPI backend
backend/scripts             Python data processing
backend/output              Output generated lokal lama; jangan commit data asli
backend/node                Node/TypeScript data classification utilities
apps/web/src                React dashboard application
apps/landing/src            React landing page application
```

## 2. Menjalankan Local Development

Cara paling mudah:

```powershell
Set-Location -LiteralPath 'D:\[03] Work\Code\finance-dashboard'
.\start-local.bat
```

URL lokal:

```text
Backend:  http://127.0.0.1:8000/api/health
Frontend: http://127.0.0.1:5173
Landing:  http://127.0.0.1:5174
```

Jika ingin menjalankan terpisah:

```powershell
Set-Location -LiteralPath 'D:\[03] Work\Code\finance-dashboard'
.\start-local-backend.bat
```

```powershell
Set-Location -LiteralPath 'D:\[03] Work\Code\finance-dashboard'
.\start-local-frontend.bat
```

```powershell
Set-Location -LiteralPath 'D:\[03] Work\Code\finance-dashboard'
.\start-local-landing.bat
```

Manual backend:

```powershell
Set-Location -LiteralPath 'D:\[03] Work\Code\finance-dashboard\backend'
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Manual frontend:

```powershell
Set-Location -LiteralPath 'D:\[03] Work\Code\finance-dashboard\apps\web'
npm.cmd run dev -- --host 127.0.0.1
```

Manual landing:

```powershell
Set-Location -LiteralPath 'D:\[03] Work\Code\finance-dashboard\apps\landing'
npm.cmd run dev -- --host 127.0.0.1 --port 5174
```

## 3. Environment Variables

File utama:

```text
backend/.env
apps/web/.env
apps/landing/.env
.env
```

Jangan commit file `.env` atau file credential JSON.

Backend env penting:

```env
GOOGLE_SHEET_ID=your_google_sheet_id
GOOGLE_SHEET_REGISTRY_JSON={"2025":{"id":"...","name":"Laporan Keuangan 2025"},"2026":{"id":"...","name":"Laporan Keuangan 2026"}}
DASHBOARD_USERNAME=your_username
DASHBOARD_PASSWORD=your_password
DASHBOARD_AUTH_TOKEN=change_this_to_a_long_random_token
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://your-vercel-url.vercel.app
USE_MOCK_DATA=false
AI_CLASSIFICATION_ENABLED=false
AI_PROVIDER=rule_based
AI_MODEL=none
AI_ONLY_LOW_CONFIDENCE=true
AI_CONFIDENCE_THRESHOLD=0.75
AI_MAX_TRANSACTIONS_PER_RUN=500
```

Google service account untuk lokal/testing, pilih salah satu:

```env
GOOGLE_SERVICE_ACCOUNT_JSON=full_json_service_account
```

atau:

```env
GOOGLE_SERVICE_ACCOUNT_JSON_BASE64=base64_encoded_service_account_json
```

atau untuk local saja:

```env
GOOGLE_APPLICATION_CREDENTIALS=backend/scripts/credentials.json
```

Service account credentials hanya boleh dipakai untuk local development,
personal testing, demo internal, atau controlled testing. Jangan gunakan service
account sebagai mekanisme onboarding default untuk public user. Arah production
adalah Google OAuth per user/workspace dengan refresh token yang disimpan
terenkripsi.

Konfigurasi OAuth foundation:

```env
GOOGLE_OAUTH_CLIENT_ID=replace_with_google_oauth_client_id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=replace_with_google_oauth_client_secret
GOOGLE_OAUTH_REDIRECT_URI=http://127.0.0.1:8000/api/google/oauth/callback
GOOGLE_OAUTH_SCOPES=openid email profile https://www.googleapis.com/auth/spreadsheets.readonly
FRONTEND_URL=http://127.0.0.1:5173
TOKEN_ENCRYPTION_KEY=replace_with_fernet_key_generated_by_Fernet_generate_key
```

Frontend env penting:

```env
VITE_API_URL=http://127.0.0.1:8000
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_GUEST_MODE_MULTIPLIER=0.75
```

Untuk production Vercel:

```env
VITE_API_URL=https://finance-dashboard-api.onrender.com
VITE_API_BASE_URL=https://finance-dashboard-api.onrender.com
```

## 4. Google Sheets Registry Tahunan

Spreadsheet tahunan didefinisikan di:

```env
GOOGLE_SHEET_REGISTRY_JSON={"2025":{"id":"ID_2025","name":"Laporan Keuangan 2025"},"2026":{"id":"ID_2026","name":"Laporan Keuangan 2026"}}
```

Jika menambah tahun baru, cukup tambahkan entry baru:

```env
GOOGLE_SHEET_REGISTRY_JSON={"2025":{"id":"ID_2025","name":"Laporan Keuangan 2025"},"2026":{"id":"ID_2026","name":"Laporan Keuangan 2026"},"2027":{"id":"ID_2027","name":"Laporan Keuangan 2027"}}
```

Setelah mengubah `.env`, restart backend.

## 5. Format Data Spreadsheet

Kolom utama yang dipakai backend:

```text
Waktu Transaksi atau Tanggal
Nama Transaksi
Kategori
Harga
Nama
Source Dana
```

Catatan:

- `Kategori` membantu rule-based classification, tetapi row transaksi valid
  masih bisa masuk sebagai expense dan dipetakan ke Uncategorized jika kosong.
- `Nama Transaksi` dipakai sebagai basis matching classification.
- `Source Dana` boleh berisi bank, e-wallet, payroll source, atau saving location.
- Input spreadsheet boleh tetap Bahasa Indonesia natural. Backend tidak menerjemahkan data transaksi.

## 6. Refresh Data Dashboard

Jika kamu mengubah Google Sheets dan ingin dashboard membaca ulang:

1. Klik tombol refresh icon di header dashboard.
2. Atau restart backend.
3. Jika masih tertahan cache, panggil endpoint refresh:

```powershell
curl -X POST "http://127.0.0.1:8000/api/dashboard/refresh?year=2026" -H "Authorization: Bearer YOUR_TOKEN"
```

Biasanya klik refresh dari UI sudah cukup.

## 7. Week 5 Rule-Based Classification

Week 5 classification berjalan deterministic rule-based only. Tidak ada AI
provider, external AI API call, atau local LLM yang diperlukan. Classification
ditulis ke PostgreSQL dengan `direction`, `financial_type`, `category`,
`confidence_score`, `method`, dan status current/manual override.

Financial type yang digunakan dashboard:

- `income`
- `need`
- `want`
- `saving`
- `uncategorized`

Sync Now otomatis menjalankan rule-based classification untuk transaksi yang
inserted/updated. User-defined rules dipakai sebelum built-in system rules, dan
manual override tidak dioverwrite.

Backfill data lama:

```powershell
curl -X POST "http://127.0.0.1:8000/api/classifications/run?limit=500" -H "Authorization: Bearer YOUR_TOKEN"
```

Dokumentasi lengkap:

```text
docs/RULE_BASED_CLASSIFICATION.md
docs/WEEK5_RULE_BASED_VERIFICATION.md
docs/WEEK6_RELEASE_READINESS.md
docs/WEEK6_DASHBOARD_QA.md
docs/WEEK6_ANALYTICS_QA.md
docs/WEEK6_DATA_ACCURACY_AUDIT.md
docs/WEEK6_SECURITY_HARDENING.md
docs/WEEK6_ONBOARDING_EMPTY_STATE.md
docs/WEEK6_WORKSPACE_SWITCHER.md
docs/WEEK6_WORKSPACE_INVITATIONS.md
docs/WEEK7_STAGING_ARCHITECTURE.md
docs/WEEK7_ENVIRONMENT_SETUP.md
docs/WEEK7_BACKEND_RENDER_DEPLOYMENT.md
docs/WEEK7_FRONTEND_VERCEL_DEPLOYMENT.md
docs/WEEK7_STAGING_DATABASE_VALIDATION.md
```

Week 7 dimulai dari arsitektur staging free/low-cost dan audit deployment
artifact. Deployment aktual dilakukan di prompt Week 7 berikutnya setelah env,
Render, Vercel, Supabase, dan Google OAuth staging disiapkan.

## 8. Financial Type Analytics

Dashboard Week 5 membaca current classifications dari PostgreSQL untuk:

- Financial Type Breakdown
- Monthly Financial Type Trend
- Rule-Based Financial Insights
- Anomaly explanation with workspace severity

Endpoint utama:

```text
GET /api/dashboard/financial-types
GET /api/dashboard/monthly-financial-types
GET /api/dashboard/rule-based-insights
GET /api/dashboard/anomalies
```

Contoh monthly financial type shape:

```json
[
  { "month": 1, "need": 5200000, "want": 3100000, "saving": 2000000, "income": 12000000, "uncategorized": 0 }
]
```

Jika chart kosong:

- Pastikan migration Week 5 sudah jalan.
- Jalankan `POST /api/classifications/run?limit=500` untuk backfill jika perlu.
- Restart backend atau klik refresh.
- Cek `docs/WEEK5_RULE_BASED_VERIFICATION.md`.

## 9. Source Dana Analytics

Kolom `Source Dana` dipakai untuk tiga chart:

- Income Sources
- Expense Methods
- Saving Allocations

Source name tidak di-hardcode. Nama baru di spreadsheet otomatis muncul.

Brand color mapping di frontend:

```text
BCA      #0066AE
BLU      #00B4D8
Gopay    #00AED6
Ovo      #4C2A86
Seabank  #FF5722
Jago     #FFB800
```

Source lain memakai fallback neutral/slate color.

## 10. Privacy Modes

Privacy mode sekarang ada di menu:

```text
Configuration > System & Integration > Account Privacy Mode
```

Mode:

- Normal: angka asli tampil penuh
- Hide: angka disensor
- Guest: angka dimasking dengan multiplier dummy

Guest multiplier:

```env
VITE_GUEST_MODE_MULTIPLIER=0.75
```

## 11. Configuration Tab

Menu `Configuration` berisi:

- Financial Cycle Settings
  - Payday Start Day
- Budgeting Mode
  - Manual
  - AI Auto
- System & Integration
  - Google Sheets Connected Source
  - Account Privacy Mode

Perubahan di Configuration memakai draft state dulu. Perubahan aktif setelah klik:

```text
Save Changes
```

Backend endpoint:

```text
POST /api/dashboard/configuration
```

Untuk workflow lokal/testing, jika Google Sheets service account punya akses
editor, backend akan menulis konfigurasi ke worksheet `Configuration`.

## 12. Budgeting & Alerts

Menu Budgeting fokus untuk:

- Budget summary
- Manual Budget Editor
- Live Smart Alert Stream
- Next Month Budget Forecast

Manual budget disimpan di browser localStorage.

AI Auto memakai historical average dari data transaksi.

## 13. Deploy Backend ke Render

Gunakan panduan Week 7 terbaru di:

```text
docs/WEEK7_BACKEND_RENDER_DEPLOYMENT.md
```

Panduan lama masih tersedia sebagai referensi historis:

```text
DEPLOY_RENDER_VERCEL.md
```

Ringkas rekomendasi staging:

```text
Runtime: Docker
Root Directory: backend
Dockerfile Path: backend/Dockerfile
Health Check Path: /api/health
```

Catatan production direction: staging Week 7 menggunakan Google OAuth per
user/workspace, penyimpanan token terenkripsi, Supabase/PostgreSQL, dan
classification rule-based. Jangan jadikan shared service account sebagai
onboarding default untuk public user.

Health check:

```text
https://finance-dashboard-api.onrender.com/api/health
```

Response benar:

```json
{"status":"ok"}
```

## 14. Deploy Frontend ke Vercel

Gunakan panduan Week 7 terbaru di:

```text
docs/WEEK7_FRONTEND_VERCEL_DEPLOYMENT.md
```

Vercel settings final untuk dashboard app:

```text
Root Directory: .
Build Command: npm run build:web
Output Directory: apps/web/dist
```

Environment variables:

```env
VITE_API_URL=https://finance-dashboard-api.onrender.com
VITE_API_BASE_URL=https://finance-dashboard-api.onrender.com
VITE_GUEST_MODE_MULTIPLIER=0.75
```

File `vercel.json` di root sudah mengatur SPA fallback agar refresh page seperti `/analytics` tidak 404.

Vercel settings untuk landing page:

```text
Root Directory: .
Build Command: npm run build:landing
Output Directory: apps/landing/dist
```

Landing env penting:

```env
VITE_DASHBOARD_URL=https://app.your-domain.com
```

## 15. Build dan Validasi

Frontend lint:

```powershell
Set-Location -LiteralPath 'D:\[03] Work\Code\finance-dashboard'
npm.cmd run lint
```

Frontend production build:

```powershell
Set-Location -LiteralPath 'D:\[03] Work\Code\finance-dashboard'
npm.cmd run build:web
```

Landing production build:

```powershell
Set-Location -LiteralPath 'D:\[03] Work\Code\finance-dashboard'
npm.cmd run build:landing
```

Root build:

```powershell
Set-Location -LiteralPath 'D:\[03] Work\Code\finance-dashboard'
npm.cmd run build
```

Backend compile check:

```powershell
Set-Location -LiteralPath 'D:\[03] Work\Code\finance-dashboard'
.\backend\venv\Scripts\python.exe -m compileall backend\app backend\scripts
```

TypeScript check untuk Node utilities:

```powershell
Set-Location -LiteralPath 'D:\[03] Work\Code\finance-dashboard'
npx.cmd tsc --noEmit --target ES2022 --module NodeNext --moduleResolution NodeNext --skipLibCheck backend/node/syncAndClassifyFinancialData.ts backend/node/runSyncAndClassifyFinancialData.ts backend/node/monthlyAllocationRoute.ts
```

## 16. Git dan Security Checklist

Sebelum push ke GitHub:

```powershell
Set-Location -LiteralPath 'D:\[03] Work\Code\finance-dashboard'
git status --short
```

Pastikan file ini tidak ikut commit:

```text
.env
backend/.env
apps/web/.env
apps/landing/.env
backend/scripts/credentials.json
backend/output/*.json
*.pem
*.key
service-account*.json
```

Jika GitHub push protection mendeteksi secret:

1. Jangan unblock secret.
2. Hapus secret dari history.
3. Rotate service account key di Google Cloud.

Checklist lengkap ada di:

```text
docs/SECURITY_CHECKLIST.md
```

## 17. Troubleshooting Cepat

### Failed to load available years

Cek:

- backend hidup di `http://127.0.0.1:8000`
- token login valid
- `GOOGLE_SHEET_REGISTRY_JSON` valid
- untuk workflow lokal, service account punya akses ke spreadsheet

### Tidak bisa login di production

Cek:

- `DASHBOARD_USERNAME` dan `DASHBOARD_PASSWORD` di Render
- frontend Vercel mengarah ke backend Render
- backend `/api/health` status ok
- CORS berisi URL Vercel

### Google auth MalformedError

Untuk workflow lokal/testing yang memakai service account, pastikan service
account JSON lengkap memiliki:

```text
type
project_id
private_key
client_email
token_uri
```

Untuk public user di production, jangan arahkan user ke shared service account.
Arah production adalah OAuth per user/workspace.

### Rule-based classification backlog

Jika masih ada transaksi lama yang belum punya current classification:

```powershell
curl -X POST "http://127.0.0.1:8000/api/classifications/run?limit=500" -H "Authorization: Bearer YOUR_TOKEN"
```

Ulangi sampai `GET /api/classifications/summary` menunjukkan unclassified
backlog habis. Manual override tetap tidak dioverwrite.

### PowerShell profile warning

Jika muncul:

```text
profile.ps1 cannot be loaded because running scripts is disabled
```

Biasanya tidak mengganggu command. Jika ingin memperbaiki permanen, ubah execution policy untuk CurrentUser sesuai kebutuhan Windows kamu.

## 18. Rutinitas Setelah Update Spreadsheet

Gunakan urutan ini:

1. Update data transaksi di Google Sheets.
2. Klik Sync Now agar transaksi inserted/updated ikut diklasifikasi otomatis.
3. Jika perlu backfill data lama:

```powershell
curl -X POST "http://127.0.0.1:8000/api/classifications/run?limit=500" -H "Authorization: Bearer YOUR_TOKEN"
```

4. Jalankan backend dan frontend local.
5. Klik refresh data di dashboard.
6. Cek Dashboard dan Analytics:
   - Financial Insights
   - Financial Type Breakdown
   - Monthly Financial Type Trend
   - Fund Source Analytics
   - Category Trend Analysis
   - Category Transaction Heat Map

## 19. File Output Penting

Legacy/generated local output:

```text
backend/output/financial-classification-reference.json
```

File ini adalah generated local output lama. Isinya dapat mengandung data
turunan transaksi pribadi, sehingga tidak boleh di-commit.

Week 5 tidak membutuhkan file JSON/base64 untuk classification dashboard. Arah
production adalah menyimpan classification di PostgreSQL, termasuk
financial_type, confidence, method, dan status manual override.

## 20. Catatan Prinsip Bahasa

Backend dan data processing:

- Jangan translate data spreadsheet.
- Biarkan `Nama Transaksi`, `Kategori`, `Source Dana`, dan input user tetap natural.

Frontend UI:

- Gunakan English untuk judul, label, tooltip, dan chart text.
- Format nominal tetap Rupiah.
