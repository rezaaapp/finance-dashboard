# UAT Local PostgreSQL Reset Workflow

## Status awal

Workflow ini dibuat untuk fase UAT stabilization yang hanya menggunakan
PostgreSQL lokal. Production Supabase tidak termasuk scope dan tidak boleh
menjadi target command reset.

Kondisi sebelum implementasi:

- database lokal `finance_dashboard_local` sudah berisi hasil validasi lama;
- seluruh 22 migration sudah pernah applied, termasuk migration 019;
- reset hanya terdokumentasi sebagai command manual `dropdb` / `createdb`;
- belum ada hard guard terhadap host remote atau database dengan nama salah;
- seed awal sudah tersedia dan idempotent berdasarkan email serta nama
  workspace, tetapi nilai seed aktif belum disejajarkan dengan akun login UAT.

## Risiko yang ditutup

1. Salah target ke PostgreSQL remote atau Supabase.
2. Salah drop database lokal lain.
3. Reset berjalan tanpa konfirmasi eksplisit.
4. Reset berjalan ketika backend atau koneksi database masih aktif.
5. Seed membuat identity/workspace kedua karena email seed berbeda dari login.

## Solusi yang direncanakan

- Tambah script reset khusus `finance_dashboard_local`.
- Izinkan host hanya `localhost`, `127.0.0.1`, atau `::1`.
- Validasi seluruh database URL yang terkonfigurasi, termasuk alias Supabase.
- Tolak reset saat backend port lokal masih listening atau ada koneksi aktif.
- Wajibkan `--confirm finance_dashboard_local`.
- Jalankan migration dari nol, validasi 22 version unik dan migration 019.
- Samakan `SEED_USER_EMAIL` dengan akun login UAT.
- Jalankan seed dua kali untuk membuktikan idempotency.

## Hasil implementasi dan validasi

PASS

### File implementasi

- `backend/scripts/reset_local_database.py`
  - membaca konfigurasi lokal dengan precedence yang sama seperti backend;
  - memvalidasi semua database URL yang terkonfigurasi;
  - hanya menerima host `localhost`, `127.0.0.1`, atau `::1`;
  - hanya menerima database `finance_dashboard_local`;
  - menolak hostname Supabase dan host remote;
  - mewajibkan `--confirm finance_dashboard_local`;
  - menolak reset jika backend port `8000` masih listening;
  - menolak reset jika masih ada koneksi aktif ke database target;
  - drop/recreate dilakukan melalui database admin `postgres`.
- `backend/tests/test_reset_local_database.py`
  - coverage host lokal yang valid;
  - coverage host remote/Supabase yang ditolak;
  - coverage nama database yang salah;
  - coverage seluruh configured URL, termasuk alias Supabase;
  - coverage pemilihan migration URL dan admin URL.
- `package.json`
  - menambahkan command `db:reset:local`.
- `docs/project-audit/LOCAL_POSTGRES_MIGRATION_019_CHECKLIST.md`
  - mendokumentasikan guarded reset dan seed minimal UAT.

### Bukti guard

- `--confirm wrong_database`: ditolak sebelum koneksi reset.
- Backend aktif pada port `8000`: reset ditolak.
- Seluruh instance backend lokal dihentikan sebelum reset dilanjutkan.
- Target yang lolos guard:
  - host: `127.0.0.1`
  - database: `finance_dashboard_local`
  - production Supabase: tidak disentuh

### Hasil reset dan migration

- Drop/recreate database lokal: PASS.
- Migration ditemukan: `22`.
- Migration applied dari nol: `22`.
- `schema_migrations` total: `22`.
- `schema_migrations` distinct version: `22`.
- Migration `019_scope_import_fingerprints_by_workspace.sql`: tepat `1`.

### Bug validasi yang ditemukan

`UAT-RESET-001` ditemukan saat full unittest discovery:

- gejala: import test reset gagal pada `from psycopg import sql`;
- penyebab: test legacy lain memasang stub module `psycopg` tanpa submodule
  `sql`, sehingga hasil bergantung urutan import;
- dampak: full test suite gagal, walaupun targeted reset test dan runtime reset
  sebelumnya berhasil;
- fix: hapus dependency `psycopg.sql` dan gunakan statement statis untuk nama
  database yang memang hard-coded serta sudah dijaga persis
  `finance_dashboard_local`;
- scope: tidak mengubah guard maupun target reset.

Kondisi tepat setelah migration dan sebelum seed:

| Data | Count |
|---|---:|
| users | 0 |
| workspaces | 0 |
| workspace_members | 0 |
| transactions | 0 |
| import_jobs | 0 |
| import_draft_transactions | 0 |
| import_transaction_registry | 0 |

### Hasil seed minimal

Konfigurasi lokal/ignored disamakan dengan identity login UAT:

- `SEED_USER_EMAIL=admin@local.finance-dashboard`
- `SEED_USER_NAME=Admin`
- `SEED_WORKSPACE_NAME=Admin's Household`

Seed dijalankan dua kali. Kedua eksekusi mengembalikan user ID dan workspace ID
yang sama.

Kondisi final:

| Data | Count |
|---|---:|
| users | 1 |
| expected UAT seed user | 1 |
| workspaces | 1 |
| workspace_members | 1 |
| owner memberships | 1 |
| workspace_configurations | 1 |
| transactions | 0 |
| import_jobs | 0 |
| import_draft_transactions | 0 |
| import_transaction_registry | 0 |

Kesimpulan: workflow reset aman untuk target lokal yang ditentukan, migration
berjalan bersih dari nol, dan seed minimal idempotent tanpa membuat
akun/workspace kedua.

### Regression validation

- Guard + migration runner targeted tests: PASS (`10 tests`).
- Backend unittest discovery: PASS (`115 tests`).
- Dashboard frontend lint: PASS.
- Landing frontend lint: PASS.
- `git diff --check`: PASS.
