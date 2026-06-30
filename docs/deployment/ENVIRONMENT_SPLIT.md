# Environment Split

Tanggal: 2026-06-27

## Scope Fase Pertama

Dokumen ini adalah canonical note untuk fondasi environment split Omon Dashboard fase pertama. Scope saat ini hanya dua environment lokal:

- `local-dev`: development lokal dengan PostgreSQL local.
- `local-prod`: production simulation lokal dengan Supabase.

Belum ada VPS, domain, atau staging. Karena itu, semua URL masih memakai localhost dengan port berbeda.

## Perbedaan Environment

| Area | local-dev | local-prod |
| --- | --- | --- |
| Database | PostgreSQL local | Supabase |
| Backend | `localhost:8000` | `localhost:8001` |
| Frontend | `localhost:5173` | `localhost:5174` |
| `APP_ENV` | `local-dev` | `local-prod` |
| `ENV_PROFILE` | `local-dev` | `local-prod` |
| `DB_TARGET` | `postgres-local` | `supabase` |
| `IMPORT_TEMP_DIR` | `backend/output/imports/temp/local-dev` | `backend/output/imports/temp/local-prod` |
| CORS | frontend local-dev only | frontend local-prod only |
| OAuth redirect | backend port 8000 | backend port 8001 |

## Env Example Files

Backend templates:

- `.env.local-dev.example`
- `.env.local-prod.example`

Frontend templates:

- `apps/web/.env.local-dev.example`
- `apps/web/.env.local-prod.example`

Local copies are intentionally ignored:

- `.env.local-dev`
- `.env.local-prod`
- `apps/web/.env.local-dev`
- `apps/web/.env.local-prod`

Backend profile loading is intentionally small. It loads `.env.local-dev` by default after the existing base env files. To load `.env.local-prod`, set `APP_ENV=local-prod` or `ENV_PROFILE=local-prod` before backend startup. Phase 2 runner scripts do that for the operator.

## Runner Scripts

Phase 2 adds local runner scripts:

| Script | Purpose |
| --- | --- |
| `scripts/start-local-dev-backend.bat` | Load `.env.local-dev`, validate `APP_ENV=local-dev`, `DB_TARGET=postgres-local`, and port `8000`, then run backend. |
| `scripts/start-local-dev-frontend.bat` | Load `apps/web/.env.local-dev`, validate API URL `http://127.0.0.1:8000`, then run Vite on port `5173`. |
| `scripts/start-local-prod-backend.bat` | Load `.env.local-prod`, validate `APP_ENV=local-prod`, `DB_TARGET=supabase`, and port `8001`, then run backend. |
| `scripts/start-local-prod-frontend.bat` | Load `apps/web/.env.local-prod`, validate API URL `http://127.0.0.1:8001`, then run Vite on port `5174`. |
| `scripts/start-local-dev.bat` | Open local-dev backend and frontend terminals. |
| `scripts/start-local-prod.bat` | Open local-prod backend and frontend terminals. |
| `scripts/start-all-local.bat` | Open all four local environment terminals. |

Reusable helper:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local-env-runner.ps1 -Target local-dev -Service backend -ValidateOnly
```

The helper never prints secrets. Its startup banner prints only identity, target, ports, env file path, and frontend API URL values.

## How To Run

Run local-dev:

```bat
scripts\start-local-dev.bat
```

Run local-prod:

```bat
scripts\start-local-prod.bat
```

Run both environments:

```bat
scripts\start-all-local.bat
```

Before running, create the ignored local env files from examples and fill real local values. Do not commit those files.

## Cross-Connect Checks

| Environment | Frontend port | Backend port | Required frontend API env |
| --- | --- | --- | --- |
| `local-dev` | `5173` | `8000` | `VITE_API_URL=http://127.0.0.1:8000` and `VITE_API_BASE_URL=http://127.0.0.1:8000` |
| `local-prod` | `5174` | `8001` | `VITE_API_URL=http://127.0.0.1:8001` and `VITE_API_BASE_URL=http://127.0.0.1:8001` |

If the helper sees a mismatched API URL, it fails before starting Vite.

## Backend Foundation

Backend config now exposes environment identity through:

- `APP_ENV`
- `ENV_PROFILE`
- `DB_TARGET`
- `BACKEND_PORT`

It also validates the minimum identity/target pair:

- `local-dev` requires `DB_TARGET=postgres-local`.
- `local-prod` requires `DB_TARGET=supabase`.

The backend startup log prints a masked environment summary so operators can confirm which environment is running without exposing secrets.

## Temp Upload Split

`IMPORT_TEMP_DIR` separates upload temp files between local-dev and local-prod. This matters when both environments run on the same machine, because import review files should not share one temp directory.

## Database Lifecycle Phase 3

Phase 3 adds one reusable helper, `scripts/database-lifecycle-runner.ps1`, and guarded wrappers for migrate, reset, seed, and verify. The helper loads only the selected backend env file and the Python engine validates the same identity and URL again before any database connection.

| Target | Required identity | Required database |
| --- | --- | --- |
| `local-dev` | `APP_ENV=local-dev`, `ENV_PROFILE=local-dev`, `DB_TARGET=postgres-local` | Loopback host and database `finance_dashboard_local` |
| `local-prod` | `APP_ENV=local-prod`, `ENV_PROFILE=local-prod`, `DB_TARGET=supabase` | Supabase host; loopback is rejected |

Lifecycle scripts:

