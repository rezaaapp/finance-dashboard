import {
  CalendarDays,
  CheckCircle2,
  Cloud,
  Eye,
  MailPlus,
  Link2,
  LoaderCircle,
  RefreshCw,
  Trash2,
  Unplug,
  XCircle,
  Settings,
  SlidersHorizontal,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getWorkspaceConfiguration,
  getWorkspaceMembers,
  saveConfiguration,
} from "../api/dashboardApi";
import {
  cancelWorkspaceInvitation,
  createWorkspaceInvitation,
  getWorkspacePendingInvitations,
} from "../api/workspaceInvitationsApi";
import {
  disconnectGoogleOAuth,
  getGoogleOAuthConnectionStatus,
  startGoogleOAuth,
} from "../api/googleOAuthApi";
import {
  createGoogleSheetSource,
  getGoogleSheetSources,
  syncGoogleSheetSource,
  testGoogleSheetSource,
  resetGoogleSheetSourceData,
} from "../api/googleSheetSourcesApi";
import {
  getInsightThresholds,
  updateInsightThresholds,
} from "../api/insightSettingsApi";

import { PRIVACY_MODES } from "../utils/privacy";
import { getActiveWorkspaceId } from "../api/workspaceContext";
import SystemInfoPanel from "../components/environment/SystemInfoPanel";
import ImportResultDetailsModal from "../components/import/ImportResultDetailsModal";
import ConfirmationDialog from "../components/ConfirmationDialog";
import { factoryResetWorkspaceData } from "../api/workspaceResetApi";
import {
  changedValues,
  dirtySettingsSummary,
  SETTINGS_FIELDS,
} from "../utils/settingsDirtyState";

const privacyOptions = [
  { label: "Normal", value: PRIVACY_MODES.normal },
  { label: "Sembunyikan", value: PRIVACY_MODES.hide },
  { label: "Tamu", value: PRIVACY_MODES.guest },
];

const friendlyErrorMessage = (detail, fallback) => {
  const rawMessage = typeof detail === "string" ? detail : detail?.message;
  const message = String(rawMessage || "").trim();

  if (!message) return fallback;
  if (/[{}]|authorization|bearer|credential|password|secret|token/i.test(message)) {
    return fallback;
  }

  return message;
};

const formatWorkspaceRole = (role) => {
  if (!role) return "Akses mengikuti sesi aktif";
  return String(role)
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
};

const defaultInsightThresholds = {
  need_warning_ratio: 0.80,
  need_danger_ratio: 0.90,
  want_warning_ratio: 0.30,
  want_danger_ratio: 0.45,
  saving_warning_ratio: 0.10,
  saving_good_ratio: 0.20,
  uncategorized_warning_count: 1,
  uncategorized_danger_count: 20,
  anomaly_warning_multiplier: 2.0,
  anomaly_danger_multiplier: 3.0,
  source: "default",
};

const ratioToPercent = (value) => (
  Number.isFinite(Number(value))
    ? Number((Number(value) * 100).toFixed(1))
    : ""
);

const percentToRatio = (value) => Number((Number(value) / 100).toFixed(4));

const settingsToForm = (settings = defaultInsightThresholds) => ({
  need_warning_ratio: ratioToPercent(settings.need_warning_ratio),
  need_danger_ratio: ratioToPercent(settings.need_danger_ratio),
  want_warning_ratio: ratioToPercent(settings.want_warning_ratio),
  want_danger_ratio: ratioToPercent(settings.want_danger_ratio),
  saving_warning_ratio: ratioToPercent(settings.saving_warning_ratio),
  saving_good_ratio: ratioToPercent(settings.saving_good_ratio),
  uncategorized_warning_count: settings.uncategorized_warning_count ?? 1,
  uncategorized_danger_count: settings.uncategorized_danger_count ?? 20,
  anomaly_warning_multiplier: settings.anomaly_warning_multiplier ?? 2.0,
  anomaly_danger_multiplier: settings.anomaly_danger_multiplier ?? 3.0,
  source: settings.source || "default",
});

const formToPayload = (form) => ({
  need_warning_ratio: percentToRatio(form.need_warning_ratio),
  need_danger_ratio: percentToRatio(form.need_danger_ratio),
  want_warning_ratio: percentToRatio(form.want_warning_ratio),
  want_danger_ratio: percentToRatio(form.want_danger_ratio),
  saving_warning_ratio: percentToRatio(form.saving_warning_ratio),
  saving_good_ratio: percentToRatio(form.saving_good_ratio),
  uncategorized_warning_count: Number(form.uncategorized_warning_count),
  uncategorized_danger_count: Number(form.uncategorized_danger_count),
  anomaly_warning_multiplier: Number(form.anomaly_warning_multiplier),
  anomaly_danger_multiplier: Number(form.anomaly_danger_multiplier),
});

