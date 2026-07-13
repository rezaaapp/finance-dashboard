import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  PERIOD_MODES,
  createYearMonthPeriod,
  formatPeriodLabel,
  isDateRangeValid,
  normalizePeriodState,
  resolvePresetRange,
  toPeriodQuery,
} from "./periodState.js";

const referenceDate = new Date(2026, 6, 13);

describe("period state query mapping", () => {
  it("maps year_month to year and month only", () => {
    assert.deepEqual(
      toPeriodQuery(createYearMonthPeriod(2026, 7)),
      { year: 2026, month: 7 },
    );
  });

  it("maps date_range to inclusive start and end dates", () => {
    assert.deepEqual(
      toPeriodQuery({
        mode: PERIOD_MODES.dateRange,
        startDate: "2026-07-01",
        endDate: "2026-07-31",
      }),
      { start_date: "2026-07-01", end_date: "2026-07-31" },
    );
  });

  it("maps preset without stale year or month", () => {
    assert.deepEqual(
      toPeriodQuery({ mode: PERIOD_MODES.preset, preset: "last_3_months" }),
      { period_mode: "last_3_months" },
    );
  });

  it("maps all_time without stale parameters", () => {
    assert.deepEqual(
      toPeriodQuery({ mode: PERIOD_MODES.allTime, year: 2026, month: 7 }),
      { period_mode: "all_time" },
    );
  });

  it("falls back safely for invalid state", () => {
    assert.deepEqual(
      normalizePeriodState(null, 2026),
      { mode: PERIOD_MODES.yearMonth, year: 2026, month: "" },
    );
  });
});

describe("period preset resolver", () => {
  it("keeps last_7_days inclusive of today", () => {
    assert.deepEqual(
      resolvePresetRange("last_7_days", referenceDate),
      { startDate: "2026-07-07", endDate: "2026-07-13" },
    );
  });

  it("resolves rolling one month across month boundary", () => {
    assert.deepEqual(
      resolvePresetRange("last_1_month", referenceDate),
      { startDate: "2026-06-14", endDate: "2026-07-13" },
    );
  });

  it("resolves rolling three months", () => {
    assert.deepEqual(
      resolvePresetRange("last_3_months", referenceDate),
      { startDate: "2026-04-14", endDate: "2026-07-13" },
    );
  });

  it("resolves rolling six months across year boundary", () => {
    assert.deepEqual(
      resolvePresetRange("last_6_months", referenceDate),
      { startDate: "2026-01-14", endDate: "2026-07-13" },
    );
  });

  it("resolves last_year as previous calendar year", () => {
    assert.deepEqual(
      resolvePresetRange("last_year", referenceDate),
      { startDate: "2025-01-01", endDate: "2025-12-31" },
    );
  });

  it("handles leap day when rolling one month", () => {
    assert.deepEqual(
      resolvePresetRange("last_1_month", new Date(2024, 2, 31)),
      { startDate: "2024-03-01", endDate: "2024-03-31" },
    );
  });
});

describe("period label formatter", () => {
  it("formats month label", () => {
    assert.equal(formatPeriodLabel(createYearMonthPeriod(2026, 7)), "Juli 2026");
  });

  it("formats same-month range", () => {
    assert.equal(
      formatPeriodLabel({
        mode: PERIOD_MODES.dateRange,
        startDate: "2026-07-07",
        endDate: "2026-07-13",
      }),
      "7-13 Juli 2026",
    );
  });

  it("formats cross-month range", () => {
    assert.equal(
      formatPeriodLabel({
        mode: PERIOD_MODES.dateRange,
        startDate: "2026-06-28",
        endDate: "2026-07-04",
      }),
      "28 Juni-4 Juli 2026",
    );
  });

  it("formats cross-year range", () => {
    assert.equal(
      formatPeriodLabel({
        mode: PERIOD_MODES.dateRange,
        startDate: "2025-12-01",
        endDate: "2026-01-31",
      }),
      "1 Desember 2025-31 Januari 2026",
    );
  });

  it("formats all-time label", () => {
    assert.equal(
      formatPeriodLabel({ mode: PERIOD_MODES.allTime }),
      "Semua periode",
    );
  });

  it("validates custom range ordering", () => {
    assert.equal(isDateRangeValid("2026-07-13", "2026-07-07"), false);
    assert.equal(isDateRangeValid("2026-07-07", "2026-07-13"), true);
  });
});
