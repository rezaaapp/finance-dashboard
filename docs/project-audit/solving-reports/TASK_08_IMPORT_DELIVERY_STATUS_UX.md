# Task 8 - Import UX Delivery Status

## 1. Root cause UX ambiguity

Root cause utama ada di wording UI import yang masih mencampur dua hal berbeda:

1. approval transaksi final di Omon
2. pengiriman salinan transaksi ke Google Spreadsheet

Di beberapa titik, copy lama masih terasa seperti approve + append Spreadsheet adalah satu aksi atomic. Efeknya:

- user bisa mengira transaksi belum tersimpan sama sekali saat pengiriman Spreadsheet gagal
- status history sulit dibaca karena masih menampilkan istilah internal/raw seperti `needs_reconnect`
- retry wording belum cukup jelas bahwa retry hanya mengirim ulang ke Spreadsheet, bukan membuat ulang transaksi Omon

Task 8 merapikan pemisahan UX ini tanpa mengubah behavior approval/sync Task 4.

## 2. UI/copy yang diubah

Area yang diperjelas:

- Import Review
  - CTA approve diubah menjadi berorientasi Omon: `Setujui & Simpan di Omon`
  - loading state menjelaskan urutan: simpan approval ke Omon dulu, lalu coba kirim salinan ke Spreadsheet
  - warning/error untuk missing target sheet / reconnect / invalid header sekarang menegaskan bahwa approval belum dijalankan bila target Spreadsheet belum siap
  - success/warning feedback approval sekarang memisahkan:
    - approval berhasil tersimpan di Omon
    - status pengiriman Spreadsheet setelah approval

- Import History
  - tabel history sekarang membedakan `Status Omon` dan `Status Spreadsheet`
  - detail history sekarang menampilkan:
    - `Disetujui di Omon`
    - `Terkirim ke Spreadsheet`
    - `Belum Terkirim`
    - badge `Status Spreadsheet`
  - wording retry diubah menjadi `Retry Pengiriman Spreadsheet`
  - ada penjelasan eksplisit bahwa retry tidak membuat ulang transaksi final di Omon

- Retry / reconnect / pending detail
  - status raw seperti `needs_reconnect` tidak ditampilkan mentah
  - diganti ke copy Indonesia yang lebih mudah dipahami

## 3. Status mapping approval vs spreadsheet delivery

Mapping UX yang dipakai:

### Status Omon

- `Menunggu review`
  - belum ada transaksi final yang disimpan di Omon
- `Tersimpan di Omon`
  - ada transaksi final yang sudah disetujui dan tersimpan
- `Tidak disimpan`
  - transaksi ditolak saat review, jadi tidak masuk Omon

### Status Spreadsheet

- `Belum ada pengiriman`
  - belum ada transaksi yang disetujui di Omon
- `Spreadsheet pending`
  - transaksi sudah tersimpan di Omon, tetapi masih ada salinan yang belum selesai dikirim
- `Spreadsheet berhasil`
  - semua salinan yang relevan sudah terkirim ke Google Spreadsheet
- `Spreadsheet gagal`
  - approval Omon sudah aman, tetapi pengiriman Spreadsheet gagal dan perlu retry
- `Perlu hubungkan ulang Google`
  - approval Omon sudah aman, tetapi OAuth Google perlu reconnect
- `Tab tujuan belum siap`
  - approval/retry butuh target tab Spreadsheet yang valid atau format kolom yang sesuai

## 4. Retry behavior

Retry behavior yang diperjelas di UI:

- retry hanya mencoba mengirim ulang salinan ke Google Spreadsheet
- retry tidak membuat ulang transaksi yang sudah tersimpan di Omon
- hasil retry dibedakan menjadi:
  - retry selesai
  - retry tertunda karena reconnect
  - retry belum berhasil
  - tidak ada pengiriman ulang yang diperlukan

Copy feedback retry sekarang konsisten dengan status delivery di history/detail.

## 5. File yang diubah

- `apps/web/src/components/import/deliveryStatusUx.js`
- `apps/web/src/components/import/ImportReview.jsx`
- `apps/web/src/components/import/ImportHistory.jsx`
- `apps/web/src/pages/ImportTransactions.jsx`
- `backend/app/imports/services/import_service.py`
- `backend/tests/imports/test_blu_pdf_parser.py`
- `docs/project-audit/solving-reports/TASK_08_IMPORT_DELIVERY_STATUS_UX.md`

## 6. Test/validasi

Automated validation:

```text
.\backend\venv\Scripts\python.exe -m unittest discover -s backend\tests -t .
npm --prefix apps/web run lint
npm --prefix apps/landing run lint
```

Hasil:

- backend unittest: PASS (`Ran 104 tests`)
- web lint: PASS
- landing lint: PASS

Minimal import regression:

- `GET /api/import/history` = `200`
- `GET /api/import/history/{job_id}` = `200`
- `GET /api/import/category-options` = `200`
- route frontend `/import` = `200`
- detail history masih memuat key penting seperti:
  - `approved_transactions`
  - `needs_reconnect`
  - `retryable_sync_count`
  - `unsynced_count`

## 7. Risiko tersisa

1. Backend approve flow saat ini masih mensyaratkan target Spreadsheet siap sebelum approval dijalankan. Task 8 hanya memperjelas UX-nya, bukan mengubah behavior itu.
2. Status `missing target sheet` pada history agregat tidak selalu bisa diketahui dari satu field job-level; paling jelas tetap terlihat di review/retry flow dan detail retry context.
3. Belum ada visual browser QA penuh di task ini; regression import dilakukan via lint, backend unittest, dan smoke/API check.

## 8. Commit hash

Commit Task 8 akan dibuat dengan message:

```text
fix(import): clarify spreadsheet delivery status
```

Hash final dicatat pada output handoff/git log setelah commit selesai dibuat.
