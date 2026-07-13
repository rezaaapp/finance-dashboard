# Period Filter Contract

This document describes the backend period parameters prepared for the future date picker UI.

## Supported Modes

- `year_month`: existing behavior using `year` and optional `month`.
- `date_range`: explicit inclusive `start_date` and `end_date`.
- `preset`: relative period presets, sent through `period_mode` for now.
- `all_time`: no date bounds.

## Parameters

- `year`: numeric year, kept for backward compatibility.
- `month`: numeric month, only meaningful with `year`.
- `start_date`: ISO date string, `YYYY-MM-DD`.
- `end_date`: ISO date string, `YYYY-MM-DD`.
- `period_mode`: accepts `all_time` or preset values such as `last_7_days`, `last_1_month`, `last_3_months`, `last_6_months`, and `last_year`.

## Resolution Priority

1. Explicit `start_date` and `end_date`.
2. `period_mode=all_time`.
3. Preset values in `period_mode`.
4. Existing `year` and optional `month`.
5. Existing default behavior.

`end_date` is inclusive at the API boundary. Internally, repositories use a half-open range with `transaction_date < end_date + 1 day`.

## Scope Notes

Dashboard, Analytics, and Search data endpoints can consume the shared period model. Budget remains monthly and continues to use `year` and `month`.

## Frontend State

The web app uses a single period state object with these modes:

- `year_month`: `{ mode, year, month }`
- `date_range`: `{ mode, startDate, endDate }`
- `preset`: `{ mode, preset }`
- `all_time`: `{ mode }`

`apps/web/src/utils/periodState.js` owns:

- query mapping to backend parameters;
- preset date definitions;
- Indonesian period labels;
- compatibility values for legacy `selectedYear` and `selectedMonth` consumers.

Legacy consumers may still receive derived `selectedYear` and `selectedMonth` while Epic 3 completes cross-feature alignment.

## Frontend Presets

- `last_7_days`: rolling 7-day range including today.
- `last_1_month`: rolling range ending today.
- `last_3_months`: rolling range ending today.
- `last_6_months`: rolling range ending today.
- `last_year`: previous calendar year.
- `all_time`: sends `period_mode=all_time`.

The current selector sends preset modes as `period_mode` instead of resolving them into query date ranges, keeping the backend contract as the source of truth for request filtering.

## Compatibility Notes

- Budget remains monthly. When the global period is not monthly, Budget receives the existing derived year fallback and an empty month until Epic 3 resolves the product behavior.
- The main Refresh button still calls the existing source refresh with the derived selected year. For non-monthly periods this is intentionally conservative and does not attempt to sync every external source.
- Custom date range changes are staged in the selector and only update global state after `Terapkan`.
