# UAT Fix — Default Workspace User FK

## Root cause

UAT menemukan kasus saat JWT/session internal masih valid, tetapi row `users.id = current_user["sub"]` sudah tidak ada di database local.

Akibatnya, saat request `GET /api/dashboard/view-model` masuk ke:

- `dashboard_view_model`
- `resolve_workspace_for_request`
- `ensure_default_workspace_for_user`
- `upsert_workspace_member(role="owner")`

FK `workspace_members_user_id_fkey` gagal karena `workspace_members.user_id` mengacu ke row `users` yang belum ada.

Masalah utamanya bukan di constraint, tetapi di provisioning flow yang mengasumsikan row `users` selalu ada untuk session aktif.

## File yang diubah

- `backend/app/auth.py`
- `backend/app/repositories/users.py`
- `backend/tests/test_local_login_session.py`
- `backend/tests/test_dashboard_view_model.py`

## Solusi teknis

Fix diterapkan di dependency session user, bukan dengan bypass FK.

Perubahan utama:

1. Tambah helper repository `upsert_session_user(...)`
   - memastikan `users` row ada untuk `sub/email/name/role` dari session
   - validasi `sub` harus UUID valid
   - validasi `email` dan `name` wajib ada
   - jika `email` sudah dipakai user lain dengan `id` berbeda, return controlled error

2. `require_current_user(...)` sekarang:
   - melakukan upsert/sync user session ke tabel `users` sebelum endpoint memakai `current_user`
   - mengembalikan `401` terkontrol jika session invalid dan user tidak bisa direkonsiliasi

3. Dengan perubahan ini:
   - local login/JWT internal flow aman
   - Google login flow yang memakai internal JWT juga ikut aman
   - provisioning workspace default tidak lagi menabrak FK hanya karena row `users` hilang

## Test yang ditambah

1. Session user valid tetapi users row belum ada
   - `test_require_current_user_upserts_missing_session_user_row`

2. Session user invalid memberi controlled error
   - `test_require_current_user_returns_401_for_invalid_session_user`

3. Dashboard view-model tetap bisa resolve/provision workspace
   - `test_dashboard_view_model_provisions_default_workspace_for_session_user`

4. Existing user path tetap jalan
   - existing local login tests tetap PASS

## Validation result

### Backend unittest

PASS

- `python -m unittest discover -s backend/tests -t .`
- Result: `Ran 108 tests ... OK`

### Frontend lint

PASS

- `npm --prefix apps/web run lint`

### Landing lint

PASS

- `npm --prefix apps/landing run lint`

### Smoke

PASS

- local login → `200`
- `GET /api/workspaces` → `200`
- `GET /api/dashboard/view-model` → `200`

## Remaining risk

1. Jika token internal berisi `sub/email` yang saling bentrok dengan data user lain, request sekarang gagal dengan `401` terkontrol.
   - Ini sengaja, agar kita tidak silently memetakan session ke account yang salah.

2. Fix ini tidak mengubah semantics token refresh / revocation.
   - Jadi audit session lifecycle tetap bisa ditingkatkan terpisah jika nanti dibutuhkan.

3. Response `current_sheet_name` pada dataset kosong masih bisa menampilkan label legacy source name.
   - Ini tidak terkait FK bug dan tidak diubah di task ini.

## Commit hash

- To be filled after commit: `PENDING`
