# UAT-DATA-001 — Editable Transaction Name in Import Review

Tanggal: 22 Juni 2026  
Branch: `uat/local-postgres-stabilization`

## Problem

Nama transaksi pada Import Review sebelumnya hanya berupa teks hasil parser.
User tidak dapat merapikan nama yang kosong, terpotong, mengandung kode bank,
atau kurang sesuai dengan konteks personal sebelum approval.

## Root Cause

- Review UI tidak menyediakan input untuk `merchant_display`.
- Approval request hanya membawa category dan notes.
- Approval service selalu membangun ulang display name dari
  `merchant_original`, sehingga tidak ada jalur untuk menyimpan koreksi user.

## Fix Summary

- Semua row Import Review sekarang menampilkan input editable untuk nama
  transaksi.
- Default value tetap memakai `merchant_display`, lalu fallback ke
  `merchant_normalized` atau `merchant_original`.
- Input kosong menampilkan placeholder `Isi nama transaksi`.
- Approval request membawa `merchant_display` untuk selected rows.
- Approval service memakai nama hasil edit sebagai final `transactions.title`
  dan `raw_payload.merchant_display`.
- `merchant_original`, `merchant_normalized`, `raw_text`, amount, date, owner,
  category, dan notes tetap mengikuti kontrak existing.
- Fingerprint dan canonical fingerprint tidak dihitung ulang dari nama edit.
- Client lama yang tidak mengirim `merchant_display`, atau mengirim `null`,
  tetap memakai display name hasil parser.

## Files Changed

- `apps/web/src/components/import/ImportReview.jsx`
- `backend/app/api/imports.py`
- `backend/app/imports/services/import_service.py`
- `backend/tests/imports/test_blu_pdf_parser.py`
- `docs/project-audit/solving-reports/UAT_DATA_001_EDITABLE_TRANSACTION_NAME.md`

## Backend / API Behavior

`item_updates` pada approval menerima field opsional:

```json
{
  "draft_id": "draft-id",
  "merchant_display": "Reimburse makan Divya",
  "category": "Food",
  "notes": ""
}
```

Nama edit diserialisasi ke:

- `transactions.title`
- `transactions.raw_payload.merchant_display`

Audit fields tetap dipertahankan:

- `raw_payload.merchant_original`
- `raw_payload.merchant_normalized`
- `raw_payload.raw_text`

Dedupe fields tetap sama:

- `import_transaction_fingerprint`
- `canonical_fingerprint`
- `canonical_fingerprint_date`

## Frontend Behavior

- Kolom Nama Transaksi menggunakan text input untuk setiap draft row.
- Nama parser langsung tersedia sebagai default value.
- Nama kosong menampilkan `Isi nama transaksi`.
- Hanya nama selected row yang dikirim bersama approval.
- Category selection dan approval controls tidak berubah.

## Verification

Automated persistence test memakai edit:

- parser/original: `Ayam Gepuk Pak Gembus, Ke M143872 | ...`
- edited display: `Reimburse makan Divya`

Hasil yang diverifikasi:

- final title: `Reimburse makan Divya`
- raw payload display: `Reimburse makan Divya`
- original merchant tetap utuh
- fingerprint tetap `fp-1`
- canonical fingerprint tetap `canon-fp-1`
- category, notes, owner, source, amount, dan tanggal tidak berubah.

Compatibility test memverifikasi `merchant_display = null` tetap menghasilkan
nama parser `Fore Coffee`, dengan original/raw text/fingerprint tetap utuh.

Manual UI verification pada job stale 15.41:

- seluruh `28/28` row memiliki editable name input;
- row transfer yang kosong menampilkan placeholder;
- value dapat diedit menjadi `Reimburse makan Divya`;
- halaman di-reload sebelum approval sehingga database evidence tidak berubah.

Karena final title adalah field yang dibaca Dashboard dan Search, transaksi baru
yang di-approve dengan nama edit akan tampil dan dapat dicari menggunakan nama
tersebut. Edit final transaction setelah approval tidak termasuk scope task ini.

## Test Results

- Targeted import tests: **PASS** — 69 tests.
- Full backend tests: **PASS** — 119 tests.
- Web lint: **PASS**.
- `git diff --check`: **PASS**.

## Database Evidence

Database tidak di-reset dan tidak dimutasi selama manual UI verification:

- final transactions: `25`
- total final amount: `Rp1.867.169`
- approved registry: `25`
- rejected registry: `11`

Supabase production tidak disentuh.
