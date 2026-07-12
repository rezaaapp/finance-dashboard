# Product Experience UAT

## Document Information

| Item | Value |
|------|-------|
| Project | Omon Dashboard |
| Document | Product Experience UAT |
| Version | v1.0 |
| Blueprint | Product Experience Blueprint v1.0 |
| Branch | `uat/product-experience-visual` |
| Status | In Progress |
| Last Updated | 2026-07-11 |

---

# Objective

Dokumen ini menjadi sumber utama seluruh hasil **User Acceptance Testing (UAT)** untuk Product Experience Omon setelah implementasi Product Experience Blueprint v1.0 selesai.

Dokumen ini digunakan untuk:

- Mendokumentasikan seluruh temuan UAT.
- Menentukan prioritas perbaikan.
- Melacak status setiap defect.
- Menghubungkan defect dengan commit perbaikannya.
- Memastikan tidak terjadi regression sebelum release.

Dokumen ini **bukan** backlog fitur baru.

Fokus utama hanya pada validasi Product Experience yang telah diimplementasikan.

---

# Scope

Area yang termasuk dalam Product Experience UAT:

- Landing
- Login
- Dashboard
- Analytics
- Budget
- Search
- Import
- Settings

---

# Focus Area

Seluruh pengujian difokuskan pada:

- User Experience (UX)
- User Interface (UI)
- Responsive Design
- Accessibility
- Content & Copywriting
- Navigation
- Loading State
- Empty State
- Error State
- Success State
- Privacy (Hide Amount)
- Visual Consistency
- Product Consistency
- Regression

---

# Severity

| Level | Description |
|--------|-------------|
| P0 | Critical. Menghambat penggunaan aplikasi atau menyebabkan data/privacy bermasalah. |
| P1 | High. Fitur utama masih berjalan tetapi terdapat masalah penting yang harus diperbaiki sebelum release. |
| P2 | Medium. Mengurangi kualitas Product Experience namun masih memiliki workaround. |
| P3 | Low. Cosmetic issue atau minor polish. |

---

# Status

| Status | Description |
|---------|-------------|
| Open | Belum dikerjakan. |
| In Progress | Sedang diperbaiki. |
| Fixed | Sudah diperbaiki oleh developer. |
| Verified | Sudah diverifikasi setelah perbaikan. |
| Closed | Selesai dan tidak memerlukan tindakan lanjutan. |
| Won't Fix | Disepakati tidak diperbaiki. |

---

# UAT Findings

---

# UAT-PX-001 — Login layout terlalu kompleks

- **Area**: Login
- **Severity**: P2 — Medium
- **Status**: Fixed
- **Category**: Product Experience

## Scenario

Pengguna membuka halaman Login pada desktop.

## Expected

Halaman memiliki satu fokus utama, yaitu proses masuk ke Omon, dengan pola yang sederhana dan familiar.

## Actual

Branding, informasi environment, dan form login ditampilkan sebagai beberapa panel dengan bobot visual hampir sama sehingga fokus pengguna terpecah. Informasi development juga terlihat terlalu dominan.

## Recommendation

- Gunakan satu area login utama yang lebih sederhana.
- Kurangi dominasi panel branding.
- Jadikan informasi environment sebagai elemen sekunder yang lebih ringkas.
- Pertahankan seluruh authentication behavior existing.

## Screenshot

-

## Affected Files

- apps/web/src/pages/Login.jsx

## Fix Commit

- b2e1f5a

---

# UAT-PX-002 — Posisi tombol Google Login kurang familiar

- **Area**: Login
- **Severity**: P2 — Medium
- **Status**: Fixed
- **Category**: Product Experience

## Scenario

Pengguna memilih metode untuk masuk ke Omon.

## Expected

Form login lokal tampil terlebih dahulu, kemudian opsi Google Login tersedia setelah divider **"atau"**, serta mudah dikenali melalui identitas visual Google.

## Actual

Tombol Google Login berada di bagian atas form sehingga halaman terasa kurang mengikuti pola login modern yang umum digunakan. Tombol juga belum menggunakan logo Google sehingga kurang mudah dikenali.

## Recommendation

- Tampilkan username, password, dan tombol login lokal terlebih dahulu.
- Letakkan divider **"atau"** setelah form login lokal.
- Tempatkan tombol **"Lanjutkan dengan Google"** setelah divider.
- Tambahkan logo Google menggunakan asset atau library yang sudah tersedia.
- Jangan mengubah OAuth URL, callback, redirect, token storage, maupun authentication behavior existing.

