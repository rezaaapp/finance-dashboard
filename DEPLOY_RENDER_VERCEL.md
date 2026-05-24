# Deploy Financial Dashboard

Panduan ini dipakai agar frontend Vercel terhubung ke backend FastAPI, bukan ke service lain.

## 1. Deploy Backend FastAPI ke Render

Di Render, buat **New Web Service** baru dari repository ini.

Gunakan setting berikut. Cara paling aman adalah Docker supaya Render tidak salah mendeteksi project sebagai Java/Spring Boot.

```text
Name: finance-dashboard-api
Runtime: Docker
Root Directory: backend
Dockerfile Path: backend/Dockerfile
```

Jangan gunakan service yang terdeteksi sebagai Java atau Spring Boot. Jika halaman `/api/health` menampilkan "Whitelabel Error Page", berarti service yang aktif bukan backend FastAPI dari project ini.

## 2. Environment Variables Backend Render

Isi environment variables berikut di Render:

```env
GOOGLE_SHEET_ID=your_google_sheet_id
DASHBOARD_USERNAME=your_username
DASHBOARD_PASSWORD=your_password
DASHBOARD_AUTH_TOKEN=change_this_to_a_long_random_token
GOOGLE_SERVICE_ACCOUNT_JSON=your_full_google_service_account_json
CORS_ALLOWED_ORIGINS=https://finance-dashboard-mu-lac.vercel.app
```

Untuk `GOOGLE_SERVICE_ACCOUNT_JSON`, paste isi file service account JSON Google secara utuh sebagai satu value. JSON itu wajib memiliki field seperti `client_email`, `private_key`, dan `token_uri`. Jangan memakai placeholder seperti `{"type":"service_account","project_id":"..."}`.

Jika Render sulit menerima JSON mentah, gunakan base64:

```powershell
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-Content -Raw backend\scripts\credentials.json)))
```

Lalu isi hasilnya ke:

```env
GOOGLE_SERVICE_ACCOUNT_JSON_BASE64=hasil_base64
```

Jika memakai base64, kosongkan `GOOGLE_SERVICE_ACCOUNT_JSON`.

## 3. Test Backend

Setelah deploy Render berhasil, buka:

```text
https://finance-dashboard-api.onrender.com/api/health
```

Response yang benar:

```json
{"status":"ok"}
```

Jika masih 404 atau "Whitelabel Error Page", cek lagi setting Render:

- Root Directory harus `backend`
- Runtime harus `Docker`
- Dockerfile Path harus `backend/Dockerfile`
- Branch repo harus branch yang berisi folder `backend/app/main.py`

## 4. Setting Frontend Vercel

Di Vercel frontend project, isi environment variables:

```env
VITE_API_URL=https://finance-dashboard-api.onrender.com
VITE_API_BASE_URL=https://finance-dashboard-api.onrender.com
```

Lalu lakukan redeploy frontend. Pilih opsi untuk tidak memakai build cache jika tersedia.

## 5. Test Login

Setelah backend `/api/health` sudah `ok` dan frontend sudah redeploy, login memakai:

- `DASHBOARD_USERNAME`
- `DASHBOARD_PASSWORD`

yang sama persis dengan environment variables di Render.
