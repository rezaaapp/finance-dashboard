# Omon UX Copywriting Guideline

## Philosophy

Omon membantu pengguna memahami kondisi keuangan dan bertindak dengan percaya diri. Copy harus menjelaskan keadaan, dampak, dan langkah berikutnya tanpa membuat pengguna menebak. Gunakan bahasa manusia; detail teknis tetap di log atau tampilan developer.

Prinsip: jelas sebelum ringkas, sebut hasil nyata, jelaskan konsekuensi sebelum action berisiko, bedakan kosong/proses/gagal, dan berikan satu langkah berikutnya yang relevan.

## Voice and Tone

Gunakan Bahasa Indonesia modern yang hangat, tenang, dan langsung. English dipakai hanya untuk action modern yang disetujui. Penjelasan, toast, error, confirmation, insight, dan empty state memakai Bahasa Indonesia. Hindari bahasa kaku, menggurui, atau bercanda saat membahas error dan data sensitif.

## English Terms to Keep

Gunakan persis: Login, Logout, Dashboard, Import, Export, Review, Save Source, Save Changes, Sync Now, Test Connection, Disconnect, Upload PDF, dan Reset Synced Data.

Jangan membuat variasi untuk action yang sama. Contoh: gunakan `Save Source`, bukan `Simpan Source` atau `Save Spreadsheet`.

## Bahasa Indonesia Financial Terms

Gunakan: Pengeluaran, Pemasukan, Tabungan, Kebutuhan, Keinginan, dan Anggaran. Hindari expense, income, saving, dan budget dalam penjelasan pengguna. Nama internal tidak perlu diubah.

## Button and Action Naming Rules

- Awali dengan kata kerja dan sebut objek bila konteks belum jelas.
- Import Review memakai `Upload PDF`, `Review`, `Simpan ke Omon`, `Tolak`, dan `Selesai`.
- Jangan gunakan Approve, Reject, Tinjau, atau Lewati.
- Gunakan `Batalkan Pilihan`, bukan `Hapus Pilihan`, saat data tidak dihapus.
- Action destruktif menyebut objek: `Hapus Anggaran`, bukan `Ya`.
- Loading menjelaskan proses: `Menyimpan...`, `Menyinkronkan...`, `Menghapus...`.
- `Save Changes` hanya untuk draft konfigurasi. Connect, Test, Save Source, Sync, Disconnect, dan Reset adalah action langsung.

## Toast Examples

Toast menyebut hasil dan objek yang berubah.

- `Spreadsheet berhasil disinkronkan.`
- `Source berhasil disimpan.`
- `Anggaran berhasil diperbarui.`
- `PDF Blu berhasil diimport.`
- `Semua perubahan berhasil disimpan.`
- `Undangan berhasil dikirim ke nama@email.com.`
- `Akses Google berhasil diputuskan. Data Omon dan konfigurasi source tetap aman.`

Hindari Success, Done, Completed, atau `Berhasil` tanpa objek/hasil.

## Error Message Structure

Susun error dalam tiga bagian: apa yang gagal, penyebab yang mungkin jika aman disampaikan, lalu action berikutnya.

> Sinkronisasi gagal.  
> Omon belum dapat mengambil data dari Google Sheet.  
> Periksa koneksi atau coba lagi.

Sediakan `Coba Lagi`, kembali, atau action alternatif untuk error yang memblokir. Jangan tampilkan endpoint, API Error, OAuth, registry, HTTP 500, Internal Server Error, stack trace, nama environment, atau raw backend error yang belum dipastikan aman. Jangan menyamarkan kegagalan sebagai empty state.

## Confirmation Dialog Pattern

Confirmation berisi:

1. Judul berupa pertanyaan spesifik.
2. Ringkasan konsekuensi.
3. **Yang akan terjadi** — data/akses yang berubah atau dihapus.
4. **Yang tetap aman** — data yang tidak berubah.
5. Tombol `Batal` dan tombol destruktif yang menyebut action.

Contoh Disconnect: akses Omon ke Google diputuskan dan Sync Now tidak tersedia; data Omon, Google Sheet asli, source, dan konfigurasi workspace tetap aman.

Untuk Reset Synced Data, selalu tegaskan bahwa Google Sheet asli tidak dihapus/diubah dan data dapat disinkronkan kembali.

## Empty State Pattern

Empty state menjawab: apa yang belum ada, mengapa itu terjadi/penting, dan apa langkah berikutnya. Gunakan CTA bila action-nya jelas.

> **Belum ada riwayat Import.**  
> Upload PDF Blu untuk memulai Import pertama.  
> `Upload PDF`

Untuk hasil filter kosong, gunakan `Tidak ditemukan transaksi.` dan `Clear Filter`. Jangan gunakan copy setup awal untuk hasil filter kosong.

## Terms to Avoid

- Success, Done, Completed
- Approve, Reject, Tinjau, Lewati
- Expense, Income, Saving, Budget dalam penjelasan
- Endpoint, API Error, OAuth, registry, HTTP 500, Internal Server Error
- Raw backend error yang belum user-safe
- `Hapus Pilihan` saat hanya membatalkan selection
- `Reset` tanpa menjelaskan objek/dampak
- Identitas produk selain `Belum ada namanya` sampai branding final disetujui

## Area Examples

### Google Sheet

Path: `Connect Google` → `Tambahkan URL spreadsheet` → `Test Connection` → `Save Source` → `Sync Now` → `Buka Dashboard`. Success: `Spreadsheet berhasil disinkronkan. 235 transaksi ditambahkan.` Error: `Sinkronisasi gagal. Omon belum dapat mengambil data dari Google Sheet. Periksa koneksi atau coba lagi.`

### Import

Gunakan action yang disetujui. Empty Review: `Belum ada transaksi untuk di-Review. Upload PDF Blu untuk menyiapkan transaksi.` Partial result harus menjelaskan secara terpisah bahwa transaksi sudah tersimpan di Omon tetapi sebagian belum terkirim ke Google Sheet.

### Anggaran

Gunakan Anggaran, Pengeluaran, dan Pemasukan. Success: `Anggaran Makanan berhasil diperbarui.` Confirmation menyebut anggaran yang dihapus dan bahwa seluruh transaksi tetap aman.

### Search

Primary action: `Cari Transaksi`. No result: `Tidak ditemukan transaksi.` Error: `Pencarian belum dapat dilakukan. Periksa koneksi, lalu coba lagi.`

### Dashboard

Loading: `Omon sedang menyiapkan Dashboard kamu...`. Blocking error: `Dashboard belum dapat dibuka.` dengan `Coba Lagi`, `Buka Settings`, atau `Logout`. No-data copy harus membedakan Google belum terhubung, source belum ada, dan source belum disinkronkan.

### Settings

Draft: `Ada perubahan yang belum disimpan.` + `Save Changes`. Immediate integration actions tidak menunggu Save Changes. Success: `Semua perubahan berhasil disimpan.` Reset mengikuti pola **Yang akan terjadi** dan **Yang tetap aman**.

## Review Checklist

- Identitas produk dan istilah konsisten.
- Toast menyebut hasil nyata.
- Error memberi recovery.
- Confirmation menyebut affected dan safe scope.
- Empty state memberi langkah berikutnya.
- Copy bebas istilah developer/raw error.
- Action dapat dipahami tanpa warna atau ikon.
