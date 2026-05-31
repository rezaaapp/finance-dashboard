# Environment

Dokumen ini menjelaskan file environment yang dipakai Finance Dashboard untuk
local setup, development, dan arah deployment production. Jangan menaruh secret
asli di dokumentasi atau file `.env.example`.

## Lokasi File Environment

| File | Fungsi |
| --- | --- |
| `.env.example` | Template gabungan untuk backend, dashboard frontend, dan landing page. Praktis untuk melihat seluruh konfigurasi dalam satu tempat. |
| `backend/.env.example` | Template khusus backend FastAPI, Google Sheets, auth, database, Gemini, service account, dan OAuth. |
| `apps/web/.env.example` | Template khusus dashboard frontend React/Vite. |
| `apps/landing/.env.example` | Template khusus landing page React/Vite. |

File lokal yang biasanya dibuat dari template:

```text
.env
backend/.env
apps/web/.env
apps/landing/.env
```

File `.env` lokal tidak boleh di-commit.

## Setup Lokal Windows PowerShell

Jalankan dari root repository:

```powershell
Copy-Item .env.example .env
Copy-Item backend/.env.example backend/.env
Copy-Item apps/web/.env.example apps/web/.env
Copy-Item apps/landing/.env.example apps/landing/.env
```

Setelah copy, isi nilai lokal di file `.env` yang sesuai. Gunakan placeholder
untuk nilai yang belum siap. Secret asli hanya boleh berada di file lokal yang
di-ignore Git atau di environment variable provider deployment.

## Mode Akses Google Sheets

### `service_account` Mode

Mode service account dipakai untuk local development, personal testing, demo
internal, atau controlled testing. Mode ini dapat memakai salah satu variabel:

- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `GOOGLE_SERVICE_ACCOUNT_JSON_BASE64`
- `GOOGLE_APPLICATION_CREDENTIALS`

Jangan commit file JSON service account, isi JSON-nya, versi base64-nya, atau
path lokal yang mengarah ke credential asli. Mode ini tidak boleh menjadi
mekanisme onboarding default untuk public user.

### `oauth` Mode

Mode OAuth adalah arah production. Setiap user/workspace menghubungkan Google
Sheets miliknya sendiri melalui Google OAuth. Refresh token harus disimpan
terenkripsi, dan arah penyimpanan production adalah PostgreSQL.

Variabel target OAuth:

