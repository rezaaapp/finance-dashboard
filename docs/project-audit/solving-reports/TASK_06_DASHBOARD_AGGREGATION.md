# Task 6 — Dashboard Aggregation Endpoint

## 1. Root cause dashboard fan-out

Root cause utama ada di `Dashboard.jsx`:

- initial load memanggil beberapa endpoint terpisah hanya untuk menyiapkan state dashboard
- dashboard main view masih melakukan request fan-out besar untuk summary, charts, insights, transactions, anomaly, dan budget forecast
- sebagian request berjalan sequential, sehingga latency HTTP terakumulasi walaupun source data dasarnya sama

Sebelum perubahan:

- initial load:
  - workspace configuration
  - Google Sheet sources
  - Google connection status
  - available years
- dashboard data load:
  - summary
  - monthly spending
  - monthly saving
  - monthly income
  - top spending
  - spending by category
  - financial types
  - monthly financial types
  - rule-based insights
  - grocery vs food
  - category heatmap
  - transactions
  - category trends
  - personal analytics
  - budget forecast
  - anomalies

Efeknya:

- request count tinggi
- waterfall sequential panjang
- dashboard jadi sensitif terhadap latency per-endpoint

## 2. Endpoint baru

Endpoint baru:

```text
GET /api/dashboard/view-model
```

Tujuan endpoint:

- menggabungkan data utama dashboard ke satu payload
- tetap mempertahankan endpoint lama untuk backward compatibility
- tidak mengubah business logic analytics; endpoint baru hanya mengorkestrasi query yang sudah ada

## 3. Payload response

Struktur response utama:

```json
{
  "workspace": {
    "id": "uuid",
    "name": "Workspace Name",
    "role": "owner",
    "subscription_status": "free"
  },
  "selected_period": {
    "year": 2026,
    "month": 6,
    "name": "optional-user-filter"
  },
  "available_years": [2026, 2025],
  "google_connection": {
    "connected": true,
    "google_email": "user@example.com",
    "status": "active",
    "needs_reconnect": false
  },
  "google_sheet_sources": [],
  "has_active_google_sheet": true,
  "current_sheet_name": "Google Sheet 2026",
  "dashboard": {
    "summary": {},
    "monthly_spending": [],
    "monthly_saving": [],
    "monthly_income": [],
    "top_spending": [],
    "spending_by_category": [],
    "financial_types": [],
    "monthly_financial_types": [],
    "rule_based_insights": {},
    "grocery_vs_food": [],
    "category_heatmap": {},
    "transactions": [],
    "category_trends": {},
    "personal_analytics": {},
    "budget_forecast": {},
    "anomalies": []
  }
}
```

Catatan:

- untuk non-premium role, section premium tetap ada tetapi diisi payload kosong yang aman
- `selected_period.year` otomatis fallback ke available year terbaru bila caller tidak mengirim `year`

## 4. Request lama vs baru

### Dashboard initial load

Sebelum:

- 4 request untuk bootstrap
- lalu 16 request untuk dashboard utama
- total awal efektif: sekitar 20 HTTP requests

Sesudah:

- 1 request `GET /api/dashboard/view-model` saat bootstrap
- 1 request `GET /api/dashboard/view-model` saat fetch dashboard period
- total awal efektif: 2 HTTP requests

### Dashboard period/filter change

Sebelum:

- sekitar 16 request

Sesudah:

- 1 request

### Backward compatibility

- endpoint granular lama tetap ada
- regression check memastikan `/api/dashboard/summary` tetap `200`

## 5. File yang diubah

- `backend/app/api/dashboard.py`
- `backend/tests/test_dashboard_view_model.py`
- `apps/web/src/api/dashboardApi.js`
- `apps/web/src/pages/Dashboard.jsx`

## 6. Test/validasi

### Automated validation

Command yang dijalankan:

```bash
.\backend\venv\Scripts\python.exe -m unittest backend.tests.test_dashboard_view_model
.\backend\venv\Scripts\python.exe -m unittest discover -s backend/tests -t .
npm --prefix apps/web run lint
npm --prefix apps/landing run lint
```

Hasil:

- targeted dashboard view-model backend test: PASS
- full backend unittest: PASS (`Ran 98 tests`)
- web lint: PASS
- landing lint: PASS

### Minimal dashboard regression

Runtime smoke test terhadap backend fresh:

- `GET /api/dashboard/view-model` → `200`
- `GET /api/dashboard/summary` → `200`
- payload `view-model.dashboard.summary.transaction_count` cocok dengan endpoint summary lama
- response `view-model` memuat key utama yang diharapkan:
  - `workspace`
  - `selected_period`
  - `available_years`
  - `google_connection`
  - `google_sheet_sources`
  - `has_active_google_sheet`
  - `current_sheet_name`
  - `dashboard`

## 7. Risiko tersisa

1. Aggregation endpoint saat ini fokus ke dashboard main view. Analytics lazy-load yang lebih dalam (`sourceDanaAnalytics`, `monthlyAllocation`) masih memakai endpoint granular.
2. Backend masih melakukan beberapa query internal untuk menyusun payload agregat. Jadi penghematan terbesar ada di network round-trip frontend, bukan berarti semua query database kini menjadi satu query SQL.
3. Initial load frontend masih dua call pada alur sekarang:
   - bootstrap `view-model`
   - fetch period `view-model`
   
   Ini sudah jauh lebih kecil dari fan-out lama, tetapi masih bisa dioptimalkan lagi nanti jika dibutuhkan.

## 8. Commit hash

Commit Task 6:

```text
perf(dashboard): add aggregate view model endpoint
```

Hash final dicatat pada output handoff setelah commit dibuat.
