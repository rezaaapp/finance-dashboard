# UAT-IMPORT-002 — Local-First Approval

Tanggal: 21 Juni 2026  
Branch: `uat/local-postgres-stabilization`

## Bug

- Bug ID: `UAT-IMPORT-002`
- Severity: **High**

Blu PDF review tidak dapat disetujui pada fresh workspace tanpa Google OAuth,
Google Sheet source, dan target tab. Hal ini memblokir persistence ledger Omon
meskipun PostgreSQL adalah source of truth dan Spreadsheet hanya
projection/export layer.

## Root Cause

1. Frontend men-disable tombol `Setujui & Simpan di Omon` ketika source dan tab
   Spreadsheet belum dipilih.
2. Backend me-resolve source, OAuth, dan header Spreadsheet sebelum membuat
   final transaction dan fingerprint registry.
3. Kolom `transactions.sheet_source_id` masih `NOT NULL`, sehingga schema belum
   mengizinkan transaksi Blu tanpa Google Sheet source.

## Fix Summary

- Migration 020 membuat `transactions.sheet_source_id` nullable.
- Approval menyimpan final transaction dan fingerprint registry terlebih dulu.
- Spreadsheet delivery hanya dicoba bila source dan tab tersedia.
- Tanpa target Spreadsheet:
  - ledger tetap tersimpan;
  - transaction memakai delivery status `pending`;
  - API mengembalikan `ledger_saved = true` dan `sync_status = skipped`;
  - response menyertakan detail `sheet_delivery`.
- Existing Google Sheet path tetap menggunakan validasi source, OAuth, header,
  dan sync yang sudah ada.
- Tombol approval tidak lagi bergantung pada source/tab.
- Review menampilkan informasi bahwa transaksi tetap disimpan ke Omon.
- History membedakan `Spreadsheet belum terhubung` dari sync failure.
- Dashboard menganggap final PostgreSQL transaction sebagai data siap tampil,
  meskipun Google belum terhubung.

## Files Changed

- `backend/db/migrations/020_allow_transactions_without_sheet_source.sql`
- `backend/app/imports/repositories/final_transaction_repository.py`
- `backend/app/imports/repositories/import_repository.py`
- `backend/app/imports/services/import_service.py`
- `backend/tests/imports/test_blu_pdf_parser.py`
- `apps/web/src/components/import/ImportReview.jsx`
- `apps/web/src/components/import/deliveryStatusUx.js`
- `apps/web/src/pages/ImportTransactions.jsx`
- `apps/web/src/pages/Dashboard.jsx`
- `docs/project-audit/solving-reports/UAT_IMPORT_002_LOCAL_FIRST_APPROVAL.md`

## Backend / API Behavior

Approval tanpa `sheet_source_id` dan `sheet_name` sekarang:

1. membuat final transaction di PostgreSQL;
2. membuat approved fingerprint registry;
3. menghapus selected draft sesuai existing lifecycle;
4. mempertahankan job `review` bila masih ada draft;
5. menyimpan transaction delivery state sebagai `pending`;
6. mengembalikan response terkontrol:
   - `ledger_saved = true`
   - `sync_status = skipped`
   - `sync_success = 0`
   - `sync_failed = jumlah transaksi yang belum dikirim`
   - `sheet_delivery.status = skipped`.

Approval ulang terhadap draft ID yang sudah diproses menghasilkan
`approved_count = 0`, sehingga tidak membuat duplicate final transaction.

## Frontend Behavior

- Tombol approval aktif setelah minimal satu draft dipilih, tanpa mewajibkan
  Spreadsheet/tab.
- Warning menjelaskan transaksi akan disimpan di Omon dan sinkronisasi dapat
  dilakukan setelah Google Sheet terhubung.
- Approval feedback menegaskan ledger tersimpan dan delivery dilewati.
- Import History menampilkan:
  - status Omon: `Tersimpan di Omon`;
  - status Spreadsheet: `Spreadsheet belum terhubung`.
- Dashboard menampilkan final PostgreSQL transaction tanpa menunggu koneksi
  Google.

## Manual UAT Evidence

Import job:

- Job ID: `6bdf20db-299b-4eb7-8d2a-f65e8556aba7`
- Workspace: `Admin's Household`
- Owner: `Reza`

Dua draft disetujui tanpa source/tab Spreadsheet:

- `2b31b7c0-437b-463a-b181-5be463a5d055`
- `fa412375-f90c-4e05-a7a5-dbb8dc58842b`

Hasil:

- final transactions: `2`
- approved fingerprint registry: `2`
- remaining drafts: `34`
- import job status: `review`
- kedua transaction memakai `sheet_source_id = NULL`
- kedua transaction memakai `sync_status = pending`
- History menampilkan `Spreadsheet belum terhubung`
- Dashboard menampilkan total expense `Rp 229.420`
- Dashboard menampilkan dua uncategorized transaction dan dua row Top Spending.

Idempotency:

- approval ulang dua draft ID yang sama menghasilkan `approved_count = 0`;
- final transaction count tetap `2`.

Database tidak di-reset dan seluruh evidence UAT dipertahankan.

## Test Results

- Targeted Blu import tests: **PASS** — 65 tests.
- Full backend tests: **PASS** — 115 tests.
- Web lint: **PASS**.
- Landing lint sebelumnya: **PASS**.
- Migration 020: **PASS**, diterapkan hanya ke PostgreSQL lokal.
- `git diff --check`: **PASS**.

## Remaining Issue

`UAT-IMPORT-001` belum diperbaiki. Fresh workspace masih belum memiliki category
options untuk bootstrap kategori pertama. Fix ini sengaja tidak mengubah
category maupun `review_group`.

## Deferred UX Backlog

Di task berikutnya, Import UI perlu memisahkan status penyimpanan Omon dan
status sinkronisasi Spreadsheet secara lebih eksplisit, termasuk CTA sync yang
menyebut jumlah transaksi, Spreadsheet, dan nama sheet tujuan. Backlog ini
tidak diimplementasikan pada task UAT-IMPORT-002.
