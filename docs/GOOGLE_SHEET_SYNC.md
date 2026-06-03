# Google Sheet Sync

## Overview

Data flow:

Google OAuth -> Google Sheet Source -> Sync Job -> Transactions -> Rule-Based Classification -> Dashboard Analytics

The sync uses the connected user's Google OAuth token to read Google Sheets and stores normalized rows in `public.transactions`. Dashboard analytics use `public.transactions` as the source of truth.

After Sync Now writes inserted or updated transactions, the backend runs
rule-based classification for those transaction IDs. User-defined
classification rules are applied before built-in rules, and manual overrides
(`method = 'manual'` or `status = 'manual_override'`) are not overwritten.
The standalone `POST /api/classifications/run` endpoint remains available for
backfill and manual debug runs.

## Required Columns

Each synced tab must include these columns. Header matching is case-insensitive and trims whitespace.

- `Waktu Transaksi`
- `Nama Transaksi`
- `Kategori`
- `Harga`
- `Source Dana`
- `Keterangan`

Accepted aliases:

- `Waktu Transaksi`: `Tanggal`, `Tanggal Transaksi`
- `Nama Transaksi`: `Transaksi`, `Deskripsi`
- `Kategori`: `Category`
- `Harga`: `Amount`, `Nominal`
- `Source Dana`: `Sumber Dana`, `Payment Source`
- `Keterangan`: `Note`, `Notes`

Optional:

- `Nama`

Year and month filters are derived from `Waktu Transaksi`, not from source configuration. Actual dashboard data only includes `transaction_date <= current_date`.

Slash numeric dates from Google Sheets default to US ordering for this project:

- `01/15/2026` -> January 15, 2026
- `1/5/2026` -> January 5, 2026
- `05/06/2026` -> May 6, 2026

Indonesian fallback is still supported when the first segment is greater than 12, for example `15/01/2026` -> January 15, 2026.

## Currency Rule

All spreadsheet amounts are treated as Rupiah / IDR. There is no currency conversion.

`transactions.amount` stores the numeric Rupiah amount. `Rp` symbols, spaces, thousand separators, and decimal separators are normalized during sync. Negative values are stored as absolute amounts for MVP; `direction` still comes from `Kategori`.

Supported examples:

- `Rp25.000`
- `25.000`
- `25000`
- `25,000`
- `25.000,50`
- `25000.50`
- numeric values returned by the Google Sheets API

## Direction Rule

`Kategori` is the source of truth.

- `Kategori = Income` -> `direction = income`
- `Kategori = Saving` -> `direction = saving_transfer`
- Any other non-empty category -> `direction = expense`
- Empty category on an otherwise valid transaction -> `direction = expense`

Explicit expense categories:

- `Tagihan non rutin`
- `Tagihan Tahunan`
- `Gift`
- `Transportasi non rutin`

## Category Normalization

`raw_category` keeps the original `Kategori` value. Display-oriented normalized category is stored in `raw_payload._category_normalized`.

Initial mappings:

- `income` -> `Income`
- `saving` -> `Saving`
- `groceries`, `grocery`, `belanja bulanan` -> `Groceries`
- `food`, `makanan`, `jajan`, `resto`, `restaurant` -> `Food`
- `transport`, `transportasi`, `bensin`, `parkir`, `gojek`, `grab` -> `Transport`
- `tagihan non rutin` -> `Tagihan non rutin`
- `tagihan tahunan` -> `Tagihan Tahunan`
- `gift` -> `Gift`
- `transportasi non rutin` -> `Transportasi non rutin`
- `rent`, `apartemen`, `sewa` -> `Housing`
- `listrik`, `internet`, `utility` -> `Utilities`
- `health`, `obat`, `dokter` -> `Health`
- `entertainment`, `hiburan`, `pacaran` -> `Entertainment`

If no mapping matches, the trimmed raw category is used.

## Row Validation

Valid transaction row:

- `Waktu Transaksi` exists and can be parsed.
- `Nama Transaksi` exists.
- `Harga` exists and parses to a number greater than 0.
- `Kategori` may be empty; empty category defaults to expense.

