# Environment Split Audit - Omon Dashboard

Tanggal audit: 2026-06-25

## Executive Summary

Audit ini menemukan bahwa konfigurasi environment saat ini masih memakai model campuran: root `.env` dibaca lebih dulu, lalu `backend/.env` menimpa nilai backend; frontend dashboard membaca `.env` di `apps/web` melalui Vite. Model ini cukup untuk local-only development, tetapi belum aman untuk skenario baru ketika DEV memakai PostgreSQL local dan PROD / production simulation memakai Supabase sambil keduanya berjalan bersamaan di mesin lokal.

Area yang paling wajib dipisahkan adalah koneksi database, migration database, port backend/frontend, URL API frontend, CORS, OAuth redirect URI, JWT/auth secret, token encryption secret/key, dan seed/reset workflow. Risiko tertinggi ada pada migration runner dan script Node database yang memakai `DATABASE_URL` aktif tanpa konsep target environment eksplisit. Script reset local sudah memiliki guard kuat terhadap Supabase, tetapi migration dan seed/backfill belum punya guard yang sama.

Frontend memiliki guard production build melalui `apps/web/scripts/validate-env.mjs`, tetapi runtime development masih bisa salah connect bila `VITE_API_URL` mengarah ke backend environment lain. Backend juga masih memiliki beberapa default localhost yang aman untuk DEV, tetapi unsafe jika berjalan sebagai production simulation tanpa env eksplisit.

Rekomendasi utama tahap berikutnya adalah membuat profil env terpisah: `.env.dev.local` untuk backend local PostgreSQL, `.env.prod.supabase` untuk backend Supabase simulation, dan file Vite terpisah seperti `apps/web/.env.dev.local` serta `apps/web/.env.prod.supabase`. Script start/migrate/seed harus menerima target eksplisit dan menolak operasi berbahaya jika target tidak sesuai.

## Current Environment Variables