- `scripts/migrate-local-dev.bat`
- `scripts/migrate-local-prod.bat`
- `scripts/reset-local-dev-db.bat`
- `scripts/reset-local-prod-supabase-db.bat`
- `scripts/seed-local-dev.bat`
- `scripts/seed-local-prod.bat`
- `scripts/verify-local-dev-db.bat`
- `scripts/verify-local-prod-db.bat`

`local-prod` migration requires `MIGRATE SUPABASE OMON`. Supabase reset requires `RESET SUPABASE OMON` and recreates only schema `public`. Both operations reject missing or incorrect phrases before connecting.

The migration URL selection is explicit: use `DATABASE_MIGRATION_URL` when configured, otherwise validate and use `DATABASE_URL`. No connection string or credential is printed.

Seed upserts the configured owner and workspace using `SEED_USER_EMAIL`, `SEED_USER_NAME`, and `SEED_WORKSPACE_NAME`. It does not delete existing business data. Verify reports migration state and baseline table counts without exposing secrets.

## Real Environment Verification Phase 3.5

Connection verification is separated from lifecycle operations:

- `scripts/verify-local-dev-connection.bat`
- `scripts/verify-local-prod-connection.bat`
- `scripts/verify-all-local.bat`

The verifier uses runtime `DATABASE_URL`, validates the selected environment identity and target, starts an explicitly read-only transaction with forced rollback, executes `SELECT 1`, and reads migration metadata. Supabase connections require `DATABASE_SSL=true` and force either `sslmode=require` or `sslmode=verify-full` according to `DATABASE_SSL_REJECT_UNAUTHORIZED`.

The initial 2026-06-27 read-only verification found local-dev at 24 migrations/latest `021`, and local-prod at 21 migrations/latest `018`. Both connections and migration tables passed during that verification.

## Database Lifecycle Execution Phase 4

The approved Phase 4 execution then reset, migrated, seeded, and verified both environments. local-dev and local-prod now each have 24 migrations with latest `021_backfill_blu_transaction_search_index.sql`, one owner user, one workspace, and zero transactions, import jobs, drafts, fingerprint registry rows, and budgets. Supabase reset intentionally skipped backup because local-prod remains a disposable production simulation baseline.

## Concurrent Environment Testing Phase 5

`scripts/start-all-local.bat` starts both backend/frontend pairs, while `scripts/verify-concurrent-local.bat` verifies the live four-port topology. The verifier rejects frontend API cross-connects, backend database target mismatches, shared import temp directories, wrong CORS origins, missing migration metadata, and baseline count drift.

The safe read-only endpoint `GET /api/system/info` exposes only `APP_ENV`, `ENV_PROFILE`, `DB_TARGET`, backend port, masked database host, database name, import temp directory, and migration metadata. It never returns connection URLs or credentials.

The 2026-06-28 concurrent run passed on ports `8000`, `8001`, `5173`, and `5174`. local-dev resolved to PostgreSQL local, local-prod resolved to Supabase, frontend API mappings stayed isolated, temp directories differed, CORS passed for each matching frontend, and both fresh baselines remained unchanged.

## Environment Awareness UI Phase 6

Environment identity is now visible before and after authentication. Login renders an `EnvironmentCard`; the authenticated shell renders an `EnvironmentBadge` across every main view; Settings renders a reusable `SystemInfoPanel`.

The frontend fetches `GET /api/system/info` through one reusable helper and normalizes only allowlisted fields. local-dev uses a green identity, local-prod uses orange, and endpoint failure falls back to a gray `UNKNOWN / Offline` state derived from `VITE_API_URL` or `VITE_API_BASE_URL`. System-info failure never blocks authentication.

Allowed UI metadata is limited to environment/profile, DB target/type, safe API origin, frontend/backend port, version, masked database host, database name, import temp directory, and migration metadata. Database URLs, passwords, tokens, JWT/OAuth secrets, and credentials are discarded by the frontend normalization layer.

Local builds use `build:local-dev` or `build:local-prod`. The regular production build keeps its existing rejection of localhost API targets.

## Safety Rules

- Script availability is not approval to run Supabase operations.
- Supabase reset, migrate, and seed require explicit operator authorization for the run.
- Supabase reset and migration require their exact confirmation phrases.
- local-dev rejects Supabase/remote hosts and wrong database names.
- local-prod rejects loopback and non-Supabase hosts.
- Supabase backup is skipped only because this environment is currently a disposable production simulation baseline. Revisit this rule before real production data exists.
- Use `-ValidateOnly -UseExample` for guard tests that must not connect to a database.

## Out of Scope for Fase Pertama

- Runner `.bat` lengkap.
- Reset Supabase.
- Migration Supabase.
- Seed Supabase.
- Concurrent run full test.
- UI environment badge.
- Google OAuth flow changes.
- Blu PDF import business logic changes.
- Dashboard analytics logic changes.

## Out of Scope After Phase 3

- Executing Supabase reset, migration, or seed without a separate explicit request.
- Backing up Supabase during the current disposable-baseline phase.
- Concurrent full runtime testing of both environments.
- UI environment badge.
- Changes to Google OAuth, Blu PDF import, or dashboard analytics business logic.

## Relationship to Audit

The detailed audit is in `docs/deployment/ENVIRONMENT_SPLIT_AUDIT.md`. This file narrows the audit recommendation to the current decision: only `local-dev` and `local-prod`, with no VPS, no domain, and no staging.
