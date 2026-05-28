import {
  Bot,
  CalendarDays,
  CheckCircle2,
  Eye,
  Link2,
  LoaderCircle,
  Settings,
  SlidersHorizontal,
} from "lucide-react";
import { useEffect, useState } from "react";

import { saveConfiguration } from "../api/dashboardApi";

import { PRIVACY_MODES } from "../utils/privacy";

const privacyOptions = [
  { label: "Normal", value: PRIVACY_MODES.normal },
  { label: "Hide", value: PRIVACY_MODES.hide },
  { label: "Guest", value: PRIVACY_MODES.guest },
];

const ConfigurationCard = ({
  icon: Icon,
  title,
  description,
  children,
}) => (
  <section className="panel rounded-lg p-5 shadow-lg">
    <div className="mb-5 flex items-start gap-3">
      <div className="icon-badge rounded-xl p-3">
        <Icon size={22} />
      </div>

      <div className="min-w-0">
        <h2 className="text-xl font-bold text-main">
          {title}
        </h2>
        {description && (
          <p className="mt-1 text-sm leading-6 text-muted">
            {description}
          </p>
        )}
      </div>
    </div>

    {children}
  </section>
);

const Configuration = ({
  autoBudget,
  paydayStartDay,
  selectedYear,
  currentSheetName,
  privacyMode,
  onSaveChanges,
  onUnauthorized,
}) => {
  const [draftAutoBudget, setDraftAutoBudget] = useState(autoBudget);
  const [draftPaydayStartDay, setDraftPaydayStartDay] = useState(paydayStartDay);
  const [draftPrivacyMode, setDraftPrivacyMode] = useState(privacyMode);
  const [isSaving, setIsSaving] = useState(false);
  const [showSaved, setShowSaved] = useState(false);

  useEffect(() => {
    setDraftAutoBudget(autoBudget);
  }, [autoBudget]);

  useEffect(() => {
    setDraftPaydayStartDay(paydayStartDay);
  }, [paydayStartDay]);

  useEffect(() => {
    setDraftPrivacyMode(privacyMode);
  }, [privacyMode]);

  useEffect(() => {
    if (!showSaved) {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => {
      setShowSaved(false);
    }, 3000);

    return () => window.clearTimeout(timeoutId);
  }, [showSaved]);

  const handleSave = async () => {
    try {
      setIsSaving(true);

      const payload = {
        year: selectedYear,
        payday_start_day: draftPaydayStartDay,
        auto_budget: draftAutoBudget,
        privacy_mode: draftPrivacyMode,
      };

      const response = await saveConfiguration(payload);

      if (response?.status === "ok") {
        onSaveChanges({
          paydayStartDay: draftPaydayStartDay,
          autoBudget: draftAutoBudget,
          privacyMode: draftPrivacyMode,
        });
        setShowSaved(true);
      }
    } catch (err) {
      console.error(err);

      if (err?.response?.status === 401) {
        onUnauthorized();
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
  <div className="min-w-0 overflow-x-hidden">
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <h1 className="text-2xl font-bold text-main sm:text-3xl">
          Configuration
        </h1>
        <p className="mt-1 text-sm text-muted sm:text-base">
          Centralized settings for financial cycles, budgeting behavior, and integrations.
        </p>
      </div>

      <div
        className={`flex items-center gap-2 text-sm font-medium metric-positive transition-opacity duration-300 ${
          showSaved ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        aria-live="polite"
      >
        <CheckCircle2 size={16} />
        All changes saved to Google Sheets
      </div>
    </div>

    <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
      <ConfigurationCard
        icon={CalendarDays}
        title="Financial Cycle Settings"
        description="Control how transactions are assigned to monthly budget cycles."
      >
        <label className="block text-sm font-semibold text-muted">
          Payday Start Day
        </label>
        <select
          value={draftPaydayStartDay}
          onChange={(event) => setDraftPaydayStartDay(Number(event.target.value))}
          className="form-control mt-2 w-full rounded-xl px-4 py-3 text-base"
        >
          {Array.from({ length: 31 }, (_, index) => index + 1).map((day) => (
            <option key={day} value={day}>
              {day}
            </option>
          ))}
        </select>
        <p className="mt-3 text-sm leading-6 text-muted">
          Transactions on or after this day automatically count toward the next
          month's budget cycle.
        </p>
      </ConfigurationCard>

      <ConfigurationCard
        icon={Settings}
        title="Budgeting Mode"
        description="Switch between manual allocation or historical average forecasting engine."
      >
        <div className="grid grid-cols-2 gap-2 rounded-xl border border-[var(--color-border)] p-1">
          <button
            type="button"
            onClick={() => setDraftAutoBudget(false)}
            className={`rounded-lg px-4 py-3 text-sm font-semibold transition-colors ${
              !draftAutoBudget
                ? "bg-[var(--color-accent-strong)] text-white"
                : "text-muted hover:text-accent"
            }`}
          >
            <SlidersHorizontal size={16} className="mr-2 inline" />
            Manual
          </button>

          <button
            type="button"
            onClick={() => setDraftAutoBudget(true)}
            className={`rounded-lg px-4 py-3 text-sm font-semibold transition-colors ${
              draftAutoBudget
                ? "bg-[var(--color-accent-strong)] text-white"
                : "text-muted hover:text-accent"
            }`}
          >
            <Bot size={16} className="mr-2 inline" />
            AI Auto
          </button>
        </div>

        <div className="mt-4 rounded-xl bg-[var(--color-panel-hover)] px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">
            Active Engine
          </p>
          <p className="mt-1 text-sm font-bold text-main">
            {draftAutoBudget ? "Historical Average Forecasting" : "Manual Allocation"}
          </p>
        </div>
      </ConfigurationCard>

      <ConfigurationCard
        icon={Link2}
        title="System & Integration"
        description="Connection and account-level controls for future commercial scaling."
      >
        <label className="block text-sm font-semibold text-muted">
          Google Sheets Connected Source
        </label>
        <input
          readOnly
          value={currentSheetName || "No active Google Sheets source"}
          className="form-control mt-2 w-full cursor-default rounded-xl px-4 py-3 text-sm"
        />

        <label className="mt-5 block text-sm font-semibold text-muted">
          Account Privacy Mode
        </label>
        <div className="mt-2 grid grid-cols-3 gap-2 rounded-xl border border-[var(--color-border)] p-1">
          {privacyOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setDraftPrivacyMode(option.value)}
              className={`rounded-lg px-3 py-2 text-sm font-semibold transition-colors ${
                draftPrivacyMode === option.value
                  ? "bg-[var(--color-accent-strong)] text-white"
                  : "text-muted hover:text-accent"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>

        <p className="mt-3 flex items-center gap-2 text-sm leading-6 text-muted">
          <Eye size={15} />
          This setting syncs with the dashboard privacy control after saving.
        </p>
      </ConfigurationCard>
    </div>

    <div className="mt-8 flex justify-stretch sm:justify-end">
      <button
        type="button"
        onClick={handleSave}
        disabled={isSaving}
        className="primary-button inline-flex w-full items-center justify-center gap-2 rounded-lg px-6 py-2.5 font-medium shadow-sm disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
      >
        {isSaving && <LoaderCircle size={16} className="animate-spin" />}
        {isSaving ? "Saving..." : "Save Changes"}
      </button>
    </div>
  </div>
  );
};

export default Configuration;