Skipped row:

- Empty row.
- Repeated header row.
- Summary row such as exact `Total`, `Subtotal`, `Grand Total`, `Saldo`, `Balance`, or `Summary`.
- Clear template/sample row.
- Future transaction date.

Failed row:

- Looks like a transaction but date cannot be parsed.
- Looks like a transaction but amount cannot be parsed.
- Looks like a transaction but title is empty.

Skipped rows do not fail the whole tab. Failed rows are counted and sync continues for valid rows.

## Sync Diagnostics

Sync responses may include:

- `failed_reasons`
- `skipped_reasons`
- `failed_samples`
- `skipped_samples`
- `classification`
- `warnings`

Safe reasons:

- `empty_row`
- `repeated_header`
- `summary_row`
- `future_transaction_date`
- `invalid_date`
- `invalid_amount`
- `empty_title`
- `invalid_header`
- `google_read_failed`
- `normalization_failed`
- `database_write_failed`

Samples include only `sheet_name`, `row_number`, `reason`, and optional `category`. They do not include full title, amount, note, raw row, token, or credentials.

`classification` contains safe counters such as `processed`, `classified`,
`updated`, `low_confidence`, `skipped_manual`, `errors`, and `duration_ms`.
If classification fails after transaction sync succeeds, the sync response can
still be successful and include `warnings: ["classification_failed"]`.

## Dashboard Source Of Truth

- Table: `public.transactions`
- Year/month: `transaction_date`
- Income/expense/saving: `direction`
- Category breakdown: `raw_category` and normalized category metadata
- Actual dashboard filter: `transaction_date <= current_date`

## SQL Diagnostics & Validation Queries

All sample outputs use dummy data.

### A. Cek Google OAuth Connection

Tujuan:
Memastikan OAuth connection tersedia.

Kapan digunakan:
Sebelum test/sync Google Sheet.

Query:

```sql
select
  id,
  workspace_id,
  user_id,
  google_email,
  status,
  token_expiry,
  access_token_encrypted is not null as has_access_token,
  refresh_token_encrypted is not null as has_refresh_token,
  created_at,
  updated_at
from public.google_oauth_connections
order by created_at desc;
```

Contoh output:

| google_email | status | has_access_token | has_refresh_token |
| --- | --- | --- | --- |
| user@example.com | active | true | true |

Cara membaca:
`status` harus `active`, dan `has_access_token` harus `true`.

Red flag:
Tidak ada row, `status = disconnected`, atau `has_access_token = false`.

### B. Cek Google Sheet Sources Aktif

Tujuan:
Memastikan source yang dipakai sync adalah source aktif.

Kapan digunakan:
Setelah Save Source atau sebelum Sync Now.

Query:

```sql
select
  id,
  workspace_id,
  sheet_id,
  sheet_name,
  year,
  status,
  last_synced_at,
  null::text as error_message,
  created_at,
  updated_at
from public.google_sheet_sources
where status = 'active'
order by created_at desc;
```

Contoh output:

| sheet_name | year | status | last_synced_at |
| --- | --- | --- | --- |
| null | null | active | 2026-06-01 09:30:00+00 |

Cara membaca:
Expected source Week 4 biasanya `sheet_name = null`, `year = null`, dan `status = active`.

Red flag:
Tidak ada active source, source lama masih punya `sheet_name`/`year`, atau status bukan `active`.

### C. Cek Sync Job Terakhir

Tujuan:
Melihat hasil Sync Now terakhir.

Kapan digunakan:
Setelah klik Sync Now.

Query:

```sql
select
  id,
  sheet_source_id,
  status,
  total_rows,
  inserted_rows,
  updated_rows,
  skipped_rows,
  failed_rows,
  error_message,
  started_at,
  finished_at,
  created_at
from public.sync_jobs
order by created_at desc
limit 10;
```

Contoh output:

| status | total_rows | inserted_rows | skipped_rows | failed_rows | finished_at |
| --- | ---: | ---: | ---: | ---: | --- |
| success | 550 | 480 | 65 | 5 | 2026-06-01 09:35:00+00 |

