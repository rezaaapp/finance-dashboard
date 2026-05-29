import {
  Bot,
  CalendarDays,
  CheckCircle2,
  Copy,
  Eye,
  Link2,
  LoaderCircle,
  Plus,
  Trash2,
  XCircle,
  Settings,
  SlidersHorizontal,
} from "lucide-react";
import { useEffect, useState } from "react";

import {
  getWorkspaceConfiguration,
  refreshDashboardData,
  saveConfiguration,
  updateWorkspaceConfiguration,
} from "../api/dashboardApi";

import { PRIVACY_MODES } from "../utils/privacy";

const privacyOptions = [
  { label: "Normal", value: PRIVACY_MODES.normal },
  { label: "Hide", value: PRIVACY_MODES.hide },
  { label: "Guest", value: PRIVACY_MODES.guest },
];

const truncateMiddle = (value, head = 6, tail = 6) => {
  if (!value || value.length <= head + tail + 3) {
    return value;
  }

  return `${value.slice(0, head)}...${value.slice(-tail)}`;
};

const normalizeGoogleSheetSources = (configuration = {}) => {
  if (Array.isArray(configuration.google_sheet_sources)) {
    return configuration.google_sheet_sources
      .map((source, index) => ({
        id: source.id || source.google_sheet_id || "",
        label: source.label || `Source ${index + 1}`,
      }))
      .filter((source) => source.id);
  }

  return configuration.google_sheet_id
    ? [{
        id: configuration.google_sheet_id,
        label: "Source 1",
      }]
    : [];
};

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
  const [workspaceName, setWorkspaceName] = useState("");
  const [activeGoogleSheetSources, setActiveGoogleSheetSources] = useState([]);
  const [maxGoogleSheetSources, setMaxGoogleSheetSources] = useState(5);
  const [draftGoogleSheetId, setDraftGoogleSheetId] = useState("");
  const [isAddingConnection, setIsAddingConnection] = useState(false);
  const [isConnectingSheet, setIsConnectingSheet] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDisconnectingSheet, setIsDisconnectingSheet] = useState(false);
  const [isLoadingWorkspaceConfiguration, setIsLoadingWorkspaceConfiguration] = useState(true);
  const [showSaved, setShowSaved] = useState(false);
  const [notification, setNotification] = useState(null);
  const [workspaceConfigurationError, setWorkspaceConfigurationError] = useState("");

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

  useEffect(() => {
    if (!notification) {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => {
      setNotification(null);
    }, 4500);

    return () => window.clearTimeout(timeoutId);
  }, [notification]);

  useEffect(() => {
    let isMounted = true;

    const loadWorkspaceConfiguration = async () => {
      try {
        setIsLoadingWorkspaceConfiguration(true);
        setWorkspaceConfigurationError("");

        const response = await getWorkspaceConfiguration();

        if (!isMounted) {
          return;
        }

        const sources = normalizeGoogleSheetSources(response?.configuration);

        setWorkspaceName(response?.workspace?.name || "");
        setActiveGoogleSheetSources(sources);
        setMaxGoogleSheetSources(
          response?.configuration?.max_google_sheet_sources || 5
        );
        setDraftGoogleSheetId("");
        setIsAddingConnection(
          sources.length < (response?.configuration?.max_google_sheet_sources || 5)
        );
      } catch (err) {
        console.error(err);

        if (err?.response?.status === 401) {
          onUnauthorized();
          return;
        }

        if (isMounted) {
          setWorkspaceConfigurationError(
            "Workspace settings are not available for this session."
          );
        }
      } finally {
        if (isMounted) {
          setIsLoadingWorkspaceConfiguration(false);
        }
      }
    };

    loadWorkspaceConfiguration();

    return () => {
      isMounted = false;
    };
  }, [onUnauthorized]);

  const handleSave = async () => {
    try {
      setIsSaving(true);
      setNotification(null);
      setWorkspaceConfigurationError("");

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
        setNotification({
          type: "success",
          title: "Configuration saved",
          message: "Financial cycle, budgeting, and privacy settings were saved.",
        });
      }
    } catch (err) {
      console.error(err);

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      const backendDetail = err?.response?.data?.detail;
      const message = backendDetail?.includes("format datanya tidak sesuai")
        ? `${backendDetail} Pastikan sheet memiliki header transaksi yang benar dan minimal satu baris data.`
        : backendDetail
        || err?.message
        || "Google Sheet ID gagal disimpan. Periksa ID spreadsheet dan akses Google Sheets.";

      setWorkspaceConfigurationError(message);
      setNotification({
        type: "error",
        title: "Google Sheet ID gagal",
        message,
      });
    } finally {
      setIsSaving(false);
    }
  };

  const connectGoogleSheetSource = async (googleSheetId) => {
    if (!googleSheetId) {
      throw new Error("Masukkan Google Sheet ID terlebih dahulu.");
    }

    if (activeGoogleSheetSources.some((source) => source.id === googleSheetId)) {
      throw new Error("Google Sheet ID ini sudah aktif di workspace.");
    }

    const nextDraftSources = [
      ...activeGoogleSheetSources,
      {
        id: googleSheetId,
        label: `Source ${activeGoogleSheetSources.length + 1}`,
      },
    ];

    if (nextDraftSources.length > maxGoogleSheetSources) {
      throw new Error(`Maximum ${maxGoogleSheetSources} Google Sheet sources are allowed.`);
    }

    const workspaceResponse = await updateWorkspaceConfiguration({
      google_sheet_id: nextDraftSources[0]?.id || null,
      google_sheet_sources: nextDraftSources,
    });
    const nextSources = normalizeGoogleSheetSources(workspaceResponse?.configuration);

    await refreshDashboardData(selectedYear || undefined);

    setWorkspaceName(workspaceResponse?.workspace?.name || workspaceName);
    setActiveGoogleSheetSources(nextSources);
    setDraftGoogleSheetId("");
    setIsAddingConnection(nextSources.length < maxGoogleSheetSources);

    return nextSources;
  };

  const handleAddConnection = async () => {
    try {
      setIsConnectingSheet(true);
      setNotification(null);
      setWorkspaceConfigurationError("");

      const nextSources = await connectGoogleSheetSource(draftGoogleSheetId.trim());

      onSaveChanges({
        paydayStartDay: draftPaydayStartDay,
        autoBudget: draftAutoBudget,
        privacyMode: draftPrivacyMode,
        googleSheetId: nextSources[0]?.id || "",
      });
      setNotification({
        type: "success",
        title: "Google Sheet connected",
        message: `Backend processed the spreadsheet. Workspace sekarang terhubung ke ${nextSources.length} source.`,
      });
    } catch (err) {
      console.error(err);

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      const backendDetail = err?.response?.data?.detail;
      const message = backendDetail?.includes("format datanya tidak sesuai")
        ? `${backendDetail} Pastikan sheet memiliki header transaksi yang benar dan minimal satu baris data.`
        : backendDetail
        || err?.message
        || "Google Sheet ID gagal diproses. Periksa ID spreadsheet dan akses Google Sheets.";

      setWorkspaceConfigurationError(message);
      setNotification({
        type: "error",
        title: "Google Sheet gagal diproses",
        message,
      });
    } finally {
      setIsConnectingSheet(false);
    }
  };

  const handleCopyGoogleSheetId = async (sheetId) => {
    if (!sheetId) {
      return;
    }

    try {
      await navigator.clipboard.writeText(sheetId);
      setNotification({
        type: "success",
        title: "Google Sheet ID disalin",
        message: "ID spreadsheet aktif sudah disalin ke clipboard.",
      });
    } catch (err) {
      console.error(err);
      setNotification({
        type: "error",
        title: "Gagal menyalin",
        message: "Browser tidak mengizinkan akses clipboard.",
      });
    }
  };

  const handleDisconnectGoogleSheet = async (sheetId) => {
    try {
      setIsDisconnectingSheet(true);
      setNotification(null);
      setWorkspaceConfigurationError("");
      const remainingSources = activeGoogleSheetSources
        .filter((source) => source.id !== sheetId);

      const workspaceResponse = await updateWorkspaceConfiguration({
        google_sheet_id: remainingSources[0]?.id || null,
        google_sheet_sources: remainingSources,
      });
      const nextSources = normalizeGoogleSheetSources(workspaceResponse?.configuration);

      setActiveGoogleSheetSources(nextSources);
      setDraftGoogleSheetId("");
      setIsAddingConnection(nextSources.length < maxGoogleSheetSources);
      setWorkspaceName(workspaceResponse?.workspace?.name || workspaceName);
      onSaveChanges({
        paydayStartDay: draftPaydayStartDay,
        autoBudget: draftAutoBudget,
        privacyMode: draftPrivacyMode,
        googleSheetId: nextSources[0]?.id || "",
      });
      setNotification({
        type: "success",
        title: "Koneksi Google Sheet dihapus",
        message: nextSources.length > 0
          ? `Workspace masih terhubung ke ${nextSources.length} source.`
          : "Workspace tidak lagi terhubung ke Google Sheet mana pun.",
      });
    } catch (err) {
      console.error(err);

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      const message = err?.response?.data?.detail
        || "Koneksi Google Sheet gagal dihapus.";

      setWorkspaceConfigurationError(message);
      setNotification({
        type: "error",
        title: "Gagal menghapus koneksi",
        message,
      });
    } finally {
      setIsDisconnectingSheet(false);
    }
  };

  return (
  <div className="min-w-0 overflow-x-hidden">
    {notification && (
      <div
        className={`fixed right-4 top-4 z-[80] flex w-[calc(100vw-2rem)] max-w-sm items-start gap-3 rounded-lg border px-4 py-3 shadow-lg ${
          notification.type === "success"
            ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-700"
            : "border-red-500/40 bg-red-500/15 text-red-500"
        }`}
        role="status"
        aria-live="polite"
      >
        {notification.type === "success" ? (
          <CheckCircle2 size={18} className="mt-0.5 shrink-0" />
        ) : (
          <XCircle size={18} className="mt-0.5 shrink-0" />
        )}

        <div className="min-w-0">
          <p className="font-semibold">
            {notification.title}
          </p>
          <p className="mt-1 text-sm leading-5">
            {notification.message}
          </p>
        </div>
      </div>
    )}

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
        description="Workspace-level Google Sheets source and account controls."
      >
        <label className="block text-sm font-semibold text-muted">
          Workspace
        </label>
        <input
          readOnly
          value={workspaceName || "No workspace found"}
          className="form-control mt-2 w-full cursor-default rounded-xl px-4 py-3 text-sm"
        />

        <div className="mt-5 flex items-center justify-between gap-3">
          <label className="block text-sm font-semibold text-muted">
            Active Google Sheet Connections
          </label>

          <button
            type="button"
            onClick={handleAddConnection}
            disabled={
              isConnectingSheet
              || activeGoogleSheetSources.length >= maxGoogleSheetSources
            }
            className="secondary-button min-h-9 rounded-lg px-3 py-1.5 text-sm font-semibold"
          >
            {isConnectingSheet ? (
              <LoaderCircle size={15} className="animate-spin" />
            ) : (
              <Plus size={15} />
            )}
            {isConnectingSheet ? "Processing..." : "Add Connection"}
          </button>
        </div>
        <div className="mt-2 rounded-xl border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3">
          {activeGoogleSheetSources.length > 0 ? (
            <ul className="space-y-2">
              {activeGoogleSheetSources.map((source, index) => (
                <li
                  key={source.id}
                  className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-panel)] px-3 py-2"
                >
                  <span className="whitespace-nowrap text-xs font-semibold text-muted">
                    🟢 Source {index + 1}
                  </span>

                  <span
                    className="min-w-0 truncate font-mono text-sm font-semibold text-main"
                    title={source.id}
                  >
                    {truncateMiddle(source.id)}
                  </span>

                  <div className="flex shrink-0 items-center gap-1">
                    <button
                      type="button"
                      onClick={() => handleCopyGoogleSheetId(source.id)}
                      className="theme-toggle h-9 w-9 rounded-lg p-0"
                      aria-label={`Copy Source ${index + 1} ID`}
                      title="Copy ID"
                    >
                      <Copy size={15} />
                    </button>

                    <button
                      type="button"
                      onClick={() => handleDisconnectGoogleSheet(source.id)}
                      disabled={isDisconnectingSheet}
                      className="theme-toggle h-9 w-9 rounded-lg p-0 text-red-500 disabled:cursor-not-allowed disabled:opacity-60"
                      aria-label={`Delete Source ${index + 1} connection`}
                      title="Delete Connection"
                    >
                      {isDisconnectingSheet ? (
                        <LoaderCircle size={15} className="animate-spin" />
                      ) : (
                        <Trash2 size={15} />
                      )}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm font-semibold text-muted">
              No Google Sheet connected. Dashboard data will stay empty.
            </p>
          )}
        </div>

        <p className="mt-2 text-xs text-muted">
          {activeGoogleSheetSources.length}/{maxGoogleSheetSources} sources connected.
        </p>

        {isAddingConnection && activeGoogleSheetSources.length < maxGoogleSheetSources && (
          <>
            <label className="mt-5 block text-sm font-semibold text-muted">
              New Google Sheet ID
            </label>
            <input
              value={draftGoogleSheetId}
              onChange={(event) => setDraftGoogleSheetId(event.target.value)}
              disabled={isLoadingWorkspaceConfiguration || isConnectingSheet}
              placeholder="Paste spreadsheet ID from Google Sheets URL"
              className="form-control mt-2 w-full rounded-xl px-4 py-3 text-sm disabled:cursor-not-allowed disabled:opacity-70"
            />
          </>
        )}

        <p className="mt-3 text-sm leading-6 text-muted">
          {activeGoogleSheetSources.length > 0
            ? `🟢 Data successfully aggregated from ${activeGoogleSheetSources.length} sources.`
            : `Active source: ${currentSheetName || "No active Google Sheets source"}.`}
        </p>

        {workspaceConfigurationError && (
          <p className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {workspaceConfigurationError}
          </p>
        )}

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