| Env | Area | Current usage | Split recommendation |
| --- | --- | --- | --- |
| `DATABASE_URL` | Database runtime | FastAPI, migration fallback, Node DB scripts | Wajib dipisah DEV vs PROD. Berbahaya jika tertukar. |
| `SUPABASE_DATABASE_URL` | Supabase fallback | Backend Python fallback jika `DATABASE_URL` kosong | Wajib dipisah/ditata ulang. Jangan aktif di DEV local reset. |
| `DATABASE_MIGRATION_URL` | Migration DB | Python migration runner via `get_migration_database_url()` | Wajib dipisah DEV vs PROD. Berbahaya jika tertukar. |
| `SUPABASE_MIGRATION_DATABASE_URL` | Supabase migration fallback | Backend Python fallback jika `DATABASE_MIGRATION_URL` kosong | Wajib dipisah/ditata ulang. |
| `DATABASE_SSL` | Database SSL | Python psycopg and Node pg config | DEV local biasanya `false`, Supabase `true`. Wajib dipisah. |
| `DATABASE_SSL_REJECT_UNAUTHORIZED` | Database SSL verification | Python psycopg and Node pg config | DEV dapat longgar, PROD sebaiknya `true`. Wajib dipisah. |
| `DATABASE_POOL_MAX` | DB pool | Python and Node pool size | Boleh berbeda; production simulation perlu tuning sendiri. |
| `DATABASE_IDLE_TIMEOUT_MS` | DB pool | Python and Node pool timeout | Boleh sama, tetapi perlu eksplisit di kedua env. |
| `DATABASE_CONNECTION_TIMEOUT_MS` | DB pool | Python and Node pool timeout | Boleh sama, tetapi perlu eksplisit di kedua env. |
| `PORT` | Backend port | Dockerfile and `start:replit` only | Wajib dipisah jika DEV dan PROD simulation berjalan bersamaan. Backend code tidak membaca langsung. |
| `VITE_API_URL` | Frontend API base URL | Dashboard API resolver and build validator | Wajib dipisah. Frontend DEV harus menunjuk DEV backend; PROD simulation harus menunjuk PROD backend. |
| `VITE_API_BASE_URL` | Frontend API base URL alias | Dashboard API resolver and build validator | Wajib dipisah dan dijaga tetap sama dengan `VITE_API_URL`. |
| `VITE_API_MODE` | Frontend API routing | Dashboard same-origin mode | Boleh sama jika tidak dipakai. Jangan aktif kecuali single-app deployment. |
| `VITE_GUEST_MODE_MULTIPLIER` | Frontend feature/demo | Privacy multiplier | Boleh sama; public client value. |
| `DASHBOARD_USERNAME` | Auth | Backend local login config | Wajib dipisah. Jangan gunakan akun/credential prod di DEV. |
| `DASHBOARD_PASSWORD` | Auth secret | Backend local login config | Wajib dipisah. Secret. |
| `DASHBOARD_AUTH_TOKEN` | Auth secret / JWT fallback | Required by settings, fallback for `JWT_SECRET` and token encryption | Wajib dipisah. Berbahaya jika sama antar env. |
| `JWT_SECRET` | Auth secret | JWT encode/decode and OAuth state | Wajib dipisah. Berbahaya jika tertukar/sama. |
| `JWT_EXPIRES_IN_MINUTES` | Auth policy | JWT lifetime | Bisa berbeda; PROD sebaiknya lebih ketat dari default 7 hari. |
| `TOKEN_ENCRYPTION_KEY` | OAuth token encryption | Google token tests and expected production config | Wajib dipisah. Secret. |
| `TOKEN_ENCRYPTION_SECRET` | OAuth token encryption fallback | Required by settings | Wajib dipisah. Secret. |
| `SUPER_ADMIN_EMAILS` | Auth/RBAC | Backend settings and tests | Wajib dipisah. Berbahaya jika email dev menjadi super admin prod. |
| `CORS_ALLOWED_ORIGINS` | CORS | FastAPI CORS middleware | Wajib dipisah. Harus exact origin per frontend env. |
| `FRONTEND_URL` | OAuth redirect UX | Backend settings | Wajib dipisah; currently defaults to `http://127.0.0.1:5173`. |
| `FRONTEND_AUTH_REDIRECT_URL` | Auth redirect UX | Backend settings/examples | Wajib dipisah jika flow legacy digunakan. |
| `GOOGLE_AUTH_MODE` | Google integration mode | Documented/example only in audited code path | Wajib dipisah conceptually: DEV may service-account, PROD should OAuth. |
| `GOOGLE_OAUTH_CLIENT_ID` | Google OAuth | Backend settings and tests | Wajib dipisah if using separate OAuth clients. |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google OAuth secret | Backend settings and tests | Wajib dipisah. Secret. |
| `GOOGLE_OAUTH_REDIRECT_URI` | Google OAuth callback | Backend settings with localhost default | Wajib dipisah. Must match Google Console exactly. |
| `GOOGLE_LOGIN_REDIRECT_URI` | Legacy Google login callback | Backend settings with localhost default | Wajib dipisah if enabled. |
| `GOOGLE_OAUTH_SCOPES` | Google OAuth scopes | Backend settings | Boleh sama; keep minimal. Code default is broader than examples. |
| `GOOGLE_SHEET_ID` | Google Sheets | Backend settings and Python data script | Wajib dipisah if DEV/PROD use different sheets. |
| `GOOGLE_SPREADSHEET_ID` | Legacy sheet id | Python/Node data scripts fallback | Wajib dipisah or deprecated. |
| `GOOGLE_SHEET_REGISTRY_JSON` | Google Sheets registry | Backend settings and Node classification script | Wajib dipisah. May contain real sheet IDs. |
| `MAX_GOOGLE_SHEET_SOURCES` | Google Sheets limit | Backend settings | Boleh sama, but explicit. |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Google service account secret | Python and Node data processing | DEV-only unless intentionally used. Secret, do not commit. |
| `GOOGLE_SERVICE_ACCOUNT_JSON_BASE64` | Google service account secret | Python and Node data processing | DEV-only unless intentionally used. Secret, do not commit. |
| `GOOGLE_APPLICATION_CREDENTIALS` | Google credential path | Python and Node data processing | DEV-only local path. Wajib dipisah. |
| `USE_MOCK_DATA` | Feature flag | Backend settings | Boleh sama, but must be `false` in PROD simulation unless explicitly testing. |
| `AI_CLASSIFICATION_ENABLED` | Feature flag | Backend settings | Boleh same default false; explicit in both env. |
| `AI_PROVIDER` | Feature flag | Backend settings | Boleh same default `rule_based`. |
| `AI_MODEL` | Feature flag | Backend settings | Boleh same default `none`. |
| `AI_ONLY_LOW_CONFIDENCE` | Feature flag | Backend settings | Boleh sama. |
| `AI_CONFIDENCE_THRESHOLD` | Feature flag | Backend settings | Boleh sama. |
| `AI_MAX_TRANSACTIONS_PER_RUN` | Feature flag | Backend settings | Boleh sama. |
| `GEMINI_API_KEY` | Legacy AI secret | Node classification script | Wajib dipisah if script still used. Secret. |
| `GEMINI_CLASSIFICATION_MODEL` | Legacy AI | Node classification script/example | Boleh sama. |
| `GEMINI_CLASSIFICATION_BATCH_SIZE` | Legacy AI | Node classification script/example | Boleh sama. |
| `INSIGHT_*` | Insight defaults | Backend settings | Boleh sama; business defaults. |
| `SEED_USER_EMAIL` | Seed/reset | Node seed script and examples | Wajib dipisah. Can create wrong users/workspaces. |
| `SEED_USER_NAME` | Seed/reset | Node seed script and examples | Wajib dipisah. |
| `SEED_WORKSPACE_NAME` | Seed/reset | Node seed script and examples | Wajib dipisah. |
| `PYTHON_BIN` | Script runtime | Node monthly allocation route | Boleh sama or machine-local. |
| Upload/temp storage env | Upload/temp | Tidak ada env saat ini; path hardcoded to `backend/output/imports/temp` | Perlu ditambahkan: `IMPORT_TEMP_DIR`, optional `IMPORT_TEMP_TTL_HOURS`, `MAX_IMPORT_UPLOAD_MB`. |
| Logging env | Logging | Tidak ditemukan env logging eksplisit | Perlu ditambahkan: `LOG_LEVEL`, optional `ENV_NAME`. |
| Environment identity | Safety guard | Tidak ada env eksplisit | Perlu ditambahkan: `APP_ENV`, `ENV_PROFILE`, `DB_TARGET`, `ALLOW_PROD_DB_MUTATIONS`. |