Cara membaca:
`status = success`, `finished_at` terisi, dan `inserted_rows > 0`.

Red flag:
`status = failed`, `finished_at` null, atau `failed_rows` mendominasi total rows.

### D. Cek Total Transaksi Dan Range Tanggal

Tujuan:
Memastikan transaksi valid masuk dan field penting tidak kosong.

Kapan digunakan:
Setelah sync selesai.

Query:

```sql
select
  count(*) as total_transactions,
  min(transaction_date) as min_date,
  max(transaction_date) as max_date,
  count(*) filter (where transaction_date is null) as missing_date,
  count(*) filter (where amount is null) as missing_amount,
  count(*) filter (where amount <= 0) as non_positive_amount
from public.transactions;
```

Contoh output:

| total_transactions | min_date | max_date | missing_date | missing_amount | non_positive_amount |
| ---: | --- | --- | ---: | ---: | ---: |
| 480 | 2026-01-01 | 2026-06-01 | 0 | 0 | 0 |

Cara membaca:
Expected: `missing_date = 0`, `missing_amount = 0`, `non_positive_amount = 0`.

Red flag:
`total_transactions = 0` atau banyak missing/non-positive amount.

### E. Cek Transaksi Per Sheet/Tab

Tujuan:
Memastikan semua tab bulanan valid masuk.

Kapan digunakan:
Jika dashboard hanya menampilkan sebagian bulan.

Query:

```sql
select
  raw_payload->>'_sheet_name' as sheet_name,
  count(*) as rows,
  min(transaction_date) as min_date,
  max(transaction_date) as max_date,
  sum(amount) as total_amount
from public.transactions
group by 1
order by 1;
```

Contoh output:

| sheet_name | rows | min_date | max_date | total_amount |
| --- | ---: | --- | --- | ---: |
| Start 1 Januari | 80 | 2026-01-01 | 2026-01-31 | 3500000 |
| Start 1 Februari | 75 | 2026-02-01 | 2026-02-28 | 3300000 |

Cara membaca:
Setiap tab bulanan valid seharusnya punya rows.

Red flag:
Hanya satu tab masuk, atau tab `Configuration`/`Summary` ikut masuk.

### F. Cek Distribusi Direction

Tujuan:
Memastikan classifier direction berjalan benar.

Kapan digunakan:
Setelah Sync Now selesai, terutama setelah perubahan normalizer/classifier.

Query:

```sql
select
  direction,
  count(*) as rows,
  sum(amount) as total_amount
from public.transactions
group by direction
order by total_amount desc;
```

Contoh output:

| direction | rows | total_amount |
| --- | ---: | ---: |
| expense | 420 | 18500000 |
| saving_transfer | 12 | 3500000 |
| income | 2 | 12500000 |

Cara membaca:
Income hanya kategori `Income`, saving hanya kategori `Saving`, selain itu expense.

Red flag:
Semua row expense padahal ada `Income`/`Saving`, atau banyak kategori expense masuk `saving_transfer`.

### G. Cek Raw Category + Direction

Tujuan:
Melihat mapping kategori asli ke direction.

Kapan digunakan:
Saat angka summary terasa tidak masuk akal.

Query:

```sql
select
  raw_category,
  direction,
  count(*) as rows,
  sum(amount) as total_amount
from public.transactions
group by raw_category, direction
order by sum(amount) desc;
```

Contoh output:

| raw_category | direction | rows | total_amount |
| --- | --- | ---: | ---: |
| Groceries | expense | 90 | 5000000 |
| Income | income | 2 | 12500000 |
| Saving | saving_transfer | 12 | 3500000 |
| Tagihan Tahunan | expense | 3 | 1800000 |
| Gift | expense | 4 | 750000 |

Cara membaca:
`Income -> income`, `Saving -> saving_transfer`, semua lainnya `expense`.

Red flag:
`Tagihan Tahunan` masuk saving, `Gift` masuk income, atau `Saving` masuk expense.

### H. Validasi Classifier Income/Saving/Expense

