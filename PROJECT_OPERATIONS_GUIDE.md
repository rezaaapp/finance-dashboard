# Finance Dashboard Operations Guide

Dokumen ini adalah panduan operasional project Financial Dashboard agar kamu bisa menjalankan, merawat, dan mengupdate data tanpa perlu meminta instruksi manual setiap kali.

## 1. Ringkasan Project

Project ini terdiri dari:

- Frontend: React + Vite + Tailwind CSS + Recharts
- Backend: FastAPI + Python + Pandas + Google Sheets
- AI classification pipeline: Node.js + TypeScript + Gemini API
- Data source utama: Google Spreadsheet laporan keuangan tahunan
- Deployment umum:
  - Frontend: Vercel
  - Backend API: Render

Folder penting:

```text
backend/app                 FastAPI backend
backend/scripts             Python data processing
backend/output              Output hasil AI classification
backend/node                Node/TypeScript data classification utilities
frontend/src                React application
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

Manual backend:

```powershell
Set-Location -LiteralPath 'D:\[03] Work\Code\finance-dashboard\backend'
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Manual frontend:

```powershell
Set-Location -LiteralPath 'D:\[03] Work\Code\finance-dashboard\frontend'
npm.cmd run dev -- --host 127.0.0.1
```

## 3. Environment Variables

File utama:

```text
backend/.env
frontend/.env
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
GEMINI_API_KEY=your_gemini_api_key
GEMINI_CLASSIFICATION_MODEL=gemini-2.0-flash
GEMINI_CLASSIFICATION_BATCH_SIZE=25
```

Google service account, pilih salah satu:

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

- `Kategori` wajib diisi untuk klasifikasi AI.
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

## 7. AI Classification: Needs, Wants, Savings

File hasil klasifikasi:

```text
backend/output/financial-classification-reference.json
```

Untuk menjalankan klasifikasi ulang setelah ada data baru di spreadsheet:

```powershell
Set-Location -LiteralPath 'D:\[03] Work\Code\finance-dashboard'
npm.cmd run classify:financial-data
```

Script ini akan:

- scan semua spreadsheet dari `GOOGLE_SHEET_REGISTRY_JSON`
- skip row yang `Kategori` kosong
- dedupe global berdasarkan `Nama Transaksi + Kategori`
- resume dari output lama jika sudah ada
- hanya melabeli pasangan transaksi baru
- menyimpan hasil ke `backend/output/financial-classification-reference.json`

Jika terkena quota Gemini:

- Tunggu quota reset atau beberapa menit lalu ulangi command.
- Script sudah punya checkpoint/resume, jadi hasil sebelumnya tidak hilang.

Jika model Gemini bermasalah, ubah env:

```env
GEMINI_CLASSIFICATION_MODEL=gemini-2.0-flash-lite
GEMINI_CLASSIFICATION_BATCH_SIZE=25
```

## 8. Monthly Budget Allocation Trend

Chart `Monthly Budget Allocation Trend` membaca:

1. Transaksi aktual dari Google Sheets
2. Mapping AI dari `backend/output/financial-classification-reference.json`
3. Join fleksibel case-insensitive berdasarkan `Nama Transaksi` / `input_title`
4. Agregasi per bulan:

```json
[
  { "month": "2026-01", "Needs": 5200000, "Wants": 3100000, "Savings": 2000000 }
]
```

Endpoint backend aktif:

```text
GET /api/dashboard/monthly-allocation
```

Jika chart kosong:

- Pastikan file classification JSON ada.
- Jalankan `npm.cmd run classify:financial-data`.
- Restart backend atau klik refresh.
- Pastikan `Nama Transaksi` di spreadsheet bisa match dengan `input_title` di JSON.

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

Jika Google Sheets service account punya akses editor, backend akan menulis konfigurasi ke worksheet `Configuration`.

## 12. Budgeting & Alerts

Menu Budgeting fokus untuk:

- Budget summary
- Manual Budget Editor
- Live Smart Alert Stream
- Next Month Budget Forecast

Manual budget disimpan di browser localStorage.

AI Auto memakai historical average dari data transaksi.

## 13. Deploy Backend ke Render

Gunakan panduan detail di:

```text
DEPLOY_RENDER_VERCEL.md
```

Ringkas:

```text
Runtime: Docker
Root Directory: backend
Dockerfile Path: backend/Dockerfile
```