## Current Env Usage by File

| File | Env/config read | Notes |
| --- | --- | --- |
| `backend/app/config.py` | Loads root `.env`, then `backend/.env` with override. Reads DB, auth/JWT, Google OAuth, CORS, feature flags, insight thresholds, sheet registry. | Central backend settings. Has localhost defaults for OAuth and frontend redirect. |
| `backend/app/database.py` | Uses DB settings and migration fallback. | `get_migration_database_url()` returns `DATABASE_MIGRATION_URL` or `DATABASE_URL`. No environment target guard. |
| `backend/scripts/run_migrations.py` | Indirectly uses `DATABASE_MIGRATION_URL` or `DATABASE_URL`. | Can migrate whichever DB is active. Needs target-specific command/guard. |
| `backend/scripts/reset_local_database.py` | Loads root `.env`, then `backend/.env`. Reads `DATABASE_URL`, `DATABASE_MIGRATION_URL`, `SUPABASE_DATABASE_URL`, `SUPABASE_MIGRATION_DATABASE_URL`. | Strong local guard exists: only loopback host and database `finance_dashboard_local`, rejects Supabase host and any configured bad DB URL. |
| `backend/node/db.ts` | Loads root `.env`, then `backend/.env`. Reads `DATABASE_URL`, `DATABASE_SSL`, SSL reject flag, pool settings. | Does not read `DATABASE_MIGRATION_URL` or Supabase aliases. No target guard. |
| `backend/node/seedInitialWorkspace.ts` | Reads `SEED_USER_EMAIL`, `SEED_USER_NAME`, `SEED_WORKSPACE_NAME`; uses Node DB pool. | Can seed whichever DB `DATABASE_URL` points to. Needs DEV/PROD target guard. |
| `backend/node/backfillUserWorkspaces.ts` | Uses Node DB pool. | Mutates whichever DB `DATABASE_URL` points to. Needs target guard. |
| `backend/node/syncAndClassifyFinancialData.ts` | Reads Google service account env, `GOOGLE_APPLICATION_CREDENTIALS`, `GEMINI_API_KEY`, model config. | Legacy external-service path. Secrets and sheet access must be isolated by env. |
| `backend/node/runSyncAndClassifyFinancialData.ts` | Loads root/backend env, reads sheet registry, `GOOGLE_SPREADSHEET_ID`, Gemini config, writes backend output JSON. | Output can contain private financial classification data; security check blocks staged backend output JSON. |
| `backend/scripts/data_processing.py` | Loads `.env` files, reads Google service account env, `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_SPREADSHEET_ID`, `GOOGLE_SHEET_ID`. | DEV/PROD sheet credentials need separation. |
| `backend/app/main.py` | Uses `settings.CORS_ALLOWED_ORIGINS`; serves built frontend if present. | CORS defaults allow only local dashboard origins; methods/headers wildcard. |
| `backend/app/imports/utils/temp_storage.py` | No env; uses `backend/output/imports/temp`; TTL is hardcoded 24h. | Needs env split if two backend instances run together, otherwise temp paths overlap. |
| `apps/web/src/api/config.js` | Reads `import.meta.env.VITE_API_MODE`, `VITE_API_URL`, `VITE_API_BASE_URL`, and `PROD`. | Has hardcoded fallback `http://127.0.0.1:8000/api/dashboard` for non-production builds. |
| `apps/web/src/utils/privacy.js` | Reads `VITE_GUEST_MODE_MULTIPLIER`. | Public frontend value, low risk. |
| `apps/web/scripts/validate-env.mjs` | Reads process env and local `apps/web/.env` for `VITE_API_URL`, `VITE_API_BASE_URL`, `VITE_API_MODE`. | Production build guard rejects localhost, missing, and invalid URL. |
| `backend/Dockerfile` | Uses shell `${PORT:-8000}` in CMD. | Good for Render/Replit style runtime, but local concurrent runs need explicit ports. |
| `package.json` | Scripts use default commands; `start:replit` uses `${PORT:-8000}`. | Current scripts do not select env file profiles. |
| `render.yaml` | Declares backend production env keys. | Does not include Supabase alias keys, all pool timeouts, Google auth mode, insight defaults, or seed vars. `DATABASE_URL`/migration/CORS/OAuth are provider env. |
| `scripts/security-check.ps1` | Checks staged files for `.env*` except `.env.example`, credential JSON, PEM/key, token JSON, backend/output JSON. | Useful guard; commit should include only audit doc. |
| `backend/tests/*` | Several tests set safe auth defaults via `os.environ.setdefault`; reset tests validate local reset guard. | Test env defaults are safe dummy values. |
| `.env.example`, `backend/.env.example`, `apps/web/.env.example` | Template values for local env. | Templates contain localhost defaults and placeholders. Fine for DEV, dangerous if copied blindly to PROD simulation. |
| `README.md`, `docs/ENVIRONMENT.md`, `docs/GOOGLE_OAUTH.md`, `docs/WEEK7_*`, `docs/PROJECT_OPERATIONS_GUIDE.md` | Setup docs mention localhost, Render/Vercel/Supabase, OAuth, CORS, API URLs. | Existing docs are useful but mixed across local/staging histories; new split docs should be canonical. |