Tujuan:
Menguji kategori bisnis penting secara langsung.

Kapan digunakan:
Setelah perubahan classifier.

Query:

```sql
select
  raw_category,
  direction,
  count(*) as rows,
  sum(amount) as total_amount
from public.transactions
where lower(trim(coalesce(raw_category, ''))) in (
  'income',
  'saving',
  'tagihan non rutin',
  'tagihan tahunan',
  'gift',
  'transportasi non rutin'
)
group by raw_category, direction
order by raw_category, direction;
```

Contoh output:

| raw_category | direction | rows | total_amount |
| --- | --- | ---: | ---: |
| Gift | expense | 4 | 750000 |
| Income | income | 2 | 12500000 |
| Saving | saving_transfer | 12 | 3500000 |
| Tagihan Tahunan | expense | 3 | 1800000 |
| Tagihan non rutin | expense | 5 | 900000 |
| Transportasi non rutin | expense | 2 | 300000 |

Cara membaca:
Semua mapping harus sesuai aturan bisnis.

Red flag:
Income bukan income, Saving bukan saving_transfer, atau explicit expense bukan expense.

### I. Cek Future Rows

Tujuan:
Memastikan actual dashboard tidak menghitung transaksi masa depan.

Kapan digunakan:
Jika dashboard current year menampilkan bulan masa depan.

Query:

```sql
select
  count(*) as future_rows
from public.transactions
where transaction_date > current_date;
```

Contoh output:

| future_rows |
| ---: |
| 0 |

Cara membaca:
Expected ideal: `future_rows = 0`.

Red flag:
Nilai lebih dari 0 berarti future rows sudah masuk actual transactions.

### J. Detail Future Rows Jika Ada

Tujuan:
Menemukan future row yang perlu dibersihkan saat development.

Kapan digunakan:
Jika query future rows lebih dari 0.

Query:

```sql
select
  transaction_date,
  title,
  raw_category,
  amount,
  direction,
  raw_payload->>'_sheet_name' as sheet_name,
  raw_payload->>'_row_number' as row_number
from public.transactions
where transaction_date > current_date
order by transaction_date
limit 100;
```

Contoh output ideal:

No rows returned

Contoh output bermasalah:

| transaction_date | title | raw_category | amount | sheet_name | row_number |
| --- | --- | --- | ---: | --- | ---: |
| 2026-09-01 | Template row | Groceries | 100000 | Start 1 September | 12 |

Cara membaca:
Idealnya tidak ada rows.

Red flag:
Ada transaksi future masuk actual transactions.

### K. Cek Transaksi Yang Kemungkinan Bukan Transaksi

Tujuan:
Mendeteksi total/subtotal/header yang ikut tersimpan.

Kapan digunakan:
Jika jumlah transaksi terlalu besar.

Query:

```sql
select
  transaction_date,
  title,
  raw_category,
  amount,
  direction,
  raw_payload->>'_sheet_name' as sheet_name,
  raw_payload->>'_row_number' as row_number
from public.transactions
where
  lower(trim(coalesce(title, ''))) in ('total', 'subtotal', 'grand total')
  or lower(trim(coalesce(raw_category, ''))) in ('total', 'subtotal', 'grand total')
  or title is null
  or trim(title) = ''
order by transaction_date desc
limit 100;
```

Contoh output ideal:

No rows returned

Cara membaca:
Tidak boleh ada row summary/header.

Red flag:
Ada row total/subtotal masuk transactions.

### L. Cek Duplicate Berdasarkan Source + Row Key

Tujuan:
Memastikan sync idempotent.

Kapan digunakan:
Setelah sync ulang source yang sama.

Query:

```sql
select
  sheet_source_id,
  external_row_key,
  count(*) as duplicate_count
from public.transactions
group by sheet_source_id, external_row_key
having count(*) > 1;
```

Contoh output ideal:

No rows returned

Cara membaca:
Tidak ada duplicate.

Red flag:
Ada row hasil query berarti sync tidak idempotent.

### M. Cek Monthly Dashboard Source

Tujuan:
Memastikan data bulanan dashboard berasal dari actual transactions.

