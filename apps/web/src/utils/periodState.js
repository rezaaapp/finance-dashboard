const MONTH_NAMES = [
  "Januari",
  "Februari",
  "Maret",
  "April",
  "Mei",
  "Juni",
  "Juli",
  "Agustus",
  "September",
  "Oktober",
  "November",
  "Desember",
];

export const PERIOD_MODES = {
  yearMonth: "year_month",
  dateRange: "date_range",
  preset: "preset",
  allTime: "all_time",
};

export const PERIOD_PRESETS = [
  { value: "last_7_days", label: "7 hari terakhir" },
  { value: "last_1_month", label: "1 bulan terakhir" },
  { value: "last_3_months", label: "3 bulan terakhir" },
  { value: "last_6_months", label: "6 bulan terakhir" },
  { value: "last_year", label: "Tahun lalu" },
  { value: "all_time", label: "Semua periode" },
];

const pad = (value) => String(value).padStart(2, "0");

export const toIsoDate = (date) => (
  `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
);

const parseIsoDate = (value) => {
  if (!value || typeof value !== "string") return null;

  const [year, month, day] = value.split("-").map(Number);

  if (!year || !month || !day) return null;

  const date = new Date(year, month - 1, day);

  return Number.isNaN(date.getTime()) ? null : date;
};

const addDays = (date, amount) => {
  const nextDate = new Date(date);
  nextDate.setDate(nextDate.getDate() + amount);
  return nextDate;
};

const addMonths = (date, amount) => {
  const nextDate = new Date(date);
  const originalDay = nextDate.getDate();
  nextDate.setDate(1);
  nextDate.setMonth(nextDate.getMonth() + amount);
  const lastDay = new Date(nextDate.getFullYear(), nextDate.getMonth() + 1, 0).getDate();
  nextDate.setDate(Math.min(originalDay, lastDay));
  return nextDate;
};

export const createYearMonthPeriod = (year, month = "") => ({
  mode: PERIOD_MODES.yearMonth,
  year: year ? Number(year) : "",
  month: month ? Number(month) : "",
});

export const createDefaultPeriod = (year = "", month = "") => (
  year ? createYearMonthPeriod(year, month) : { mode: PERIOD_MODES.yearMonth, year: "", month: "" }
);

export const normalizePeriodState = (period, fallbackYear = "") => {
  if (!period || typeof period !== "object") {
    return createDefaultPeriod(fallbackYear);
  }

  if (period.mode === PERIOD_MODES.dateRange) {
    return {
      mode: PERIOD_MODES.dateRange,
      startDate: period.startDate || "",
      endDate: period.endDate || "",
    };
  }

  if (period.mode === PERIOD_MODES.preset) {
    return {
      mode: PERIOD_MODES.preset,
      preset: period.preset || "last_7_days",
    };
  }

  if (period.mode === PERIOD_MODES.allTime) {
    return { mode: PERIOD_MODES.allTime };
  }

  return createYearMonthPeriod(period.year || fallbackYear, period.month || "");
};

export const getCompatibilityPeriod = (period, fallbackYear = "") => {
  const normalized = normalizePeriodState(period, fallbackYear);

  if (normalized.mode === PERIOD_MODES.yearMonth) {
    return {
      selectedYear: normalized.year ? String(normalized.year) : "",
      selectedMonth: normalized.month ? String(normalized.month) : "",
    };
  }

  return {
    selectedYear: fallbackYear ? String(fallbackYear) : "",
    selectedMonth: "",
  };
};

export const resolvePresetRange = (preset, referenceDate = new Date()) => {
  const today = new Date(
    referenceDate.getFullYear(),
    referenceDate.getMonth(),
    referenceDate.getDate(),
  );

  if (preset === "last_year") {
    const previousYear = today.getFullYear() - 1;
    return {
      startDate: `${previousYear}-01-01`,
      endDate: `${previousYear}-12-31`,
    };
  }

  if (preset === "last_7_days") {
    return {
      startDate: toIsoDate(addDays(today, -6)),
      endDate: toIsoDate(today),
    };
  }

  const monthMap = {
    last_1_month: -1,
    last_3_months: -3,
    last_6_months: -6,
  };

  if (monthMap[preset]) {
    return {
      startDate: toIsoDate(addDays(addMonths(today, monthMap[preset]), 1)),
      endDate: toIsoDate(today),
    };
  }

  return { startDate: "", endDate: "" };
};

export const toPeriodQuery = (period) => {
  const normalized = normalizePeriodState(period);

  if (normalized.mode === PERIOD_MODES.dateRange) {
    if (!normalized.startDate || !normalized.endDate) return {};
    return {
      start_date: normalized.startDate,
      end_date: normalized.endDate,
    };
  }

  if (normalized.mode === PERIOD_MODES.preset) {
    return { period_mode: normalized.preset };
  }

  if (normalized.mode === PERIOD_MODES.allTime) {
    return { period_mode: "all_time" };
  }

  return {
    ...(normalized.year && { year: normalized.year }),
    ...(normalized.month && { month: normalized.month }),
  };
};

export const isDateRangeValid = (startDate, endDate) => {
  const start = parseIsoDate(startDate);
  const end = parseIsoDate(endDate);

  return Boolean(start && end && start <= end);
};

const formatDate = (isoDate, { includeYear = true } = {}) => {
  const date = parseIsoDate(isoDate);
  if (!date) return "";

  const day = date.getDate();
  const month = MONTH_NAMES[date.getMonth()];
  const year = date.getFullYear();

  return includeYear ? `${day} ${month} ${year}` : `${day} ${month}`;
};

export const formatPeriodLabel = (period, options = {}) => {
  const normalized = normalizePeriodState(period);
  const compact = Boolean(options.compact);

  if (normalized.mode === PERIOD_MODES.allTime) {
    return "Semua periode";
  }

  if (normalized.mode === PERIOD_MODES.preset) {
    if (normalized.preset === "last_year") {
      const range = resolvePresetRange("last_year", options.referenceDate || new Date());
      return `Tahun ${range.startDate.slice(0, 4)}`;
    }

    return PERIOD_PRESETS.find((item) => item.value === normalized.preset)?.label || "Periode pilihan";
  }

  if (normalized.mode === PERIOD_MODES.dateRange) {
    const start = parseIsoDate(normalized.startDate);
    const end = parseIsoDate(normalized.endDate);

    if (!start || !end) return "Pilih rentang tanggal";

    const sameYear = start.getFullYear() === end.getFullYear();
    const sameMonth = sameYear && start.getMonth() === end.getMonth();

    if (sameMonth) {
      return `${start.getDate()}-${end.getDate()} ${MONTH_NAMES[end.getMonth()]} ${end.getFullYear()}`;
    }

    if (sameYear && compact) {
      return `${formatDate(normalized.startDate, { includeYear: false })}-${formatDate(normalized.endDate)}`;
    }

    return `${formatDate(normalized.startDate, { includeYear: !sameYear })}-${formatDate(normalized.endDate)}`;
  }

  if (normalized.year && normalized.month) {
    return `${MONTH_NAMES[Number(normalized.month) - 1]} ${normalized.year}`;
  }

  if (normalized.year) {
    return `Tahun ${normalized.year}`;
  }

  return "Belum ada periode";
};
