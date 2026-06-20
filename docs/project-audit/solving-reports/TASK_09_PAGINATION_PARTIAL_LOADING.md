# TASK 09 — Pagination & Partial Loading

## 1. Root cause unbounded list/loading issue

Import Review dan Import History sebelumnya mengambil seluruh data sekaligus tanpa limit.

Akibatnya:

- payload API bisa membesar seiring jumlah draft transaksi atau job import,
- UI review/history cenderung all-or-nothing saat reload,
- refresh/paging berikutnya berisiko terasa berat karena seluruh list dimuat ulang.

## 2. Endpoint/page yang dipaginasi

Backend:

- `GET /api/import/review/{job_id}?limit=&offset=`
- `GET /api/import/history?limit=&offset=`

Frontend:

- `apps/web/src/components/import/ImportReview.jsx`
- `apps/web/src/components/import/ImportHistory.jsx`
- `apps/web/src/pages/ImportTransactions.jsx`

Backward compatibility dipertahankan:

- endpoint tetap sama,
- key utama `draft_transactions` dan `jobs` tetap ada,
- pagination ditambahkan sebagai metadata baru pada field `pagination`.

## 3. Default limit/page size

- Import Review: `100`
- Import History: `20`
- hard cap backend untuk query param `limit`: `100`

## 4. Loading/error behavior yang diubah

- Review dan History sekarang bisa reload halaman berikutnya tanpa selalu mengosongkan data lama lebih dulu.
- Jika data lama masih ada, loading ditampilkan sebagai inline notice, bukan panel kosong penuh.
- Error saat paging/reload tidak lagi harus menjatuhkan seluruh panel kalau data sebelumnya masih tersedia.
- Pagination UI ditambahkan dengan kontrol `Sebelumnya` dan `Berikutnya`.
- Review diberi copy tambahan bahwa pencarian/filter berlaku pada transaksi yang sedang tampil di halaman aktif.

## 5. File yang diubah

- `backend/app/api/imports.py`
- `backend/app/imports/repositories/import_repository.py`
- `backend/app/imports/services/import_service.py`
- `backend/tests/imports/test_blu_pdf_parser.py`
- `apps/web/src/api/importApi.js`
- `apps/web/src/pages/ImportTransactions.jsx`
- `apps/web/src/components/import/ImportReview.jsx`
- `apps/web/src/components/import/ImportHistory.jsx`

## 6. Test/validasi

Berhasil:

- `backend/venv/Scripts/python.exe -m unittest discover -s backend/tests -t .`
- `npm --prefix apps/web run lint`
- `npm --prefix apps/landing run lint`

Catatan eksekusi:

- backend unittest perlu dijalankan memakai interpreter virtualenv proyek karena sandbox default tidak bisa mengeksekusi interpreter venv secara langsung.
- lint frontend dijalankan via `npm.cmd` dari root workspace agar path Windows/PowerShell tidak salah mengarah ke `System32`.

Regression import minimal yang tervalidasi lewat suite/codepath:

- import page data contract tetap ada,
- review payload sekarang membawa page metadata tanpa menghapus field lama,
- history payload sekarang membawa page metadata tanpa menghapus field lama,
- retry sync flow tidak diubah,
- wording delivery status Task 8 tetap dipertahankan.

## 7. Risiko tersisa

- Filter/pencarian Review saat ini bekerja pada transaksi yang sedang tampil di halaman aktif, bukan lintas seluruh dataset review dalam satu request.
- Approve/reject yang mengembalikan payload review akan kembali mengikuti default page endpoint bila backend dipanggil tanpa offset lanjutan.
- Belum ada browser automation/regression visual langsung pada UI; validasi UI saat ini berbasis lint dan verifikasi codepath.

## 8. Commit hash

- Final commit tercatat di git history untuk perubahan ini dengan message `perf(ui): add pagination and partial loading states`.