Kapan digunakan:
Jika chart bulanan terlihat salah.

Query:

```sql
select
  extract(year from transaction_date)::int as year,
  extract(month from transaction_date)::int as month,
  direction,
  count(*) as rows,
  sum(amount) as total_amount
from public.transactions
where transaction_date is not null
  and transaction_date <= current_date
group by 1, 2, 3
order by 1 desc, 2, 3;
```

Contoh output:

| year | month | direction | rows | total_amount |
| ---: | ---: | --- | ---: | ---: |
| 2026 | 1 | expense | 80 | 3500000 |
| 2026 | 1 | income | 1 | 6250000 |
| 2026 | 1 | saving_transfer | 2 | 1000000 |

Cara membaca:
Bulan future untuk current year tidak muncul.

Red flag:
Bulan future muncul, atau direction tercampur.

### N. Cek Available Years Untuk Dropdown

Tujuan:
Memastikan dropdown tahun berasal dari actual transactions.

Kapan digunakan:
Jika dropdown tahun kosong/salah.

Query:

```sql
select distinct
  extract(year from transaction_date)::int as year
from public.transactions
where transaction_date is not null
  and transaction_date <= current_date
order by year desc;
```

Contoh output:

| year |
| ---: |
| 2026 |

Cara membaca:
Tahun yang muncul harus sesuai data actual.

Red flag:
Tahun future muncul.

### O. Cek Category Breakdown Dashboard

Tujuan:
Memastikan pie/category chart hanya berisi expense.

Kapan digunakan:
Jika Income/Saving muncul di breakdown expense.

Query:

```sql
select
  coalesce(raw_category, 'Uncategorized') as category,
  count(*) as rows,
  sum(amount) as total_amount
from public.transactions
where transaction_date is not null
  and transaction_date <= current_date
  and direction = 'expense'
group by 1
order by total_amount desc;
```

Contoh output:

| category | rows | total_amount |
| --- | ---: | ---: |
| Groceries | 90 | 5000000 |
| Makanan | 80 | 4200000 |
| Tagihan Tahunan | 3 | 1800000 |
| Gift | 4 | 750000 |

Cara membaca:
Hanya expense categories yang muncul.

Red flag:
Income/Saving muncul di breakdown expense.

### P. Cek Top Spending Dashboard

Tujuan:
Memastikan top spending hanya transaksi expense.

Kapan digunakan:
Jika gaji/saving muncul di top spending.

Query:

```sql
select
  transaction_date,
  title,
  raw_category,
  source_fund,
  amount,
  note
from public.transactions
where transaction_date is not null
  and transaction_date <= current_date
  and direction = 'expense'
order by amount desc
limit 20;
```

Contoh output:

| transaction_date | title | raw_category | source_fund | amount |
| --- | --- | --- | --- | ---: |
| 2026-01-15 | Service motor | Transportasi non rutin | BCA | 750000 |
| 2026-02-10 | Tagihan asuransi | Tagihan Tahunan | BCA | 1200000 |

Cara membaca:
Hanya expense transaksi, tanpa Income/Saving.

Red flag:
Income/Saving muncul.

### Q. Cek Summary Manual Dashboard

Tujuan:
Membandingkan summary SQL dengan summary cards UI.

Kapan digunakan:
Jika angka dashboard terasa tidak valid.

Query:

```sql
select
  coalesce(sum(amount) filter (where direction = 'income'), 0) as total_income,
  coalesce(sum(amount) filter (where direction = 'expense'), 0) as total_expense,
  coalesce(sum(amount) filter (where direction = 'saving_transfer'), 0) as total_saving,
  coalesce(sum(amount) filter (where direction = 'income'), 0)
    - coalesce(sum(amount) filter (where direction = 'expense'), 0)
    - coalesce(sum(amount) filter (where direction = 'saving_transfer'), 0)
    as net_cashflow,
  count(*) as transaction_count
from public.transactions
where transaction_date is not null
  and transaction_date <= current_date;
```

Contoh output:

