# Week 6 Onboarding Empty State

## First-Time States

The frontend infers onboarding state from existing endpoints:

- `GET /api/google/connection/status`
- `GET /api/data-sources`
- `GET /api/dashboard/available-years`
- Dashboard summary, chart, insight, and analytics responses

States:

- `google_not_connected`: Google account is not connected.
- `no_data_source`: Google is connected, but no Google Sheet source is saved.
- `data_source_not_synced`: a source exists, but no synced year/transaction data is available.
- `no_valid_transactions`: setup exists, but the selected period has no dashboard data.
- `ready`: synced data is available and normal dashboard/analytics rendering can proceed.

## Dashboard Behavior

- Before setup is ready, Dashboard shows a single onboarding card instead of a grid of empty charts.
- No Google connection prompts the user to go to Configuration.
- No data source prompts the user to add a Google Sheet source.
- Saved source without synced data prompts the user to run Sync Now.
- Ready workspace with an empty selected period shows a compact message:
  `No data available for this period.`
- Financial Insights and charts still have local empty placeholders for empty sections.

## Analytics Behavior

- Before setup is ready, Analytics shows the same onboarding guidance as Dashboard.
- If there is no analytics data at all, Analytics shows:
  `Analytics will appear after you sync transactions.`
- If a selected person has no KPI data for the selected period, Personal Finance
  Performance shows:
  `No transactions found for this person in the selected period.`
- Zero KPI cards are not shown as valid analytics when the selected scope has no data.

## Configuration Guidance

Google Sheet setup now follows this lightweight sequence:

1. Connect Google.
2. Add source.
3. Sync Now.

Configuration copy clarifies:

- The spreadsheet should contain required transaction columns.
- Sync reads all valid monthly tabs.
- Year is detected from `Waktu Transaksi`.
- Transactions are classified automatically after sync.

## Manual QA

Existing user with data:

- Dashboard renders normal summary, insights, charts, and tables.
- Analytics renders normal performance cards and charts.
- No false onboarding state appears.

No setup:

- Dashboard shows connect/add/sync guidance instead of empty charts.
- Analytics shows onboarding guidance.
- CTA opens Configuration.

No selected period data:

- Pick a month/year with no transactions.
- Dashboard shows `No data available for this period.`
- Section placeholders remain readable.
- Analytics does not show misleading zero KPI cards.

Configuration:

- Setup sequence is visible.
- Google Sheet helper copy is clear.
- No AI/Gemini wording appears in the setup path.

Responsive and theme:

- Empty states are readable on mobile.
- Dark/light mode text and borders remain legible.
- No horizontal overflow.

## Known Limitations

- The frontend uses existing endpoints only; no new backend onboarding endpoint
  was added.
- Sync Now remains on Configuration next to each source, so dashboard CTAs route
  to Configuration instead of starting sync directly.
- A workspace with legacy saved sheet configuration but no OAuth connection may
  still be prompted to reconnect Google before new sync actions.
