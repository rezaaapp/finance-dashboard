# Google OAuth Foundation

Dokumen ini menjelaskan setup Google OAuth untuk fondasi akses Google Sheets
per user/workspace. Scope Week 3 hanya menyiapkan konfigurasi, helper keamanan,
dan dokumentasi. Week 3 belum melakukan sync spreadsheet, belum membaca
spreadsheet via OAuth, dan belum insert transaksi ke database.

## Google Cloud Project Setup

1. Buka Google Cloud Console.
2. Buat project baru atau pilih project khusus untuk Finance Dashboard.
3. Pastikan billing dan organization policy project sudah sesuai kebutuhan
   environment yang dipakai.
4. Jangan gunakan project pribadi yang berisi credential production lain untuk
   eksperimen lokal.

## Enable Google Sheets API

1. Di Google Cloud Console, buka APIs & Services.
2. Pilih Library.
3. Cari Google Sheets API.
4. Klik Enable untuk project yang dipakai OAuth.

## OAuth Consent Screen

1. Buka APIs & Services > OAuth consent screen.
2. Pilih user type sesuai environment:
   - Internal jika hanya untuk Google Workspace organisasi.
   - External jika perlu diuji oleh akun Gmail/test user.
3. Isi app name, support email, developer contact, dan domain yang relevan.
4. Tambahkan scope minimum:

```text
openid
email
profile
https://www.googleapis.com/auth/spreadsheets.readonly
```

`openid email profile` dipakai untuk mengambil identitas dasar user/email dari
Google. `https://www.googleapis.com/auth/spreadsheets.readonly` dipakai untuk
membaca Google Sheets tanpa akses tulis. App tetap meminta akses minimum untuk
kebutuhan Week 3/4; jangan meminta scope write untuk fondasi OAuth.

## Testing Mode dan Test Users

Untuk External app yang masih testing:

1. Set publishing status ke Testing.
2. Tambahkan email tester di bagian Test users.
3. Gunakan akun tester tersebut saat mencoba OAuth lokal.
4. Jika akun tidak terdaftar sebagai tester, Google dapat menolak authorization.

## Create OAuth Client ID

1. Buka APIs & Services > Credentials.
2. Klik Create Credentials > OAuth client ID.
3. Pilih Application type: Web application.
4. Beri nama yang jelas, misalnya `Finance Dashboard Local`.
5. Tambahkan Authorized redirect URI lokal:

```text
http://127.0.0.1:8000/api/google/oauth/callback
```

6. Untuk production, tambahkan redirect URI backend production, misalnya:

```text
https://api.example.com/api/google/oauth/callback
```

Gunakan host production yang benar saat deployment sudah final.

## Required Env Variables

Backend membutuhkan env berikut untuk fondasi OAuth:

```env
GOOGLE_OAUTH_CLIENT_ID=replace_with_google_oauth_client_id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=replace_with_google_oauth_client_secret
GOOGLE_OAUTH_REDIRECT_URI=http://127.0.0.1:8000/api/google/oauth/callback
GOOGLE_LOGIN_REDIRECT_URI=http://127.0.0.1:8000/auth/google/callback
GOOGLE_OAUTH_SCOPES=openid email profile https://www.googleapis.com/auth/spreadsheets.readonly
FRONTEND_URL=http://127.0.0.1:5173
TOKEN_ENCRYPTION_KEY=replace_with_fernet_key_generated_by_Fernet_generate_key
```

`GOOGLE_OAUTH_CLIENT_SECRET` dan `TOKEN_ENCRYPTION_KEY` adalah secret. Simpan
hanya di file `.env` lokal yang di-ignore Git atau environment variable provider
deployment. Jangan menaruh nilai asli di `.env.example`, dokumentasi, log, atau
issue tracker.

Generate `TOKEN_ENCRYPTION_KEY` lokal dengan Python:

```powershell
.\backend\venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Backend Endpoints

OAuth foundation menyediakan endpoint berikut:

```text
GET  /api/google/oauth/start
GET  /api/google/oauth/callback
GET  /api/google/connection/status
POST /api/google/connection/disconnect
```

`/api/google/oauth/start` membutuhkan session user dan mengembalikan
`auth_url`. Frontend mengarahkan browser ke URL tersebut. Callback menyimpan
token secara terenkripsi ke `google_oauth_connections` dan hanya me-redirect
browser ke frontend dengan status sederhana:

```text
/settings/data-sources?google_connected=success
/settings/data-sources?google_connected=failed
```

Token Google, encrypted token, dan client secret tidak boleh dikirim ke browser.

## OAuth Flow Separation

Google Sheets Connection dan legacy Google login memakai callback berbeda:

```text
Google Sheets Connection:
GET /api/google/oauth/start
GET /api/google/oauth/callback

