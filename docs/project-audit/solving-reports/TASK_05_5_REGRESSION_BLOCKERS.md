# Task 5.5 — Regression Blocker Fix

## Executive Summary

PARTIAL

Blocker 1 dan Blocker 2 sudah diperbaiki dan tervalidasi lewat unit test + runtime re-test minimal.

Blocker 3 belum bisa ditutup penuh karena local PostgreSQL belum siap untuk menjalankan migration 019. Yang diselesaikan pada task ini adalah static safety review dan checklist verifikasi lokal agar migrasi bisa diuji dengan aman nanti.

## Blocker 1 — Auth Session Compatibility

### Root Cause

`POST /api/auth/login` mengembalikan `DASHBOARD_AUTH_TOKEN` statis, bukan JWT internal user session. Akibatnya:

- login terlihat berhasil di UI
- beberapa endpoint yang hanya butuh bearer token menerima request
- endpoint workspace-scoped yang membutuhkan `require_current_user` tetap menolak dengan `401 User session required`

Boundary auth menjadi membingungkan karena “sudah login” tidak sama dengan “punya user session”.

### Solution

Local login diubah agar:

- tetap memverifikasi `DASHBOARD_USERNAME` dan `DASHBOARD_PASSWORD`
- membentuk identity user yang nyata
- upsert user ke tabel `users`
- memastikan user punya default workspace
- mengembalikan JWT internal dari `create_internal_token`
- menyertakan `email`, `userId`, `workspaceId`, `role`, dan `provider`

Dengan ini local login tidak lagi bergantung pada fake static-token path untuk flow workspace.

### Files Changed

- `backend/app/api/auth.py`
- `backend/tests/test_local_login_session.py`

### Tests Added

- local login menghasilkan JWT internal, bukan static token
- token hasil login bisa dipakai sebagai `require_current_user`
- username email-style tetap dipreservasi sebagai email session

### Validation Result

PASS

Runtime re-test minimal pada backend baru di port `8001`:

- login valid: PASS
- login invalid: PASS (`401`)
- `/api/workspaces`: PASS
- `/api/google/connection/status`: PASS (`connected: false` pada workspace local baru, tetapi tidak lagi `401 User session required`)

### Remaining Risk

- Local login masih merupakan mode internal/dev-style auth, bukan pengganti Google OAuth untuk flow production.
- Jika environment memakai username non-email, sistem sekarang membentuk email sintetis yang deterministik agar session tetap workspace-aware.
- Behavior login lokal lintas environment tetap perlu dipahami QA agar tidak tertukar dengan flow Google login.

### Commit

- `c31b86f` — `fix(auth): align local login with workspace sessions`
- `fe40238` — `test(backend): stabilize regression blocker coverage`

## Blocker 2 — Invalid Worksheet Source ID

### Root Cause

Endpoint `GET /api/data-sources/{source_id}/worksheets` menerima `source_id` mentah dan meneruskannya ke query repository. Saat format ID tidak valid, request bisa jatuh ke error database/internal dan berujung `500`.

Selain itu, endpoint belum membedakan dengan jelas:

- format ID invalid
- source tidak ada
- source ada tetapi milik workspace lain

### Solution

Ditambahkan handling terstruktur:

- `400 Bad Request` untuk format `source_id` invalid
- `404 Not Found` untuk source ID valid tetapi tidak ada
- `403 Forbidden` untuk source yang ada tetapi bukan milik workspace aktif

Helper lookup yang sama juga dipakai untuk route `worksheets`, `sync`, dan `delete` agar perilakunya konsisten.

### Files Changed

- `backend/app/api/data_sources.py`
- `backend/app/repositories/google_sheet_source_repository.py`
- `backend/tests/test_data_source_worksheet_endpoint.py`

### Tests Added

- invalid source id format → `400`
- non-existing source id → `404`
- foreign workspace source id → `403`
- valid source id → controlled response path

### Validation Result

PASS

Runtime re-test minimal:

