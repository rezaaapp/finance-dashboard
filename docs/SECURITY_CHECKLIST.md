# Checklist Keamanan

Gunakan checklist ini sebelum setiap push. Project ini memakai backend FastAPI,
frontend dashboard Vite, landing page Vite, integrasi Google Sheets, klasifikasi
Gemini, dan onboarding Google OAuth opsional.

## File Yang Tidak Boleh Pernah Di-commit

- [ ] File `.env`, termasuk `.env`, `backend/.env`, `apps/web/.env`, dan
  `apps/landing/.env`
- [ ] Backup env lokal seperti `.env_backup`, `.env.local`, `.env.production`,
  atau salinan file env lain
- [ ] File JSON kredensial Google, termasuk nama seperti `credentials.json`,
  `client_secret.json`, atau OAuth client secret hasil unduhan
- [ ] File JSON service account Google
- [ ] File token, termasuk OAuth refresh token, access token, dump session, dan
  cache auth yang dihasilkan otomatis
- [ ] File PEM, private key, certificate, atau signing key, termasuk `*.pem`,
  `*.key`, `*.p8`, `*.p12`, dan `*.crt`
- [ ] File JSON hasil generate di `backend/output/`
- [ ] File apa pun yang berisi nilai asli untuk `DASHBOARD_PASSWORD`,
  `DASHBOARD_AUTH_TOKEN`, `JWT_SECRET`, `TOKEN_ENCRYPTION_SECRET`,
  `TOKEN_ENCRYPTION_KEY`, `GEMINI_API_KEY`, `GOOGLE_SERVICE_ACCOUNT_JSON`,
  `GOOGLE_SERVICE_ACCOUNT_JSON_BASE64`, `GOOGLE_APPLICATION_CREDENTIALS`,
  `GOOGLE_OAUTH_CLIENT_SECRET`, Google Sheet ID asli, atau database URL asli

Yang boleh di-commit hanya template contoh seperti `.env.example`, dan isinya
harus tetap berupa placeholder.

## Pemeriksaan Git

Jalankan dari root repository sebelum staging atau push:

```powershell
git status --short
git diff -- . ':!package-lock.json'
git diff --cached
```

Periksa apakah file rahasia lokal yang seharusnya di-ignore masih terlihat oleh
Git:

```powershell
git ls-files --others --exclude-standard
git check-ignore -v .env backend/.env apps/web/.env apps/landing/.env
```

Cari pola rahasia umum di file yang sudah tracked:

```powershell
git grep -n -I -E "AIza[0-9A-Za-z_-]{20,}|-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----|private_key|client_secret|refresh_token|access_token|DASHBOARD_PASSWORD|DASHBOARD_AUTH_TOKEN|JWT_SECRET|TOKEN_ENCRYPTION_SECRET|TOKEN_ENCRYPTION_KEY|GEMINI_API_KEY|GOOGLE_SERVICE_ACCOUNT_JSON|GOOGLE_SERVICE_ACCOUNT_JSON_BASE64|GOOGLE_OAUTH_CLIENT_SECRET|postgresql://|mongodb\\+srv://|sk-[A-Za-z0-9_-]+"
```

Cari pola rahasia hanya di perubahan yang sudah staged:

```powershell
git diff --cached --name-only
git diff --cached -G "AIza|PRIVATE KEY|private_key|client_secret|refresh_token|access_token|DASHBOARD_PASSWORD|DASHBOARD_AUTH_TOKEN|JWT_SECRET|TOKEN_ENCRYPTION_SECRET|TOKEN_ENCRYPTION_KEY|GEMINI_API_KEY|GOOGLE_SERVICE_ACCOUNT_JSON|GOOGLE_SERVICE_ACCOUNT_JSON_BASE64|GOOGLE_OAUTH_CLIENT_SECRET|postgresql://|sk-"
```