Legacy Google login:
GET /auth/google
GET /auth/google/callback
```

`/api/google/oauth/callback` hanya menerima state dari
`/api/google/oauth/start`, yaitu state yang berisi `user_id`, `workspace_id`,
`nonce`, dan `created_at`. Jangan arahkan `/auth/google` ke callback ini.

Jika legacy login masih dipakai, konfigurasikan `GOOGLE_LOGIN_REDIRECT_URI`
ke `/auth/google/callback`.

## Dashboard UI Flow

Dashboard menampilkan card `Google Sheets Connection` di halaman Configuration.
Flow UI:

1. Frontend memanggil `GET /api/google/connection/status`.
2. User klik `Connect Google`.
3. Frontend memanggil `GET /api/google/oauth/start`.
4. Browser diarahkan ke Google authorization URL.
5. Callback backend menyimpan token terenkripsi dan redirect kembali ke
   `/settings/data-sources`.
6. User dapat klik `Disconnect` untuk memanggil
   `POST /api/google/connection/disconnect`.

Frontend tidak menyimpan access token, refresh token, atau encrypted token di
`localStorage` maupun `sessionStorage`.

## Redirect URI Local

Default lokal backend:

```text
http://127.0.0.1:8000/api/google/oauth/callback
```

Nilai ini harus sama persis antara:

- Google Cloud Console Authorized redirect URIs
- `GOOGLE_OAUTH_REDIRECT_URI` di backend `.env`
- route backend yang akan dibuat pada task OAuth endpoint berikutnya

Google Cloud Console harus memuat redirect URI berikut untuk Google Sheets:

```text
http://127.0.0.1:8000/api/google/oauth/callback
```

Jika legacy Google login dipakai, tambahkan juga:

```text
http://127.0.0.1:8000/auth/google/callback
```

## Redirect URI Production

Gunakan domain backend production, bukan domain frontend. Contoh:

```text
https://finance-dashboard-api.example.com/api/google/oauth/callback
```

Jika backend berada di Render atau provider lain, gunakan URL public backend
yang menerima callback Google.

## Troubleshooting `redirect_uri_mismatch`

Error `redirect_uri_mismatch` berarti redirect URI yang dikirim backend tidak
sama persis dengan Authorized redirect URI di Google Cloud Console.

Cek hal berikut:

- Scheme harus sama, misalnya `http` vs `https`.
- Host harus sama, misalnya `127.0.0.1` berbeda dari `localhost`.
- Port harus sama, misalnya `8000`.
- Path harus sama, misalnya `/api/google/oauth/callback`.
- Tidak ada trailing slash tambahan.
- Setelah mengubah Google Cloud Console, tunggu sebentar lalu coba ulang.

## Troubleshooting `Required parameter is missing: response_type`

Error Google `invalid_request` dengan pesan `Required parameter is missing:
response_type` berarti authorization URL yang diterima Google tidak lengkap.
Endpoint `GET /api/google/oauth/start` harus menghasilkan `auth_url` ke:

```text
https://accounts.google.com/o/oauth2/v2/auth
```

Pastikan query parameter di `auth_url` mencakup `response_type=code`,
`client_id`, `redirect_uri`, `scope`, `state`, `access_type=offline`, dan
`prompt=consent`. Client secret tidak boleh muncul di authorization URL.

## Week 3 Limitation

Fondasi Week 3 menyiapkan konfigurasi, helper keamanan, repository koneksi,
endpoint OAuth, endpoint status/disconnect, dan UI connect/disconnect. Week 3
belum melakukan sync Google Sheets, belum membaca spreadsheet via OAuth, belum
insert transaksi ke database, dan belum meminta input Spreadsheet URL.

## Final Validation

Command validasi yang dipakai untuk Week 3:

```powershell
.\backend\venv\Scripts\python.exe -m compileall backend\app backend\scripts
npm run lint
npm run build:web
npm run security:check
```

Jika backend sedang berjalan, cek manual:

```text
GET /api/health
GET /api/health/db
GET /api/google/connection/status
GET /api/google/oauth/start
```
