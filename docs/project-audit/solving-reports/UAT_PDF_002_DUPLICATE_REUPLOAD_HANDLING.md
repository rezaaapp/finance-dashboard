# UAT-PDF-002 — Duplicate / Reupload Handling

Tanggal: 21 Juni 2026  
Branch: `uat/local-postgres-stabilization`

## Bug Report

- Bug ID: `UAT-PDF-002`
- Result sebelum fix: **FAIL**
- Severity:
  - **High** — rejected transaction dapat dihidupkan kembali dari stale review job.
  - **Medium** — duplicate approval dihitung seperti approval baru.
  - **Medium** — upload tanpa transaksi baru tetap berstatus review dan menawarkan CTA review.

## Root Cause

1. Approval dan reject hanya membaca draft job tanpa memeriksa ulang status
   fingerprint registry pada saat action.
2. Registry approval menggunakan upsert yang dapat mengganti status `rejected`
   menjadi `approved`.
3. Final transaction insert memakai `ON CONFLICT DO UPDATE ... RETURNING`,
   sehingga row existing terlihat seperti insert baru dan ikut dihitung sebagai
   approval berhasil.
4. Upload dengan `new_transactions = 0` tetap menyimpan status job `review`.
5. History menentukan CTA hanya dari status job dan belum mengenali no-new
   result.

## Fix Summary

- Approval dan reject sekarang membaca ulang status fingerprint registry tepat
  sebelum action.
- Draft dengan registry `approved` diproses sebagai `skipped_existing`.
- Draft dengan registry `rejected` diproses sebagai `skipped_rejected`.
- Hanya fingerprint tanpa registry yang dapat membuat final transaction atau
  mengubah registry.
- Final transaction duplicate memakai `ON CONFLICT DO NOTHING`.
- Response approval menyertakan:
  - `approved_count`
  - `skipped_existing_count`
  - `skipped_rejected_count`.
- Semua selected stale draft dibersihkan dari stale job, tetapi tidak dihitung
  sebagai approval/reject baru.
- Job upload dengan seluruh transaksi existing langsung masuk `completed`.
- History menampilkan `Tidak ada transaksi baru` dan tidak menampilkan CTA
  `Lanjutkan Review` untuk no-new job.
- Feedback UI menjelaskan bila tidak ada ledger row baru dan menyebut jumlah
  transaksi yang sudah approved/rejected sebelumnya.

## Files Changed

- `backend/app/imports/repositories/final_transaction_repository.py`
- `backend/app/imports/services/import_service.py`
- `backend/app/api/imports.py`
- `backend/tests/imports/test_blu_pdf_parser.py`
- `apps/web/src/components/import/deliveryStatusUx.js`
- `apps/web/src/components/import/ImportHistory.jsx`
- `docs/project-audit/solving-reports/UAT_PDF_002_DUPLICATE_REUPLOAD_HANDLING.md`

## Backend / API Behavior

Approval stale draft sekarang:

- tidak membuat duplicate final transaction;
- tidak mengubah registry existing;
- tidak mengirim stale transaction ke Spreadsheet;
- menghapus selected stale draft dari stale review queue;
- mengembalikan skip counters yang eksplisit;
- memakai `ledger_saved = false` bila tidak ada transaksi baru.

Reject stale draft juga tidak dapat mengubah approved registry menjadi rejected
atau menambah rejected count untuk fingerprint yang sudah diproses.

Upload dengan 0 transaksi baru:

- `status = completed`
- `new_transactions = 0`
- `existing_transactions = transactions_found`
- draft count 0
- response tetap membawa `no_new_transactions = true`.

## Frontend Behavior

- History menampilkan `Tidak ada transaksi baru` untuk import yang seluruh
  fingerprint-nya sudah pernah diproses.
- CTA `Lanjutkan Review` hanya tampil untuk job `review` yang memiliki
  `new_transactions > 0`.
- Duplicate/rejected stale approval menampilkan:
  - `Tidak ada transaksi baru yang disimpan.`
  - alasan transaksi sudah approved atau rejected sebelumnya.

## Manual Verification

### Stale rejected approval

Job stale:

- Job ID: `b474049e-a2e9-41a4-a865-c201ae3f101b`
- Upload time: 21 Juni 2026, 15.41

Draft `MAKCIAK BASSURA 1 — Rp64.000`, yang sebelumnya berstatus registry
`rejected`, dicoba approve melalui UI.

Hasil:

- UI: `Tidak ada transaksi baru yang disimpan.`
- UI: `1 sudah ditolak sebelumnya`
- final transactions tetap `25`
- approved registry tetap `25`
- rejected registry tetap `11`
- registry MAKCIAK tetap `rejected`
- stale draft count turun dari `29` menjadi `28`.

### Complete-registry reupload

Upload ulang file yang sama:

- Job ID: `f7f514cb-6c72-46cd-9f62-785fa8f231d2`
- Upload time: 21 Juni 2026, 18.36

Hasil:

- job status: `completed`
- transactions found: `36`
- new transactions: `0`
- existing transactions: `36`
- draft count: `0`
- History: `Tidak ada transaksi baru`
- History: tidak ada CTA `Lanjutkan Review`
- Dashboard tetap `Rp1.867.169`
- tidak ada browser error.

Job 18.11 dibuat sebelum fix dan tetap mempertahankan status database historis
`review`. UI kini tetap menampilkan no-new state dan tidak menawarkan CTA
review. Evidence historis tidak dimutasi.

## Database Verification

- final transactions: `25`
- approved registry: `25`
- rejected registry: `11`
- job 15.41:
  - status: `review`
  - remaining drafts: `28`
- latest no-new job 18.36:
  - status: `completed`
  - remaining drafts: `0`
- dashboard total: `Rp1.867.169`

## Test Results

- Targeted import tests: **PASS** — 68 tests.
- Full backend tests: **PASS** — 118 tests.
- Web lint: **PASS**.
- `git diff --check`: **PASS**.

Database tidak di-reset, Supabase production tidak disentuh, dan seluruh
evidence UAT dipertahankan.
