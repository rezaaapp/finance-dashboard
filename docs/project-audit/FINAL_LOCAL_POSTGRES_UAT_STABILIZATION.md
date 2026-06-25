# Final Report — Local PostgreSQL UAT Stabilization

## 1. Executive summary

Status akhir fase: **PASS**

Branch: `uat/local-postgres-stabilization`

Fase ini menstabilkan alur utama Omon Dashboard dengan PostgreSQL lokal
sebagai source of truth. Cakupan yang tervalidasi meliputi reset database
lokal, seed workspace, Blu PDF import, review/approve/reject, duplicate
handling, Dashboard, Search, Analytics, serta Budgeting & Alerts.

Seluruh pengujian fase ini menggunakan PostgreSQL lokal. Supabase production
tidak disentuh. Google Sheet belum terhubung dan tetap diperlakukan sebagai
projection/export layer yang terpisah dari persistence ledger Omon.

## 2. Scope completion

| Area | Status | Evidence utama |
|---|---|---|
| Reset local database | PASS | Guard environment lokal, drop/recreate terkontrol, migration dan seed idempotent |
| Seed workspace | PASS | `Admin's Household` tersedia dengan satu member lokal |
| Blu PDF upload/parsing | PASS | 36 transaksi statement Blu terbaca |
| Import review | PASS | Category bootstrap, editable name, approve dan reject tervalidasi |
| Local-first approval | PASS | Final transaction dan registry tersimpan tanpa Google Sheet |
| Duplicate/reupload | PASS | Registry approved/rejected mencegah duplicate dan stale revival |
| Import lifecycle/history | PASS | Review dapat dibuka ulang; terminal/no-new state konsisten |
| Dashboard | PASS | Total, kategori, owner, filter, dan top spending cocok dengan database |
| Search | PASS | Seluruh transaksi Blu terindeks dan keyword merchant/kategori ditemukan |
| Analytics | PASS | Total, kategori, owner, chart, filter, dan empty state konsisten |
| Budgeting & Alerts | PASS | Create, edit/save/reload, forecast, alert, dan reset period tervalidasi |

## 3. UAT status by ID

| UAT ID | Final status | Ringkasan |
|---|---|---|
| UAT-IMPORT-001 | PASS | Default category bootstrap tersedia tanpa auto-assign category |
| UAT-IMPORT-002 | PASS | Approval local-first tidak bergantung pada Google OAuth/Sheet |
| UAT-IMPORT-003 | PASS | Existing review job dapat dibuka kembali setelah refresh |
| UAT-PDF-001 | PASS | Lifecycle 36 transaksi selesai: 25 approved dan 11 rejected |
| UAT-PDF-002 | PASS | Duplicate/reupload dan stale registry handling aman |
| UAT-DATA-001 | PASS | Nama transaksi dapat diedit saat review tanpa mengubah fingerprint |
| UAT-DASH-001 | PASS | Dashboard membaca 25 transaksi dengan total Rp1.867.169 |
| UAT-SEARCH-001 | FAIL, superseded | Audit awal menemukan search index Blu kosong |
| UAT-SEARCH-001A | PASS | Transaksi Blu baru dan existing memiliki search index konsisten |
| UAT-ANALYTICS-001 | PASS | Analytics konsisten dengan PostgreSQL, Dashboard, dan Search |
| UAT-BUDGET-001 | PASS via 001A/001B | Create, calculation, forecast, alert, persistence, dan reset tervalidasi |
| UAT-BUDGET-001A | PASS | Dirty state dan explicit save mencegah edit budget semu |
| UAT-BUDGET-001B | PASS | Reset hanya menghapus budget Juni; evidence lain tetap utuh |

## 4. Bug fixed list

### High

1. **UAT-IMPORT-002 — Approval blocked by Google Sheet dependency**
   - Ledger persistence dipisahkan dari spreadsheet delivery.
   - Missing source/tab/OAuth menjadi controlled skipped/pending delivery.

2. **UAT-IMPORT-003 — Existing review job tidak dapat dibuka kembali**
   - Active review job dapat dipulihkan setelah refresh dan dibuka dari History.

3. **UAT-PDF-002 — Rejected transaction dapat dihidupkan dari stale job**
   - Registry direvalidasi saat action.
   - Existing approved/rejected fingerprint di-skip secara eksplisit.

4. **UAT-SEARCH-001A — Search index kosong untuk transaksi Blu**
   - Approval Blu mengisi `search_text_normalized`.
   - Existing Blu transactions dibackfill dengan kontrak Search yang sama.

5. **UAT-BUDGET-001A — Edit budget tampak tersimpan tetapi hanya local state**
   - Dirty indicator, explicit save, saving state, dan unload warning ditambahkan.

### Medium

1. **UAT-IMPORT-001 — Category options kosong pada fresh workspace**
   - Default category bootstrap ditambahkan tanpa taxonomy management atau
     mapping `review_group` menjadi category.

2. **UAT-PDF-002 — Duplicate response dan no-new lifecycle menyesatkan**
   - Response membedakan newly approved, skipped existing, dan skipped rejected.
   - Job no-new menjadi terminal tanpa CTA review.

3. **UAT-DATA-001 — Nama transaksi tidak dapat dirapikan sebelum approval**
   - Semua draft row mendukung editable display title.

## 5. Commit list

