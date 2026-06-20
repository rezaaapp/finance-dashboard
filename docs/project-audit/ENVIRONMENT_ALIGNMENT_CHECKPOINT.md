# Environment Alignment Checkpoint

## Executive Summary

Status: PASS

Checkpoint ini memastikan backend runtime smoke test benar-benar membaca konfigurasi PostgreSQL local dan memakai schema hasil migration terbaru.

Hasil akhirnya:

- runtime backend sudah mengarah ke `127.0.0.1:5432/finance_dashboard_local`,
- 22 migrations terdeteksi applied,
- constraint penting migration 019 tervalidasi di database local,
- smoke test import minimal kembali PASS setelah backend direstart fresh dengan env yang align,
- tidak ada blocker tersisa untuk PR hardening Task 1–9,
- Task 10 tetap boleh ditahan dulu.

## Runtime DB Target

- `DATABASE_URL` → `postgresql://<redacted>@127.0.0.1:5432/finance_dashboard_local`
- `DATABASE_MIGRATION_URL` → `postgresql://<redacted>@127.0.0.1:5432/finance_dashboard_local`
- Source resolution runtime:
  - repo root `.env` dibaca lebih dulu,
  - `backend/.env` dibaca sesudahnya dengan mode override,
  - runtime aligned ketika kedua file menunjuk local PostgreSQL.

## Backend Restart Verification

- Backend lama dimatikan.
- Backend dijalankan ulang fresh via `backend/venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
- Listener aktif tervalidasi di `127.0.0.1:8000`.
- `GET /api/health` return `200`.

## Migration / Schema Verification

- Migration count applied: `22`
- Latest applied migration: `019_scope_import_fingerprints_by_workspace.sql`

Schema checks:

- `public.import_transaction_registry.workspace_id` ada
- primary key `import_transaction_registry` = `(workspace_id, transaction_fingerprint)`
- `public.transactions` memiliki:
  - `workspace_id`
  - `canonical_fingerprint`
  - `canonical_fingerprint_date`
- Workspace-scoped indexes / constraints yang tervalidasi:
  - `transactions_workspace_import_fingerprint_unique`
  - `transactions_workspace_canonical_fingerprint_unique`
  - `transactions_workspace_transaction_date_idx`
  - `transactions_workspace_transaction_date_desc_idx`

## Minimal Smoke Test

Endpoint smoke yang dijalankan:

- `GET /api/health`
- `POST /api/auth/login`
- `GET /api/workspaces`
- `GET /api/dashboard/view-model`
- `GET /api/import/history?limit=20&offset=0`
- `GET /api/import/category-options`
- `POST /api/import/upload` dengan `backend/tests/fixtures/blu_statement_june_real.pdf`
- `GET /api/import/review/{job_id}?limit=20&offset=0`
- `POST /api/import/review/{job_id}/reject`

Observed result:

| Check | Result |
|---|---|
| Health | PASS (`200`) |
| Login valid | PASS (`200`) |
| Workspaces | PASS (`200`) |
| Dashboard view-model | PASS (`200`) |
| Import history page 1 | PASS (`200`) |
| Import category options | PASS (`200`) |
| Blu PDF upload | PASS (`200`) |
| Import review load | PASS (`200`) |
| Reject local | PASS (`200`) |

Latency snapshot:

- `/api/dashboard/view-model` ≈ `68 ms`
- `/api/import/history?limit=20&offset=0` ≈ `16 ms`
- `/api/import/category-options` ≈ `10 ms`
- `/api/import/upload` ≈ `775 ms`
- `/api/import/review/{job_id}` ≈ `20 ms`

## Import Upload Result

Upload fixture PDF valid berhasil membuat import job baru di workspace local:

- provider: `blu`
- status awal: `review`
- `transactions_found`: `29`
- `new_transactions`: `29`

Ini menutup blocker lama yang sebelumnya terlihat sebagai upload/review failure ketika runtime masih belum align dengan local PostgreSQL.

## Root Cause of Prior Failure

Blokir sebelumnya bukan berasal dari migration 019 local PostgreSQL, melainkan dari runtime backend yang aktif saat smoke test lama belum memakai env/schema local yang benar.

Setelah runtime direstart dengan env aligned:

- upload PASS,
- review PASS,
- schema checks sesuai ekspektasi code Task 1–9.

## Validation

- Backend unittest: PASS
  - `python -m unittest discover -s backend/tests -t .`
- Web lint: PASS
  - `npm --prefix apps/web run lint`
- Landing lint: PASS
  - `npm --prefix apps/landing run lint`
- API smoke import minimal: PASS

## Remaining Risk

Masih ada risiko non-blocking berikut:

1. Google OAuth / Google Sheet connect-reconnect belum diuji end-to-end penuh pada runtime aligned ini.
2. Approve + spreadsheet delivery tidak diulang pada checkpoint ini untuk menghindari side effect eksternal yang tidak perlu.
3. Browser-level logout / UX visual belum diuji otomatis pada checkpoint ini.

## Final Recommendation

- Aman PR ke `main`? **YES**
- Task 10 perlu sekarang? **NO, tetap hold boleh**

Alasan teknis:

- blocker environment mismatch sudah tertutup,
- schema migration local dan runtime smoke sudah selaras,
- flow hardening inti Task 1–9 kembali lolos pada backend runtime yang benar.