## Required DEV vs PROD Split

### DEV: `.env.dev.local`

Recommended backend DEV profile:

```dotenv
APP_ENV=development
ENV_PROFILE=dev-local
DB_TARGET=local-postgres
PORT=8000
DATABASE_URL=postgresql://postgres:<local_password>@127.0.0.1:5432/finance_dashboard_local
DATABASE_MIGRATION_URL=postgresql://postgres:<local_password>@127.0.0.1:5432/finance_dashboard_local
DATABASE_SSL=false
DATABASE_SSL_REJECT_UNAUTHORIZED=false
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
FRONTEND_URL=http://127.0.0.1:5173
FRONTEND_AUTH_REDIRECT_URL=http://127.0.0.1:5173/auth/google/callback
GOOGLE_OAUTH_REDIRECT_URI=http://127.0.0.1:8000/api/google/oauth/callback
GOOGLE_LOGIN_REDIRECT_URI=http://127.0.0.1:8000/auth/google/callback
JWT_SECRET=<dev-only-secret>
TOKEN_ENCRYPTION_SECRET=<dev-only-secret>
TOKEN_ENCRYPTION_KEY=<dev-only-fernet-key>
SUPER_ADMIN_EMAILS=<dev-admin-email>
SEED_USER_EMAIL=<dev-admin-email>
SEED_USER_NAME=Local Admin
SEED_WORKSPACE_NAME=Local Household
IMPORT_TEMP_DIR=backend/output/imports/temp/dev
LOG_LEVEL=debug
```

