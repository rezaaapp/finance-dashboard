import {
  Bot,
  CalendarDays,
  CheckCircle2,
  Cloud,
  Copy,
  Eye,
  MailPlus,
  Link2,
  LoaderCircle,
  Plus,
  Trash2,
  Unplug,
  XCircle,
  Settings,
  SlidersHorizontal,
} from "lucide-react";
import { useEffect, useState } from "react";

import {
  getWorkspaceConfiguration,
  getWorkspaceMembers,
  inviteWorkspaceMember,
  refreshDashboardData,
  saveConfiguration,
  updateWorkspaceConfiguration,
} from "../api/dashboardApi";
import {
  disconnectGoogleOAuth,
  getGoogleOAuthConnectionStatus,
  startGoogleOAuth,
} from "../api/googleOAuthApi";

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
  className = "",
}) => (
  <section className={`rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-[var(--color-border)] dark:bg-[var(--color-panel)] sm:p-8 ${className}`}>
    <div className="mb-6 flex items-start gap-4">
      <div className="icon-badge rounded-2xl p-3">
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
  userRole = "user",
  onSaveChanges,
  onUnauthorized,
}) => {
  const [draftAutoBudget, setDraftAutoBudget] = useState(autoBudget);
  const [draftPaydayStartDay, setDraftPaydayStartDay] = useState(paydayStartDay);
  const [draftPrivacyMode, setDraftPrivacyMode] = useState(privacyMode);
  const [workspaceName, setWorkspaceName] = useState("");
  const [workspaceMembers, setWorkspaceMembers] = useState([]);
  const [activeGoogleSheetSources, setActiveGoogleSheetSources] = useState([]);
  const [maxGoogleSheetSources, setMaxGoogleSheetSources] = useState(5);
  const [draftGoogleSheetId, setDraftGoogleSheetId] = useState("");
  const [isAddingConnection, setIsAddingConnection] = useState(false);
  const [isConnectingSheet, setIsConnectingSheet] = useState(false);
  const [isConnectingGoogle, setIsConnectingGoogle] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDisconnectingSheet, setIsDisconnectingSheet] = useState(false);
  const [isDisconnectingGoogle, setIsDisconnectingGoogle] = useState(false);
  const [isLoadingGoogleConnection, setIsLoadingGoogleConnection] = useState(true);
  const [isInvitingMember, setIsInvitingMember] = useState(false);
  const [isLoadingWorkspaceConfiguration, setIsLoadingWorkspaceConfiguration] = useState(true);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [showSaved, setShowSaved] = useState(false);
  const [notification, setNotification] = useState(null);
  const [googleConnection, setGoogleConnection] = useState({
    connected: false,
  });
  const [googleConnectionError, setGoogleConnectionError] = useState("");
  const [workspaceConfigurationError, setWorkspaceConfigurationError] = useState("");
  const isGoogleSheetReadOnly = userRole === "member";
  const canInviteMembers = userRole === "owner" || userRole === "super_admin";

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
        const membersResponse = await getWorkspaceMembers();

        setWorkspaceName(response?.workspace?.name || "");
        setWorkspaceMembers(membersResponse?.members || []);
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

  useEffect(() => {
    let isMounted = true;

    const loadGoogleConnection = async () => {
      try {
        setIsLoadingGoogleConnection(true);
        setGoogleConnectionError("");

        const response = await getGoogleOAuthConnectionStatus();

        if (isMounted) {
          setGoogleConnection(response || { connected: false });
        }
      } catch (err) {
        console.error(err);

        if (err?.response?.status === 401) {
          onUnauthorized();
          return;
        }

        if (isMounted) {
          setGoogleConnectionError("Google connection status is not available.");
        }
      } finally {
        if (isMounted) {
          setIsLoadingGoogleConnection(false);
        }
      }
    };

    loadGoogleConnection();

    return () => {
      isMounted = false;
    };
  }, [onUnauthorized]);

  useEffect(() => {
    const queryParams = new URLSearchParams(window.location.search);
    const googleConnected = queryParams.get("google_connected");

    if (!googleConnected) {
      return;
    }

    if (googleConnected === "success") {
      setNotification({
        type: "success",
        title: "Google connected",
        message: "Google account access is connected for this workspace.",
      });
      getGoogleOAuthConnectionStatus()
        .then((response) => {
          setGoogleConnection(response || { connected: false });
        })
        .catch((err) => {
          console.error(err);
          setGoogleConnectionError("Google connection status is not available.");
        });
    } else if (googleConnected === "failed") {
      setNotification({
        type: "error",
        title: "Google connection failed",
        message: "Google account access was not connected. Try again from this page.",
      });
    }

    queryParams.delete("google_connected");
    const nextQuery = queryParams.toString();
    const nextUrl = `${window.location.pathname}${nextQuery ? `?${nextQuery}` : ""}`;
    window.history.replaceState({}, "", nextUrl);
  }, []);

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

  const handleConnectGoogle = async () => {
    try {
      setIsConnectingGoogle(true);
      setGoogleConnectionError("");
      setNotification(null);

      const response = await startGoogleOAuth();

      if (!response?.auth_url) {
        throw new Error("Google authorization URL is not available.");
      }

      window.location.href = response.auth_url;
    } catch (err) {
      console.error(err);

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      const message = err?.response?.data?.detail
        || "Google connection could not be started.";

      setGoogleConnectionError(message);
      setNotification({
        type: "error",
        title: "Google connection failed",
        message,
      });
      setIsConnectingGoogle(false);
    }
  };

  const handleDisconnectGoogle = async () => {
    try {
      setIsDisconnectingGoogle(true);
      setGoogleConnectionError("");
      setNotification(null);

      await disconnectGoogleOAuth();
      const response = await getGoogleOAuthConnectionStatus();

      setGoogleConnection(response || { connected: false });
      setNotification({
        type: "success",
        title: "Google disconnected",
        message: "Google account access has been disconnected.",
      });
    } catch (err) {
      console.error(err);

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      const message = err?.response?.data?.detail
        || "Google connection could not be disconnected.";

      setGoogleConnectionError(message);
      setNotification({
        type: "error",
        title: "Disconnect failed",
        message,
      });
    } finally {
      setIsDisconnectingGoogle(false);
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

  const handleInviteMember = async (event) => {
    event.preventDefault();

    try {
      setIsInvitingMember(true);
      setNotification(null);
      setWorkspaceConfigurationError("");

      const response = await inviteWorkspaceMember({
        email: inviteEmail.trim(),
        name: inviteName.trim(),
      });

      setWorkspaceMembers(response?.members || []);
      setInviteEmail("");
      setInviteName("");
      setNotification({
        type: "success",
        title: "Member invited",
        message: `${response?.member?.email || "Member"} sekarang terhubung ke workspace sebagai member.`,
      });
    } catch (err) {
      console.error(err);

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      const message = err?.response?.data?.detail
        || "Member gagal diundang ke workspace.";

      setWorkspaceConfigurationError(message);
      setNotification({
        type: "error",
        title: "Invite gagal",
        message,
      });
    } finally {
      setIsInvitingMember(false);
    }
  };

  return (
  <div className="mx-auto w-full max-w-4xl min-w-0 overflow-x-hidden">
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

    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
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

    <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
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
        className="lg:col-span-2"
      >
        <label className="block text-sm font-semibold text-muted">
          Workspace
        </label>
        <input
          readOnly
          value={workspaceName || "No workspace found"}
          className="form-control mt-2 w-full cursor-default rounded-2xl px-4 py-3 text-sm font-semibold"
        />

        <div className="mt-6 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-[var(--color-border)] dark:bg-[var(--color-panel)] sm:p-8">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[var(--color-accent-bg)] text-accent">
              <Cloud size={21} />
            </div>

            <div className="min-w-0">
              <h3 className="text-lg font-bold leading-7 text-main">
                Google Sheets Connection
              </h3>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-muted">
                Connect your Google account to access Google Sheets data.
              </p>
            </div>
          </div>

          <div className="my-6 h-px bg-gray-200 dark:bg-[var(--color-border)]" />

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
            <div className="min-w-0">
              <p className="text-xs font-bold uppercase tracking-wide text-subtle">
                Connection Status
              </p>

              <div className="mt-2 flex flex-wrap items-center gap-3">
                <span className={`inline-flex min-h-7 items-center rounded-full px-3 py-1 text-xs font-bold ${
                  googleConnection.connected
                    ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                    : "bg-gray-100 text-gray-600 dark:bg-white/10 dark:text-gray-300"
                }`}>
                  {isLoadingGoogleConnection
                    ? "Checking..."
                    : googleConnection.connected ? "Connected" : "Not Connected"}
                </span>

                {googleConnection.connected && googleConnection.google_email && (
                  <span className="min-w-0 max-w-full truncate text-sm font-semibold text-main">
                    Connected as: {googleConnection.google_email}
                  </span>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:min-w-[320px]">
              <button
                type="button"
                onClick={handleConnectGoogle}
                disabled={isLoadingGoogleConnection || isConnectingGoogle}
                className="primary-button inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl px-4 py-2 text-sm font-semibold shadow-sm disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isConnectingGoogle ? (
                  <LoaderCircle size={16} className="animate-spin" />
                ) : (
                  <Cloud size={16} />
                )}
                {googleConnection.connected ? "Reconnect Google" : "Connect Google"}
              </button>

              <button
                type="button"
                onClick={handleDisconnectGoogle}
                disabled={
                  isLoadingGoogleConnection
                  || isDisconnectingGoogle
                  || !googleConnection.connected
                }
                className="secondary-button inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl px-4 py-2 text-sm font-semibold shadow-sm disabled:cursor-not-allowed disabled:border-gray-200 disabled:bg-gray-50 disabled:text-gray-400 disabled:opacity-100 dark:disabled:border-white/10 dark:disabled:bg-white/5 dark:disabled:text-gray-500"
              >
                {isDisconnectingGoogle ? (
                  <LoaderCircle size={16} className="animate-spin" />
                ) : (
                  <Unplug size={16} />
                )}
                Disconnect
              </button>
            </div>
          </div>

          {googleConnectionError && (
            <div className="mt-6 flex w-full items-start gap-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm leading-6 text-red-700 shadow-sm dark:border-red-400/20 dark:bg-red-500/10 dark:text-red-300">
              <XCircle size={17} className="mt-0.5 shrink-0" />
              <p className="min-w-0">
                {googleConnectionError}
              </p>
            </div>
          )}
        </div>

        <div className="mt-5 flex items-center justify-between gap-3">
          <label className="block text-sm font-semibold text-muted">
            Active Google Sheet Connections
          </label>

          <button
            type="button"
            onClick={handleAddConnection}
            disabled={
              isGoogleSheetReadOnly
              ||
              isConnectingSheet
              || activeGoogleSheetSources.length >= maxGoogleSheetSources
            }
            className={`secondary-button min-h-9 rounded-lg px-3 py-1.5 text-sm font-semibold ${
              isGoogleSheetReadOnly ? "hidden" : ""
            }`}
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

                    <a
                      href={`https://docs.google.com/spreadsheets/d/${source.id}`}
                      target="_blank"
                      rel="noreferrer"
                      className="theme-toggle inline-flex h-9 w-9 rounded-lg p-0"
                      aria-label={`Open Source ${index + 1} in Google Sheets`}
                      title="Open Google Sheets"
                    >
                      <Link2 size={15} />
                    </a>

                    {!isGoogleSheetReadOnly && (
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
                    )}
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

        {isGoogleSheetReadOnly && (
          <p className="mt-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] px-4 py-3 text-sm font-semibold text-muted">
            Role Member bisa membuka shortcut Google Sheets, tetapi konfigurasi
            source bersifat read-only.
          </p>
        )}

        {!isGoogleSheetReadOnly
          && isAddingConnection
          && activeGoogleSheetSources.length < maxGoogleSheetSources && (
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

      {canInviteMembers && (
        <ConfigurationCard
          icon={MailPlus}
          title="Workspace Members"
          description="Manage team access and invite new members to this financial workspace."
        >
          <form onSubmit={handleInviteMember} className="grid grid-cols-1 gap-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="block">
                <span className="mb-2 block text-sm font-semibold text-muted">
                  Email
                </span>
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(event) => setInviteEmail(event.target.value)}
                  placeholder="pasangan@example.com"
                  className="form-control w-full rounded-xl px-4 py-3 text-sm"
                  required
                />
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-semibold text-muted">
                  Member Name
                </span>
                <input
                  value={inviteName}
                  onChange={(event) => setInviteName(event.target.value)}
                  placeholder="Nama member (opsional)"
                  className="form-control w-full rounded-xl px-4 py-3 text-sm"
                />
              </label>
            </div>

            <div className="flex justify-stretch sm:justify-end">
              <button
                type="submit"
                disabled={isInvitingMember}
                className="primary-button w-full rounded-lg px-5 py-2.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
              >
                {isInvitingMember ? (
                  <LoaderCircle size={16} className="animate-spin" />
                ) : (
                  <MailPlus size={16} />
                )}
                {isInvitingMember ? "Inviting..." : "Invite Member"}
              </button>
            </div>
          </form>

          <div className="mt-6 rounded-xl border border-gray-100 bg-gray-50 p-4 dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)]">
            <p className="mb-3 text-xs font-bold uppercase tracking-wide text-muted">
              Current Members
            </p>

            {workspaceMembers.length > 0 ? (
              <ul className="space-y-2">
                {workspaceMembers.map((member) => (
                  <li
                    key={member.id}
                    className="flex items-center justify-between gap-3 rounded-lg border border-gray-100 bg-white px-4 py-3 dark:border-[var(--color-border)] dark:bg-[var(--color-panel)]"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-bold text-main">
                        {member.name}
                      </p>
                      <p className="truncate text-xs text-muted">
                        {member.email}
                      </p>
                    </div>

                    <span className="shrink-0 rounded-full bg-[var(--color-accent-bg)] px-2 py-1 text-xs font-bold text-accent">
                      {member.workspace_role}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted">
                Belum ada member di workspace ini.
              </p>
            )}
          </div>
        </ConfigurationCard>
      )}
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
