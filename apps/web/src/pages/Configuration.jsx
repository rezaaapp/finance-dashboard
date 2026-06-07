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
import { useCallback, useEffect, useState } from "react";

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
  deleteGoogleSheetSource,
  getGoogleSheetSources,
  syncGoogleSheetSource,
  testGoogleSheetSource,
} from "../api/googleSheetSourcesApi";
import {
  getInsightThresholds,
  updateInsightThresholds,
} from "../api/insightSettingsApi";

import { PRIVACY_MODES } from "../utils/privacy";
import { getActiveWorkspaceId } from "../api/workspaceContext";

const privacyOptions = [
  { label: "Normal", value: PRIVACY_MODES.normal },
  { label: "Hide", value: PRIVACY_MODES.hide },
  { label: "Guest", value: PRIVACY_MODES.guest },
];

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
    return "Never synced";
  }

  try {
    return new Intl.DateTimeFormat("en", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return "Last sync unavailable";
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

  return `Classification: ${classification.processed || 0} transactions processed, ${classification.low_confidence || 0} low confidence.`;
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
}) => {
  const [draftAutoBudget, setDraftAutoBudget] = useState(autoBudget);
  const [draftPaydayStartDay, setDraftPaydayStartDay] = useState(paydayStartDay);
  const [draftPrivacyMode, setDraftPrivacyMode] = useState(privacyMode);
  const [workspaceName, setWorkspaceName] = useState("");
  const [workspaceId, setWorkspaceId] = useState("");
  const [workspaceRole, setWorkspaceRole] = useState("");
  const [workspaceMembers, setWorkspaceMembers] = useState([]);
  const [workspacePendingInvitations, setWorkspacePendingInvitations] = useState([]);
  const [isConnectingGoogle, setIsConnectingGoogle] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDisconnectingGoogle, setIsDisconnectingGoogle] = useState(false);
  const [isLoadingGoogleConnection, setIsLoadingGoogleConnection] = useState(true);
  const [isLoadingSources, setIsLoadingSources] = useState(false);
  const [isTestingSource, setIsTestingSource] = useState(false);
  const [isSavingSource, setIsSavingSource] = useState(false);
  const [syncingSourceId, setSyncingSourceId] = useState("");
  const [deletingSourceId, setDeletingSourceId] = useState("");
  const [isInvitingMember, setIsInvitingMember] = useState(false);
  const [cancelingInvitationId, setCancelingInvitationId] = useState("");
  const [, setIsLoadingWorkspaceConfiguration] = useState(true);
  const [inviteEmail, setInviteEmail] = useState("");
  const [spreadsheetUrl, setSpreadsheetUrl] = useState("");
  const [showSaved, setShowSaved] = useState(false);
  const [notification, setNotification] = useState(null);
  const [googleConnection, setGoogleConnection] = useState({
    connected: false,
  });
  const [googleSheetSources, setGoogleSheetSources] = useState([]);
  const [sourceTestResult, setSourceTestResult] = useState(null);
  const [sourceError, setSourceError] = useState("");
  const [syncResults, setSyncResults] = useState({});
  const [googleConnectionError, setGoogleConnectionError] = useState("");
  const [workspaceConfigurationError, setWorkspaceConfigurationError] = useState("");
  const [insightThresholds, setInsightThresholds] = useState(
    settingsToForm(defaultInsightThresholds)
  );
  const [isLoadingInsightThresholds, setIsLoadingInsightThresholds] = useState(false);
  const [isSavingInsightThresholds, setIsSavingInsightThresholds] = useState(false);
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
      return "All insight threshold fields must be filled.";
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
      return "All insight threshold fields must contain valid numbers.";
    }

    if (percentFields.some((field) => Number(form[field]) < 0 || Number(form[field]) > 100)) {
      return "Percentage thresholds must be between 0 and 100.";
    }

    if (payload.need_warning_ratio > payload.need_danger_ratio) {
      return "Need warning threshold must be less than or equal to Need danger threshold.";
    }

    if (payload.want_warning_ratio > payload.want_danger_ratio) {
      return "Want warning threshold must be less than or equal to Want danger threshold.";
    }

    if (payload.saving_warning_ratio > payload.saving_good_ratio) {
      return "Saving warning threshold must be less than or equal to Saving good threshold.";
    }

    if (payload.uncategorized_warning_count < 0 || payload.uncategorized_danger_count < 0) {
      return "Uncategorized counts cannot be negative.";
    }

    if (payload.uncategorized_warning_count > payload.uncategorized_danger_count) {
      return "Uncategorized warning count must be less than or equal to danger count.";
    }

    if (payload.anomaly_warning_multiplier < 1 || payload.anomaly_danger_multiplier < 1) {
      return "Anomaly multipliers must be at least 1.0.";
    }

    if (payload.anomaly_warning_multiplier > payload.anomaly_danger_multiplier) {
      return "Anomaly warning multiplier must be less than or equal to danger multiplier.";
    }

    return "";
  }, []);

  const insightValidationError = validateInsightThresholds(insightThresholds);

  const loadInsightThresholds = useCallback(async () => {
    try {
      setIsLoadingInsightThresholds(true);
      setInsightThresholdError("");

      const response = await getInsightThresholds();

      setInsightThresholds(settingsToForm(response || defaultInsightThresholds));
    } catch (err) {
      console.error("Failed to load insight thresholds.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      setInsightThresholdError("Insight severity settings are not available.");
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

      setSourceError("Google Sheet sources are not available.");
    } finally {
      setIsLoadingSources(false);
    }
  }, [onUnauthorized]);

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
          if (response?.connected) {
            loadGoogleSheetSources();
          }
        })
        .catch(() => {
          console.error("Failed to refresh Google connection status.");
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
  }, [loadGoogleSheetSources]);

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
      console.error("Failed to save configuration.");

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
        setSourceError(response?.message || "Google Sheet connection test failed.");
        return;
      }

      setNotification({
        type: "success",
        title: "Google Sheet verified",
        message: `${response.spreadsheet_title || "Spreadsheet"} is accessible.`,
      });
    } catch (err) {
      console.error("Failed to save workspace configuration.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      const message = err?.response?.data?.detail
        || "Google Sheet connection test failed.";

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
      });

      setSpreadsheetUrl("");
      setSourceTestResult(null);
      setNotification({
        type: "success",
        title: "Google Sheet source saved",
        message: `${response?.spreadsheet_title || "Google Spreadsheet"} is ready to sync.`,
      });
      await loadGoogleSheetSources();
    } catch (err) {
      console.error("Failed to test Google Sheet connection.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      const message = err?.response?.data?.detail
        || "Google Sheet source could not be saved.";

      setSourceError(message);
      setNotification({
        type: "error",
        title: "Save source failed",
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
          `${response?.inserted_rows || 0} inserted, ${response?.updated_rows || 0} updated.`,
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
      const message = typeof detail === "string"
        ? detail
        : detail?.message || "Google Sheet sync failed.";

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

  const handleDeleteSource = async (sourceId) => {
    const shouldDelete = window.confirm(
      "Delete this Google Sheet source? Existing synced transactions will stay in the database."
    );

    if (!shouldDelete) {
      return;
    }

    try {
      setDeletingSourceId(sourceId);
      setSourceError("");
      setNotification(null);

      await deleteGoogleSheetSource(sourceId);

      setSyncResults((currentResults) => {
        const nextResults = { ...currentResults };
        delete nextResults[sourceId];
        return nextResults;
      });
      setNotification({
        type: "success",
        title: "Source deleted",
        message: "Google Sheet source was removed from saved sources.",
      });
      await loadGoogleSheetSources();
    } catch (err) {
      console.error("Failed to save insight thresholds.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      const message = err?.response?.data?.detail
        || "Google Sheet source could not be deleted.";

      setSourceError(message);
      setNotification({
        type: "error",
        title: "Delete source failed",
        message,
      });
    } finally {
      setDeletingSourceId("");
    }
  };

  const handleSaveInsightThresholds = async () => {
    const validationMessage = validateInsightThresholds(insightThresholds);

    if (validationMessage) {
      setInsightThresholdError(validationMessage);
      return;
    }

    try {
      setIsSavingInsightThresholds(true);
      setInsightThresholdError("");
      setInsightThresholdSuccess("");

      const response = await updateInsightThresholds(
        formToPayload(insightThresholds)
      );

      setInsightThresholds(settingsToForm(response || {
        ...defaultInsightThresholds,
        source: "workspace",
      }));
      setInsightThresholdSuccess("Insight severity settings saved.");
    } catch (err) {
      console.error("Failed to disconnect Google account.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      setInsightThresholdError(
        err?.response?.data?.detail
        || "Insight severity settings could not be saved."
      );
    } finally {
      setIsSavingInsightThresholds(false);
    }
  };

  const handleResetInsightThresholds = () => {
    const shouldReset = window.confirm(
      "Load default insight severity values? Click Save Settings afterward to apply them."
    );

    if (!shouldReset) {
      return;
    }

    setInsightThresholds(settingsToForm(defaultInsightThresholds));
    setInsightThresholdError("");
    setInsightThresholdSuccess("Default values loaded. Click Save Settings to apply.");
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
      console.error("Failed to sync Google Sheet source.");

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
        title: "Invitation sent",
        message: `${response?.email || "Member"} is waiting for acceptance.`,
      });
    } catch (err) {
      console.error("Failed to invite workspace member.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      const message = err?.response?.data?.detail
        || "Member gagal diundang ke workspace.";

      setWorkspaceConfigurationError(message);
      setNotification({
        type: "error",
        title: "Invite failed",
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
        title: "Invite cancelled",
        message: "Pending invitation was cancelled.",
      });
    } catch (err) {
      console.error("Failed to cancel workspace invitation.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      const message = err?.response?.data?.detail
        || "Invitation could not be cancelled.";

      setWorkspaceConfigurationError(message);
      setNotification({
        type: "error",
        title: "Cancel failed",
        message,
      });
    } finally {
      setCancelingInvitationId("");
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
            <RefreshCw size={16} className="mr-2 inline" />
            Auto
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

        <div className="mt-6 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-[var(--color-border)] dark:bg-[var(--color-panel)] sm:p-8">
          <div className="flex flex-col gap-2">
            <h3 className="text-lg font-bold text-main">
              Google Sheet Data Sources
            </h3>
            <p className="text-sm leading-6 text-muted">
              Paste a spreadsheet URL, test access, then sync all valid monthly tabs.
            </p>
          </div>

          <div className="mt-5 grid grid-cols-1 gap-3 rounded-2xl border border-gray-200 bg-gray-50 p-4 text-sm leading-6 text-muted dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)] md:grid-cols-3">
            {[
              ["1", "Connect Google", "Authorize this workspace to read your Google Sheets."],
              ["2", "Add source", "Paste the spreadsheet URL, test access, and save it."],
              ["3", "Sync Now", "Import valid transactions and classify them automatically."],
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
              Connect Google first to add spreadsheet sources.
            </div>
          ) : (
            <>
              <div className="mt-6 grid grid-cols-1 gap-4">
                <label className="block">
                  <span className="mb-2 block text-sm font-semibold text-muted">
                    Spreadsheet URL
                  </span>
                  <input
                    value={spreadsheetUrl}
                    onChange={(event) => {
                      setSpreadsheetUrl(event.target.value);
                      setSourceTestResult(null);
                    }}
                    placeholder="https://docs.google.com/spreadsheets/d/..."
                    className="form-control w-full rounded-2xl px-4 py-3 text-sm"
                  />
                </label>

                <div className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm leading-6 text-muted dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)]">
                  <p>Your spreadsheet should contain the required transaction columns.</p>
                  <p>This spreadsheet will sync all valid monthly tabs.</p>
                  <p>Transaction year will be detected from Waktu Transaksi.</p>
                  <p>Transactions are classified automatically after sync.</p>
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
                    {isTestingSource ? "Testing..." : "Test Connection"}
                  </button>

                  <button
                    type="button"
                    onClick={handleSaveGoogleSheetSource}
                    disabled={
                      isSavingSource
                      || !sourceTestResult?.valid
                    }
                    className="primary-button min-h-11 rounded-2xl px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isSavingSource ? (
                      <LoaderCircle size={16} className="animate-spin" />
                    ) : (
                      <Link2 size={16} />
                    )}
                    {isSavingSource ? "Saving..." : "Save Source"}
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
                          {sourceTestResult.spreadsheet_title || "Google Sheet reachable"}
                        </p>
                        <p className="mt-1">
                          Tabs: {(sourceTestResult.tabs || []).join(", ") || "No tabs found"}
                        </p>
                        <p className="mt-1">
                          Detected tabs: {(sourceTestResult.detected_tabs || []).join(", ") || "No transaction tabs detected"}
                        </p>
                        {(sourceTestResult.skipped_tabs || []).length > 0 && (
                          <p className="mt-1">
                            Skipped tabs: {sourceTestResult.skipped_tabs.join(", ")}
                          </p>
                        )}
                      </>
                    ) : (
                      <p>{sourceTestResult.message || "Connection test failed."}</p>
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
                      Saved Sources
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
                      Refresh
                    </button>
                  </div>

                  {isLoadingSources ? (
                    <div className="rounded-2xl border border-gray-200 bg-gray-50 px-4 py-4 text-sm text-muted dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)]">
                      Loading sources...
                    </div>
                  ) : googleSheetSources.length > 0 ? (
                    <ul className="space-y-3">
                      {googleSheetSources.map((source) => {
                        const syncResult = syncResults[source.source_id];
                        const sourceTitle = String(
                          source.spreadsheet_title || "Google Spreadsheet"
                        ).trim();
                        const sourceStatus = source.status === "disabled"
                          ? "Disabled"
                          : source.status === "error"
                            ? "Error"
                            : "Active";

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
                                  Spreadsheet-level sync - {sourceStatus}
                                </p>
                                <div className="mt-2 space-y-1 text-xs leading-5 text-muted">
                                  <p>Syncs all valid monthly tabs.</p>
                                  <p>Year is detected from Waktu Transaksi.</p>
                                  {source.sheet_name && (
                                    <p>Selected tab: {source.sheet_name}</p>
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
                                    || deletingSourceId === source.source_id
                                  }
                                  className="primary-button min-h-10 rounded-2xl px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                  {syncingSourceId === source.source_id ? (
                                    <LoaderCircle size={16} className="animate-spin" />
                                  ) : (
                                    <RefreshCw size={16} />
                                  )}
                                  {syncingSourceId === source.source_id ? "Syncing..." : "Sync Now"}
                                </button>

                                <button
                                  type="button"
                                  onClick={() => handleDeleteSource(source.source_id)}
                                  disabled={
                                    deletingSourceId === source.source_id
                                    || syncingSourceId === source.source_id
                                  }
                                  className="secondary-button min-h-10 rounded-2xl border-red-200 px-4 py-2 text-sm font-semibold text-red-600 hover:border-red-300 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-red-400/30 dark:text-red-300 dark:hover:bg-red-500/10"
                                >
                                  {deletingSourceId === source.source_id ? (
                                    <LoaderCircle size={16} className="animate-spin" />
                                  ) : (
                                    <Trash2 size={16} />
                                  )}
                                  {deletingSourceId === source.source_id ? "Deleting..." : "Delete"}
                                </button>
                              </div>
                            </div>

                            {syncResult && (
                              <>
                                <div className="mt-4 grid grid-cols-2 gap-2 text-xs sm:grid-cols-5">
                                  {[
                                    ["Total", syncResult.total_rows],
                                    ["Inserted", syncResult.inserted_rows],
                                    ["Updated", syncResult.updated_rows],
                                    ["Skipped", syncResult.skipped_rows],
                                    ["Failed", syncResult.failed_rows],
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

                                <div className="mt-3 space-y-1 text-xs leading-5 text-muted">
                                  {syncResult.classification && (
                                    <p className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 font-semibold text-emerald-800 dark:border-emerald-400/20 dark:bg-emerald-500/10 dark:text-emerald-200">
                                      {formatClassificationSummary(syncResult.classification)}
                                      {" "}
                                      Skipped manual: {syncResult.classification.skipped_manual || 0}.
                                      {" "}
                                      Errors: {syncResult.classification.errors || 0}.
                                    </p>
                                  )}
                                  {(syncResult.warnings || []).includes("classification_failed") && (
                                    <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 font-semibold text-amber-800 dark:border-amber-400/20 dark:bg-amber-500/10 dark:text-amber-200">
                                      Classification did not finish. You can run classification manually later.
                                    </p>
                                  )}
                                  {(syncResult.failed_rows || 0) > 0 && (
                                    <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 font-semibold text-amber-800 dark:border-amber-400/20 dark:bg-amber-500/10 dark:text-amber-200">
                                      Some rows were not imported. Review reasons below.
                                    </p>
                                  )}
                                  {(syncResult.processed_tabs || []).length > 0 && (
                                    <p>
                                      Processed tabs: {syncResult.processed_tabs.join(", ")}
                                    </p>
                                  )}
                                  {(syncResult.skipped_tabs || []).length > 0 && (
                                    <p>
                                      Skipped tabs: {syncResult.skipped_tabs.join(", ")}
                                    </p>
                                  )}
                                  {(syncResult.failed_tabs || []).length > 0 && (
                                    <p>
                                      Failed tabs: {syncResult.failed_tabs.join(", ")}
                                    </p>
                                  )}
                                </div>

                                {(hasReasonEntries(syncResult.failed_reasons)
                                  || hasReasonEntries(syncResult.skipped_reasons)
                                  || (syncResult.failed_samples || []).length > 0
                                  || (syncResult.skipped_samples || []).length > 0) && (
                                  <div className="mt-3 grid grid-cols-1 gap-2 text-xs leading-5 md:grid-cols-2">
                                    <SyncReasonBreakdown
                                      title="Failed reasons"
                                      reasons={syncResult.failed_reasons}
                                      tone="warning"
                                    />
                                    <SyncReasonBreakdown
                                      title="Skipped reasons"
                                      reasons={syncResult.skipped_reasons}
                                    />
                                    <SyncSamples
                                      title="Failed samples"
                                      samples={syncResult.failed_samples || []}
                                    />
                                    <SyncSamples
                                      title="Skipped samples"
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
                      No Google Sheet sources saved yet. Add a source above, then run Sync Now to populate the dashboard.
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

      <ConfigurationCard
        icon={SlidersHorizontal}
        title="Insight Severity Settings"
        description="Customize how the dashboard highlights Need, Want, Saving, Uncategorized, and anomaly severity for this workspace."
      >
        <div className="space-y-6">
          <div className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm leading-6 text-muted dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)]">
            <p>
              Severity is calculated by the backend based on these workspace-level thresholds.
            </p>
            <p className="mt-1 font-semibold text-main">
              {insightThresholds.source === "workspace"
                ? "Using workspace custom thresholds."
                : "Using default thresholds."}
            </p>
          </div>

          {isLoadingInsightThresholds ? (
            <div className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-4 text-sm text-muted dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)]">
              Loading insight severity settings...
            </div>
          ) : (
            <>
              <div>
                <h3 className="text-sm font-bold text-main">
                  Spending Ratio Thresholds
                </h3>
                <div className="mt-3 grid grid-cols-1 gap-3">
                  <ThresholdSlider
                    label="Need warning threshold"
                    helperText="Warning when Need spending reaches this percentage of total expense."
                    valuePercent={insightThresholds.need_warning_ratio}
                    onChangePercent={(value) => updateInsightField("need_warning_ratio", value)}
                    disabled={isSavingInsightThresholds}
                  />
                  <ThresholdSlider
                    label="Need danger threshold"
                    helperText="Danger when Need spending reaches this percentage of total expense."
                    valuePercent={insightThresholds.need_danger_ratio}
                    onChangePercent={(value) => updateInsightField("need_danger_ratio", value)}
                    disabled={isSavingInsightThresholds}
                  />
                  <ThresholdSlider
                    label="Want warning threshold"
                    helperText="Warning when Want spending reaches this percentage of total expense."
                    valuePercent={insightThresholds.want_warning_ratio}
                    onChangePercent={(value) => updateInsightField("want_warning_ratio", value)}
                    disabled={isSavingInsightThresholds}
                  />
                  <ThresholdSlider
                    label="Want danger threshold"
                    helperText="Danger when Want spending reaches this percentage of total expense."
                    valuePercent={insightThresholds.want_danger_ratio}
                    onChangePercent={(value) => updateInsightField("want_danger_ratio", value)}
                    disabled={isSavingInsightThresholds}
                  />
                </div>
              </div>

              <div className="border-t border-gray-200 pt-5 dark:border-[var(--color-border)]">
                <h3 className="text-sm font-bold text-main">
                  Saving Thresholds
                </h3>
                <div className="mt-3 grid grid-cols-1 gap-3">
                  <ThresholdSlider
                    label="Saving warning threshold"
                    helperText="Warning when Saving allocation is below this percentage of income."
                    valuePercent={insightThresholds.saving_warning_ratio}
                    onChangePercent={(value) => updateInsightField("saving_warning_ratio", value)}
                    disabled={isSavingInsightThresholds}
                  />
                  <ThresholdSlider
                    label="Saving good threshold"
                    helperText="Positive when Saving allocation reaches this percentage of income."
                    valuePercent={insightThresholds.saving_good_ratio}
                    onChangePercent={(value) => updateInsightField("saving_good_ratio", value)}
                    disabled={isSavingInsightThresholds}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 gap-5 border-t border-gray-200 pt-5 dark:border-[var(--color-border)] md:grid-cols-2">
                <div>
                  <h3 className="text-sm font-bold text-main">
                    Data Quality Thresholds
                  </h3>
                  <div className="mt-3 grid grid-cols-1 gap-3">
                    {[
                      [
                        "uncategorized_warning_count",
                        "Uncategorized warning count",
                        "Warning when uncategorized transaction count reaches this number.",
                      ],
                      [
                        "uncategorized_danger_count",
                        "Uncategorized danger count",
                        "Danger when uncategorized transaction count reaches this number.",
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
                          disabled={isSavingInsightThresholds}
                          className="form-control mt-3 w-full rounded-xl px-3 py-2 text-sm"
                        />
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-bold text-main">
                    Anomaly Thresholds
                  </h3>
                  <div className="mt-3 grid grid-cols-1 gap-3">
                    {[
                      [
                        "anomaly_warning_multiplier",
                        "Anomaly warning multiplier",
                        "Warning when a transaction is this many times above its category average.",
                      ],
                      [
                        "anomaly_danger_multiplier",
                        "Anomaly danger multiplier",
                        "Danger when a transaction is this many times above its category average.",
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
                          disabled={isSavingInsightThresholds}
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
                  onClick={handleResetInsightThresholds}
                  disabled={isSavingInsightThresholds}
                  className="secondary-button min-h-11 rounded-2xl px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Reset to Defaults
                </button>
                <button
                  type="button"
                  onClick={handleSaveInsightThresholds}
                  disabled={
                    isSavingInsightThresholds
                    || Boolean(insightValidationError)
                  }
                  className="primary-button min-h-11 rounded-2xl px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isSavingInsightThresholds && (
                    <LoaderCircle size={16} className="animate-spin" />
                  )}
                  {isSavingInsightThresholds ? "Saving..." : "Save Settings"}
                </button>
              </div>
            </>
          )}
        </div>
      </ConfigurationCard>

      <ConfigurationCard
        icon={MailPlus}
        title="Workspace Members"
        description="Manage team access and invite new members to this financial workspace."
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
                {isInvitingMember ? "Inviting..." : "Invite Member"}
              </button>
            </div>
          </form>
        )}

          <div className={`${canInviteMembers ? "mt-6" : ""} rounded-xl border border-gray-100 bg-gray-50 p-4 dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)]`}>
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

        {canInviteMembers && (
          <div className="mt-6 rounded-xl border border-gray-100 bg-gray-50 p-4 dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)]">
            <p className="mb-3 text-xs font-bold uppercase tracking-wide text-muted">
              Pending Invitations
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
                        {invitation.role} | Waiting for acceptance
                      </p>
                    </div>

                    <div className="flex shrink-0 items-center gap-2">
                      <span className="rounded-full bg-amber-100 px-2 py-1 text-xs font-bold text-amber-800 dark:bg-amber-500/10 dark:text-amber-200">
                        pending
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
                          ? "Cancelling..."
                          : "Cancel Invite"}
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted">
                No pending invitations.
              </p>
            )}
          </div>
        )}
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