Recommended frontend DEV profile:

```dotenv
VITE_API_URL=http://127.0.0.1:8000
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_GUEST_MODE_MULTIPLIER=0.75
```

### PROD Simulation: `.env.prod.supabase`

Recommended backend production simulation profile:

```dotenv
APP_ENV=production-simulation
ENV_PROFILE=prod-supabase
DB_TARGET=supabase
PORT=8001
DATABASE_URL=<supabase-runtime-or-pooled-connection-string>
DATABASE_MIGRATION_URL=<supabase-direct-or-session-connection-string>
DATABASE_SSL=true
DATABASE_SSL_REJECT_UNAUTHORIZED=true
CORS_ALLOWED_ORIGINS=http://localhost:5174,http://127.0.0.1:5174
FRONTEND_URL=http://127.0.0.1:5174
FRONTEND_AUTH_REDIRECT_URL=http://127.0.0.1:5174/auth/google/callback
GOOGLE_OAUTH_REDIRECT_URI=http://127.0.0.1:8001/api/google/oauth/callback
GOOGLE_LOGIN_REDIRECT_URI=http://127.0.0.1:8001/auth/google/callback
GOOGLE_OAUTH_CLIENT_ID=<prod-simulation-oauth-client-id>
GOOGLE_OAUTH_CLIENT_SECRET=<prod-simulation-oauth-secret>
JWT_SECRET=<prod-simulation-secret>
TOKEN_ENCRYPTION_SECRET=<prod-simulation-secret>
TOKEN_ENCRYPTION_KEY=<prod-simulation-fernet-key>
SUPER_ADMIN_EMAILS=<prod-simulation-admin-email>
IMPORT_TEMP_DIR=backend/output/imports/temp/prod-supabase
LOG_LEVEL=info
```

Recommended frontend production simulation profile:

```dotenv
VITE_API_URL=http://127.0.0.1:8001
VITE_API_BASE_URL=http://127.0.0.1:8001
VITE_GUEST_MODE_MULTIPLIER=0.75
```

### Env That May Stay The Same

These may stay equal across DEV and PROD simulation if business policy allows: `GOOGLE_OAUTH_SCOPES`, `MAX_GOOGLE_SHEET_SOURCES`, `AI_CLASSIFICATION_ENABLED=false`, `AI_PROVIDER=rule_based`, `AI_MODEL=none`, `AI_ONLY_LOW_CONFIDENCE`, `AI_CONFIDENCE_THRESHOLD`, `AI_MAX_TRANSACTIONS_PER_RUN`, `INSIGHT_*`, and `VITE_GUEST_MODE_MULTIPLIER`.

### Env That Must Not Be Shared