const formatSyncTimestamp = (value) => {
  if (!value) {
    return "Belum pernah sinkron";
  }

  try {
    return new Intl.DateTimeFormat("id-ID", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return "Waktu sinkronisasi belum tersedia";
  }
};

const formatReasonLabel = (reason) => (
  String(reason || "")
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ")
);

const hasReasonEntries = (reasons = {}) => Object.keys(reasons || {}).length > 0;

const formatClassificationSummary = (classification) => {
  if (!classification) {
    return "";
  }

  return `Klasifikasi: ${classification.processed || 0} transaksi diproses, ${classification.low_confidence || 0} perlu dicek.`;
};

const SyncReasonBreakdown = ({ title, reasons, tone = "muted" }) => {
  if (!hasReasonEntries(reasons)) {
    return null;
  }

  const toneClass = tone === "warning"
    ? "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-400/20 dark:bg-amber-500/10 dark:text-amber-200"
    : "border-gray-200 bg-white text-muted dark:border-[var(--color-border)] dark:bg-[var(--color-panel)]";

  return (
    <div className={`rounded-xl border px-3 py-2 ${toneClass}`}>
      <p className="font-semibold text-main">{title}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {Object.entries(reasons).map(([reason, count]) => (
          <span
            key={reason}
            className="rounded-lg border border-current/20 px-2 py-1 font-semibold"
          >
            {formatReasonLabel(reason)}: {count}
          </span>
        ))}
      </div>
    </div>
  );
};

const SyncSamples = ({ title, samples = [] }) => {
  if (!samples.length) {
    return null;
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white px-3 py-2 dark:border-[var(--color-border)] dark:bg-[var(--color-panel)]">
      <p className="font-semibold text-main">{title}</p>
      <ul className="mt-2 space-y-1">
        {samples.slice(0, 6).map((sample, index) => (
          <li
            key={`${sample.sheet_name}-${sample.row_number}-${sample.reason}-${index}`}
            className="text-muted"
          >
            {sample.sheet_name || "Unknown sheet"}
            {sample.row_number ? ` row ${sample.row_number}` : ""}:{" "}
            {formatReasonLabel(sample.reason)}
            {sample.category ? ` (${sample.category})` : ""}
          </li>
        ))}
      </ul>
    </div>
  );
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

const ThresholdSlider = ({
  label,
  helperText,
  valuePercent,
  onChangePercent,
  disabled = false,
}) => {
  const sliderValue = valuePercent === "" ? 0 : Number(valuePercent);

  return (
    <label className="block rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)]">
      <div className="flex flex-col gap-3 md:flex-row md:items-center">
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm font-bold text-main">{label}</span>
            <span className="shrink-0 text-xs font-bold text-accent">
              {valuePercent === "" ? "-" : `${valuePercent}%`}
            </span>
          </div>
          <p className="mt-1 text-xs leading-5 text-muted">{helperText}</p>
          <input
            type="range"
            min="0"
            max="100"
            step="0.5"
            value={sliderValue}
            onChange={(event) => onChangePercent(event.target.value)}
            disabled={disabled}
            className="mt-3 h-2 w-full cursor-pointer accent-[var(--color-accent-strong)] disabled:cursor-not-allowed disabled:opacity-60"
          />
        </div>

        <div className="flex items-center gap-2 md:w-32">
          <input
            type="number"
            min="0"
            max="100"
            step="0.1"
            value={valuePercent}
            onChange={(event) => onChangePercent(event.target.value)}
            disabled={disabled}
            className="form-control w-full rounded-xl px-3 py-2 text-sm"
          />
          <span className="text-sm font-semibold text-muted">%</span>
        </div>
      </div>
    </label>
  );
};

const Configuration = ({
  autoBudget,
  paydayStartDay,
  selectedYear,
  privacyMode,
  userRole = "user",
  onSaveChanges,
  onUnauthorized,
  systemInfoState,
  pendingNavigation,
  onDirtyStateChange,
  onCancelNavigation,
  onDiscardAndNavigate,
  onSaveAndNavigate,
}) => {
  const [draftAutoBudget, setDraftAutoBudget] = useState(autoBudget);
  const [draftPaydayStartDay, setDraftPaydayStartDay] = useState(paydayStartDay);
  const [draftPrivacyMode, setDraftPrivacyMode] = useState(privacyMode);
  const [savedConfiguration, setSavedConfiguration] = useState({
    payday_start_day: paydayStartDay,
    auto_budget: autoBudget,
    privacy_mode: privacyMode,
  });
  const [workspaceName, setWorkspaceName] = useState("");
  const [workspaceId, setWorkspaceId] = useState("");
  const [workspaceRole, setWorkspaceRole] = useState("");
  const [workspaceMembers, setWorkspaceMembers] = useState([]);
  const [workspacePendingInvitations, setWorkspacePendingInvitations] = useState([]);
  const [isConnectingGoogle, setIsConnectingGoogle] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDisconnectingGoogle, setIsDisconnectingGoogle] = useState(false);
  const [disconnectConfirmOpen, setDisconnectConfirmOpen] = useState(false);
  const [insightResetConfirmOpen, setInsightResetConfirmOpen] = useState(false);
  const [isLoadingGoogleConnection, setIsLoadingGoogleConnection] = useState(true);
  const [isLoadingSources, setIsLoadingSources] = useState(false);
  const [isTestingSource, setIsTestingSource] = useState(false);
  const [isSavingSource, setIsSavingSource] = useState(false);
  const [syncingSourceId, setSyncingSourceId] = useState("");
  const [resettingSourceId, setResettingSourceId] = useState("");
  const [resetSource, setResetSource] = useState(null);
  const [factoryResetOpen, setFactoryResetOpen] = useState(false);
  const [isFactoryResetting, setIsFactoryResetting] = useState(false);
  const [isInvitingMember, setIsInvitingMember] = useState(false);
  const [cancelingInvitationId, setCancelingInvitationId] = useState("");
  const [, setIsLoadingWorkspaceConfiguration] = useState(true);
  const [inviteEmail, setInviteEmail] = useState("");
  const [spreadsheetUrl, setSpreadsheetUrl] = useState("");
  const [sourceSelectedTabs, setSourceSelectedTabs] = useState([]);
  const [showSaved, setShowSaved] = useState(false);
  const [notification, setNotification] = useState(null);
  const [googleConnection, setGoogleConnection] = useState({
    connected: false,
  });
  const [googleSheetSources, setGoogleSheetSources] = useState([]);
  const [sourceTestResult, setSourceTestResult] = useState(null);
  const [sourceError, setSourceError] = useState("");
  const [syncResults, setSyncResults] = useState({});
  const [detailResult, setDetailResult] = useState(null);
  const [googleConnectionError, setGoogleConnectionError] = useState("");
  const [workspaceConfigurationError, setWorkspaceConfigurationError] = useState("");
  const [insightThresholds, setInsightThresholds] = useState(
    settingsToForm(defaultInsightThresholds)
  );
  const [savedInsightThresholds, setSavedInsightThresholds] = useState(
    settingsToForm(defaultInsightThresholds)
  );
  const [isLoadingInsightThresholds, setIsLoadingInsightThresholds] = useState(false);
  const [insightThresholdError, setInsightThresholdError] = useState("");
  const [insightThresholdSuccess, setInsightThresholdSuccess] = useState("");
  const canInviteMembers = (
    userRole === "super_admin"
    || workspaceRole === "owner"
    || workspaceRole === "admin"
  );

  const updateInsightField = (field, value) => {
    setInsightThresholds((currentThresholds) => ({
      ...currentThresholds,
      [field]: value,
    }));
    setInsightThresholdError("");
    setInsightThresholdSuccess("");
  };

  const validateInsightThresholds = useCallback((form) => {
    if (Object.values(form).some((value) => value === "" || value === null)) {
      return "Semua ambang insight perlu diisi.";
    }

    const payload = formToPayload(form);
    const percentFields = [
      "need_warning_ratio",
      "need_danger_ratio",
      "want_warning_ratio",
      "want_danger_ratio",
      "saving_warning_ratio",
      "saving_good_ratio",
    ];

    if (Object.values(payload).some((value) => Number.isNaN(value))) {
      return "Semua ambang insight harus berupa angka yang valid.";
    }

    if (percentFields.some((field) => Number(form[field]) < 0 || Number(form[field]) > 100)) {
      return "Ambang persentase harus berada di antara 0 dan 100.";
    }

    if (payload.need_warning_ratio > payload.need_danger_ratio) {
      return "Ambang perhatian Need harus lebih kecil atau sama dengan ambang tinggi.";
    }

    if (payload.want_warning_ratio > payload.want_danger_ratio) {
      return "Ambang perhatian Want harus lebih kecil atau sama dengan ambang tinggi.";
    }

    if (payload.saving_warning_ratio > payload.saving_good_ratio) {
      return "Ambang perhatian Saving harus lebih kecil atau sama dengan ambang baik.";
    }

    if (payload.uncategorized_warning_count < 0 || payload.uncategorized_danger_count < 0) {
      return "Jumlah transaksi tanpa kategori tidak boleh negatif.";
    }

    if (payload.uncategorized_warning_count > payload.uncategorized_danger_count) {
      return "Ambang perhatian tanpa kategori harus lebih kecil atau sama dengan ambang tinggi.";
    }

    if (payload.anomaly_warning_multiplier < 1 || payload.anomaly_danger_multiplier < 1) {
      return "Pengali anomali minimal 1.0.";
    }

    if (payload.anomaly_warning_multiplier > payload.anomaly_danger_multiplier) {
      return "Pengali perhatian anomali harus lebih kecil atau sama dengan pengali tinggi.";
    }

    return "";
  }, []);

  const insightValidationError = validateInsightThresholds(insightThresholds);
  const draftConfiguration = useMemo(() => ({
    payday_start_day: draftPaydayStartDay,
    auto_budget: draftAutoBudget,
    privacy_mode: draftPrivacyMode,
  }), [draftAutoBudget, draftPaydayStartDay, draftPrivacyMode]);
  const dirtySummary = useMemo(() => dirtySettingsSummary({
    configuration: draftConfiguration,
    savedConfiguration,
    insights: insightThresholds,
    savedInsights: savedInsightThresholds,
  }), [draftConfiguration, insightThresholds, savedConfiguration, savedInsightThresholds]);
  const hasDirtySettings = dirtySummary.count > 0;

  useEffect(() => {
    onDirtyStateChange?.(hasDirtySettings);
    return () => onDirtyStateChange?.(false);
  }, [hasDirtySettings, onDirtyStateChange]);

  useEffect(() => {
    if (!hasDirtySettings) return undefined;
    const handleBeforeUnload = (event) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [hasDirtySettings]);

  const loadInsightThresholds = useCallback(async () => {
    try {
      setIsLoadingInsightThresholds(true);
      setInsightThresholdError("");

      const response = await getInsightThresholds();

      const loadedThresholds = settingsToForm(response || defaultInsightThresholds);
      setInsightThresholds(loadedThresholds);
      setSavedInsightThresholds(loadedThresholds);
    } catch (err) {
      console.error("Failed to load insight thresholds.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return false;
      }

      setInsightThresholdError("Pengaturan insight belum tersedia untuk sesi ini.");
    } finally {
      setIsLoadingInsightThresholds(false);
    }
  }, [onUnauthorized]);

  const loadGoogleSheetSources = useCallback(async () => {
    try {
      setIsLoadingSources(true);
      setSourceError("");

      const response = await getGoogleSheetSources();

      setGoogleSheetSources(response?.sources || []);
    } catch (err) {
      console.error("Failed to load workspace configuration.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      setSourceError("Sumber Google Sheet belum tersedia untuk sesi ini.");
    } finally {
      setIsLoadingSources(false);
    }
  }, [onUnauthorized]);

  useEffect(() => {
    setDraftAutoBudget(autoBudget);
    setSavedConfiguration((current) => ({ ...current, auto_budget: autoBudget }));
  }, [autoBudget]);

  useEffect(() => {
    setDraftPaydayStartDay(paydayStartDay);
    setSavedConfiguration((current) => ({ ...current, payday_start_day: paydayStartDay }));
  }, [paydayStartDay]);

  useEffect(() => {
    setDraftPrivacyMode(privacyMode);
    setSavedConfiguration((current) => ({ ...current, privacy_mode: privacyMode }));
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

        const membersResponse = await getWorkspaceMembers();
        const currentWorkspaceId = response?.workspace?.id || getActiveWorkspaceId();
        const currentWorkspaceRole = response?.workspace?.role || "";
        const canLoadPendingInvitations = (
          userRole === "super_admin"
          || currentWorkspaceRole === "owner"
          || currentWorkspaceRole === "admin"
        );
        const pendingInvitationsResponse = (
          canLoadPendingInvitations && currentWorkspaceId
            ? await getWorkspacePendingInvitations(currentWorkspaceId)
            : { invitations: [] }
        );

        if (!isMounted) {
          return;
        }

        setWorkspaceId(currentWorkspaceId);
        setWorkspaceName(response?.workspace?.name || "");
        setWorkspaceRole(currentWorkspaceRole);
        setWorkspaceMembers(membersResponse?.members || []);
        setWorkspacePendingInvitations(
          pendingInvitationsResponse?.invitations || []
        );
      } catch (err) {
        console.error("Failed to load Google Sheet sources.");

        if (err?.response?.status === 401) {
          onUnauthorized();
          return;
        }

        if (isMounted) {
          setWorkspaceConfigurationError(
            "Pengaturan workspace belum tersedia untuk sesi ini."
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
  }, [onUnauthorized, userRole]);

  useEffect(() => {
    if (!googleConnection.connected) {
      setGoogleSheetSources([]);
      return;
    }

    loadGoogleSheetSources();
  }, [googleConnection.connected, loadGoogleSheetSources]);

  useEffect(() => {
    loadInsightThresholds();
  }, [loadInsightThresholds]);

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
        console.error("Failed to load Google connection status.");

        if (err?.response?.status === 401) {
          onUnauthorized();
          return;
        }

        if (isMounted) {
          setGoogleConnectionError("Status koneksi Google belum tersedia.");
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
        title: "Google terhubung",
        message: "Akses akun Google aktif untuk workspace ini.",
      });
      getGoogleOAuthConnectionStatus()
        .then((response) => {
          setGoogleConnection(response || { connected: false });
          if (response?.connected) {
            loadGoogleSheetSources();
          }
        })
        .catch(() => {
          console.error("Failed to refresh Google connection status.");
          setGoogleConnectionError("Status koneksi Google belum tersedia.");
        });
    } else if (googleConnected === "failed") {
      setNotification({
        type: "error",
        title: "Koneksi Google belum berhasil",
        message: "Akses akun Google belum terhubung. Coba lagi dari halaman ini.",
      });
    }

    queryParams.delete("google_connected");
    const nextQuery = queryParams.toString();
    const nextUrl = `${window.location.pathname}${nextQuery ? `?${nextQuery}` : ""}`;
    window.history.replaceState({}, "", nextUrl);
  }, [loadGoogleSheetSources]);

  const handleSave = async () => {
    if (!hasDirtySettings) return true;
    if (dirtySummary.insightFields.length > 0 && insightValidationError) {
      setInsightThresholdError(insightValidationError);
      return false;
    }
    try {
      setIsSaving(true);
      setNotification(null);
      setWorkspaceConfigurationError("");

      const changedConfiguration = changedValues(
        draftConfiguration,
        savedConfiguration,
        SETTINGS_FIELDS
      );
      if (dirtySummary.configurationFields.length > 0) {
        const response = await saveConfiguration({ year: selectedYear, ...changedConfiguration });
        if (response?.status !== "ok") return false;
        onSaveChanges({
          paydayStartDay: draftPaydayStartDay,
          autoBudget: draftAutoBudget,
          privacyMode: draftPrivacyMode,
        });
      }
      if (dirtySummary.insightFields.length > 0) {
        const response = await updateInsightThresholds(formToPayload(insightThresholds));
        const savedThresholds = settingsToForm(response || insightThresholds);
        setInsightThresholds(savedThresholds);
        setSavedInsightThresholds(savedThresholds);
      }
      setSavedConfiguration(draftConfiguration);
      setShowSaved(true);
      setNotification({ type: "success", title: "Perubahan tersimpan", message: "Semua perubahan berhasil disimpan." });
      return true;
    } catch (err) {
      console.error("Failed to save configuration.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      const backendDetail = err?.response?.data?.detail;
      const message = backendDetail?.includes?.("format datanya tidak sesuai")
        ? `${backendDetail} Pastikan sheet memiliki header transaksi yang benar dan minimal satu baris data.`
        : friendlyErrorMessage(
          backendDetail,
          "Kami belum bisa menyimpan perubahan. Periksa isian dan coba lagi."
        );

      setWorkspaceConfigurationError(message);
      setNotification({
        type: "error",
        title: "Perubahan belum tersimpan",
        message,
      });
      return false;
    } finally {
      setIsSaving(false);
    }
  };

  const handleDiscard = () => {
    setDraftPaydayStartDay(savedConfiguration.payday_start_day);
    setDraftAutoBudget(savedConfiguration.auto_budget);
    setDraftPrivacyMode(savedConfiguration.privacy_mode);
    setInsightThresholds(savedInsightThresholds);
    setInsightThresholdError("");
    setInsightThresholdSuccess("");
  };

  const handleTestGoogleSheetSource = async () => {
    try {
      setIsTestingSource(true);
      setNotification(null);
      setSourceError("");
      setSourceTestResult(null);

      const response = await testGoogleSheetSource({
        spreadsheet_url: spreadsheetUrl.trim(),
      });

      setSourceTestResult(response);

      if (!response?.valid) {
        setSourceError(friendlyErrorMessage(
          response?.message,
          "Spreadsheet belum bisa diperiksa."
        ));
        return;
      }

      const availableTabs = response?.detected_tabs || response?.tabs || [];
      setSourceSelectedTabs(availableTabs.length === 1 ? availableTabs : []);

      setNotification({
        type: "success",
        title: "Spreadsheet berhasil diperiksa",
        message: `${response.spreadsheet_title || "Spreadsheet"} dapat dipakai sebagai sumber sinkronisasi.`,
      });
    } catch (err) {
      console.error("Failed to save workspace configuration.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      const message = friendlyErrorMessage(
        err?.response?.data?.detail,
        "Spreadsheet belum bisa diperiksa. Pastikan akses Google masih aktif dan URL benar."
      );

      setSourceError(message);
    } finally {
      setIsTestingSource(false);
    }
  };

  const handleSaveGoogleSheetSource = async () => {
    try {
      setIsSavingSource(true);
      setNotification(null);
      setSourceError("");

      const response = await createGoogleSheetSource({
        spreadsheet_url: spreadsheetUrl.trim(),
        selected_tabs: sourceSelectedTabs,
      });

      setSpreadsheetUrl("");
      setSourceSelectedTabs([]);
      setSourceTestResult(null);
      setNotification({
        type: "success",
        title: "Sumber Spreadsheet tersimpan",
        message: `${response?.spreadsheet_title || "Google Spreadsheet"} siap disinkronkan ke Omon.`,
      });
      await loadGoogleSheetSources();
    } catch (err) {
      console.error("Failed to test Google Sheet connection.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      const message = friendlyErrorMessage(
        err?.response?.data?.detail,
        "Sumber Spreadsheet belum bisa disimpan. Coba periksa URL dan tab yang dipilih."
      );

      setSourceError(message);
      setNotification({
        type: "error",
        title: "Sumber belum tersimpan",
        message,
      });
    } finally {
      setIsSavingSource(false);
    }
  };

  const handleSyncSource = async (sourceId) => {
    try {
      setSyncingSourceId(sourceId);
      setSourceError("");
      setNotification(null);

      const response = await syncGoogleSheetSource(sourceId);

      setSyncResults((currentResults) => ({
        ...currentResults,
        [sourceId]: response,
      }));
      setNotification({
        type: "success",
        title: "Sync complete",
        message: [
          `${response?.inserted_rows || 0} transaksi baru, ${response?.updated_rows || 0} diperbarui di Omon.`,
          formatClassificationSummary(response?.classification),
        ].filter(Boolean).join(" "),
      });
      await loadGoogleSheetSources();
    } catch (err) {
      console.error("Failed to connect Google Sheet source.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      const detail = err?.response?.data?.detail;
      const message = friendlyErrorMessage(
        detail,
        "Sinkronisasi belum berhasil. Data yang sudah tersimpan di Omon tetap aman."
      );

      setSourceError(message);

      if (detail?.job_id) {
        setSyncResults((currentResults) => ({
          ...currentResults,
          [sourceId]: {
            job_id: detail.job_id,
            status: "failed",
            total_rows: 0,
            inserted_rows: 0,
            updated_rows: 0,
            skipped_rows: 0,
            failed_rows: 0,
          },
        }));
      }
    } finally {
      setSyncingSourceId("");
    }
  };

  const handleResetSourceData = async () => {
    if (!resetSource?.source_id) return;
    try {
      setResettingSourceId(resetSource.source_id);
      setSourceError("");
      setNotification(null);
      const response = await resetGoogleSheetSourceData(resetSource.source_id);
      setSyncResults((currentResults) => ({
        ...currentResults,
        [resetSource.source_id]: null,
      }));
      setNotification({
        type: "success",
        title: "Data tersinkron berhasil direset",
        message: `Data hasil sinkronisasi Google Sheet berhasil dihapus dari Omon (${response.deleted_transactions || 0} transaksi). Google Sheet asli tidak berubah.`,
      });
      setResetSource(null);
      await loadGoogleSheetSources();
    } catch (err) {
      console.error("Failed to reset synced Google Sheet data.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      const message = friendlyErrorMessage(
        err?.response?.data?.detail,
        "Data tersinkron belum bisa direset. Coba lagi setelah beberapa saat."
      );

      setSourceError(message);
      setNotification({
        type: "error",
        title: "Reset belum berhasil",
        message,
      });
    } finally {
      setResettingSourceId("");
    }
  };

  const handleFactoryResetWorkspace = async () => {
    try {
      setIsFactoryResetting(true);
      const response = await factoryResetWorkspaceData();
      setFactoryResetOpen(false);
      setNotification({
        type: "success",
        title: "Data workspace berhasil direset",
        message: `${Object.values(response.deleted || {}).reduce((sum, count) => sum + Number(count || 0), 0)} data operasional di Omon dihapus. Identitas dan integrasi tetap aman.`,
      });
    } catch (err) {
      setNotification({
        type: "error",
        title: "Reset workspace belum berhasil",
        message: friendlyErrorMessage(
          err?.response?.data?.detail,
          "Data workspace belum bisa direset. Coba lagi setelah beberapa saat."
        ),
      });
    } finally {
      setIsFactoryResetting(false);
    }
  };

  const handleResetInsightThresholds = () => {
    setInsightResetConfirmOpen(false);
    setInsightThresholds(settingsToForm(defaultInsightThresholds));
    setInsightThresholdError("");
    setInsightThresholdSuccess("Nilai default dimuat. Pilih Simpan Perubahan untuk menyimpannya.");
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
      console.error("Failed to start Google OAuth.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      const message = friendlyErrorMessage(
        err?.response?.data?.detail,
        "Koneksi Google belum bisa dimulai. Coba lagi dari halaman ini."
      );

      setGoogleConnectionError(message);
      setNotification({
        type: "error",
        title: "Koneksi Google belum berhasil",
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
        title: "Koneksi Google berhasil diputus",
        message: "Akses akun Google telah diputuskan. Data Omon dan konfigurasi sumber tetap aman.",
      });
      setDisconnectConfirmOpen(false);
    } catch (err) {
      console.error("Failed to sync Google Sheet source.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      const message = friendlyErrorMessage(
        err?.response?.data?.detail,
        "Koneksi Google belum bisa diputus. Coba lagi."
      );

      setGoogleConnectionError(message);
      setNotification({
        type: "error",
        title: "Koneksi belum terputus",
        message: "Akses Google belum dapat diputuskan. Silakan coba lagi.",
      });
    } finally {
      setIsDisconnectingGoogle(false);
    }
  };

  const handleInviteMember = async (event) => {
    event.preventDefault();

    try {
      setIsInvitingMember(true);
      setNotification(null);
      setWorkspaceConfigurationError("");

      const currentWorkspaceId = workspaceId || getActiveWorkspaceId();

      if (!currentWorkspaceId) {
        throw new Error("Workspace is not available.");
      }

      const response = await createWorkspaceInvitation(currentWorkspaceId, {
        email: inviteEmail.trim(),
        role: "member",
      });

      setWorkspacePendingInvitations((currentInvitations) => [
        response,
        ...currentInvitations.filter((invitation) => invitation.id !== response?.id),
      ]);
      setInviteEmail("");
      setNotification({
        type: "success",
        title: "Undangan terkirim",
        message: `${response?.email || "Member"} menunggu diterima.`,
      });
    } catch (err) {
      console.error("Failed to invite workspace member.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      const message = friendlyErrorMessage(
        err?.response?.data?.detail,
        "Member belum bisa diundang ke workspace."
      );

      setWorkspaceConfigurationError(message);
      setNotification({
        type: "error",
        title: "Undangan belum terkirim",
        message,
      });
    } finally {
      setIsInvitingMember(false);
    }
  };

  const handleCancelInvitation = async (invitationId) => {
    try {
      setCancelingInvitationId(invitationId);
      setWorkspaceConfigurationError("");

      const currentWorkspaceId = workspaceId || getActiveWorkspaceId();

      await cancelWorkspaceInvitation(currentWorkspaceId, invitationId);

      setWorkspacePendingInvitations((currentInvitations) => (
        currentInvitations.filter((invitation) => invitation.id !== invitationId)
      ));
      setNotification({
        type: "success",
        title: "Undangan dibatalkan",
        message: "Undangan tertunda sudah dibatalkan.",
      });
    } catch (err) {
      console.error("Failed to cancel workspace invitation.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      const message = friendlyErrorMessage(
        err?.response?.data?.detail,
        "Undangan belum bisa dibatalkan."
      );

      setWorkspaceConfigurationError(message);
      setNotification({
        type: "error",
        title: "Undangan belum dibatalkan",
        message,
      });
    } finally {
      setCancelingInvitationId("");
    }
  };

  return (
  <div className={`mx-auto w-full max-w-4xl min-w-0 overflow-x-hidden ${hasDirtySettings ? "pb-28" : ""}`}>
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
        <p className="text-xs font-bold uppercase tracking-wider text-muted">
          Pengaturan Omon
        </p>
        <h1 className="text-2xl font-bold text-main sm:text-3xl">
          Settings
        </h1>
        <p className="mt-1 text-sm text-muted sm:text-base">
          Kelola preferensi, workspace, dan koneksi Google Sheet tanpa mengubah data secara tidak sengaja.
        </p>
      </div>

      <div
        className={`flex items-center gap-2 text-sm font-medium metric-positive transition-opacity duration-300 ${
          showSaved ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        aria-live="polite"
      >
        <CheckCircle2 size={16} />
          Semua perubahan tersimpan
      </div>
    </div>

    <section className="mt-6 rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-[var(--color-border)] dark:bg-[var(--color-panel)]">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-bold uppercase tracking-wider text-muted">
            Workspace aktif
          </p>
          <h2 className="mt-1 break-words text-xl font-bold text-main">
            {workspaceName || "Workspace belum tersedia"}
          </h2>
          <p className="mt-1 text-sm leading-6 text-muted">
            Semua pengaturan di halaman ini berlaku untuk workspace ini.
          </p>
        </div>

        <div className="flex flex-wrap gap-2 text-xs font-bold">
          <span className="rounded-full bg-[var(--color-accent-bg)] px-3 py-1 text-accent">
            {formatWorkspaceRole(workspaceRole)}
          </span>
          <span className={`rounded-full px-3 py-1 ${
            hasDirtySettings
              ? "bg-amber-100 text-amber-800 dark:bg-amber-500/10 dark:text-amber-200"
              : "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/10 dark:text-emerald-200"
          }`}>
            {hasDirtySettings ? `${dirtySummary.count} belum disimpan` : "Tidak ada perubahan tertunda"}
          </span>
        </div>
      </div>
    </section>

    <div className="mt-8"><p className="text-xs font-bold uppercase tracking-wider text-muted">Preferensi dan konfigurasi</p></div>
    <div className="mt-3 grid grid-cols-1 gap-6 lg:grid-cols-2">
      <ConfigurationCard
        icon={CalendarDays}
        title="Siklus Bulanan"
        description="Atur kapan transaksi mulai dihitung ke periode budget berikutnya."
      >
        <label className="block text-sm font-semibold text-muted">
          Tanggal mulai periode
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
          Transaksi pada tanggal ini atau setelahnya akan masuk ke siklus budget bulan berikutnya.
        </p>
      </ConfigurationCard>

      <ConfigurationCard
        icon={Settings}
        title="Mode Budget"
        description="Pilih apakah alokasi budget dikelola manual atau dibantu rata-rata historis."
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
            <RefreshCw size={16} className="mr-2 inline" />
            Otomatis
          </button>
        </div>

        <div className="mt-4 rounded-xl bg-[var(--color-panel-hover)] px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">
             Mode aktif
          </p>
          <p className="mt-1 text-sm font-bold text-main">
            {draftAutoBudget ? "Rata-rata historis" : "Alokasi manual"}
          </p>
        </div>
      </ConfigurationCard>

      <ConfigurationCard
        icon={Eye}
        title="Privasi Nominal"
        description="Atur bagaimana nominal ditampilkan saat kamu memakai Omon bersama orang lain."
      >
        <div className="grid grid-cols-3 gap-2 rounded-xl border border-[var(--color-border)] p-1">
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

        <p className="mt-3 flex items-start gap-2 text-sm leading-6 text-muted">
          <Eye size={15} className="mt-0.5 shrink-0" />
          Perubahan ini tersambung dengan kontrol sembunyikan nominal di dashboard setelah disimpan.
        </p>
      </ConfigurationCard>

      <ConfigurationCard
        icon={Link2}
        title="Google Sheet"
        description="Kelola koneksi Google, sumber Spreadsheet, tab sinkronisasi, dan action yang terkait data."
        className="lg:col-span-2"
      >
        <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-[var(--color-border)] dark:bg-[var(--color-panel)] sm:p-8">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[var(--color-accent-bg)] text-accent">
              <Cloud size={21} />
            </div>

            <div className="min-w-0">
              <h3 className="text-lg font-bold leading-7 text-main">
                Koneksi Google
              </h3>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-muted">
                Hubungkan akun Google agar Omon dapat membaca Spreadsheet yang kamu pilih.
              </p>
            </div>
          </div>

          <div className="my-6 h-px bg-gray-200 dark:bg-[var(--color-border)]" />

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
            <div className="min-w-0">
              <p className="text-xs font-bold uppercase tracking-wide text-subtle">
                Status koneksi
              </p>

              <div className="mt-2 flex flex-wrap items-center gap-3">
                <span className={`inline-flex min-h-7 items-center rounded-full px-3 py-1 text-xs font-bold ${
                  googleConnection.connected
                    ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                    : "bg-gray-100 text-gray-600 dark:bg-white/10 dark:text-gray-300"
                }`}>
                  {isLoadingGoogleConnection
                    ? "Memeriksa..."
                    : googleConnection.connected ? "Google Sheet terhubung" : "Belum terhubung"}
                </span>

                {googleConnection.connected && googleConnection.google_email && (
                  <span className="min-w-0 max-w-full truncate text-sm font-semibold text-main">
                    Akun: {googleConnection.google_email}
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
                {googleConnection.connected ? "Hubungkan ulang Google" : "Hubungkan Google"}
              </button>

              <button
                type="button"
                onClick={() => setDisconnectConfirmOpen(true)}
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
                Putuskan Koneksi
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

        <div className="mt-6 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-[var(--color-border)] dark:bg-[var(--color-panel)] sm:p-8">
          <div className="flex flex-col gap-2">
            <h3 className="text-lg font-bold text-main">
              Sumber dan tab Spreadsheet
            </h3>
            <p className="text-sm leading-6 text-muted">
              Tambahkan URL Spreadsheet, periksa akses, lalu pilih tab bulanan yang akan disinkronkan ke Omon.
            </p>
          </div>

          <div className="mt-5 grid grid-cols-1 gap-3 rounded-2xl border border-gray-200 bg-gray-50 p-4 text-sm leading-6 text-muted dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)] md:grid-cols-3">
            {[
              ["1", "Hubungkan Google", "Berikan akses baca untuk workspace ini."],
              ["2", "Simpan sumber", "Pilih Spreadsheet dan tab yang akan dipakai."],
              ["3", "Sinkronkan", "Salin transaksi valid ke Omon dan klasifikasikan."],
            ].map(([step, title, description]) => (
              <div key={step} className="flex gap-3">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[var(--color-accent-bg)] text-xs font-bold text-accent">
                  {step}
                </span>
                <div className="min-w-0">
                  <p className="font-bold text-main">{title}</p>
                  <p>{description}</p>
                </div>
              </div>
            ))}
          </div>

          {!googleConnection.connected ? (
            <div className="mt-6 rounded-2xl border border-gray-200 bg-gray-50 px-4 py-4 text-sm leading-6 text-muted dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)]">
              Hubungkan Google terlebih dahulu untuk menambahkan sumber Spreadsheet. Ini bukan error; data Omon tetap aman.
            </div>
          ) : (
            <>
              <div className="mt-6 grid grid-cols-1 gap-4">
                <label className="block">
                  <span className="mb-2 block text-sm font-semibold text-muted">
                    URL Spreadsheet
                  </span>
                  <input
                    value={spreadsheetUrl}
                    onChange={(event) => {
                      setSpreadsheetUrl(event.target.value);
                      setSourceTestResult(null);
                      setSourceSelectedTabs([]);
                    }}
                    placeholder="https://docs.google.com/spreadsheets/d/..."
                    className="form-control w-full rounded-2xl px-4 py-3 text-sm"
                  />
                </label>

                <fieldset className="block">
                  <span className="mb-2 block text-sm font-semibold text-muted">
                    Pilihan tab bulanan
                  </span>
                  {sourceTestResult?.valid ? (
                    <div className="space-y-2 rounded-2xl border border-gray-200 p-4 dark:border-[var(--color-border)]">
                      {(() => {
                        const tabs = sourceTestResult?.detected_tabs || sourceTestResult?.tabs || [];
                        const allSelected = tabs.length > 0 && sourceSelectedTabs.length === tabs.length;
                        return <>
                          <label className="flex items-center gap-3 font-bold text-main"><input type="checkbox" checked={allSelected} onChange={() => setSourceSelectedTabs(allSelected ? [] : tabs)} /> Pilih semua</label>
                          {tabs.map((tabName) => <label key={tabName} className="flex items-center gap-3 text-sm text-main"><input type="checkbox" checked={sourceSelectedTabs.includes(tabName)} onChange={() => setSourceSelectedTabs((current) => current.includes(tabName) ? current.filter((name) => name !== tabName) : [...current, tabName])} /> {tabName}</label>)}
                        </>;
                      })()}
                    </div>
                  ) : <div className="rounded-2xl border border-gray-200 px-4 py-3 text-sm text-muted dark:border-[var(--color-border)]">Periksa akses Spreadsheet terlebih dahulu.</div>}
                  <p className="mt-2 text-xs leading-5 text-muted">
                    {sourceSelectedTabs.length} tab dipilih
                  </p>
                </fieldset>

                <div className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm leading-6 text-muted dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)]">
                  <p>Spreadsheet perlu memiliki kolom transaksi yang sudah didukung Omon.</p>
                  <p>Omon hanya membaca tab yang dipilih, lalu menyimpan hasil sinkronisasi di Omon.</p>
                  <p>Isi Google Sheet asli tidak diubah oleh proses konfigurasi ini.</p>
                  <p>Tahun transaksi dibaca dari kolom Waktu Transaksi.</p>
                </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <button
                    type="button"
                    onClick={handleTestGoogleSheetSource}
                    disabled={isTestingSource || !spreadsheetUrl.trim()}
                    className="secondary-button min-h-11 rounded-2xl px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isTestingSource ? (
                      <LoaderCircle size={16} className="animate-spin" />
                    ) : (
                      <CheckCircle2 size={16} />
                    )}
                    {isTestingSource ? "Memeriksa..." : "Periksa Akses"}
                  </button>

                  <button
                    type="button"
                    onClick={handleSaveGoogleSheetSource}
                    disabled={
                      isSavingSource
                      || !sourceTestResult?.valid
                      || sourceSelectedTabs.length === 0
                    }
                    className="primary-button min-h-11 rounded-2xl px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isSavingSource ? (
                      <LoaderCircle size={16} className="animate-spin" />
                    ) : (
                      <Link2 size={16} />
                    )}
                    {isSavingSource ? "Menyimpan..." : "Simpan Sumber"}
                  </button>
                </div>

                {sourceTestResult && (
                  <div className={`mt-5 rounded-2xl border px-4 py-3 text-sm leading-6 ${
                    sourceTestResult.valid
                      ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-400/20 dark:bg-emerald-500/10 dark:text-emerald-300"
                      : "border-red-200 bg-red-50 text-red-700 dark:border-red-400/20 dark:bg-red-500/10 dark:text-red-300"
                  }`}>
                    {sourceTestResult.valid ? (
                      <>
                        <p className="font-bold">
                          {sourceTestResult.spreadsheet_title || "Spreadsheet dapat diakses"}
                        </p>
                        <p className="mt-1">
                          Tab tersedia: {(sourceTestResult.tabs || []).join(", ") || "Belum ada tab terdeteksi"}
                        </p>
                        <p className="mt-1">
                          Tab transaksi terdeteksi: {(sourceTestResult.detected_tabs || []).join(", ") || "Belum ada tab transaksi terdeteksi"}
                        </p>
                        {(sourceTestResult.skipped_tabs || []).length > 0 && (
                          <p className="mt-1">
                            Tab dilewati: {sourceTestResult.skipped_tabs.join(", ")}
                          </p>
                        )}
                      </>
                    ) : (
                      <p>{friendlyErrorMessage(sourceTestResult.message, "Spreadsheet belum bisa diperiksa.")}</p>
                    )}
                  </div>
                )}

                {sourceError && (
                  <div className="mt-5 flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm leading-6 text-red-700 dark:border-red-400/20 dark:bg-red-500/10 dark:text-red-300">
                    <XCircle size={17} className="mt-0.5 shrink-0" />
                    <p className="min-w-0">{sourceError}</p>
                  </div>
                )}

                <div className="mt-8">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <p className="text-sm font-bold text-main">
                      Sumber tersimpan
                    </p>
                    <button
                      type="button"
                      onClick={loadGoogleSheetSources}
                      disabled={isLoadingSources}
                      className="secondary-button min-h-9 rounded-xl px-3 py-1.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {isLoadingSources ? (
                        <LoaderCircle size={15} className="animate-spin" />
                      ) : (
                        <RefreshCw size={15} />
                      )}
                      Muat ulang
                    </button>
                  </div>

                  {isLoadingSources ? (
                    <div className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-4 text-sm text-muted dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)]">
                      Memuat sumber...
                    </div>
                  ) : googleSheetSources.length > 0 ? (
                    <ul className="space-y-3">
                      {googleSheetSources.map((source) => {
                        const syncResult = syncResults[source.source_id];
                        const sourceTitle = String(
                          source.spreadsheet_title || "Google Spreadsheet"
                        ).trim();
                        const sourceStatus = source.status === "disabled"
                          ? "Nonaktif"
                          : source.status === "error"
                            ? "Perlu dicek"
                            : "Aktif";

                        return (
                          <li
                            key={source.source_id}
                            className="rounded-2xl border border-gray-200 bg-gray-50 p-4 dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)]"
                          >
                            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                              <div className="min-w-0 flex-1">
                                <p
                                  className="line-clamp-2 break-words text-sm font-bold leading-5 text-main"
                                  title={sourceTitle}
                                >
                                  {sourceTitle}
                                </p>
                                <p className="mt-1 text-xs text-muted">
                                  Status sumber - {sourceStatus}
                                </p>
                                <div className="mt-2 space-y-1 text-xs leading-5 text-muted">
                                  <p>Sinkronisasi hanya memakai tab yang dipilih.</p>
                                  <p>Tahun dibaca dari Waktu Transaksi.</p>
                                  {(source.selected_tabs || []).length > 0 ? (
                                    <p>Tab dipilih: {source.selected_tabs.join(", ")}</p>
                                  ) : source.sheet_name && (
                                    <p>Tab utama: {source.sheet_name}</p>
                                  )}
                                </div>
                                <p className="mt-2 text-xs text-muted">
                                  {formatSyncTimestamp(source.last_synced_at)}
                                </p>
                              </div>

                              <div className="flex shrink-0 flex-col gap-2 sm:flex-row sm:flex-wrap sm:justify-end">
                                <button
                                  type="button"
                                  onClick={() => handleSyncSource(source.source_id)}
                                  disabled={
                                    syncingSourceId === source.source_id
                                    || resettingSourceId === source.source_id
                                  }
                                  className="primary-button min-h-10 rounded-2xl px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                  {syncingSourceId === source.source_id ? (
                                    <LoaderCircle size={16} className="animate-spin" />
                                  ) : (
                                    <RefreshCw size={16} />
                                  )}
                                  {syncingSourceId === source.source_id ? "Menyinkronkan..." : "Sinkronkan"}
                                </button>

                                <button
                                  type="button"
                                  onClick={() => setResetSource(source)}
                                  disabled={
                                    resettingSourceId === source.source_id
                                    || syncingSourceId === source.source_id
                                  }
                                  className="secondary-button min-h-10 rounded-2xl border-red-200 px-4 py-2 text-sm font-semibold text-red-600 hover:border-red-300 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-red-400/30 dark:text-red-300 dark:hover:bg-red-500/10"
                                >
                                  {resettingSourceId === source.source_id ? (
                                    <LoaderCircle size={16} className="animate-spin" />
                                  ) : (
                                    <Trash2 size={16} />
                                  )}
                                  {resettingSourceId === source.source_id ? "Mereset..." : "Reset Data Tersinkron"}
                                </button>
                              </div>
                            </div>

                            {syncResult && (
                              <>
                                <div className="mt-4 grid grid-cols-2 gap-2 text-xs sm:grid-cols-5">
                                  {[
                                    ["Total", syncResult.total_rows],
                                    ["Baru", syncResult.inserted_rows],
                                    ["Diperbarui", syncResult.updated_rows],
                                    ["Dilewati", syncResult.skipped_rows],
                                    ["Gagal", syncResult.failed_rows],
                                  ].map(([label, value]) => (
                                    <div
                                      key={label}
                                      className="rounded-xl border border-gray-200 bg-white px-3 py-2 dark:border-[var(--color-border)] dark:bg-[var(--color-panel)]"
                                    >
                                      <p className="font-semibold text-muted">{label}</p>
                                      <p className="mt-1 text-base font-bold text-main">
                                        {value ?? 0}
                                      </p>
                                    </div>
                                  ))}
                                </div>

                                {(
                                  (syncResult.inserted_rows || 0)
                                  + (syncResult.updated_rows || 0)
                                  + (syncResult.skipped_rows || 0)
                                  + (syncResult.failed_rows || 0)
                                ) > 0 && (
                                  <button type="button" onClick={() => setDetailResult(syncResult)} className="secondary-button mt-3 min-h-10 rounded-xl px-4 py-2 text-sm font-bold">
                                    <Eye size={16} /> Lihat Detail
                                  </button>
                                )}

                                <div className="mt-3 space-y-1 text-xs leading-5 text-muted">
                                  {syncResult.classification && (
                                    <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 font-semibold text-emerald-800 dark:border-emerald-400/20 dark:bg-emerald-500/10 dark:text-emerald-200">
                                      {formatClassificationSummary(syncResult.classification)}
                                      {" "}
                                      Dilewati manual: {syncResult.classification.skipped_manual || 0}.
                                      {" "}
                                      Error: {syncResult.classification.errors || 0}.
                                    </p>
                                  )}
                                  {(syncResult.warnings || []).includes("classification_failed") && (
                                    <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 font-semibold text-amber-800 dark:border-amber-400/20 dark:bg-amber-500/10 dark:text-amber-200">
                                      Klasifikasi belum selesai. Data yang sudah masuk Omon tetap aman.
                                    </p>
                                  )}
                                  {(syncResult.failed_rows || 0) > 0 && (
                                    <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 font-semibold text-amber-800 dark:border-amber-400/20 dark:bg-amber-500/10 dark:text-amber-200">
                                      Beberapa baris belum masuk Omon. Lihat alasannya di bawah.
                                    </p>
                                  )}
                                  {(syncResult.processed_tabs || []).length > 0 && (
                                    <p>
                                      Tab diproses: {syncResult.processed_tabs.join(", ")}
                                    </p>
                                  )}
                                  {(syncResult.skipped_tabs || []).length > 0 && (
                                    <p>
                                      Tab dilewati: {syncResult.skipped_tabs.join(", ")}
                                    </p>
                                  )}
                                  {(syncResult.failed_tabs || []).length > 0 && (
                                    <p>
                                      Tab gagal: {syncResult.failed_tabs.join(", ")}
                                    </p>
                                  )}
                                </div>

                                {(hasReasonEntries(syncResult.failed_reasons)
                                  || hasReasonEntries(syncResult.skipped_reasons)
                                  || (syncResult.failed_samples || []).length > 0
                                  || (syncResult.skipped_samples || []).length > 0) && (
                                  <div className="mt-3 grid grid-cols-1 gap-2 text-xs leading-5 md:grid-cols-2">
                                    <SyncReasonBreakdown
                                      title="Alasan gagal"
                                      reasons={syncResult.failed_reasons}
                                      tone="warning"
                                    />
                                    <SyncReasonBreakdown
                                      title="Alasan dilewati"
                                      reasons={syncResult.skipped_reasons}
                                    />
                                    <SyncSamples
                                      title="Contoh gagal"
                                      samples={syncResult.failed_samples || []}
                                    />
                                    <SyncSamples
                                      title="Contoh dilewati"
                                      samples={syncResult.skipped_samples || []}
                                    />
                                  </div>
                                )}
                              </>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  ) : (
                    <div className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-4 text-sm text-muted dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)]">
                      Belum ada sumber tersimpan. Tambahkan URL Spreadsheet, periksa akses, simpan sumber, lalu sinkronkan untuk mengisi Omon.
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
        {workspaceConfigurationError && (
          <p className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {workspaceConfigurationError}
          </p>
        )}

      </ConfigurationCard>

      <ConfigurationCard
        icon={SlidersHorizontal}
        title="Ambang Insight"
        description="Atur kapan insight Need, Want, Saving, uncategorized, dan anomali mulai ditandai untuk workspace ini."
      >
        <div className="space-y-6">
          <div className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm leading-6 text-muted dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)]">
            <p>
              Ambang ini mengatur cara Omon memberi tanda perhatian pada pola keuangan.
            </p>
            <p className="mt-1 font-semibold text-main">
              {insightThresholds.source === "workspace"
                ? "Menggunakan ambang khusus workspace."
                : "Menggunakan ambang default Omon."}
            </p>
          </div>

          {isLoadingInsightThresholds ? (
            <div className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-4 text-sm text-muted dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)]">
              Memuat pengaturan insight...
            </div>
          ) : (
            <>
              <div>
                <h3 className="text-sm font-bold text-main">
                  Rasio pengeluaran
                </h3>
                <div className="mt-3 grid grid-cols-1 gap-3">
                  <ThresholdSlider
                    label="Need mulai perlu perhatian"
                    helperText="Ditandai ketika pengeluaran Need mencapai persentase ini dari total expense."
                    valuePercent={insightThresholds.need_warning_ratio}
                    onChangePercent={(value) => updateInsightField("need_warning_ratio", value)}
                    disabled={isSaving}
                  />
                  <ThresholdSlider
                    label="Need tinggi"
                    helperText="Ditandai kuat ketika pengeluaran Need mencapai persentase ini dari total expense."
                    valuePercent={insightThresholds.need_danger_ratio}
                    onChangePercent={(value) => updateInsightField("need_danger_ratio", value)}
                    disabled={isSaving}
                  />
                  <ThresholdSlider
                    label="Want mulai perlu perhatian"
                    helperText="Ditandai ketika pengeluaran Want mencapai persentase ini dari total expense."
                    valuePercent={insightThresholds.want_warning_ratio}
                    onChangePercent={(value) => updateInsightField("want_warning_ratio", value)}
                    disabled={isSaving}
                  />
                  <ThresholdSlider
                    label="Want tinggi"
                    helperText="Ditandai kuat ketika pengeluaran Want mencapai persentase ini dari total expense."
                    valuePercent={insightThresholds.want_danger_ratio}
                    onChangePercent={(value) => updateInsightField("want_danger_ratio", value)}
                    disabled={isSaving}
                  />
                </div>
              </div>

              <div className="border-t border-gray-200 pt-5 dark:border-[var(--color-border)]">
                <h3 className="text-sm font-bold text-main">
                  Saving
                </h3>
                <div className="mt-3 grid grid-cols-1 gap-3">
                  <ThresholdSlider
                    label="Saving perlu perhatian"
                    helperText="Ditandai ketika alokasi Saving berada di bawah persentase income ini."
                    valuePercent={insightThresholds.saving_warning_ratio}
                    onChangePercent={(value) => updateInsightField("saving_warning_ratio", value)}
                    disabled={isSaving}
                  />
                  <ThresholdSlider
                    label="Saving sehat"
                    helperText="Ditandai positif ketika alokasi Saving mencapai persentase income ini."
                    valuePercent={insightThresholds.saving_good_ratio}
                    onChangePercent={(value) => updateInsightField("saving_good_ratio", value)}
                    disabled={isSaving}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 gap-5 border-t border-gray-200 pt-5 dark:border-[var(--color-border)] md:grid-cols-2">
                <div>
                  <h3 className="text-sm font-bold text-main">
                    Kualitas data
                  </h3>
                  <div className="mt-3 grid grid-cols-1 gap-3">
                    {[
                      [
                        "uncategorized_warning_count",
                        "Tanpa kategori mulai perlu perhatian",
                        "Ditandai ketika jumlah transaksi tanpa kategori mencapai angka ini.",
                      ],
                      [
                        "uncategorized_danger_count",
                        "Tanpa kategori tinggi",
                        "Ditandai kuat ketika jumlah transaksi tanpa kategori mencapai angka ini.",
                      ],
                    ].map(([field, label, helperText]) => (
                      <label
                        key={field}
                        className="block rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)]"
                      >
                        <span className="text-sm font-bold text-main">{label}</span>
                        <p className="mt-1 text-xs leading-5 text-muted">{helperText}</p>
                        <input
                          type="number"
                          min="0"
                          step="1"
                          value={insightThresholds[field]}
                          onChange={(event) => updateInsightField(field, event.target.value)}
                          disabled={isSaving}
                          className="form-control mt-3 w-full rounded-xl px-3 py-2 text-sm"
                        />
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-bold text-main">
                    Anomali transaksi
                  </h3>
                  <div className="mt-3 grid grid-cols-1 gap-3">
                    {[
                      [
                        "anomaly_warning_multiplier",
                        "Anomali mulai perlu perhatian",
                        "Ditandai ketika transaksi sekian kali lebih tinggi dari rata-rata kategorinya.",
                      ],
                      [
                        "anomaly_danger_multiplier",
                        "Anomali tinggi",
                        "Ditandai kuat ketika transaksi sekian kali lebih tinggi dari rata-rata kategorinya.",
                      ],
                    ].map(([field, label, helperText]) => (
                      <label
                        key={field}
                        className="block rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)]"
                      >
                        <span className="text-sm font-bold text-main">{label}</span>
                        <p className="mt-1 text-xs leading-5 text-muted">{helperText}</p>
                        <input
                          type="number"
                          min="1"
                          step="0.1"
                          value={insightThresholds[field]}
                          onChange={(event) => updateInsightField(field, event.target.value)}
                          disabled={isSaving}
                          className="form-control mt-3 w-full rounded-xl px-3 py-2 text-sm"
                        />
                      </label>
                    ))}
                  </div>
                </div>
              </div>

              {(insightValidationError || insightThresholdError) && (
                <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm leading-6 text-red-700 dark:border-red-400/20 dark:bg-red-500/10 dark:text-red-300">
                  <XCircle size={17} className="mt-0.5 shrink-0" />
                  <p>{insightThresholdError || insightValidationError}</p>
                </div>
              )}

              {insightThresholdSuccess && (
                <div className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm leading-6 text-emerald-800 dark:border-emerald-400/20 dark:bg-emerald-500/10 dark:text-emerald-300">
                  <CheckCircle2 size={17} className="mt-0.5 shrink-0" />
                  <p>{insightThresholdSuccess}</p>
                </div>
              )}

              <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
                <button
                  type="button"
                  onClick={() => setInsightResetConfirmOpen(true)}
                  disabled={isSaving}
                  className="secondary-button min-h-11 rounded-2xl px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Muat Nilai Default
                </button>
              </div>
            </>
          )}
        </div>
      </ConfigurationCard>

      <ConfigurationCard
        icon={MailPlus}
        title="Workspace & Akses"
        description="Lihat siapa saja yang memiliki akses ke workspace ini dan kirim undangan jika peranmu mengizinkan."
      >
        {canInviteMembers && (
          <form onSubmit={handleInviteMember} className="grid grid-cols-1 gap-4">
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
                {isInvitingMember ? "Mengirim..." : "Undang Member"}
              </button>
            </div>
          </form>
        )}

          <div className={`${canInviteMembers ? "mt-6" : ""} rounded-xl border border-gray-100 bg-gray-50 p-4 dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)]`}>
            <p className="mb-3 text-xs font-bold uppercase tracking-wide text-muted">
              Member aktif
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
                Belum ada member lain di workspace ini. Gunakan form di atas untuk mengirim undangan pertama.
              </p>
            )}
          </div>

        {canInviteMembers && (
          <div className="mt-6 rounded-xl border border-gray-100 bg-gray-50 p-4 dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)]">
            <p className="mb-3 text-xs font-bold uppercase tracking-wide text-muted">
              Undangan tertunda
            </p>

            {workspacePendingInvitations.length > 0 ? (
              <ul className="space-y-2">
                {workspacePendingInvitations.map((invitation) => (
                  <li
                    key={invitation.id}
                    className="flex flex-col gap-3 rounded-lg border border-gray-100 bg-white px-4 py-3 dark:border-[var(--color-border)] dark:bg-[var(--color-panel)] sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-bold text-main">
                        {invitation.email}
                      </p>
                      <p className="truncate text-xs text-muted">
                        {invitation.role} | Menunggu diterima
                      </p>
                    </div>

                    <div className="flex shrink-0 items-center gap-2">
                      <span className="rounded-full bg-amber-100 px-2 py-1 text-xs font-bold text-amber-800 dark:bg-amber-500/10 dark:text-amber-200">
                        tertunda
                      </span>
                      <button
                        type="button"
                        onClick={() => handleCancelInvitation(invitation.id)}
                        disabled={cancelingInvitationId === invitation.id}
                        className="secondary-button min-h-9 rounded-lg px-3 py-1.5 text-xs font-bold disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {cancelingInvitationId === invitation.id ? (
                          <LoaderCircle size={14} className="animate-spin" />
                        ) : (
                          <XCircle size={14} />
                        )}
                        {cancelingInvitationId === invitation.id
                          ? "Membatalkan..."
                          : "Batalkan Undangan"}
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted">
                Tidak ada undangan yang sedang menunggu.
              </p>
            )}
          </div>
        )}
      </ConfigurationCard>
    </div>

    {systemInfoState?.data?.appEnv === "local-dev" && (
      <div className="mt-8">
        <p className="mb-3 text-xs font-bold uppercase tracking-wider text-muted">Environment</p>
        <SystemInfoPanel systemInfoState={systemInfoState} />
        <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-5 dark:border-red-400/20 dark:bg-red-500/10"><h3 className="font-bold text-main">Reset Data Workspace Local</h3><p className="mt-2 text-sm leading-6 text-muted">Tindakan ini hanya tersedia di Local Development. Data operasional Omon di workspace ini akan dihapus; akun, akses member, koneksi Google, dan konfigurasi Google Sheet tetap aman.</p><button type="button" onClick={() => setFactoryResetOpen(true)} className="mt-4 rounded-xl bg-red-600 px-4 py-2 text-sm font-bold text-white">Reset Data Workspace Local</button></div>
      </div>
    )}
    {hasDirtySettings && (
      <div className="fixed inset-x-4 bottom-20 z-[70] mx-auto max-w-3xl animate-[fadeIn_180ms_ease-out] rounded-2xl border border-[var(--color-border)] bg-[var(--color-panel)] p-4 shadow-xl lg:bottom-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div><p className="font-bold text-main">Perubahan belum disimpan</p><p className="text-sm text-muted">{dirtySummary.count} pengaturan berubah. Action langsung seperti sinkronisasi dan reset tidak masuk hitungan ini.</p></div>
          <div className="flex gap-2"><button type="button" onClick={handleDiscard} disabled={isSaving} className="secondary-button flex-1 rounded-xl px-4 py-2 font-bold sm:flex-none">Batalkan Perubahan</button><button type="button" onClick={handleSave} disabled={isSaving || Boolean(insightValidationError && dirtySummary.insightFields.length)} className="primary-button flex-1 rounded-xl px-4 py-2 font-bold sm:flex-none">{isSaving && <LoaderCircle size={16} className="animate-spin" />}{isSaving ? "Menyimpan..." : "Simpan Perubahan"}</button></div>
        </div>
      </div>
    )}
    {pendingNavigation && (
      <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label="Perubahan belum disimpan">
        <div className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-xl dark:bg-[var(--color-panel)]"><h2 className="text-xl font-bold text-main">Perubahan belum disimpan</h2><p className="mt-3 text-sm leading-6 text-muted">Ada konfigurasi Settings yang belum disimpan.</p><p className="mt-2 text-sm leading-6 text-muted">Jika keluar sekarang, perubahan form akan dibatalkan. Data Omon dan Google Sheet tetap aman.</p><div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end"><button type="button" onClick={onCancelNavigation} className="secondary-button rounded-xl px-4 py-2 font-bold">Tetap di Settings</button><button type="button" onClick={() => { handleDiscard(); onDiscardAndNavigate?.(); }} className="secondary-button rounded-xl px-4 py-2 font-bold text-red-600">Batalkan & Keluar</button><button type="button" onClick={async () => { if (await handleSave()) onSaveAndNavigate?.(); }} disabled={isSaving} className="primary-button rounded-xl px-4 py-2 font-bold">Simpan & Keluar</button></div></div>
      </div>
    )}
    {factoryResetOpen && (
      <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label="Reset Data Workspace Local"><div className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-xl dark:bg-[var(--color-panel)]"><h2 className="text-xl font-bold text-main">Reset Data Workspace Local</h2><div className="mt-4 space-y-3 text-sm leading-6 text-muted"><p>Tindakan ini menghapus data operasional Omon untuk workspace aktif, termasuk transaksi, draft import, history import, fingerprint, budget, dan riwayat sinkronisasi.</p><p className="font-bold text-main">Isi Google Sheet asli tidak akan dihapus atau diubah.</p><p>Akun, workspace, akses member, koneksi Google, dan konfigurasi Google Sheet tetap aman.</p></div><div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end"><button type="button" onClick={() => setFactoryResetOpen(false)} disabled={isFactoryResetting} className="secondary-button rounded-xl px-4 py-2 font-bold">Batal</button><button type="button" onClick={handleFactoryResetWorkspace} disabled={isFactoryResetting} className="rounded-xl bg-red-600 px-4 py-2 font-bold text-white disabled:opacity-60">{isFactoryResetting ? "Mereset..." : "Reset Data Workspace"}</button></div></div></div>
    )}
    {detailResult && (
      <ImportResultDetailsModal result={detailResult} onClose={() => setDetailResult(null)} privacyMode={privacyMode} />
    )}
    {resetSource && (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label="Reset Data Hasil Sinkronisasi">
        <div className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-xl dark:bg-[var(--color-panel)]">
          <h2 className="text-xl font-bold text-main">Reset Data Hasil Sinkronisasi</h2>
          <div className="mt-4 space-y-3 text-sm leading-6 text-muted">
            <p>Transaksi yang berasal dari sumber Spreadsheet ini akan dihapus dari Omon sesuai sumber yang dipilih.</p>
            <p className="font-bold text-main">Isi Google Sheet asli tetap aman dan tidak akan diubah.</p>
            <p>Kamu dapat melakukan sinkronisasi ulang kapan saja dengan tombol Sinkronkan.</p>
          </div>
          <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <button type="button" onClick={() => setResetSource(null)} disabled={Boolean(resettingSourceId)} className="secondary-button rounded-xl px-4 py-2 font-bold">Batal</button>
            <button type="button" onClick={handleResetSourceData} disabled={Boolean(resettingSourceId)} className="inline-flex items-center justify-center gap-2 rounded-xl bg-red-600 px-4 py-2 font-bold text-white disabled:opacity-60">
              {resettingSourceId && <LoaderCircle size={16} className="animate-spin" />}
              {resettingSourceId ? "Mereset..." : "Reset Data Tersinkron"}
            </button>
          </div>
        </div>
      </div>
    )}
    <ConfirmationDialog
      open={disconnectConfirmOpen}
      title="Putuskan koneksi Google?"
      description="Omon tidak akan dapat sinkronisasi baru sampai akun Google dihubungkan kembali."
      affectedItems={["Akses Omon ke akun Google akan diputuskan", "Sinkronisasi baru tidak dapat dijalankan"]}
      safeItems={["Data yang sudah tersimpan di Omon", "Google Sheet asli", "Sumber dan konfigurasi workspace"]}
      confirmLabel="Putuskan Koneksi"
      isLoading={isDisconnectingGoogle}
      onCancel={() => setDisconnectConfirmOpen(false)}
      onConfirm={handleDisconnectGoogle}
    />
    <ConfirmationDialog
      open={insightResetConfirmOpen}
      title="Muat nilai insight default?"
      description="Nilai default hanya dimuat ke form dan belum disimpan sampai kamu memilih Simpan Perubahan."
      affectedItems={["Perubahan insight yang belum disimpan akan diganti"]}
      safeItems={["Pengaturan tersimpan tetap aman sampai Simpan Perubahan dipilih"]}
      confirmLabel="Muat Nilai Default"
      onCancel={() => setInsightResetConfirmOpen(false)}
      onConfirm={handleResetInsightThresholds}
    />
  </div>
  );
};

export default Configuration;