| Scenario | Result | Notes |
|---|---|---|
| Invalid source id format | PASS | return `400`, tidak lagi `500` |
| Non-existing source id | PASS | return `404` |
| Source id milik workspace lain | PASS | return `403` |
| Valid source id | PASS | return controlled `400` karena Google connection expired, bukan `500` |

### Remaining Risk

- Endpoint valid source masih bisa return `400` jika OAuth/token Google memang expired; ini expected operational state, bukan regression source-id handling.
- Error copy untuk invalid Google Sheet URL pada endpoint test-connection masih generik dan belum termasuk task ini.

### Commit

- `e61c134` — `fix(data-sources): handle invalid worksheet source ids`
- `fe40238` — `test(backend): stabilize regression blocker coverage`

## Blocker 3 — Migration 019 Local Verification

### Root Cause

Runtime import code sudah mengandalkan `workspace_id`, tetapi local PostgreSQL belum siap sehingga migration 019 belum bisa dieksekusi dan diverifikasi langsung. Karena itu Blu PDF import masih belum bisa dinyatakan PASS end-to-end di local runtime migration path.

### Current Decision

- Tidak menjalankan migration database sekarang.
- Tidak mengklaim Blu PDF Import sudah PASS end-to-end.
- Menutup blocker ini sementara pada level dokumentasi operasional + static safety review.

### Checklist Created

- `docs/project-audit/LOCAL_POSTGRES_MIGRATION_019_CHECKLIST.md`

Checklist mencakup:

1. prasyarat PostgreSQL local
2. cara membuat database local
3. env vars yang dibutuhkan
4. command menjalankan migration
5. command menjalankan test setelah migration
6. SQL verifikasi kolom `workspace_id`
7. SQL verifikasi composite primary key
8. SQL verifikasi duplicate fingerprint per workspace
9. rollback/reset local yang aman
10. reminder keras untuk tidak menjalankan ke production tanpa backup

### Remaining Risk

- Selama migration 019 belum diverifikasi di local PostgreSQL atau staging clone, Blu PDF import compatibility tetap pending.
- Runtime env yang belum termigrasi masih akan gagal pada flow import baru.

### Commit

- `5f6bff3` — `docs(db): add local migration 019 verification checklist`

## Regression Re-Test Result

| Area | Result | Notes |
|---|---|---|
| Login valid | PASS | local login sekarang menghasilkan JWT user session |
| Login invalid | PASS | return `401` |
| Workspace endpoint | PASS | `/api/workspaces` berhasil dengan token hasil login |
| Google connection status | PASS | `/api/google/connection/status` berhasil dengan token hasil login |
| Invalid source id | PASS | `400` / `404` / `403` sesuai kasus |
| Import upload | SKIPPED/PENDING | Waiting local PostgreSQL migration verification |

## Validation Commands

Commands yang dijalankan:

```bash
.\backend\venv\Scripts\python.exe -m unittest backend.tests.test_local_login_session
.\backend\venv\Scripts\python.exe -m unittest backend.tests.test_data_source_worksheet_endpoint
.\backend\venv\Scripts\python.exe -m unittest discover -s backend/tests -t .
npm --prefix apps/web run lint
npm --prefix apps/landing run lint
```

Hasil:

- targeted auth test: PASS
- targeted worksheet endpoint test: PASS
- full backend unittest: PASS (`Ran 96 tests`)
- `apps/web` lint: PASS
- `apps/landing` lint: PASS

Catatan environment:

- Shell profile lokal masih menampilkan warning terkait `conda.exe` yang tidak ditemukan, tetapi command test/lint tetap berjalan dan selesai sukses.

## Final Recommendation

Apakah aman lanjut Task 6?

NO

Alasannya:

1. Blocker auth session dan worksheet source ID sudah ditutup.
2. Tetapi Blu PDF import compatibility masih menunggu verifikasi migration 019 di local PostgreSQL/staging.
3. Sampai migration path itu diverifikasi, regression status keseluruhan belum cukup kuat untuk membuka Task 6 dashboard aggregation dengan aman.
