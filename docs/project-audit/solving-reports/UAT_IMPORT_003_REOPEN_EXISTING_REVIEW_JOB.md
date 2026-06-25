# UAT-IMPORT-003 — Reopen Existing Review Job

Tanggal: 21 Juni 2026  
Branch: `uat/local-postgres-stabilization`

## Bug

- Bug ID: `UAT-IMPORT-003`
- Severity: **High**

Setelah halaman di-refresh, tab ditutup, atau state UI hilang, user tidak dapat
melanjutkan review import yang masih aktif. Tab Review menampilkan pesan bahwa
belum ada job review, walaupun PostgreSQL masih menyimpan job berstatus
`review` beserta draft yang belum diproses.

## Root Cause

1. `activeJobId` hanya disimpan di state React `ImportTransactions`.
2. State tersebut hanya diisi dari response upload pada sesi halaman yang sama.
3. Setelah reload, `activeJobId` kembali kosong.
4. Endpoint workspace-scoped `GET /api/import/review/{job_id}` sudah dapat
   membuka job existing, tetapi Import History belum menyediakan aksi untuk
   meneruskan `job_id` kembali ke layar Review.

Database, lifecycle job, dan endpoint review tidak bermasalah. Kegagalan berada
pada jalur navigasi frontend.

## Fix Summary

- Menambahkan aksi `Lanjutkan Review` pada row Import History untuk job dengan
  status `review`.
- Menambahkan aksi yang sama pada panel detail History.
- Aksi tersebut memakai `job_id` dari History dan memanggil loader review yang
  sudah ada.
- Review dibuka melalui endpoint existing, sekaligus memuat category options
  dan konfigurasi Spreadsheet seperti flow upload normal.
- Tidak ada endpoint, migration, parser, category bootstrap, atau lifecycle job
  yang diubah.

## Files Changed

- `apps/web/src/pages/ImportTransactions.jsx`
- `apps/web/src/components/import/ImportHistory.jsx`
- `docs/project-audit/solving-reports/UAT_IMPORT_003_REOPEN_EXISTING_REVIEW_JOB.md`

## Backend / API Behavior

Tidak ada perubahan backend.

Fix menggunakan API existing:

- `GET /api/import/history`
- `GET /api/import/review/{job_id}`
- `GET /api/import/category-options`

Semua endpoint tetap mengikuti authentication dan workspace scope yang sudah
ada. Approval/reject tetap menggunakan flow UAT-IMPORT-002 dan tidak berubah.

## Frontend Behavior

- History mengenali job yang masih berstatus `review`.
- Job tersebut menampilkan CTA `Lanjutkan Review`.
- CTA membuka Review berdasarkan `job_id`, bukan state upload sebelumnya.
- Setelah browser reload, user dapat kembali melalui Import Transaksi →
  History → Lanjutkan Review.
- Job selesai tidak akan menampilkan CTA tersebut.

## Manual UAT Evidence

Import job:

- Job ID: `6bdf20db-299b-4eb7-8d2a-f65e8556aba7`
- Workspace: `Admin's Household`
- Owner: `Reza`

Baseline sebelum UAT:

- job status: `review`
- final transactions: `5`
- approved fingerprint registry: `5`
- remaining drafts: `31`
- Dashboard total expense: `Rp 326.320`

Verification:

1. Browser di-reload sehingga state halaman sebelumnya hilang.
2. Import Transaksi → History menampilkan CTA `Lanjutkan Review`.
3. CTA membuka job existing dan menampilkan `31` draft.
4. Setiap dropdown menampilkan `14` default category, ditambah placeholder.
5. Draft `ketoprak cirebon robin` dipilih dan diberi category `Food`.
6. Approval dilakukan melalui UI tanpa target Spreadsheet.
7. UI menampilkan approval tersimpan di Omon dan delivery Spreadsheet dilewati
   secara terkontrol.

Database setelah approval:

- job status: `review`
- final transactions: `6`
- approved fingerprint registry: `6`
- remaining drafts: `30`
- latest final transaction: `ketoprak cirebon robin`
- latest final `raw_category`: `Food`
- latest final amount: `Rp 15.000`

Post-refresh verification:

- browser di-reload kembali;
- History menampilkan `6` approved dan CTA `Lanjutkan Review`;
- job berhasil dibuka lagi dengan `30` draft;
- category options tetap tersedia;
- Dashboard berubah menjadi `Rp 341.320`.

Tidak ada traceback atau error browser terkait import flow. Warning Recharts
tentang ukuran container tetap ada dan tidak terkait bug ini.

## Test Results

- Targeted Blu import tests: **PASS** — 66 tests.
- Web lint: **PASS**.
- `git diff --check`: **PASS**.

Database tidak di-reset dan seluruh evidence UAT dipertahankan.