## Screenshot

-

## Affected Files

- apps/web/src/pages/Login.jsx

## Fix Commit

- b2e1f5a

---

# UAT-PX-003 — Status badge sulit dibedakan pada Light Mode

- **Area**: Dashboard / Analytics
- **Severity**: P2 — Medium
- **Status**: Fixed
- **Category**: Visual Consistency

## Scenario

Pengguna melihat kartu Financial Insights pada Light Mode.

## Expected

Status seperti **Info**, **Neutral**, dan **Danger** mudah dikenali melalui perbedaan warna, kontras, dan hierarki visual sehingga pengguna dapat memahami tingkat prioritas hanya dengan sekali lihat.

## Actual

Badge **Info**, **Danger**, dan **Neutral** memiliki kontras yang rendah terhadap background putih. Perbedaan visual antar status kurang jelas sehingga pengguna harus membaca teks badge untuk memahami statusnya.

## Recommendation

- Tingkatkan kontras badge pada Light Mode.
- Gunakan warna yang lebih konsisten dengan semantic color system.
- Pastikan **Danger** menjadi status yang paling menonjol secara visual.
- Pertahankan konsistensi warna antara Light Mode dan Dark Mode.
- Jangan mengubah business logic maupun aturan penentuan status.

## Screenshot

Financial Insights (Light Mode)

## Affected Files

- apps/web/src/components/FinancialInsights.jsx

## Fix Commit

- b2e1f5a
---

# UAT-PX-004 — Informasi status Privacy terpotong

- **Area**: Dashboard
- **Severity**: P3 — Low
- **Status**: Fixed
- **Category**: Content & Accessibility

## Scenario

Pengguna mengaktifkan fitur **Hide Amount** sehingga kartu Privacy menampilkan status nominal yang sedang disembunyikan.

## Expected

Informasi status ditampilkan secara utuh sehingga dapat dipahami hanya dengan sekali lihat.

## Actual

Teks status terpotong menjadi *"Nominal disembu..."* sehingga informasi utama tidak terbaca secara lengkap.

## Recommendation

- Hindari penggunaan ellipsis pada informasi status yang penting.
- Berikan ruang yang cukup agar teks dapat tampil utuh.
- Apabila diperlukan, izinkan teks membungkus menjadi dua baris daripada dipotong.
- Pertahankan seluruh behavior Hide Amount yang sudah ada.

## Screenshot

Dashboard - Privacy Card (Hide Amount)

## Affected Files

- apps/web/src/pages/Dashboard.jsx

## Fix Commit

- b2e1f5a

---

# Summary

## Findings by Severity

| Severity | Total |
|----------|------:|
| P0 | 0 |
| P1 | 0 |
| P2 | 2 |
| P3 | 0 |

---

## Findings by Status

| Status | Total |
|---------|------:|
| Open | 2 |
| In Progress | 0 |
| Fixed | 0 |
| Verified | 0 |
| Closed | 0 |
| Won't Fix | 0 |

---

# Notes

Seluruh perbaikan UAT harus memenuhi aturan berikut:

- Tidak mengubah backend.
- Tidak mengubah database.
- Tidak membuat migration.
- Tidak mengubah API contract.
- Tidak mengubah business logic.
- Tidak mengubah authentication flow.
- Tidak mengubah authorization.
- Tidak mengubah Google OAuth behavior.
- Tidak mengubah Import workflow.
- Tidak mengubah Budget calculation.
- Tidak mengubah Search semantics.
- Tidak mengubah Dashboard aggregation.

Perbaikan hanya boleh berfokus pada:

- UX
- UI
- Copywriting
- Accessibility
- Responsive behavior
- Privacy presentation
- Visual consistency
- Product consistency

---

# UAT Completion Criteria

Product Experience UAT dianggap selesai apabila:

- Tidak terdapat temuan P0.
- Tidak terdapat temuan P1.
- Seluruh temuan P2 telah diputuskan (Fixed atau Won't Fix).
- Seluruh halaman telah diuji pada desktop.
- Seluruh halaman telah diuji pada mobile.
- Hide Amount telah diverifikasi pada seluruh halaman.
- Regression testing berhasil.
- Product Experience telah sesuai dengan Product Experience Blueprint v1.0.
