# Budgeting & Alerts

## Tujuan fitur

Budgeting & Alerts membantu user mengatur dan mengevaluasi budget pengeluaran bulanan. Fitur ini hanya dipakai untuk expense, bukan income, saving, atau transfer.

Tujuan utamanya sederhana:
- user tahu berapa budget bulan ini
- user tahu berapa yang sudah terpakai
- user tahu kategori mana yang belum dianggarkan
- user tahu kategori mana yang mendekati atau melewati budget

## Business flow

Tambah budget:
- User memilih tahun dan bulan.
- User memilih kategori dari dropdown.
- Dropdown hanya berisi kategori transaksi expense dari spreadsheet.
- User mengisi nominal budget.
- Sistem menyimpan budget untuk workspace, tahun, bulan, dan kategori.

Edit budget:
- User mengubah nominal pada kategori yang sudah punya budget.
- User klik Simpan.
- Sistem memperbarui amount budget.
- Transaksi tidak berubah.

Delete budget:
- Tombol Hapus hanya muncul untuk kategori yang sudah punya budget id.
- Sistem meminta konfirmasi.
- Budget kategori dihapus.
- Transaksi tetap tersimpan.
- Jika kategori masih punya transaksi expense, kategori muncul sebagai Belum dianggarkan.

Reset Budget Bulan Ini:
- User menghapus seluruh budget pada periode aktif.
- Sistem hanya menghapus budget pada workspace, year, dan month yang dipilih.
- Transaksi tetap aman.
- Budget bulan lain tidak ikut berubah.

## Planning

Planning dipakai untuk bulan depan. User bisa menyiapkan budget sebelum periode berjalan. Transaksi aktual mungkin belum ada, tetapi estimasi dan rekomendasi dari histori tetap bisa dipakai.

## Monitoring

Monitoring dipakai untuk bulan berjalan. Sistem membandingkan budget dengan transaksi expense aktual dan menampilkan alert aktif.

## Evaluation

Evaluation dipakai untuk bulan lampau. UI memakai wording Review Anggaran dan Hasil Evaluasi. Budget masih bisa diubah, tetapi perubahan tersebut akan mengubah hasil evaluasi.

## Budget lifecycle

Budget dimulai dari rencana, dipakai untuk monitoring saat bulan berjalan, lalu menjadi bahan evaluasi setelah bulan lewat.

Budget tidak otomatis terbawa ke bulan lain. Reset budget hanya berlaku pada periode aktif yang dipilih.

## Budget calculation

Budget disimpan per:
- workspace_id
- year
- month
- category

Actual spending dihitung dari transaksi expense saja. Definisi expense mengikuti financial summary:
- need
- want
- uncategorized

Income, saving, dan transfer tidak masuk perhitungan budget.

## Recommendation calculation

Rekomendasi memakai 3 bulan sebelum periode yang dipilih. Contoh: jika user memilih Juni 2026, histori memakai Maret, April, dan Mei 2026.

Estimasi 3 bulan adalah rata-rata spending expense kategori tersebut pada histori yang tersedia.

Rekomendasi dihitung dengan:
- estimasi 3 bulan x 1,1
- dibulatkan ke kelipatan Rp 50.000

Jika tidak ada histori, UI menampilkan Belum ada histori untuk kategori ini.

## Alert threshold

80%:
- status Perlu dipantau
- severity info

90%:
- status Hampir habis
- severity warning

100%:
- status Melewati budget
- severity danger

Alert dihitung realtime dari budget dan actual spending. Untuk MVP belum ada table alerts dan belum ada read/unread.

## Expense only budgeting

Budgeting hanya untuk pengeluaran. Kategori yang hanya pernah muncul sebagai income, saving, atau transfer tidak ditampilkan di dropdown budget.

Jika kategori pernah dipakai sebagai expense, kategori boleh muncul. Nama kategori tidak diubah, tidak direname, dan tidak dimapping otomatis.

## Available categories

`available_categories` adalah sumber utama dropdown. Data ini berasal dari `transactions.raw_category` untuk workspace aktif, tetapi hanya dari transaksi expense-like.

Normalisasi dropdown:
- trim spasi
- kategori kosong dibuang
- deduplicate case-insensitive
- sort alfabetis
- nama asli kategori tetap dipakai

Fallback default hanya dipakai jika workspace belum punya kategori transaksi expense sama sekali.

