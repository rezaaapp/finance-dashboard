# Task 7 - Date Range Query Optimization

## 1. Root cause non-sargable date filter

Root cause utama ada di beberapa query analytics/dashboard yang masih mem-filter periode dengan pola:

- `extract(year from transaction_date)::int = ...`
- `extract(month from transaction_date)::int = ...`

Pola itu membuat PostgreSQL harus menerapkan fungsi ke kolom `transaction_date` sebelum membandingkan nilainya, sehingga index pada `transaction_date` atau `(workspace_id, transaction_date)` menjadi jauh kurang efektif untuk range scan.

Perubahan Task 7 menggeser filter periode ke half-open date range:

- `transaction_date >= period_start`
- `transaction_date < period_end`

Dengan bentuk ini, planner bisa lebih mudah memanfaatkan index periode tanpa mengubah hasil bisnis analytics.

## 2. Query/function yang diubah

Function yang diubah di `backend/app/repositories/analytics_repository.py`:

- `_filters`
- `_fetch_summary_totals`
- `_personal_period_totals`
- `get_budget_spending_by_category`
- `get_budget_history_by_category`
- `get_financial_type_breakdown`
- `get_monthly_financial_type_breakdown`
- `get_anomalies`

Catatan:

- `extract(month from t.transaction_date)` masih dipakai di `get_monthly_financial_type_breakdown`, tetapi hanya untuk `SELECT/GROUP BY` output bulan, bukan lagi untuk predicate filter.
- Query `available years` tidak diubah karena itu bukan filter non-sargable terhadap lookup periode utama, melainkan projection distinct year.

## 3. Helper date range

Helper baru:

- `_period_bounds(year=None, month=None)`
- `_append_period_filter(clauses, params, *, date_expr, year=None, month=None)`

Peran helper:

- membentuk `period_start` dan `period_end` untuk filter tahunan atau bulanan
- menjaga implementasi tetap konsisten di beberapa query
- mempertahankan fallback backward-compatible untuk kasus `month` tanpa `year`

Fallback itu sengaja dipertahankan agar perilaku lama tidak berubah bila ada caller lama yang mengirim `month` saja.

## 4. Validasi hasil lama vs baru

Validasi yang dilakukan:

- unit test semantic parity untuk filter `year` saja
- unit test semantic parity untuk filter `year + month`
- unit test SQL builder untuk memastikan predicate sudah berubah ke date range
- unit test join history budget untuk memastikan join periode tidak lagi memakai `extract(...)`
- targeted dashboard view-model regression test untuk memastikan payload agregat dashboard tetap aman

Coverage baru ditambahkan di:

- `backend/tests/test_analytics_date_filters.py`

Tambahan kecil di:

- `backend/tests/test_dashboard_view_model.py`

Tambahan ini hanya memperkuat stub dependency test agar suite lokal bisa jalan konsisten; tidak mengubah app logic.

## 5. Risiko timezone/period edge case

Risiko yang masih perlu dicatat:

1. Query ini mengasumsikan `transaction_date` memang disimpan sebagai nilai date/period lokal yang konsisten. Jika suatu saat field berubah menjadi timestamp dengan konversi timezone aktif, boundary awal/akhir bulan perlu direview ulang.
2. Fallback `month` tanpa `year` masih memakai `extract(month ...)` demi backward compatibility. Ini berarti request model lama tersebut belum sepenuhnya sargable, tetapi behavior tetap aman dan tidak berubah diam-diam.
3. Query yang hanya melakukan projection `extract(year/month ...)` untuk grouping atau label tetap bergantung pada fungsi SQL, tetapi itu tidak lagi berada di jalur predicate yang paling mahal.

## 6. File yang diubah

- `backend/app/repositories/analytics_repository.py`
- `backend/tests/test_analytics_date_filters.py`
- `backend/tests/test_dashboard_view_model.py`
- `docs/project-audit/solving-reports/TASK_07_DATE_RANGE_QUERY_OPTIMIZATION.md`

## 7. Test/validasi

Command yang dijalankan:

```text
.\backend\venv\Scripts\python.exe -m unittest backend.tests.test_analytics_date_filters backend.tests.test_dashboard_view_model
.\backend\venv\Scripts\python.exe -m unittest discover backend\tests
npm --prefix apps/web run lint
npm --prefix apps/landing run lint
```

Hasil:

- targeted analytics/date-range test: PASS
- targeted dashboard regression unit test: PASS
- full backend unittest: PASS (`Ran 104 tests`)
- frontend lint: PASS
- landing lint: PASS

Minimal dashboard regression untuk Task 7 ditutup lewat targeted view-model/backend regression karena perubahan hanya berada di query repository, tanpa perubahan contract endpoint atau flow frontend.

## 8. Commit hash

Commit Task 7:

```text
perf(analytics): use date ranges for period filters
```

Hash final dicatat pada output git/final handoff setelah commit selesai.