- `GOOGLE_AUTH_MODE`
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_OAUTH_REDIRECT_URI`
- `GOOGLE_OAUTH_SCOPES`
- `TOKEN_ENCRYPTION_KEY`
- `DATABASE_URL`

## Backend Environment Variables

| Variabel | Wajib | Mode | Keterangan |
| --- | --- | --- | --- |
| `DATABASE_URL` | Ya untuk database/PostgreSQL | Runtime app / OAuth target / multi-user | URL koneksi PostgreSQL untuk runtime aplikasi, termasuk FastAPI dan script database Node saat ini. Gunakan placeholder di example. |
| `DATABASE_MIGRATION_URL` | Opsional | Migration/direct connection | URL koneksi PostgreSQL terpisah untuk migration runner atau direct/session connection jika provider membutuhkan URL berbeda untuk schema changes. Kosongkan jika tidak diperlukan. |
| `DATABASE_SSL` | Opsional | Semua mode database | `true` mengaktifkan SSL dan direkomendasikan untuk hosted Supabase/PostgreSQL. Local PostgreSQL dapat memakai `false`. Default runtime saat ini adalah SSL aktif jika variabel tidak diisi. |
| `DATABASE_SSL_REJECT_UNAUTHORIZED` | Opsional | Semua mode database | Mengontrol verifikasi sertifikat SSL. Gunakan `true` jika sertifikat server dapat diverifikasi; gunakan `false` hanya untuk kebutuhan lokal/proxy yang memang memerlukan relaxed verification. |
| `DATABASE_POOL_MAX` | Opsional | Semua mode database | Batas maksimum koneksi pool database. Default saat ini `10`. |
| `DATABASE_IDLE_TIMEOUT_MS` | Opsional | Node database scripts | Timeout idle pool Node dalam milidetik. Default saat ini `30000`. |
| `DATABASE_CONNECTION_TIMEOUT_MS` | Opsional | Node database scripts | Timeout koneksi pool Node dalam milidetik. Default saat ini `10000`. |
| `GOOGLE_SHEET_ID` | Ya untuk workflow lokal single sheet | Dev service account | ID Google Sheet utama untuk backend lokal. Jangan isi dengan ID asli di example. |
| `GOOGLE_SHEET_REGISTRY_JSON` | Ya untuk workflow lokal multi-year | Dev service account | JSON registry spreadsheet tahunan, misalnya mapping tahun ke sheet. Dipakai saat ini untuk local/dev workflow. |
| `DASHBOARD_USERNAME` | Ya untuk auth lokal saat ini | Dev/current auth | Username login dashboard lokal/internal. Jangan gunakan nilai pribadi di example. |
| `DASHBOARD_PASSWORD` | Ya untuk auth lokal saat ini | Dev/current auth | Password login dashboard lokal/internal. Secret, jangan commit nilai asli. |
| `DASHBOARD_AUTH_TOKEN` | Ya untuk auth/API saat ini | Dev/current auth | Bearer token dashboard/API. Secret, rotate jika bocor. |
| `CORS_ALLOWED_ORIGINS` | Ya | Semua mode | Daftar origin frontend yang boleh mengakses backend, dipisahkan koma. |
| `USE_MOCK_DATA` | Opsional | Dev/test | `true` untuk memakai mock data, `false` untuk data aktual dari source yang dikonfigurasi. |
| `GEMINI_API_KEY` | Ya jika menjalankan klasifikasi AI | Dev/current AI | API key Gemini untuk klasifikasi transaksi. Secret, jangan commit nilai asli. |
| `GEMINI_CLASSIFICATION_MODEL` | Opsional | Dev/current AI | Nama model Gemini untuk klasifikasi, misalnya model flash/lite sesuai konfigurasi lokal. |
| `GEMINI_CLASSIFICATION_BATCH_SIZE` | Opsional | Dev/current AI | Jumlah item per batch saat klasifikasi transaksi. |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Pilih salah satu untuk service account | Dev service account | Isi JSON service account sebagai env var. Hanya untuk lokal/demo/testing terkontrol. |
| `GOOGLE_SERVICE_ACCOUNT_JSON_BASE64` | Pilih salah satu untuk service account | Dev service account | Service account JSON dalam base64. Hanya untuk lokal/demo/testing terkontrol. |
| `GOOGLE_APPLICATION_CREDENTIALS` | Pilih salah satu untuk service account | Dev service account | Path lokal ke file credential service account. File target tidak boleh di-commit. |
| `GOOGLE_AUTH_MODE` | Target production | OAuth target | Mode akses Google. Arah production adalah `oauth`; service account hanya untuk dev/testing. |
| `GOOGLE_OAUTH_CLIENT_ID` | Target production | OAuth target | Client ID Google OAuth untuk onboarding per user/workspace. |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Target production | OAuth target | Client secret Google OAuth. Secret, simpan hanya di env provider atau file lokal ignored. |
| `GOOGLE_OAUTH_REDIRECT_URI` | Target production | OAuth target | Callback URL backend untuk menerima respons OAuth. |
| `GOOGLE_OAUTH_SCOPES` | Target production | OAuth target | Scope Google yang dibutuhkan, misalnya akses read-only spreadsheet dan profil user. |
| `TOKEN_ENCRYPTION_KEY` | Target production | OAuth target | Key untuk enkripsi token OAuth/refresh token. Secret, wajib kuat dan tidak boleh di-commit. |

Catatan: file example juga dapat berisi variabel pendukung seperti
`JWT_SECRET`, `TOKEN_ENCRYPTION_SECRET`, `SUPER_ADMIN_EMAILS`,
`FRONTEND_AUTH_REDIRECT_URL`, dan konfigurasi pool database. Ikuti
`backend/.env.example` sebagai sumber template lokal.

## Dashboard Frontend Environment Variables

File: `apps/web/.env`

| Variabel | Wajib | Keterangan |
| --- | --- | --- |
| `VITE_API_URL` | Ya | Base URL backend API untuk dashboard. Untuk lokal biasanya mengarah ke backend di `127.0.0.1:8000`. |
| `VITE_API_BASE_URL` | Ya untuk kompatibilitas saat ini | Alias/base URL backend API. Tetap isi agar kompatibel dengan script dan kode yang ada. |
| `VITE_GUEST_MODE_MULTIPLIER` | Opsional | Multiplier dummy untuk guest/privacy mode agar nilai finansial dapat disamarkan saat demo. |

Variabel dengan prefix `VITE_` akan masuk ke bundle frontend. Jangan pernah
menaruh secret backend, API key rahasia, password, atau token private di env
frontend.

## Landing Page Environment Variables

File: `apps/landing/.env`

| Variabel | Wajib | Keterangan |
| --- | --- | --- |
| `VITE_DASHBOARD_URL` | Ya | URL dashboard yang dibuka dari call-to-action landing page. Untuk lokal biasanya mengarah ke dashboard di port 5173. |

Seperti dashboard, env landing page dengan prefix `VITE_` bersifat public di
bundle frontend. Jangan taruh secret di sini.

## Ringkasan Dev Saat Ini vs Target Production

| Area | Dev saat ini | Target production |
| --- | --- | --- |
| Akses Google Sheets | Service account dan `GOOGLE_SHEET_REGISTRY_JSON` untuk lokal/testing | Google OAuth per user/workspace |
| Token Google | Tidak menjadi alur utama untuk public user | Refresh token terenkripsi |
| Sumber sheet | Env/local registry | PostgreSQL per workspace |
| Transaksi | Dibaca dari Google Sheets saat runtime/sync lokal | Disinkronkan ke PostgreSQL |
| AI classification | Generated local JSON di `backend/output/` | Hasil classification disimpan di PostgreSQL |
| Analytics dashboard | Query dari data yang diproses backend saat ini | Query dari PostgreSQL |

## Catatan Keamanan

- Jangan commit `.env`, credential JSON, token, PEM/key, atau generated JSON di
  `backend/output/`.
- Jangan isi file example dengan secret asli, Google Sheet ID asli, password,
  atau API key asli.
- Jika secret pernah ter-commit, rotate secret, hapus dari repository, hapus
  dari history jika perlu, lalu redeploy.
- Baca checklist lengkap di `docs/SECURITY_CHECKLIST.md`.