Never share these between DEV and PROD simulation: `DATABASE_URL`, `DATABASE_MIGRATION_URL`, Supabase alias URLs, `JWT_SECRET`, `DASHBOARD_AUTH_TOKEN`, `DASHBOARD_PASSWORD`, `TOKEN_ENCRYPTION_SECRET`, `TOKEN_ENCRYPTION_KEY`, `GOOGLE_OAUTH_CLIENT_SECRET`, service-account JSON/base64/path, `SUPER_ADMIN_EMAILS`, seed user/workspace env, `CORS_ALLOWED_ORIGINS`, `FRONTEND_URL`, OAuth redirect URIs, and frontend API URLs.

## Dangerous / High Risk Config

| Risk | Severity | Evidence | Recommendation |
| --- | --- | --- | --- |
| Migration can run against Supabase accidentally | High | `backend/scripts/run_migrations.py` uses `get_migration_connection()`, which uses `DATABASE_MIGRATION_URL` or `DATABASE_URL`. | Add target-specific migration scripts and guard by `APP_ENV`/`DB_TARGET`; require confirmation for Supabase. |
| Node DB scripts mutate whichever `DATABASE_URL` is active | High | `backend/node/db.ts` only reads `DATABASE_URL`; seed/backfill/classify scripts use that pool. | Add env-profile loading and DB target guard before seed/backfill/classify mutation scripts. |
| Frontend can connect to wrong backend in local concurrent mode | High | `apps/web/src/api/config.js` reads `VITE_API_URL` or falls back to `127.0.0.1:8000` for non-prod. | Use separate Vite env files and scripts for `dev:web:local` and `dev:web:prod-sim` on separate ports. |
| OAuth redirect URI defaults are hardcoded localhost | Medium/High | `backend/app/config.py` defaults Google callback to `http://127.0.0.1:8000/...`. | Require explicit redirect URI outside `APP_ENV=development`; use port 8001 for prod simulation. |
| CORS is env-driven but wildcard methods/headers are enabled | Medium | `backend/app/main.py` uses exact origins but `allow_methods=["*"]`, `allow_headers=["*"]`. | Keep exact origins per env; later consider narrowing methods/headers for production. |
| `GOOGLE_OAUTH_SCOPES` default in code is broader than examples | Medium | Code default includes `https://www.googleapis.com/auth/spreadsheets`; examples use `.readonly`. | Make scopes explicit in both env profiles; prefer readonly unless write access is required. |
| Backend temp upload directory is hardcoded | Medium | `TEMP_IMPORT_DIR = BACKEND_ROOT / "output" / "imports" / "temp"`. | Add `IMPORT_TEMP_DIR` so concurrent DEV/PROD simulation instances do not share temp files. |
| Production-like backend may start with local defaults | Medium | `FRONTEND_URL`, OAuth callbacks, CORS defaults, SSL default are embedded in settings. | Add `APP_ENV` guard that refuses production simulation if critical env are missing or localhost mismatch. |
| Secrets may exist in local workspace | Medium | `rg --files` found `.env`, `.env_backup`, `backend/.env`, `backend/.env_backup`, `backend/.env_dev`, `apps/web/.env`, and `apps/web/.env.development.local`. Values were not opened. | Keep ignored; security check blocks staging `.env*` except `.env.example`. Consider deleting/rotating backups manually if obsolete. |
| Render config may be incomplete for current split | Medium | `render.yaml` declares main env but not all profile/guard env recommended here. | Update after audit once split strategy is approved. |

## Recommended Env Files

Do not edit existing `.env` files during this audit. For the implementation phase, use new explicit profiles:

| File | Purpose | Notes |
| --- | --- | --- |
| `.env.dev.local` | Root/shared local PostgreSQL DEV backend profile | Should be gitignored. |
| `.env.prod.supabase` | Root/shared Supabase production simulation backend profile | Should be gitignored. |
| `backend/.env.dev.local` | Optional backend-specific DEV override | Only if backend values should not live at root. |
| `backend/.env.prod.supabase` | Optional backend-specific Supabase override | Only if backend values should not live at root. |
| `apps/web/.env.dev.local` | Dashboard DEV frontend profile | Points to `http://127.0.0.1:8000`. |
| `apps/web/.env.prod.supabase` | Dashboard PROD simulation frontend profile | Points to `http://127.0.0.1:8001` or chosen prod-sim backend port. |
| `docs/deployment/ENVIRONMENT_SPLIT.md` | Future canonical setup doc | Should supersede scattered Week 7 notes for local concurrent usage. |

