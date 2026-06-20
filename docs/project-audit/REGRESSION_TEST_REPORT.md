## Executive Summary

Regression status:

FAIL

Production safety:

FAIL

Regression test untuk Task 1–5 menemukan dua blocker utama:

- Flow login lokal tidak menghasilkan user session yang bisa dipakai konsisten untuk seluruh endpoint utama. Beberapa endpoint menerima token login, tetapi endpoint workspace-scoped lain menolak dengan `401 User session required`.
- Flow Blu PDF import gagal di runtime environment saat ini karena code path baru sudah membaca kolom `workspace_id`, tetapi schema database yang sedang aktif belum memiliki kolom tersebut. Akibatnya upload valid berakhir `500 Internal Server Error`.

Di luar dua blocker itu, verifikasi RBAC workspace, isolasi data lintas workspace, dan beberapa flow dashboard/budget/import history menunjukkan hasil yang konsisten.

---

## Test Matrix

| Test | Scope | Status | Evidence / Notes |
|---|---|---|---|
| 1 | Login | PARTIAL | `POST /api/auth/login` berhasil untuk kredensial valid dan gagal untuk invalid credential. Namun token hasil login tidak bisa dipakai konsisten untuk endpoint yang butuh user session riil seperti `/api/workspaces` dan `/api/google/connection/status`. Refresh/logout diverifikasi via source review, bukan browser runtime. |
| 2 | Workspace | PASS | Dengan JWT impersonation, active workspace memengaruhi hasil summary/budget/import history secara benar. Akses workspace asing ditolak `403`. |
| 3 | Google OAuth | PARTIAL | Status koneksi dan kondisi `needs_reconnect=true` tervalidasi. Invalid/expired token ditangani dengan baik pada worksheet fetch. Connect/disconnect/reconnect penuh tidak diuji end-to-end karena butuh browser OAuth flow. |
| 4 | Google Sheet Source | PARTIAL | Listing source dan invalid sheet id diuji. Worksheet discovery pada source nyata gagal dengan pesan reconnect saat token expired, which is expected. Add/delete source tidak dieksekusi agar tidak mengubah state. Ditemukan bug: invalid `source_id` pada endpoint worksheets mengembalikan 500. |
| 5 | Manual Sync | PARTIAL | Kondisi expired OAuth dan dependency ke Google connection tervalidasi. Sync manual penuh, retry, dan history sinkronisasi Google tidak dapat diuji penuh tanpa koneksi OAuth yang valid dan tanpa mengubah state. |
| 6 | Dashboard | PARTIAL | `summary` per workspace tervalidasi dan tidak terlihat loading/API hang dari sisi backend. Namun render UI, filter interaktif, card completeness, chart correctness, dan infinite loading tidak bisa diverifikasi penuh tanpa browser automation. |
| 7 | Analytics | SKIPPED | Tidak dapat diverifikasi end-to-end tanpa browser/UI interaction dan data-path analytics yang cukup di sesi ini. |
| 8 | Search / Inquiry | SKIPPED | Tidak dapat diverifikasi end-to-end tanpa browser/UI interaction. |
| 9 | Budget | PASS | Data budget terisolasi per workspace. Workspace Reza memiliki budget, workspace Divya tidak. Ini konsisten dengan expected workspace isolation. Verifikasi visual progress/alert/category masih terbatas ke API-level evidence. |
| 10 | Blu PDF Import | FAIL | Upload PDF valid ke runtime env saat ini berakhir `500` karena query fingerprint registry sudah memakai `workspace_id` sementara schema aktif belum memiliki kolom tersebut. Flow review/approve/reject/retry/history lanjutan tidak bisa dilanjutkan dari upload ini. |
| 11 | Import History | PASS | Import history berbeda jelas antar workspace: workspace Divya kosong, workspace Reza memiliki 29 jobs. Status list/pagination dasar terakses. |
| 12 | Settings | PASS | Owner bisa `GET` dan `PUT` workspace configuration. Member ditolak `403`. RBAC enforcement berjalan pada endpoint yang diuji. |
| 13 | Multi Workspace | PASS | Dashboard, budget, import history, dan workspace configuration tidak bocor lintas workspace. Foreign workspace header ditolak `403`. |
| 14 | Logout | PARTIAL | Logout behavior dan token cleanup tervalidasi lewat source review (`localStorage` cleanup). Browser refresh/back behavior tidak bisa diuji runtime tanpa browser automation. |

Legend:

- PASS = tervalidasi cukup kuat pada runtime/source evidence yang tersedia
- PARTIAL = sebagian tervalidasi, tetapi ada keterbatasan lingkungan atau state
- SKIPPED = tidak cukup evidence untuk menyatakan pass/fail secara jujur
- FAIL = ditemukan bug/blocker nyata

---

## Regression Findings

### Critical

1. Blu PDF import gagal pada runtime environment saat ini karena schema database aktif belum memiliki kolom `workspace_id` yang sudah dipakai oleh code fingerprint registry.
   - Dampak: upload PDF valid gagal total dengan `500`.
   - Dampak lanjutan: review, approve, reject, retry, dan verifikasi downstream spreadsheet delivery dari flow import tidak bisa dijalankan dari upload baru.
   - Kategori: runtime compatibility / migration dependency.

### High

