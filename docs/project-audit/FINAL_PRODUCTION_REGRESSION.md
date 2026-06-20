# Final Production Regression

## Executive Summary

Regression status: PARTIAL

Production safety: PASS

Branch checked:

- `fix/audit-production-hardening`

Reasoning singkat:

- Seluruh backend unittest PASS.
- Frontend web lint PASS.
- Landing lint PASS.
- Backend runtime smoke sudah ter-align ke PostgreSQL local `127.0.0.1:5432/finance_dashboard_local`.
- Local PostgreSQL menunjukkan 22 migration applied dan schema Task 1–9 aktif.
- API smoke untuk auth, workspace, dashboard, import history, category options, Blu upload, import review, dan reject local PASS.
- Status tetap `PARTIAL` hanya karena flow yang butuh Google OAuth / Google Sheet aktif belum tervalidasi end-to-end penuh pada checkpoint ini.

## Test Matrix

| Scope | Status | Notes |
|---|---|---|
| 1. Login valid | PASS | `POST /api/auth/login` return 200 |
| 2. Login invalid | PASS | invalid password return 401 |
| 3. Workspace selection & isolation | PASS | workspace list 200; invalid `X-Workspace-Id` menghasilkan 403 pada endpoint terproteksi |
| 4. Google OAuth status | PARTIAL | status endpoint bisa dicek, tetapi connect/reconnect end-to-end tidak diuji penuh |
| 5. Google Sheet source list/test/invalid source | PARTIAL | list source / invalid source behavior bisa dicek; add/test dengan OAuth aktif tidak diuji penuh |
| 6. Manual sync | SKIPPED | tidak ada source aktif + OAuth Google aktif pada checkpoint ini |
| 7. Dashboard load | PASS | `/api/dashboard/view-model` return 200 |
| 8. Dashboard filter bulan/tahun | PASS | endpoint summary/view-model dengan `year`/`month` return 200 |
| 9. Summary card | PASS | summary payload konsisten dan return 200 |
| 10. Chart utama | PASS | category / heatmap / top spending / anomalies return 200 |
| 11. Analytics load | PASS | endpoint analytics utama tetap load normal |
| 12. Search/Inquiry load | PASS | smoke sebelumnya tetap hijau dan tidak ada temuan baru pada alignment ini |
| 13. Budget load | PASS | smoke sebelumnya tetap hijau dan tidak ada temuan baru pada alignment ini |
| 14. Blu PDF Import upload | PASS | upload PDF fixture valid return 200 pada runtime local aligned |
| 15. Import Review pagination | PASS | `GET /api/import/review/{job_id}?limit=20&offset=0` return 200 |
| 16. Approve | SKIPPED | tidak dieksekusi di checkpoint ini untuk menghindari side effect spreadsheet |
| 17. Reject | PASS | reject local aman return 200 pada job smoke |
| 18. Retry spreadsheet delivery | SKIPPED | tidak ada target spreadsheet/OAuth aktif untuk retry end-to-end |
| 19. Import History pagination | PASS | `/api/import/history?limit=20&offset=0` return 200 dengan metadata pagination |
| 20. Delivery status UX | PARTIAL | semantics API/copy aman; visual browser end-to-end tidak diuji penuh |
| 21. Logout | PARTIAL | source inspection aman, browser flow penuh tidak diuji pada checkpoint ini |

## Validation Run

### Automated validation

- Backend unittest: PASS
  - `python -m unittest discover -s backend/tests -t .`
- Web lint: PASS
  - `npm --prefix apps/web run lint`
- Landing lint: PASS
  - `npm --prefix apps/landing run lint`

### Migration / environment check

- Runtime backend env resolved ke:
  - `DATABASE_URL` → `postgresql://<redacted>@127.0.0.1:5432/finance_dashboard_local`
  - `DATABASE_MIGRATION_URL` → `postgresql://<redacted>@127.0.0.1:5432/finance_dashboard_local`
- Backend membaca repo root `.env` lalu `backend/.env` dengan mode override.
- Runtime aktif tervalidasi memakai env local PostgreSQL.
- Local PostgreSQL status:
  - 22 migrations applied
  - latest applied: `019_scope_import_fingerprints_by_workspace.sql`
  - `import_transaction_registry.workspace_id` ada
  - primary key registry = `(workspace_id, transaction_fingerprint)`
  - `transactions` memiliki `canonical_fingerprint` dan workspace-scoped indexes yang diharapkan

### API smoke test

Smoke test dilakukan ke backend lokal aktif di `http://127.0.0.1:8000`.

Observed results:

- `GET /api/health` → 200
- `POST /api/auth/login` valid → 200
- `POST /api/auth/login` invalid → 401
- `GET /api/workspaces` → 200
- protected endpoint dengan invalid workspace header → 403
- `GET /api/dashboard/view-model` → 200
- `GET /api/import/history?limit=20&offset=0` → 200
- `GET /api/import/category-options` → 200
- `POST /api/import/upload` → 200
- `GET /api/import/review/{job_id}?limit=20&offset=0` → 200
- `POST /api/import/review/{job_id}/reject` → 200

## Performance Observation

API latency snapshot pada runtime aligned:

- `/api/dashboard/view-model` ≈ 68 ms
- `/api/import/history?limit=20&offset=0` ≈ 15–16 ms
- `/api/import/category-options` ≈ 10 ms
- `/api/import/upload` ≈ 775 ms
- `/api/import/review/{job_id}` ≈ 20 ms

Observations:

- sesudah environment alignment, latency endpoint utama turun drastis dibanding smoke sebelumnya,
- upload PDF tetap menjadi operasi terberat di checkpoint ini tetapi masih di bawah 1 detik untuk fixture lokal,
- hasil ini tetap dianggap smoke baseline, belum benchmark final production dataset.

## Key Findings

### Medium

1. Google OAuth / Google Sheet end-to-end belum tervalidasi penuh.
   - Status connection dapat dicek, tetapi connect/reconnect/manual sync tetap bergantung pada credential Google aktif yang tidak diuji penuh pada checkpoint ini.

2. Approve + spreadsheet delivery belum diulang di runtime aligned ini.
   - Checkpoint memilih reject aman untuk menghindari side effect eksternal yang tidak perlu.

### Low

3. Logout belum tervalidasi end-to-end via browser.
   - Dari source inspection, logout menghapus token dan identity keys di localStorage.
   - Browser automation tidak dipakai pada checkpoint ini.

## Final Assessment

PASS / FAIL / PARTIAL:

- Final regression overall: PARTIAL (no blocking issue found in local aligned runtime)

Apakah aman buat PR ke `main`?

- Ya, aman untuk lanjut ke tahap PR ke `main` dari sisi hardening Task 1–9.
- Catatan: PR sebaiknya menyebut bahwa environment deploy target harus memakai schema migration dan env yang sudah align seperti checkpoint ini.

Apakah Task 10 perlu sekarang atau bisa hold?

- Task 10 bisa hold dulu.
- Tidak ada urgensi teknis untuk modularization sebelum PR hardening ini direview.
