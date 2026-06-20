# Checkpoint Regression Task 6-7

## Status

PARTIAL

Alasan status:

- automated validation utama PASS
- parity endpoint dashboard lama vs endpoint agregat baru PASS
- workspace isolation PASS
- route frontend utama load PASS
- tetapi verifikasi visual/interactive UI penuh hanya bisa dilakukan secara minimal karena browser automation in-app tidak bisa dipakai di environment ini (`CreateProcessAsUserW failed: 5`)

Jadi checkpoint ini cukup kuat untuk safety/regression backend + route/frontend load, tetapi belum setara dengan exploratory visual QA penuh.

## Test Matrix

| Scope | Result | Evidence / Notes |
| --- | --- | --- |
| 1. Dashboard load normal | PASS | `GET /api/dashboard/view-model?year=2026&month=6` = `200`; route `/dashboard` on web = `200` |
| 2. Summary card benar | PASS | payload `dashboard.summary` di view-model identik dengan `/api/dashboard/summary` |
| 3. Filter bulan/tahun benar | PASS | request `year=2026&month=6` berhasil; `selected_period` dan parity endpoint lama konsisten |
| 4. Monthly chart benar | PASS | `monthly_spending`, `monthly_saving`, `monthly_income`, `monthly_financial_types` identik antara view-model dan endpoint lama |
| 5. Category chart benar | PASS | `spending_by_category` identik antara view-model dan endpoint lama |
| 6. Heatmap benar | PASS | `category_heatmap` identik antara view-model dan endpoint lama |
| 7. Top spending benar | PASS | `top_spending` identik antara view-model dan endpoint lama |
| 8. Anomaly table benar | PASS | `anomalies` identik antara view-model dan endpoint lama |
| 9. Analytics page masih load | PARTIAL | route frontend tetap `200`; API analytics utama (`category_heatmap`, `anomalies`, `personal_analytics`, `transactions`) semua `200`; tidak ada inspeksi visual interaktif penuh |
| 10. Search/Inquiry masih load | PASS | `POST /api/inquiry` = `200`; `GET /api/inquiry/detail?query=ma&limit=5&offset=0` = `200` |
| 11. Budget page masih load | PASS | route frontend aktif; `GET /api/budgets?year=2026&month=6` = `200` |
| 12. Blu Import masih load | PASS | route frontend `/import` = `200`; `GET /api/import/history` = `200`; `GET /api/import/category-options` = `200` |
| 13. Import History masih load | PASS | `GET /api/import/history` = `200` |
| 14. Owner grouping benar | PASS | `personal_analytics.users` berisi `All Data` dan `Reza`; payload identik dengan endpoint lama |
| 15. Workspace isolation tetap aman | PASS | token Reza + workspace Divya ke `/api/dashboard/view-model` menghasilkan `403 Workspace access denied` |
| 16. Endpoint lama tetap backward compatible | PASS | semua endpoint legacy dashboard yang dibandingkan tetap `200` dan payload utama identik |
| 17. Endpoint baru `/api/dashboard/view-model` return 200 | PASS | `GET /api/dashboard/view-model?year=2026&month=6` = `200` |
| 18. Bandingkan data endpoint lama vs payload view-model untuk field utama | PASS | semua field utama yang dicek match persis, tanpa mismatch |

## Endpoint yang Dites

### Auth / Context

- `POST /api/auth/login`
- `GET /api/workspaces`
- `GET /api/dashboard/available-years`
- `GET /api/admin/users`
- `POST /api/admin/users/{user_id}/impersonate`

### Dashboard aggregation + legacy endpoints

- `GET /api/dashboard/view-model?year=2026&month=6`
- `GET /api/dashboard/summary?year=2026&month=6`
- `GET /api/dashboard/monthly-spending?year=2026&month=6`
- `GET /api/dashboard/monthly-saving?year=2026&month=6`
- `GET /api/dashboard/monthly-income?year=2026&month=6`
- `GET /api/dashboard/top-spending?year=2026&month=6`
- `GET /api/dashboard/spending-by-category?year=2026&month=6`
- `GET /api/dashboard/financial-types?year=2026&month=6`
- `GET /api/dashboard/monthly-financial-types?year=2026`
- `GET /api/dashboard/category-heatmap?year=2026&month=6`
- `GET /api/dashboard/anomalies?year=2026&month=6`
- `GET /api/dashboard/personal-analytics?year=2026&month=6`
- `GET /api/dashboard/transactions?year=2026&month=6`