1. Token hasil `/api/auth/login` tidak setara dengan user session riil.
   - Dampak: user bisa terlihat “login”, tetapi endpoint workspace-scoped tertentu tetap gagal dengan `401 User session required`.
   - Contoh endpoint terdampak: `/api/workspaces`, `/api/google/connection/status`.
   - Risiko: regression UX besar pada flow user biasa, terutama flow yang memerlukan context user + workspace.

### Medium

1. Endpoint worksheet untuk `source_id` yang invalid mengembalikan `500`, bukan `404`/controlled error.
   - Endpoint: `GET /api/data-sources/{source_id}/worksheets`
   - Risiko: poor error handling, misleading operational failure, noisy alerting.

2. Invalid Google Sheet id menghasilkan pesan yang terlalu generik.
   - Endpoint: `POST /api/data-sources/google-sheet/test`
   - Response saat diuji: `valid: false`, `message: "Unable to access spreadsheet"`
   - Risiko: user sulit membedakan salah ID vs OAuth/token/access issue.

### Low

1. Beberapa verifikasi UX penting belum bisa dinyatakan PASS karena browser automation di sesi ini gagal start.
   - Area terdampak: chart rendering, loading state, disabled state, back-button logout behavior, responsive behavior.

---

## New Findings

1. Invalid `source_id` pada endpoint worksheet mengembalikan `500 Internal Server Error` alih-alih not found / controlled validation error.
2. Invalid Google Sheet identifier masih menghasilkan copy yang generik, belum cukup membantu membedakan akar masalah input.
3. Saat import gagal karena DB schema mismatch, error handling ikut jatuh ke `InFailedSqlTransaction`, sehingga user-facing failure berpotensi tampil sebagai generic 500, bukan error operasional yang lebih jelas.

---

## Existing Findings

1. Local login/static token model belum benar-benar merepresentasikan authenticated user session untuk seluruh endpoint aplikasi.
2. Runtime database environment yang belum mengikuti kebutuhan schema terbaru membuat flow import tidak kompatibel.
3. Google connection pada workspace yang diuji berada pada status `needs_reconnect`, sehingga sebagian flow Google memang dalam kondisi terblokir secara operasional.

---

## Performance Observation

- Backend health check dan frontend dev server startup normal.
- API requests yang diuji secara langsung terasa responsif dan tidak menunjukkan timeout.
- Tidak ada indikasi loading infinite dari sisi endpoint yang diuji.
- Namun observasi request duplication, waterfall browser, dan perceived UI slowness belum bisa disimpulkan penuh karena browser automation tidak tersedia di sesi ini.

---

## UX Observation

- Flow invalid credential secara backend jelas (`401`) dan source UI menunjukkan copy yang cukup ramah untuk login gagal.
- Copy invalid Google Sheet id masih terlalu generik, sehingga troubleshooting user berpotensi membingungkan.
- Error import saat schema mismatch jatuh ke generic 500; dari perspektif user biasa ini akan terasa seperti aplikasi rusak, bukan masalah compatibility environment.
- Verifikasi loading state, toast, disabled state, dan responsive belum lengkap karena keterbatasan browser runtime.

---

## Security Observation

- Workspace isolation pada endpoint yang diuji terlihat kuat: foreign workspace access ditolak `403`.
- RBAC settings sesuai untuk owner/member pada endpoint workspace configuration.
- Upload hardening Task 5 tidak bisa divalidasi penuh end-to-end untuk valid upload path karena flow import sudah gagal lebih dulu di layer DB compatibility.
- Model login yang tidak konsisten dengan user session tetap berisiko secara security/behavioral semantics karena boundary auth menjadi tidak intuitif.

---

## Data Integrity Observation

- Tidak ditemukan kebocoran data lintas workspace pada dashboard summary, budgets, import history, dan workspace configuration.
- Budget dan import history menunjukkan data yang berbeda sesuai workspace aktif, yang mendukung integritas isolation.
- Namun data integrity flow import belum bisa dinyatakan aman karena upload baru gagal sebelum masuk ke lifecycle review/approval/sync.
- Karena import gagal pada runtime env saat ini, observasi duplicate detection, owner/category assignment, period, amount, sync status, dan history untuk upload baru belum bisa diselesaikan secara end-to-end.

---

## Final Recommendation

Apakah aman lanjut Task 6?

NO

Alasan:

1. Masih ada blocker runtime nyata pada flow import utama, yaitu schema mismatch untuk `workspace_id`.
2. Flow login user biasa masih tidak konsisten terhadap endpoint yang membutuhkan user session sebenarnya.
3. Beberapa area penting masih hanya PARTIAL/SKIPPED karena browser automation tidak tersedia di sesi ini, jadi kita belum punya bukti UI-level yang cukup kuat untuk menyatakan regresi aman sepenuhnya.

Rekomendasi checkpoint sebelum Task 6:

- Selesaikan lebih dulu keputusan operasional untuk compatibility schema/import runtime.
- Tegaskan model auth yang dipakai untuk regression UAT: apakah local static login memang intended, atau harus selalu lewat user JWT/session riil.
- Jika memungkinkan, ulangi regression pass dengan browser automation atau QA manual browser agar area dashboard, analytics, search, logout, dan import UI bisa ditutup dengan evidence visual.
