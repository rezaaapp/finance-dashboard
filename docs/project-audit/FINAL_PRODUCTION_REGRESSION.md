# Final Production Regression

## Executive Summary

Regression status: PARTIAL

Production safety: PARTIAL

Branch checked:

- `fix/audit-production-hardening`

Reasoning singkat:

- Seluruh backend unittest PASS.
- Frontend web lint PASS.
- Landing lint PASS.
- API smoke untuk area dashboard, inquiry, budget, workspace, auth dasar, import history endpoint, dan delivery status payload shape sebagian besar PASS.
- Namun final checkpoint belum bisa dinyatakan full PASS karena:
  - backend runtime yang aktif saat smoke test tidak memakai local PostgreSQL config,
  - local PostgreSQL migration status check gagal connect dari `backend/.env_dev`,
  - Blu import upload pada runtime aktif gagal karena schema runtime belum cocok dengan code Task 1–9,
  - beberapa flow yang bergantung pada Google OAuth aktif / Google Sheet source aktif / data import existing tidak bisa divalidasi end-to-end penuh pada runtime saat ini.

## Test Matrix

| Scope | Status | Notes |
|---|---|---|
| 1. Login valid | PASS | `POST /api/auth/login` return 200 |
| 2. Login invalid | PASS | invalid password return 401 |
| 3. Workspace selection & isolation | PARTIAL | workspace list 200; invalid `X-Workspace-Id` menghasilkan 403 pada endpoint terproteksi |
| 4. Google OAuth status | PARTIAL | status endpoint 200 dan menunjukkan `connected: false`; reconnect flow tidak tervalidasi end-to-end |
| 5. Google Sheet source list/test/invalid source | PARTIAL | list source 200 kosong; invalid source UUID return 404; full add/test with active OAuth tidak tervalidasi |
| 6. Manual sync | SKIPPED | tidak ada source aktif dan Google tidak connected pada runtime smoke |
| 7. Dashboard load | PASS | `/api/dashboard/view-model` return 200 |
| 8. Dashboard filter bulan/tahun | PASS | endpoint summary/view-model dengan `year`/`month` return 200 |
| 9. Summary card | PASS | summary payload konsisten dan return 200 |
| 10. Chart utama | PASS | category / heatmap / top spending / anomalies return 200 |
| 11. Analytics load | PASS | `monthly-financial-types` return 200 |
| 12. Search/Inquiry load | PASS | `POST /api/inquiry` return 200 |
| 13. Budget load | PASS | `GET /api/budgets?year=2026&month=6` return 200 |
| 14. Blu PDF Import upload | FAIL | upload memicu 500 pada runtime aktif |
| 15. Import Review pagination | SKIPPED | tidak ada job review baru karena upload gagal |
| 16. Approve | SKIPPED | tergantung review import |
| 17. Reject | SKIPPED | tergantung review import |
| 18. Retry spreadsheet delivery | SKIPPED | tidak ada import history + unsynced job untuk runtime smoke |
| 19. Import History pagination | PASS | `/api/import/history?limit=20&offset=0/20` return 200 dengan metadata pagination |
| 20. Delivery status UX | PARTIAL | payload/status API dan copy Task 8 tetap ada; UI browser end-to-end tidak tervalidasi karena browser automation blocked |
| 21. Logout | PARTIAL | logout bersifat client-side token cleanup; source inspection menunjukkan localStorage cleanup, tapi browser flow tidak tervalidasi end-to-end |

## Validation Run

### Automated validation

- Backend unittest: PASS
  - `backend/venv/Scripts/python.exe -m unittest discover -s backend/tests -t .`
- Web lint: PASS
  - `npm --prefix apps/web run lint`
- Landing lint: PASS
  - `npm --prefix apps/landing run lint`

### Migration / environment check

- Runtime backend env currently does **not** look local (`backend/.env` target bukan localhost).
- Local migration status check via `backend/.env_dev`:
  - migration runner berhasil membaca 22 migration files,
  - tetapi koneksi ke local PostgreSQL gagal (`OperationalError`),
  - sehingga status applied schema di local DB saat final checkpoint ini belum bisa dikonfirmasi.

### API smoke test