Recommended env naming additions:

| New env | Why |
| --- | --- |
| `APP_ENV` | Runtime mode: development, production-simulation, production. |
| `ENV_PROFILE` | Human-readable profile loaded by scripts. |
| `DB_TARGET` | Guard value: `local-postgres` or `supabase`. |
| `ALLOW_PROD_DB_MUTATIONS` | Explicit opt-in for Supabase seed/backfill/reset-like operations. |
| `BACKEND_PORT` or standardize on `PORT` | Concurrent local process clarity. |
| `FRONTEND_PORT` | Concurrent local frontend clarity. |
| `IMPORT_TEMP_DIR` | Separate temp files per backend environment. |
| `IMPORT_TEMP_TTL_HOURS` | Configurable cleanup policy. |
| `MAX_IMPORT_UPLOAD_MB` | Configurable upload limit. |
| `LOG_LEVEL` | Environment-specific logging. |

## Recommended Scripts

Create or update these after audit:

| Script | Purpose | Required guard |
| --- | --- | --- |
| `dev:backend:local` | Start backend against local PostgreSQL on port 8000. | Load `.env.dev.local`, assert `DB_TARGET=local-postgres`. |
| `dev:backend:prod-sim` | Start backend against Supabase on port 8001. | Load `.env.prod.supabase`, assert `DB_TARGET=supabase`. |
| `dev:web:local` | Start dashboard for DEV backend on port 5173. | Load `apps/web/.env.dev.local`. |
| `dev:web:prod-sim` | Start dashboard for Supabase simulation backend on port 5174. | Load `apps/web/.env.prod.supabase`. |
| `db:migrate:local` | Run migrations against local PostgreSQL. | Assert loopback host and local DB name. |
| `db:migrate:prod-sim` | Run migrations against Supabase simulation. | Require `DB_TARGET=supabase` and explicit confirmation. |
| `db:reset:local` | Keep/reset local DB only. | Existing script is guarded; wire to `.env.dev.local`. |
| `db:seed:local` | Seed local DB. | Assert local host/db. |
| `db:seed:prod-sim` | Seed Supabase simulation if needed. | Require `ALLOW_PROD_DB_MUTATIONS=true` and confirmation. |
| `env:check:local` | Validate local env profile. | Fail on Supabase host, missing local ports, production OAuth URLs. |
| `env:check:prod-sim` | Validate Supabase env profile. | Fail on localhost DB, missing Supabase SSL, missing OAuth/CORS/API split. |

## Implementation Plan After Audit

1. Add env profile loader support for backend scripts without changing the default behavior unexpectedly.
2. Introduce `APP_ENV`, `ENV_PROFILE`, and `DB_TARGET` validation in backend startup and database mutation scripts.
3. Add separate backend start scripts for local PostgreSQL and Supabase production simulation.
4. Add separate frontend dev scripts and Vite env files for local dashboard and prod-sim dashboard.
5. Add migration guards so local migrations cannot hit Supabase and Supabase migrations require explicit target confirmation.
6. Add seed/backfill guards with the same target rules.
7. Add env-configurable import temp storage path and keep default backward compatible.
8. Update docs with one canonical concurrent local runbook.
9. Run safety checks: env validation, migration dry-run/metadata query, frontend build validator, and security check.

## Acceptance Criteria for Next Step

