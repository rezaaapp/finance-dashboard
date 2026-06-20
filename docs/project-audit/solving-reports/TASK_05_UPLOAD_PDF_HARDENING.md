# Task 5 - Upload PDF Hardening

## Summary

Task 5 menambahkan hardening pada jalur upload PDF dan temp file tanpa
mengubah flow import utama di luar area validasi upload/temp storage.

## Limit Upload

- Max upload size: `10 * 1024 * 1024` bytes
- User-facing limit: `10 MB`

## Validation Added

- Validasi extension file harus `.pdf`
- Validasi content-type bila tersedia dan spesifik
- Generic content-type seperti `application/octet-stream` tetap boleh lanjut ke
  validasi isi file
- Validasi magic bytes file harus diawali `%PDF`
- Tetap mempertahankan validasi parser/extraction yang sudah ada setelah file
  lolos gate upload

## Temp Path Containment

- Temp file write dipaksa tetap berada di direktori
  `backend/output/imports/temp`
- Delete file hanya diizinkan jika resolved path masih berada di dalam temp
  directory yang sama
- Delete ditolak untuk path di luar temp directory atau non-file path

## Invalid Scenarios Tested

- upload dengan extension non-PDF
- upload dengan content-type non-PDF
- upload dengan magic bytes non-PDF
- upload PDF melebihi max size
- delete temp file untuk path di luar temp directory
- delete temp file untuk path valid di dalam temp directory

## Files Changed

- `backend/app/imports/services/import_service.py`
- `backend/app/imports/utils/temp_storage.py`
- `backend/tests/imports/test_blu_pdf_parser.py`
- `backend/tests/imports/test_temp_storage.py`
- `docs/project-audit/solving-reports/TASK_05_UPLOAD_PDF_HARDENING.md`

## Validation Run

- `python -m unittest discover -s backend/tests -t .`
- `npm --prefix apps/web run lint`
- `npm --prefix apps/landing run lint`

Results:

- backend unittest: `90` tests passed
- web lint: passed
- landing lint: passed
