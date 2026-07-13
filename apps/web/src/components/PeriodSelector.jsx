import { CalendarDays, Check, ChevronDown } from "lucide-react";
import { useEffect, useId, useMemo, useRef, useState } from "react";

import {
  PERIOD_MODES,
  PERIOD_PRESETS,
  createYearMonthPeriod,
  formatPeriodLabel,
  isDateRangeValid,
  normalizePeriodState,
} from "../utils/periodState";

const MONTH_OPTIONS = [
  { value: "", label: "Semua bulan" },
  { value: 1, label: "Januari" },
  { value: 2, label: "Februari" },
  { value: 3, label: "Maret" },
  { value: 4, label: "April" },
  { value: 5, label: "Mei" },
  { value: 6, label: "Juni" },
  { value: 7, label: "Juli" },
  { value: 8, label: "Agustus" },
  { value: 9, label: "September" },
  { value: 10, label: "Oktober" },
  { value: 11, label: "November" },
  { value: 12, label: "Desember" },
];

const PeriodSelector = ({
  period,
  availableYears = [],
  fallbackYear = "",
  onChange,
}) => {
  const triggerRef = useRef(null);
  const panelRef = useRef(null);
  const titleId = useId();
  const normalizedPeriod = useMemo(
    () => normalizePeriodState(period, fallbackYear),
    [fallbackYear, period],
  );
  const [isOpen, setIsOpen] = useState(false);
  const [draftYear, setDraftYear] = useState(normalizedPeriod.year || fallbackYear || "");
  const [draftMonth, setDraftMonth] = useState(normalizedPeriod.month || "");
  const [draftStartDate, setDraftStartDate] = useState(normalizedPeriod.startDate || "");
  const [draftEndDate, setDraftEndDate] = useState(normalizedPeriod.endDate || "");

  const yearOptions = availableYears.length ? availableYears : [fallbackYear].filter(Boolean);
  const currentLabel = formatPeriodLabel(normalizedPeriod, { compact: true });
  const rangeIsComplete = Boolean(draftStartDate && draftEndDate);
  const rangeIsValid = isDateRangeValid(draftStartDate, draftEndDate);

  useEffect(() => {
    if (!isOpen) return undefined;

    setDraftYear(normalizedPeriod.year || fallbackYear || "");
    setDraftMonth(normalizedPeriod.month || "");
    setDraftStartDate(normalizedPeriod.startDate || "");
    setDraftEndDate(normalizedPeriod.endDate || "");

    const handlePointerDown = (event) => {
      if (
        panelRef.current?.contains(event.target)
        || triggerRef.current?.contains(event.target)
      ) {
        return;
      }

      setIsOpen(false);
      triggerRef.current?.focus();
    };

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        setIsOpen(false);
        triggerRef.current?.focus();
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [fallbackYear, isOpen, normalizedPeriod]);

  const closeSelector = () => {
    setIsOpen(false);
    triggerRef.current?.focus();
  };

  const applyPeriod = (nextPeriod) => {
    onChange?.(nextPeriod);
    closeSelector();
  };

  return (
    <div className="period-selector">
      <button
        ref={triggerRef}
        type="button"
        className="period-selector__trigger"
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((current) => !current)}
      >
        <CalendarDays size={18} aria-hidden="true" />
        <span className="period-selector__label">
          {currentLabel}
        </span>
        <ChevronDown size={16} aria-hidden="true" />
      </button>

      {isOpen && (
        <div
          ref={panelRef}
          className="period-selector__panel"
          role="dialog"
          aria-modal="false"
          aria-labelledby={titleId}
        >
          <div className="period-selector__header">
            <p id={titleId} className="text-sm font-bold text-main">
              Pilih periode
            </p>
            <p className="text-xs text-muted">
              Atur konteks data yang ditampilkan.
            </p>
          </div>

          <section aria-label="Preset cepat">
            <p className="period-selector__section-label">
              Pilihan cepat
            </p>
            <div className="period-selector__preset-grid">
              {PERIOD_PRESETS.map((preset) => {
                const isSelected = (
                  normalizedPeriod.mode === PERIOD_MODES.allTime
                    ? preset.value === "all_time"
                    : normalizedPeriod.mode === PERIOD_MODES.preset
                      && normalizedPeriod.preset === preset.value
                );

                return (
                  <button
                    key={preset.value}
                    type="button"
                    className={`period-selector__option ${isSelected ? "is-selected" : ""}`}
                    aria-pressed={isSelected}
                    onClick={() => applyPeriod(
                      preset.value === "all_time"
                        ? { mode: PERIOD_MODES.allTime }
                        : { mode: PERIOD_MODES.preset, preset: preset.value }
                    )}
                  >
                    <span>{preset.label}</span>
                    {isSelected && <Check size={14} aria-hidden="true" />}
                  </button>
                );
              })}
            </div>
          </section>

          <section aria-label="Bulan tertentu">
            <p className="period-selector__section-label">
              Bulan tertentu
            </p>
            <div className="period-selector__month-grid">
              <label>
                <span>Tahun</span>
                <select
                  value={draftYear}
                  onChange={(event) => setDraftYear(event.target.value)}
                  className="form-control w-full rounded-lg px-3 text-sm"
                >
                  {yearOptions.length === 0 && (
                    <option value="">Belum ada data</option>
                  )}
                  {yearOptions.map((year) => (
                    <option key={year} value={year}>
                      {year}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                <span>Bulan</span>
                <select
                  value={draftMonth}
                  onChange={(event) => setDraftMonth(event.target.value)}
                  className="form-control w-full rounded-lg px-3 text-sm"
                >
                  {MONTH_OPTIONS.map((month) => (
                    <option key={month.value || "all"} value={month.value}>
                      {month.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <button
              type="button"
              className="secondary-button mt-3 h-10 w-full rounded-lg px-3 text-sm font-bold"
              disabled={!draftYear}
              onClick={() => applyPeriod(createYearMonthPeriod(draftYear, draftMonth))}
            >
              Terapkan bulan
            </button>
          </section>

          <section aria-label="Rentang tanggal khusus">
            <p className="period-selector__section-label">
              Pilih rentang tanggal
            </p>
            <div className="period-selector__month-grid">
              <label>
                <span>Tanggal mulai</span>
                <input
                  type="date"
                  value={draftStartDate}
                  onChange={(event) => setDraftStartDate(event.target.value)}
                  className="form-control w-full rounded-lg px-3 text-sm"
                />
              </label>

              <label>
                <span>Tanggal akhir</span>
                <input
                  type="date"
                  value={draftEndDate}
                  onChange={(event) => setDraftEndDate(event.target.value)}
                  className="form-control w-full rounded-lg px-3 text-sm"
                />
              </label>
            </div>

            {rangeIsComplete && !rangeIsValid && (
              <p className="mt-2 text-xs font-semibold text-red-600 dark:text-red-300">
                Tanggal mulai tidak boleh setelah tanggal akhir.
              </p>
            )}

            <div className="mt-3 grid grid-cols-2 gap-2">
              <button
                type="button"
                className="secondary-button h-10 rounded-lg px-3 text-sm font-bold"
                onClick={closeSelector}
              >
                Batal
              </button>
              <button
                type="button"
                className="primary-button h-10 rounded-lg px-3 text-sm font-bold"
                disabled={!rangeIsValid}
                onClick={() => applyPeriod({
                  mode: PERIOD_MODES.dateRange,
                  startDate: draftStartDate,
                  endDate: draftEndDate,
                })}
              >
                Terapkan
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
};

export default PeriodSelector;
