# Environment Split

Tanggal: 2026-06-25

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

Backend profile loading is intentionally small in this phase. It loads `.env.local-dev` by default after the existing base env files. To load `.env.local-prod`, set `APP_ENV=local-prod` or `ENV_PROFILE=local-prod` before backend startup. Dedicated runner scripts are still out of scope for fase pertama.

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

## Safety Rules

Supabase is currently allowed to be treated as a fresh baseline, but destructive operations are still out of scope for this phase. Do not reset, seed, or migrate Supabase until the dedicated safety scripts exist and require a confirmation phrase.

Required safety direction for the next phase:

- local reset remains local PostgreSQL only.
- Supabase reset requires explicit `APP_ENV=local-prod`, `DB_TARGET=supabase`, and a confirmation phrase.
- Supabase migration requires an explicit local-prod migration command.
- Seed/backfill scripts must refuse accidental Supabase writes unless explicitly guarded.

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

## Relationship to Audit

The detailed audit is in `docs/deployment/ENVIRONMENT_SPLIT_AUDIT.md`. This file narrows the audit recommendation to the current decision: only `local-dev` and `local-prod`, with no VPS, no domain, and no staging.