Smoke test dilakukan ke backend lokal aktif di `http://127.0.0.1:8000`.

Observed results:

- `POST /api/auth/login` valid → 200
- `POST /api/auth/login` invalid → 401
- `GET /api/workspaces` → 200
- protected endpoint dengan invalid workspace header → 403
- `GET /api/google/connection/status` → 200
- `GET /api/data-sources` → 200
- `GET /api/data-sources/{uuid}/worksheets` untuk UUID dummy → 404
- `GET /api/dashboard/view-model` → 200
- `GET /api/dashboard/summary` → 200
- `GET /api/dashboard/spending-by-category` → 200
- `GET /api/dashboard/category-heatmap` → 200
- `GET /api/dashboard/top-spending` → 200
- `GET /api/dashboard/anomalies` → 200
- `GET /api/dashboard/monthly-financial-types` → 200
- `POST /api/inquiry` → 200
- `GET /api/budgets?year=2026&month=6` → 200
- `GET /api/import/history?limit=20&offset=0` → 200
- `GET /api/import/history?limit=20&offset=20` → 200
- `POST /api/import/upload` → 500

## Performance Observation

API latency snapshot pada runtime smoke:

- `/api/dashboard/view-model?year=2026&month=6` ≈ 10991 ms
- `/api/dashboard/summary?year=2026&month=6` ≈ 2136 ms
- `/api/dashboard/spending-by-category?year=2026&month=6` ≈ 2357 ms
- `/api/dashboard/category-heatmap?year=2026` ≈ 2245 ms
- `/api/dashboard/top-spending?year=2026&month=6` ≈ 1740 ms
- `/api/dashboard/anomalies?year=2026&month=6` ≈ 2456 ms
- `/api/inquiry` ≈ 3077 ms
- `/api/import/history?limit=20&offset=0` ≈ 2048 ms
- `/api/import/history?limit=20&offset=20` ≈ 2158 ms

Observations:

- agregat `/api/dashboard/view-model` masih terasa berat dibanding legacy summary endpoint pada runtime ini,
- import history pagination sudah bounded, tetapi latency masih di kisaran ~2 detik pada runtime yang diuji,
- karena dataset runtime saat smoke hampir kosong, hasil latency ini lebih cocok dianggap baseline environment/runtime observation, bukan benchmark final yang stabil.

## Key Findings

### High

1. Blu import upload gagal 500 pada runtime aktif.
   - Evidence dari backend stack trace menunjukkan query fingerprint/import menyentuh kolom `workspace_id` yang tidak ada di schema runtime aktif.
   - Ini sangat mengarah ke runtime DB/schema mismatch terhadap hardening Task 1–9.

2. Runtime backend aktif tidak menggunakan local PostgreSQL config.
   - `backend/.env` yang sedang aktif saat smoke tidak menunjuk localhost.
   - Ini membuat smoke test tidak mewakili hasil local migration 019 yang sebelumnya sudah diverifikasi.

### Medium

3. Local PostgreSQL migration status check belum bisa dikonfirmasi saat final checkpoint.
   - Runner membaca 22 file migration, tetapi koneksi ke target `backend/.env_dev` gagal `OperationalError`.

4. `/api/dashboard/view-model` masih relatif lambat.
   - Walau return 200, latency ~11 detik pada smoke ini jauh di atas endpoint summary legacy.

### Low

5. Logout belum tervalidasi end-to-end via browser.
   - Dari source inspection, logout menghapus token dan identity keys di localStorage.
   - Tetapi browser automation tidak bisa dipakai di environment audit ini.

## Final Assessment

PASS / FAIL / PARTIAL:

- Final regression overall: PARTIAL

Apakah aman buat PR ke `main`?

- Belum aman langsung bilang full-safe.
- Aman untuk lanjut ke tahap PR **hanya jika** sebelum PR kita selaraskan runtime environment target dengan schema/code Task 1–9 dan memastikan import upload tidak lagi 500.

Apakah Task 10 perlu sekarang atau bisa hold?

- Task 10 bisa hold dulu.
- Prioritas sebelum modularization adalah menutup finding environment/runtime mismatch dan memastikan final smoke import berjalan di runtime yang schema-nya sudah sesuai.