## Progress bar

Jika kategori punya budget:
- 0-79% normal
- 80-89% info
- 90-99% warning
- 100% atau lebih danger

Jika budget 0 tetapi spending ada, UI tidak menampilkan 0%. UI menampilkan Belum dianggarkan.

## Status badge

Mapping status:
- `is_budgeted = false`: Belum dianggarkan
- usage < 80: Aman
- 80-89: Perlu dipantau
- 90-99: Hampir habis
- >= 100: Melewati budget

## Reset Budget Bulan Ini

Reset Budget Bulan Ini menghapus seluruh budget pada periode aktif. Operasi ini tidak menghapus transaksi dan tidak menghapus budget bulan lain.

Konfirmasi:

```text
Reset seluruh budget periode ini?

Budget akan dihapus.

Transaksi tetap aman dan tidak akan dihapus.
```

## UI Flow

Header menampilkan:
- Total Budget
- Total Terpakai
- Total Sisa
- Kategori Melewati Budget
- Kategori Belum Dianggarkan

Form tambah budget menampilkan:
- dropdown kategori expense
- input amount
- estimasi 3 bulan
- rekomendasi
- histori
- tombol Pakai rekomendasi
- tombol Tambah

Budget per Kategori memakai table/grid di desktop dan compact card di mobile.

Action:
- Budgeted: Simpan dan Hapus
- Unbudgeted: Anggarkan

## API

GET /api/budgets?year=&month=
- Mengambil budget periode aktif.

POST /api/budgets
- Membuat atau update budget kategori.

PUT /api/budgets/{id}
- Mengupdate satu budget.

DELETE /api/budgets/{id}
- Menghapus satu budget kategori.

DELETE /api/budgets?year=&month=
- Reset seluruh budget periode aktif.
- Response: `{"deleted_count": X}`

GET /api/dashboard/budget-forecast?year=&month=
- Mengambil summary, categories, alerts, available_categories, dan category_recommendations.

## Database

table budgets:
- id
- workspace_id
- year
- month
- category
- amount
- created_at
- updated_at

Constraint:
- unique(workspace_id, year, month, category)
- amount tidak boleh negatif

table budget_category_ignores:
- Masih ada untuk kompatibilitas sementara.
- Tidak dipakai lagi oleh UI MVP.

## Edge cases

Budget kosong:
- Kategori transaksi expense tetap muncul sebagai Belum dianggarkan.
- Reset Budget Bulan Ini disabled.

Transaksi kosong:
- Budget yang sudah dibuat tetap tampil.
- Spending 0.
- Dropdown memakai fallback expense default.

Kategori tanpa budget:
- Tampil sebagai Belum dianggarkan.
- User bisa klik Anggarkan.

Budget tanpa transaksi:
- Tetap tampil.
- Terpakai 0.
- Sisa sama dengan nilai budget.

Future period:
- Dipakai sebagai Rencana Anggaran.
- Alert aktif tidak ditampilkan.
- User tetap bisa tambah, edit, hapus, dan reset budget.

Past period:
- Dipakai sebagai Review Anggaran.
- Alert ditampilkan sebagai Hasil Evaluasi.
- Mengubah budget mengubah hasil evaluasi.

Current period:
- Dipakai sebagai Budgeting & Alerts.
- Alert aktif tampil normal.

## Workspace isolation

Semua query dibatasi workspace aktif. Budget, category, spending, recommendation, dan reset tidak boleh bocor antar workspace.

## Testing checklist

- Dropdown tidak berisi kategori income.
- Dropdown tidak berisi kategori saving.
- Dropdown tidak berisi kategori transfer.
- Dropdown hanya berisi kategori expense.
- Tambah budget.
- Edit budget.
- Hapus satu budget.
- Reset Budget Bulan Ini.
- Rekomendasi tampil saat kategori punya histori.
- Pakai rekomendasi hanya mengisi amount.
- Progress bar sesuai usage.
- Status badge sesuai usage.
- Current period.
- Past period.
- Future period.
- Mobile layout.
- Desktop layout.
- Kategori panjang.
- Banyak kategori.
- Tidak ada overlap.

## Future improvement

- Copy budget bulan sebelumnya.
- Notification budget.
- Budget template.
- Master category per workspace.
- Category mapping.
- Recommendation analytics yang lebih personal.