Command grep bisa saja menandai placeholder aman di `.env.example` atau dokumen.
Itu wajar. Buka setiap hasil dan pastikan nilainya bukan secret asli.

## Kebijakan Kredensial Google

Kredensial service account hanya boleh dipakai untuk local development, demo
internal, atau controlled testing. Untuk backend lokal, gunakan tepat salah satu
dari env var berikut jika memang diperlukan:

- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `GOOGLE_SERVICE_ACCOUNT_JSON_BASE64`
- `GOOGLE_APPLICATION_CREDENTIALS`

Jangan commit JSON service account, versi base64-nya, atau path lokal yang
mengarah ke file kredensial asli.

Untuk production, onboarding user harus memakai Google OAuth per user/workspace.
Gunakan env var OAuth berikut untuk konfigurasi production:

- `GOOGLE_AUTH_MODE=oauth`
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `GOOGLE_OAUTH_REDIRECT_URI`
- `GOOGLE_OAUTH_SCOPES`
- `TOKEN_ENCRYPTION_KEY` atau `TOKEN_ENCRYPTION_SECRET`

Token OAuth harus disimpan dengan aman dan dienkripsi saat disimpan. Jangan
export atau commit token OAuth milik user.

## Jika Secret Pernah Ter-commit

1. Segera rotate secret di console provider terkait:
   Google Cloud, Gemini, database provider, hosting provider, atau layanan lain
   yang terdampak.
2. Hapus secret dari working tree dan ganti dengan placeholder atau file lokal
   yang di-ignore.
3. Commit penghapusan jika secret hanya ada di perubahan terbaru.
4. Jika secret sudah masuk Git history, hapus dari history memakai tool history
   rewrite yang disetujui seperti `git filter-repo` atau BFG. Force-push hanya
   setelah koordinasi dengan siapa pun yang memakai repository.
5. Redeploy backend dan frontend dengan nilai secret yang sudah di-rotate.
6. Invalidate session atau token lama jika `DASHBOARD_AUTH_TOKEN`,
   `JWT_SECRET`, kredensial OAuth, atau nilai enkripsi token terekspos.
7. Jalankan ulang pemeriksaan Git dan grep di atas sebelum push lagi.

Jangan mengandalkan penghapusan file di commit berikutnya. Jika secret asli
sudah masuk remote repository, anggap secret tersebut sudah bocor.

## Checklist Sebelum Push

- [ ] `git status --short` hanya menampilkan file yang memang ingin diubah.
- [ ] Tidak ada file `.env`, JSON kredensial, token, PEM/key, atau generated JSON
  dari `backend/output/` yang staged.
- [ ] `.env.example`, `backend/.env.example`, `apps/web/.env.example`, dan
  `apps/landing/.env.example` hanya berisi placeholder.
- [ ] Env backend sesuai project: `GOOGLE_SHEET_ID`,
  `GOOGLE_SHEET_REGISTRY_JSON`, `DASHBOARD_USERNAME`, `DASHBOARD_PASSWORD`,
  `DASHBOARD_AUTH_TOKEN`, `CORS_ALLOWED_ORIGINS`, `USE_MOCK_DATA`,
  `GEMINI_API_KEY`, `GEMINI_CLASSIFICATION_MODEL`,
  `GEMINI_CLASSIFICATION_BATCH_SIZE`, serta variabel Google credential/OAuth.
- [ ] Env frontend sesuai project: `VITE_API_URL`, `VITE_API_BASE_URL`,
  `VITE_GUEST_MODE_MULTIPLIER`, dan `VITE_DASHBOARD_URL`.
- [ ] Kredensial service account hanya dipakai untuk lokal/demo internal/testing.
- [ ] Jalur onboarding production adalah OAuth per user/workspace, bukan shared
  service account credentials.
- [ ] `git diff --cached` sudah direview baris demi baris.
- [ ] Command grep secret di atas tidak menemukan nilai asli yang belum
  dijelaskan.
