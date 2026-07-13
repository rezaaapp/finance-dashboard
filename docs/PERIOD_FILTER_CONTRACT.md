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