Health check:

```text
https://finance-dashboard-api.onrender.com/api/health
```

Response benar:

```json
{"status":"ok"}
```

## 14. Deploy Frontend ke Vercel

Vercel settings:

```text
Root Directory: frontend
Build Command: npm run build
Output Directory: dist
```

Environment variables:

```env
VITE_API_URL=https://finance-dashboard-api.onrender.com
VITE_API_BASE_URL=https://finance-dashboard-api.onrender.com
VITE_GUEST_MODE_MULTIPLIER=0.75
```

File `vercel.json` di root sudah mengatur SPA fallback agar refresh page seperti `/analytics` tidak 404.

## 15. Build dan Validasi

Frontend lint:

```powershell
Set-Location -LiteralPath 'D:\[03] Work\Code\finance-dashboard\frontend'
npm.cmd run lint
```

Frontend production build:

```powershell
Set-Location -LiteralPath 'D:\[03] Work\Code\finance-dashboard\frontend'
npm.cmd run build
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
frontend/.env
backend/scripts/credentials.json
*.pem
*.key
service-account*.json
```

Jika GitHub push protection mendeteksi secret:

1. Jangan unblock secret.
2. Hapus secret dari history.
3. Rotate service account key di Google Cloud.

## 17. Troubleshooting Cepat

### Failed to load available years

Cek:

- backend hidup di `http://127.0.0.1:8000`
- token login valid
- `GOOGLE_SHEET_REGISTRY_JSON` valid
- service account punya akses ke spreadsheet

### Tidak bisa login di production

Cek:

- `DASHBOARD_USERNAME` dan `DASHBOARD_PASSWORD` di Render
- frontend Vercel mengarah ke backend Render
- backend `/api/health` status ok
- CORS berisi URL Vercel

### Google auth MalformedError

Pastikan service account JSON lengkap memiliki:

```text
type
project_id
private_key
client_email
token_uri
```

### Gemini quota exceeded

Solusi:

- Tunggu quota reset
- Turunkan batch size
- Gunakan model lite

```env
GEMINI_CLASSIFICATION_MODEL=gemini-2.0-flash-lite
GEMINI_CLASSIFICATION_BATCH_SIZE=25
```

Lalu ulangi:

```powershell
npm.cmd run classify:financial-data
```

### PowerShell profile warning

Jika muncul:

```text
profile.ps1 cannot be loaded because running scripts is disabled
```

Biasanya tidak mengganggu command. Jika ingin memperbaiki permanen, ubah execution policy untuk CurrentUser sesuai kebutuhan Windows kamu.

## 18. Rutinitas Setelah Update Spreadsheet

Gunakan urutan ini:

1. Update data transaksi di Google Sheets.
2. Jalankan classification jika ada nama transaksi/kategori baru:

```powershell
Set-Location -LiteralPath 'D:\[03] Work\Code\finance-dashboard'
npm.cmd run classify:financial-data
```

3. Jalankan backend dan frontend local.
4. Klik refresh data di dashboard.
5. Cek Analytics:
   - Fund Source Analytics
   - Monthly Budget Allocation Trend
   - Category Trend Analysis
   - Category Transaction Heat Map

## 19. File Output Penting

Classification master reference:

```text
backend/output/financial-classification-reference.json
```

File ini boleh dipakai untuk caching ke Supabase atau sebagai master map lokal.

Untuk production Render, file `backend/output` tidak ikut deploy karena berisi data sensitif dan di-ignore Git. Jika ingin `Monthly Budget Allocation Trend` tetap aktif di production tanpa commit file JSON, encode file ini ke base64:

```powershell
Set-Location -LiteralPath 'D:\[03] Work\Code\finance-dashboard'
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-Content -Raw backend\output\financial-classification-reference.json)))
```

Lalu simpan hasilnya sebagai environment variable Render:

```env
FINANCIAL_CLASSIFICATION_JSON_BASE64=hasil_base64_financial_classification_reference
```

## 20. Catatan Prinsip Bahasa

Backend dan data processing:

- Jangan translate data spreadsheet.
- Biarkan `Nama Transaksi`, `Kategori`, `Source Dana`, dan input user tetap natural.

Frontend UI:

- Gunakan English untuk judul, label, tooltip, dan chart text.
- Format nominal tetap Rupiah.