- `.env.dev.local` and `.env.prod.supabase` are documented and generated only as ignored local files.
- DEV backend uses local PostgreSQL and PROD simulation backend uses Supabase with distinct ports.
- DEV dashboard and PROD simulation dashboard can run at the same time and call different backend ports.
- Migration scripts require explicit target and cannot accidentally apply local changes to Supabase.
- Reset script remains local-only and refuses Supabase even when Supabase env exists.
- Seed/backfill scripts have DB target guards.
- Google OAuth redirect URIs are explicit per backend port/environment and match Google Console entries.
- CORS origins are exact and separated per frontend port/environment.
- Frontend production build still rejects localhost unless intentionally running local production simulation through a dedicated script.
- No runtime code defaults allow production simulation to boot with missing secrets, localhost OAuth callbacks, or wrong CORS.
- No `.env`, credential JSON, private key, token file, or generated financial output is committed.

## Grep / Ripgrep Evidence Summary

Commands run during audit:

```powershell
rg -n "process\.env|import\.meta\.env|VITE_|DATABASE_URL|SUPABASE|JWT|GOOGLE|CORS|PORT|BASE_URL|API_URL|UPLOAD|TEMP|LOG|FEATURE|SEED|RESET|dotenv|\.env" backend apps/web scripts docs README* package.json pnpm-workspace.yaml docker-compose* Dockerfile* replit* .replit
rg --files -g "*.env*" -g "*docker*" -g "*Docker*" -g "*.replit" -g "replit*" -g "README*" -g "*config*" -g "*migration*" -g "*migrate*" -g "*test*"
rg -n "process\.env|dotenv|DATABASE_URL|SUPABASE|SEED_|RESET|GOOGLE|JWT|TOKEN|CORS|PORT|VITE_|FRONTEND|USE_MOCK|AI_|INSIGHT_|UPLOAD|TEMP|LOG|FEATURE" backend/node backend/scripts backend/tests scripts apps/web/scripts apps/web/vite.config.js apps/landing/vite.config.js backend/Dockerfile .replit render.yaml
rg -n "localhost|127\.0\.0\.1|0\.0\.0\.0|onrender|vercel|supabase|CORS_ALLOWED_ORIGINS|GOOGLE_OAUTH_REDIRECT_URI|GOOGLE_LOGIN_REDIRECT_URI|VITE_API_URL|DATABASE_URL|PORT" README.md docs apps/web/README.md backend/.env.example apps/web/.env.example .env.example render.yaml backend/Dockerfile package.json
```

Key evidence:

- `backend/app/config.py` loads `REPO_ROOT/.env` first and `backend/.env` second with override, then reads the backend env set listed above.
- `backend/app/database.py` chooses migration URL as `DATABASE_MIGRATION_URL or DATABASE_URL`.
- `backend/scripts/run_migrations.py` has no DEV/PROD target guard; it applies every pending SQL file to the active migration connection.
- `backend/scripts/reset_local_database.py` is local-only guarded: accepts only loopback host and database `finance_dashboard_local`, rejects Supabase hosts, and validates every configured DB URL key.
- `backend/node/db.ts` reads only `DATABASE_URL` for Node database scripts and does not use migration URL or target guard.
- `apps/web/src/api/config.js` resolves `VITE_API_URL || VITE_API_BASE_URL`, supports `VITE_API_MODE=same-origin`, and falls back to `http://127.0.0.1:8000/api/dashboard` outside production.
- `apps/web/scripts/validate-env.mjs` rejects production API URLs containing localhost, `127.0.0.1`, or `0.0.0.0`.
- `backend/app/main.py` uses exact `CORS_ALLOWED_ORIGINS`, but allows all methods and headers.
- `backend/app/imports/utils/temp_storage.py` hardcodes `backend/output/imports/temp`; no env exists for temp/upload storage.
- `backend/Dockerfile` and `package.json` `start:replit` bind `uvicorn` to `${PORT:-8000}`.
- Local secret-like files are present by filename (`.env`, `.env_backup`, `backend/.env`, `backend/.env_backup`, `backend/.env_dev`, `apps/web/.env`, and `apps/web/.env.development.local`), but this audit did not open or copy their values.
- `scripts/security-check.ps1` blocks staged `.env*` files except `.env.example`, credential JSON/token/private key files, and `backend/output/*.json`.