| total_income | total_expense | total_saving | net_cashflow | transaction_count |
| ---: | ---: | ---: | ---: | ---: |
| 12500000 | 18500000 | 3500000 | -9500000 | 434 |

Cara membaca:
Angka mendekati summary card dashboard.

Red flag:
Expense terlalu besar karena Income/Saving ikut dihitung expense.

### R. Cek Summary Per Tahun

Tujuan:
Melihat ringkasan actual per tahun.

Kapan digunakan:
Untuk validasi dropdown dan summary tahunan.

Query:

```sql
select
  extract(year from transaction_date)::int as year,
  coalesce(sum(amount) filter (where direction = 'income'), 0) as total_income,
  coalesce(sum(amount) filter (where direction = 'expense'), 0) as total_expense,
  coalesce(sum(amount) filter (where direction = 'saving_transfer'), 0) as total_saving,
  count(*) as transaction_count
from public.transactions
where transaction_date is not null
  and transaction_date <= current_date
group by 1
order by 1 desc;
```

Contoh output:

| year | total_income | total_expense | total_saving | transaction_count |
| ---: | ---: | ---: | ---: | ---: |
| 2026 | 12500000 | 18500000 | 3500000 | 434 |

Cara membaca:
Tahun harus sesuai dropdown dashboard.

Red flag:
Tahun future muncul.

### S. Cek Summary Per Bulan Untuk Tahun Tertentu

Tujuan:
Validasi monthly charts untuk satu tahun.

Kapan digunakan:
Jika monthly spending/income/saving chart tidak sesuai.

Query:

```sql
select
  extract(month from transaction_date)::int as month,
  coalesce(sum(amount) filter (where direction = 'income'), 0) as total_income,
  coalesce(sum(amount) filter (where direction = 'expense'), 0) as total_expense,
  coalesce(sum(amount) filter (where direction = 'saving_transfer'), 0) as total_saving,
  count(*) as transaction_count
from public.transactions
where transaction_date is not null
  and transaction_date <= current_date
  and extract(year from transaction_date)::int = 2026
group by 1
order by 1;
```

Contoh output:

| month | total_income | total_expense | total_saving | transaction_count |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 6250000 | 3500000 | 1000000 | 83 |
| 2 | 6250000 | 3300000 | 1000000 | 78 |

Cara membaca:
Bulan future tidak muncul untuk current year.

Red flag:
Bulan setelah current month muncul.

### T. Query Cleanup Development

Warning:
Query cleanup hanya untuk development. Jangan jalankan di production tanpa backup.

Tujuan:
Reset hasil sync workspace development.

Kapan digunakan:
Saat ingin sync ulang dari kondisi kosong di environment development.

Query:

```sql
delete from public.transactions
where workspace_id = '<workspace_id>';

delete from public.sync_jobs
where workspace_id = '<workspace_id>';
```

Contoh output:

```text
DELETE 1240
DELETE 8
```

Cara membaca:
Rows yang terhapus sesuai data workspace development.

Red flag:
Workspace ID salah atau query dijalankan di production.

## How To Investigate Invalid Dashboard Data

1. Cek sync job terakhir.
2. Cek total transaksi dan range tanggal.
3. Cek future rows.
4. Cek transaksi per sheet.
5. Cek direction distribution.
6. Cek raw_category + direction.
7. Cek duplicate row key.
8. Cek monthly dashboard source.
9. Bandingkan summary manual dashboard dengan card dashboard.

## Expected Healthy Data State

Sebuah sync dianggap sehat jika:

- OAuth connection active.
- Google Sheet source active.
- Sync job terakhir success.
- `finished_at` terisi.
- `transactions` memiliki row dari semua tab bulanan valid.
- `future_rows = 0`.
- Duplicate query return no rows.
- Income hanya masuk `income`.
- Saving hanya masuk `saving_transfer`.
- Semua kategori lain masuk `expense`.
- Dashboard summary manual mendekati angka yang tampil di UI.

## Known Limitation

Sync Now automatically runs Week 5 rule-based classification for inserted and
updated transactions. AI-assisted classification remains disabled and is not
used by sync.