### Search / Budget / Import

- `POST /api/inquiry`
- `GET /api/inquiry/detail?query=ma&limit=5&offset=0`
- `GET /api/budgets?year=2026&month=6`
- `GET /api/import/history`
- `GET /api/import/category-options`

### Isolation check

- `GET /api/dashboard/view-model` dengan token Reza + `X-Workspace-Id` milik Divya

### Frontend routes

- `GET http://127.0.0.1:5173/`
- `GET http://127.0.0.1:5173/dashboard`
- `GET http://127.0.0.1:5173/search`
- `GET http://127.0.0.1:5173/import`
- `GET http://127.0.0.1:5173/settings`

## UI / Page yang Dicek

Dicek secara minimal lewat route load dan endpoint pendukung:

- Dashboard
- Search
- Import
- Settings

Catatan:

- semua route frontend di atas return `200`
- semua response memuat root markup SPA
- karena browser automation tidak available di environment ini, visual state chart/table/button tidak diverifikasi secara klik-per-klik

## Data Mismatch

Tidak ada mismatch pada field utama yang dibandingkan.

Hasil parity:

- `summary_equal = true`
- `monthly_spending_equal = true`
- `monthly_saving_equal = true`
- `monthly_income_equal = true`
- `top_spending_equal = true`
- `spending_by_category_equal = true`
- `financial_types_equal = true`
- `monthly_financial_types_equal = true`
- `category_heatmap_equal = true`
- `anomalies_equal = true`
- `personal_analytics_equal = true`
- `transactions_equal = true`

Sample context yang dipakai:

- workspace: `Reza Putra Pratama's Household`
- year: `2026`
- month: `6`

Sample payload sanity:

- `transaction_count = 22`
- `top_spending_rows = 10`
- `category_rows = 3`
- `heatmap_rows = 3`
- `anomaly_rows = 2`
- `personal_analytics.users = [All Data, Reza]`

## Performance Observation

Observasi lokal untuk periode `2026-06`:

- `GET /api/dashboard/view-model` sekitar `6708.69 ms`
- total gabungan 12 endpoint legacy dashboard yang ekuivalen sekitar `15563.03 ms`

Implikasi:

- endpoint agregat Task 6 memang mengurangi total network round-trip secara material
- agregasi belum “murah”, karena backend masih menyusun banyak query internal
- tidak ada indikasi regression yang membuat agregasi lebih lambat daripada total fan-out lama; justru masih lebih efisien untuk bootstrap dashboard

## Issue Baru Jika Ada

Tidak ditemukan regression bug baru pada scope Task 6-7 yang diuji.

Temuan non-blocking:

1. Browser automation in-app tidak bisa dipakai di environment ini, sehingga UI verification bersifat minimal/API-backed, bukan exploratory visual penuh.
2. Workspace login lokal `admin` mengarah ke workspace kosong, jadi checkpoint harus memakai impersonation ke user existing yang memiliki data (`rezaaapp@gmail.com`) agar regression dashboard relevan.

## Validation yang Dijalankan

Automated validation:

```text
.\backend\venv\Scripts\python.exe -m unittest discover -s backend\tests -t .
npm --prefix apps/web run lint
npm --prefix apps/landing run lint
```

Hasil:

- backend unittest: PASS (`Ran 104 tests`)
- web lint: PASS
- landing lint: PASS

Manual/API regression minimal:

- login lokal: PASS
- dashboard aggregation endpoint: PASS
- endpoint legacy dashboard: PASS
- search/budget/import load endpoints: PASS
- workspace isolation: PASS
- frontend route load: PASS

## Final Recommendation

Aman lanjut Task 8: YES

Alasan teknis:

- perubahan Task 6 tidak merusak backward compatibility endpoint lama
- payload endpoint agregat baru konsisten dengan endpoint legacy untuk field utama
- perubahan Task 7 tidak mengubah hasil analytics/dashboard untuk periode yang diuji
- isolasi workspace masih ditegakkan (`403` untuk akses silang workspace)
- automated suite dan lint seluruhnya hijau

Caveat:

- sebelum release yang sangat sensitif UI, tetap bagus jika ada satu putaran exploratory visual QA manual di browser nyata untuk memastikan chart rendering, loading state, dan interaction state tidak berubah secara presentasional