| Commit | Description |
|---|---|
| `0e4c607` | `chore(uat): add guarded local database reset workflow` |
| `b4270ab` | `fix(import): allow local-first approval without spreadsheet` |
| `7b75968` | `fix(import): add category bootstrap for fresh workspace` |
| `d8c0068` | `fix(import): reopen existing review jobs` |
| `d270ea2` | `fix(import): harden duplicate reupload handling` |
| `c500cf7` | `fix(import): allow editing transaction name during review` |
| `dac2837` | `fix(search): index Blu transactions for inquiry` |
| `cf5a645` | `fix(budget): make budget edits explicit and persistent` |

Audit-only UAT yang tidak membutuhkan perubahan kode tidak menghasilkan
commit terpisah.

## 6. Current PostgreSQL evidence

Snapshot final diambil dari PostgreSQL lokal setelah UAT-BUDGET-001B.

### Database and workspace

- Migration applied: **24/24**
- Latest migration: `021_backfill_blu_transaction_search_index.sql`
- Workspace ID: `37cba4df-0935-44a2-b3e3-41e4c332aa14`
- Workspace: `Admin's Household`
- Workspace members: **1**
- Google Sheet sources: **0**
- Google OAuth connections: **0**

### Import lifecycle

- Total import jobs: **5**
- Terminal jobs: `completed` **3**, `cleanup_completed` **2**
- Remaining draft transactions: **0**
- Primary completed job:
  - Job ID: `6bdf20db-299b-4eb7-8d2a-f65e8556aba7`
  - Transactions found/new: **36/36**
  - Final transactions created: **25**
  - Rejected registry entries: **11**
- Subsequent same-PDF jobs menghasilkan `new_transactions = 0` setelah
  registry lengkap.

### Final ledger and registry

- Final transactions: **25**
- Total expense: **Rp1.867.169**
- Distinct import fingerprints: **25**
- Search-indexed transactions: **25/25**
- Approved registry: **25**
- Rejected registry: **11**
- Duplicate final transactions by import fingerprint: **0**

### Category totals

| Category | Transactions | Amount |
|---|---:|---:|
| Groceries | 6 | Rp1.156.449 |
| Food | 16 | Rp463.400 |
| Uncategorized | 2 | Rp229.420 |
| Shopping | 1 | Rp17.900 |
| **Total** | **25** | **Rp1.867.169** |

### Budget state

- June 2026 budget count after reset: **0**
- June total budget: **Rp0**
- June actual spending remains: **Rp1.867.169**
- May 2026 budget count: **2**
- May budget total: **Rp1.700.000**
- Reset June tidak mengubah budget Mei atau transaksi.

## 7. Validation summary

- Full backend unittest: **121 PASS**
- Targeted import suites: **PASS**
- Web lint: **PASS**
- Landing lint where applicable: **PASS**
- Browser UI checks:
  - tidak ada loading loop
  - tidak ada `NaN`
  - tidak ada `Infinity`
  - tidak ada render crash
  - tidak ada relevant browser console error

## 8. Deferred backlog

1. **Google Sheet Integration UAT**
   - Google OAuth connect/reconnect.
   - Spreadsheet dan destination tab selection.
   - Delivery success, retry, failure, dan reconciliation.

2. **Import delivery UX separation**
   - Pisahkan status ledger Omon dan spreadsheet delivery.
   - Future copy: `Tersimpan di Omon`, `Spreadsheet belum terhubung`, dan
     `Menunggu sinkronisasi Spreadsheet`.
   - Tambahkan CTA eksplisit untuk sync ke spreadsheet/tab bernama.

3. **Category taxonomy standardization**
   - Historical categories masih mencampur Bahasa Indonesia dan Inggris.
   - Tidak ada normalization, taxonomy CRUD, atau data migration pada fase ini.
   - `review_group` tetap terpisah dari category.

4. **Budget category source copy**
   - `Sumber kategori mengikuti transaksi dari spreadsheet` tidak lagi akurat
     sepenuhnya karena Blu PDF lokal juga menjadi sumber kategori.

5. **Search owner support**
   - Owner search/filter belum termasuk kontrak Search.

6. **Post-approval transaction editing**
   - Editable name baru tersedia pada Import Review, bukan final transaction.

7. **Legacy title cleanup**
   - Record lama sebelum editable-name UX masih dapat memiliki title kosong
     atau kurang rapi. Tidak dilakukan historical data rewrite.

8. **Branding placeholder**
   - Tetap out of scope.

## 9. Recommendation for next phase

Lanjut ke **Google Sheet Integration UAT** dengan dataset PostgreSQL lokal ini
sebagai protected ledger baseline.

Recommended sequence:

1. Hubungkan Google account non-production melalui OAuth.
2. Tambahkan dedicated UAT spreadsheet source.
3. Pilih destination tab dan kirim transaksi yang sudah tersimpan di Omon.
4. Validasi delivery success dan idempotency.
5. Simulasikan expired OAuth serta invalid sheet/tab.
6. Validasi retry dan reconnect.
7. Pastikan setiap delivery failure tidak mengubah PostgreSQL ledger,
   fingerprints, Dashboard, Search, Analytics, atau Budgeting.
8. Buat laporan Google Sheet Integration UAT sebelum production enablement.

## 10. Final disposition

**Local PostgreSQL UAT Stabilization: COMPLETE / PASS**

Local ledger dan primary product surfaces stabil untuk dilanjutkan ke Google
Sheet Integration UAT. Supabase production tetap tidak disentuh.
