# Finance Dashboard

Finance Dashboard adalah aplikasi dashboard keuangan pribadi/rumah tangga yang
mengambil data dari Google Sheets, mengolahnya di backend, lalu menampilkan
ringkasan dan analitik keuangan di frontend dashboard. Project ini juga
menyediakan landing page terpisah untuk memperkenalkan aplikasi.

## Status Project

Project ini masih dalam tahap pengembangan. Repository ini belum siap untuk
pengguna publik menghubungkan data finansial asli. Gunakan hanya untuk
development, demo internal, atau controlled testing sampai alur OAuth, keamanan
token, dan operasional production benar-benar matang.

## Fitur Utama

- Finance summary dashboard untuk melihat kondisi keuangan secara cepat
- Tren bulanan untuk spending, income, dan saving
- Analitik kategori pengeluaran
- Analitik source fund atau sumber dana
- Klasifikasi transaksi Week 5 berbasis rule untuk Need, Want, Saving,
  Income, dan Uncategorized
- Rule-based financial insights dengan severity per workspace
- Guest/privacy mode untuk menyamarkan nilai saat demo
- Landing page terpisah untuk halaman publik aplikasi

## Tech Stack

- Frontend: React, Vite, Tailwind CSS, Recharts
- Backend API: FastAPI, Python, Pandas
- Data sync dan rule-based classification: Node.js, TypeScript, PostgreSQL
- Data source: Google Sheets
- Deployment target: Vercel untuk frontend dan Render untuk backend

## Struktur Repository

```text
apps/web/        Dashboard frontend berbasis React + Vite
apps/landing/    Landing page berbasis React + Vite
backend/app/     Backend FastAPI, API routes, auth, service, repository
backend/scripts/ Script Python untuk load, proses, dan generate data finansial
backend/node/    Script Node.js/TypeScript untuk sync, seed, dan DB utilities
backend/output/  Output JSON hasil generate lokal; jangan commit data asli
docs/            Dokumentasi project, termasuk checklist keamanan
```

## Setup Environment

Jangan commit file `.env` atau credential asli. Mulai dari template berikut:

```powershell
Copy-Item .env.example .env
Copy-Item backend/.env.example backend/.env
Copy-Item apps/web/.env.example apps/web/.env
Copy-Item apps/landing/.env.example apps/landing/.env
```

File env utama:

- `.env.example`: contoh gabungan untuk backend, dashboard, dan landing
- `backend/.env.example`: konfigurasi backend, Google Sheets, auth, OAuth,
  database, rule-based classification, dan placeholder Gemini legacy
- `apps/web/.env.example`: konfigurasi dashboard frontend seperti
  `VITE_API_URL`, `VITE_API_BASE_URL`, dan `VITE_GUEST_MODE_MULTIPLIER`
- `apps/landing/.env.example`: konfigurasi landing page seperti
  `VITE_DASHBOARD_URL`

Isi semua nilai lokal dengan placeholder aman terlebih dahulu. Masukkan secret
asli hanya di file `.env` lokal atau environment variable provider deployment.

Panduan database Supabase/PostgreSQL tersedia di
[docs/DATABASE.md](docs/DATABASE.md).

Dokumentasi Week 5 rule-based classification tersedia di
[docs/RULE_BASED_CLASSIFICATION.md](docs/RULE_BASED_CLASSIFICATION.md), dengan
checklist final di
[docs/WEEK5_RULE_BASED_VERIFICATION.md](docs/WEEK5_RULE_BASED_VERIFICATION.md).

## Local Development

Install dependency Node.js dari root:

```powershell
npm install
```

Siapkan virtual environment Python untuk backend:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
cd ..
```

Jalankan backend dan dashboard sekaligus:

```powershell
.\start-local.bat
```

Endpoint lokal:

- Backend health: `http://127.0.0.1:8000/api/health`
- Dashboard frontend: `http://127.0.0.1:5173`

Jalankan service secara terpisah bila perlu:

```powershell
.\start-local-backend.bat
.\start-local-frontend.bat
.\start-local-landing.bat
```

Landing page berjalan di `http://127.0.0.1:5174`.

## Google Sheets Access

Untuk local development, demo internal, atau controlled testing, backend dapat
mengakses Google Sheets memakai service account melalui salah satu env berikut:

- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `GOOGLE_SERVICE_ACCOUNT_JSON_BASE64`
- `GOOGLE_APPLICATION_CREDENTIALS`

Jangan commit credential JSON, hasil base64, atau path ke file credential asli.
Service account bukan arah onboarding production untuk user publik.

Arah production adalah Google OAuth per user/workspace. Konfigurasi terkait:

- `GOOGLE_AUTH_MODE`
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_OAUTH_REDIRECT_URI`
- `GOOGLE_OAUTH_SCOPES`
- `FRONTEND_URL`
- `TOKEN_ENCRYPTION_KEY` atau `TOKEN_ENCRYPTION_SECRET`

Dengan OAuth, setiap user/workspace menghubungkan akses Google Sheets miliknya
sendiri, dan token harus disimpan secara aman serta dienkripsi.

Panduan setup Google Cloud OAuth tersedia di
[docs/GOOGLE_OAUTH.md](docs/GOOGLE_OAUTH.md).

## Rule-Based Classification

Week 5 menggunakan deterministic rule-based classification only. Tidak ada AI
provider, external AI API call, atau local LLM yang diperlukan untuk
classification dan insight dashboard.

Konfigurasi default aman:

```env
AI_CLASSIFICATION_ENABLED=false
AI_PROVIDER=rule_based
AI_MODEL=none
AI_ONLY_LOW_CONFIDENCE=true
AI_CONFIDENCE_THRESHOLD=0.75
AI_MAX_TRANSACTIONS_PER_RUN=500
```

Endpoint classification mendukung batch run, summary, low-confidence review,
manual correction, user-defined rules, grouped uncategorized transactions,
suggestions, dan apply suggestion untuk bulk reclassification non-manual.
Manual override tidak dioverwrite.

Sync Now otomatis menjalankan rule-based classification untuk transaksi yang
inserted/updated. Financial Type analytics, rule-based insights, dan Dashboard
Financial Insights memakai classification saat ini.

Backfill data lama bisa dilakukan dengan:

```powershell
POST /api/classifications/run?limit=500
```

## Build dan Validasi

Lint frontend:

```powershell
npm run lint
```

Build dashboard:

```powershell
npm run build:web
```

Build landing page:

```powershell
npm run build:landing
```

Build semua frontend:

```powershell
npm run build:all
```

Validasi koneksi database dan seed awal bila environment sudah siap:

```powershell
npm run db:check
npm run db:migrate
npm run db:seed
```

Catatan: `apps/web` menjalankan validasi env sebelum build production. Pastikan
`VITE_API_URL` atau `VITE_API_BASE_URL` sudah diisi.

## Deployment

Target deployment saat ini:

- Dashboard dan landing page: Vercel
- Backend API: Render

Panduan staging terbaru:

- [docs/WEEK7_STAGING_ARCHITECTURE.md](docs/WEEK7_STAGING_ARCHITECTURE.md)
- [docs/WEEK7_ENVIRONMENT_SETUP.md](docs/WEEK7_ENVIRONMENT_SETUP.md)
- [docs/WEEK7_BACKEND_RENDER_DEPLOYMENT.md](docs/WEEK7_BACKEND_RENDER_DEPLOYMENT.md)
- [docs/WEEK7_FRONTEND_VERCEL_DEPLOYMENT.md](docs/WEEK7_FRONTEND_VERCEL_DEPLOYMENT.md)

`DEPLOY_RENDER_VERCEL.md` masih ada sebagai referensi legacy.

## Keamanan

Sebelum push, baca dan ikuti checklist keamanan:

[docs/SECURITY_CHECKLIST.md](docs/SECURITY_CHECKLIST.md)

Ringkasan penting:

- Jangan commit `.env`, credential Google, token, PEM/key, atau generated JSON
  dari `backend/output/`
- Gunakan placeholder di semua file `.env.example`
- Rotate dan cabut secret jika pernah ter-commit
- Production onboarding diarahkan ke Google OAuth per user/workspace

## Catatan Untuk Contributor

- Review `git status --short` dan `git diff --cached` sebelum push
- Jangan memasukkan data finansial asli ke fixture, screenshot, output JSON,
  atau dokumentasi publik
- Jika menambah env var baru, update file `.env.example` yang relevan dan
  dokumentasikan risikonya bila variabel tersebut berisi secret
