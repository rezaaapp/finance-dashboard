import {
  BarChart3,
  BellRing,
  ChevronLeft,
  ChevronRight,
  Cloud,
  Database,
  LayoutDashboard,
  LogOut,
  Moon,
  Upload,
  RefreshCw,
  Settings,
  ShieldCheck,
  Sun,
  UserRound,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import EmptyState from "../components/EmptyState";
import SummaryCard from "../components/SummaryCard";
import FinancialInsights from "../components/FinancialInsights";
import MonthlyChart from "../components/charts/MonthlyChart";
import PieCategoryChart from "../components/charts/PieCategoryChart";
import FinancialTypeChart from "../components/charts/FinancialTypeChart";
import MonthlyFinancialTypeTrend from "../components/charts/MonthlyFinancialTypeTrend";
import GroceryVsFoodChart from "../components/charts/GroceryVsFoodChart";
import CategoryHeatmap from "../components/charts/CategoryHeatmap";
import CategoryTrendChart from "../components/charts/CategoryTrendChart";
import PersonalAnalytics from "../components/analytics/PersonalAnalytics";
import IncomeVelocityDashboard from "../components/analytics/IncomeVelocityDashboard";
import SourceDanaAnalytics from "../components/analytics/SourceDanaAnalytics";
import MonthlyAllocationTrend from "../components/analytics/MonthlyAllocationTrend";
import SidebarDataSourceIndicator from "../components/SidebarDataSourceIndicator";
import WorkspaceInvitationNotification from "../components/WorkspaceInvitationNotification";
import WorkspaceSwitcher from "../components/WorkspaceSwitcher";
import TopSpendingTable from "../components/tables/TopSpendingTable";
import AnomalyTable from "../components/tables/AnomalyTable";
import AdminUsers from "./AdminUsers";
import BudgetingAlerts from "./BudgetingAlerts";
import Configuration from "./Configuration";
import ImportTransactions from "./ImportTransactions";
import { PRIVACY_MODES } from "../utils/privacy";

import {
  getSummary,
  refreshDashboardData,
  getMonthlySpending,
  getMonthlySaving,
  getMonthlyIncome,
  getTopSpending,
  getSpendingByCategory,
  getFinancialTypes,
  getMonthlyFinancialTypes,
  getRuleBasedInsights,
  getGroceryVsFood,
  getCategoryHeatmap,
  getTransactions,
  getCategoryTrends,
  getSourceDanaAnalytics,
  getMonthlyAllocation,
  getPersonalAnalytics,
  getAnomalies,
  getAvailableYears,
  getBudgetForecast,
  getWorkspaceConfiguration,
} from "../api/dashboardApi";
import { getGoogleOAuthConnectionStatus } from "../api/googleOAuthApi";
import { getGoogleSheetSources } from "../api/googleSheetSourcesApi";
import { getWorkspaces } from "../api/workspacesApi";
import {
  acceptWorkspaceInvitation,
  declineWorkspaceInvitation,
  getPendingWorkspaceInvitations,
} from "../api/workspaceInvitationsApi";
import {
  clearActiveWorkspaceId,
  getActiveWorkspaceId,
  setActiveWorkspaceId,
} from "../api/workspaceContext";

const premiumRoles = new Set(["super_admin", "owner", "member"]);

const hasPositiveTotal = (rows = [], keys = ["total"]) => (
  rows.some((row) => keys.some((key) => Number(row?.[key] || 0) > 0))
);

const hasFinancialTypeData = (rows = []) => (
  rows.some((row) => Number(row?.amount || 0) > 0)
);

const hasMonthlyFinancialTypeData = (rows = []) => (
  rows.some((row) => (
    ["need", "want", "saving", "income", "uncategorized"].some((key) => (
      Number(row?.[key] || 0) > 0
    ))
  ))
);

const hasSummaryData = (summary = {}) => (
  Number(summary.total_pengeluaran || summary.total_expenses || 0) > 0
  || Number(summary.total_saving || 0) > 0
  || Number(summary.total_income || 0) > 0
  || Number(summary.transaction_count || 0) > 0
);

const LockedFeature = ({ title, message }) => (
  <div className="panel rounded-lg p-6 shadow-lg">
    <div className="mx-auto flex max-w-2xl flex-col items-center py-10 text-center">
      <div className="icon-badge rounded-xl p-4">
        <ShieldCheck size={28} />
      </div>

      <h2 className="mt-5 text-2xl font-bold text-main">
        {title}
      </h2>

      <p className="mt-3 text-sm leading-7 text-muted sm:text-base">
        {message}
      </p>
    </div>
  </div>
);

const ProfileWidget = ({ auth, onLogout }) => {
  const hasSessionEmail = Boolean(auth?.email);
  const displayName = hasSessionEmail
    ? auth?.username || auth?.name || "Reza Putra Pratama"
    : "Reza Putra Pratama";
  const displayEmail = auth?.email || "rezaaapp@gmail.com";
  const initial = (displayName || displayEmail || "R").trim().charAt(0).toUpperCase();

  return (
    <div className="group relative inline-flex">
      <button
        type="button"
        className="flex h-10 w-10 items-center justify-center rounded-full border border-gray-200 bg-gray-50 text-sm font-bold text-gray-800 shadow-sm transition-colors hover:border-amber-300 hover:bg-white dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:hover:border-amber-700"
        aria-label={`Profile menu ${displayName}`}
        title={`${displayName} (${displayEmail})`}
      >
        {initial || <UserRound size={18} />}
      </button>

      <div className="invisible absolute right-0 top-full z-50 mt-2 w-40 translate-y-1 opacity-0 transition-all group-hover:visible group-hover:translate-y-0 group-hover:opacity-100">
        <button
          type="button"
          onClick={onLogout}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm font-semibold text-red-600 shadow-lg transition-colors hover:bg-red-50 dark:border-gray-600 dark:bg-gray-700 dark:text-red-300 dark:hover:bg-red-950/30"
        >
          <LogOut size={16} />
          Logout
        </button>
      </div>
    </div>
  );
};

const Dashboard = ({
  auth,
  onExitImpersonation,
  onImpersonate,
  onLogout,
}) => {
  // =========================
  // STATE
  // =========================
  const [summary, setSummary] = useState({});
  const [spending, setSpending] = useState([]);
  const [saving, setSaving] = useState([]);
  const [income, setIncome] = useState([]);
  const [topSpending, setTopSpending] = useState([]);
  const [categoryData, setCategoryData] = useState([]);
  const [financialTypes, setFinancialTypes] = useState([]);
  const [monthlyFinancialTypes, setMonthlyFinancialTypes] = useState([]);
  const [ruleBasedInsights, setRuleBasedInsights] = useState({});
  const [financialInsightsLoading, setFinancialInsightsLoading] = useState(false);
  const [financialInsightsError, setFinancialInsightsError] = useState("");
  const [groceryVsFood, setGroceryVsFood] = useState([]);
  const [categoryHeatmap, setCategoryHeatmap] = useState({});
  const [rawTransactions, setRawTransactions] = useState([]);
  const [categoryTrends, setCategoryTrends] = useState({});
  const [sourceDanaAnalytics, setSourceDanaAnalytics] = useState({});
  const [monthlyAllocation, setMonthlyAllocation] = useState([]);
  const [personalAnalytics, setPersonalAnalytics] = useState({});
  const [budgetForecast, setBudgetForecast] = useState({});
  const [anomalies, setAnomalies] = useState([]);
  const [currentSheetName, setCurrentSheetName] = useState("");
  const [hasActiveGoogleSheet, setHasActiveGoogleSheet] = useState(false);
  const [googleConnection, setGoogleConnection] = useState({ connected: false });
  const [googleSheetSources, setGoogleSheetSources] = useState([]);
  const [workspaces, setWorkspaces] = useState([]);
  const [activeWorkspaceId, setActiveWorkspaceIdState] = useState(() => (
    getActiveWorkspaceId()
  ));
  const [workspaceReady, setWorkspaceReady] = useState(false);
  const [pendingInvitations, setPendingInvitations] = useState([]);
  const [invitationActionId, setInvitationActionId] = useState("");
  const [invitationError, setInvitationError] = useState("");

  const [years, setYears] = useState([]);
  const [selectedYear, setSelectedYear] = useState("");
  const [selectedMonth, setSelectedMonth] = useState("");
  const [activeView, setActiveView] = useState(() => (
    window.location.pathname.startsWith("/import")
      ? "import"
      : window.location.pathname.startsWith("/settings")
      ? "configuration"
      : "dashboard"
  ));
  const [activeAnalyticsSubTab, setActiveAnalyticsSubTab] = useState("overview");
  const [selectedAnalyticsUser, setSelectedAnalyticsUser] = useState("all");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [autoBudget, setAutoBudget] = useState(() => (
    localStorage.getItem("finance-dashboard-auto-budget") !== "false"
  ));
  const [paydayStartDay, setPaydayStartDay] = useState(() => {
    const savedDay = Number(localStorage.getItem("finance-dashboard-payday-start-day"));

    return Number.isInteger(savedDay) && savedDay >= 1 && savedDay <= 31
      ? savedDay
      : 1;
  });
  const [privacyMode, setPrivacyMode] = useState(() => (
    localStorage.getItem("finance-dashboard-privacy-mode")
    || PRIVACY_MODES.normal
  ));

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [theme, setTheme] = useState(() => {
    const savedTheme = localStorage.getItem("finance-dashboard-theme");

    if (savedTheme === "light" || savedTheme === "dark") {
      return savedTheme;
    }

    return "light";
  });

  const isDarkMode = theme === "dark";
  const isSuperAdmin = auth?.role === "super_admin";
  const hasPremiumAccess = premiumRoles.has(auth?.role);
  const isTestMode = auth?.provider === "impersonation";

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("finance-dashboard-theme", theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem("finance-dashboard-privacy-mode", privacyMode);
  }, [privacyMode]);

  useEffect(() => {
    localStorage.setItem("finance-dashboard-auto-budget", String(autoBudget));
  }, [autoBudget]);

  useEffect(() => {
    localStorage.setItem(
      "finance-dashboard-payday-start-day",
      String(paydayStartDay)
    );
  }, [paydayStartDay]);

  const loadWorkspaceOptions = useCallback(async (preferredWorkspaceId = "") => {
    try {
      const response = await getWorkspaces();
      const nextWorkspaces = response?.workspaces || [];
      const storedWorkspaceId = getActiveWorkspaceId();
      const preferredWorkspace = nextWorkspaces.find((workspace) => (
        workspace.id === preferredWorkspaceId
      ));
      const storedWorkspace = nextWorkspaces.find((workspace) => (
        workspace.id === storedWorkspaceId
      ));
      const nextActiveWorkspaceId = preferredWorkspace?.id
        || storedWorkspace?.id
        || nextWorkspaces[0]?.id
        || "";

      setWorkspaces(nextWorkspaces);
      setActiveWorkspaceIdState(nextActiveWorkspaceId);

      if (nextActiveWorkspaceId && nextActiveWorkspaceId !== storedWorkspaceId) {
        setActiveWorkspaceId(nextActiveWorkspaceId);
      } else if (!nextActiveWorkspaceId && storedWorkspaceId) {
        clearActiveWorkspaceId();
      }

      return nextActiveWorkspaceId;
    } catch (err) {
      console.error("Failed to load workspaces.");

      if (err?.response?.status === 401) {
        onLogout();
        return "";
      }

      setWorkspaces([]);
      setActiveWorkspaceIdState("");
      return "";
    } finally {
      setWorkspaceReady(true);
    }
  }, [onLogout]);

  const loadPendingInvitations = useCallback(async () => {
    try {
      setInvitationError("");
      const response = await getPendingWorkspaceInvitations();

      setPendingInvitations(response?.invitations || []);
    } catch (err) {
      console.error("Failed to load workspace invitations.");

      if (err?.response?.status === 401) {
        onLogout();
        return;
      }

      setInvitationError("Workspace invitations are not available.");
    }
  }, [onLogout]);

  useEffect(() => {
    let isMounted = true;

    const loadWorkspaceState = async () => {
      await loadWorkspaceOptions();

      if (isMounted) {
        await loadPendingInvitations();
      }
    };

    loadWorkspaceState();

    return () => {
      isMounted = false;
    };
  }, [loadPendingInvitations, loadWorkspaceOptions]);

  const toggleTheme = () => {
    setTheme((currentTheme) => (
      currentTheme === "dark" ? "light" : "dark"
    ));
  };

  const handleWorkspaceChange = (workspaceId) => {
    setActiveWorkspaceId(workspaceId);
    setActiveWorkspaceIdState(workspaceId);
    clearDashboardData();
  };

  const clearDashboardData = () => {
    setSummary({});
    setSpending([]);
    setSaving([]);
    setIncome([]);
    setTopSpending([]);
    setCategoryData([]);
    setFinancialTypes([]);
    setMonthlyFinancialTypes([]);
    setRuleBasedInsights({});
    setFinancialInsightsLoading(false);
    setFinancialInsightsError("");
    setGroceryVsFood([]);
    setCategoryHeatmap({});
    setRawTransactions([]);
    setCategoryTrends({});
    setSourceDanaAnalytics({});
    setMonthlyAllocation([]);
    setPersonalAnalytics({});
    setBudgetForecast({});
    setAnomalies([]);
    setCurrentSheetName("");
    setHasActiveGoogleSheet(false);
    setGoogleConnection({ connected: false });
    setGoogleSheetSources([]);
    setYears([]);
    setSelectedYear("");
    setSelectedMonth("");
  };

  const handleAcceptInvitation = async (invitationId) => {
    try {
      setInvitationActionId(invitationId);
      setInvitationError("");

      const response = await acceptWorkspaceInvitation(invitationId);
      const acceptedWorkspaceId = response?.workspace?.id || "";

      setPendingInvitations((currentInvitations) => (
        currentInvitations.filter((invitation) => invitation.id !== invitationId)
      ));

      await loadWorkspaceOptions(acceptedWorkspaceId);

      if (acceptedWorkspaceId) {
        setActiveWorkspaceId(acceptedWorkspaceId);
        setActiveWorkspaceIdState(acceptedWorkspaceId);
        clearDashboardData();
      }
    } catch (err) {
      console.error("Failed to accept workspace invitation.");

      if (err?.response?.status === 401) {
        onLogout();
        return;
      }

      setInvitationError(
        err?.response?.data?.detail || "Invitation could not be accepted."
      );
    } finally {
      setInvitationActionId("");
    }
  };

  const handleDeclineInvitation = async (invitationId) => {
    try {
      setInvitationActionId(invitationId);
      setInvitationError("");

      await declineWorkspaceInvitation(invitationId);

      setPendingInvitations((currentInvitations) => (
        currentInvitations.filter((invitation) => invitation.id !== invitationId)
      ));
    } catch (err) {
      console.error("Failed to decline workspace invitation.");

      if (err?.response?.status === 401) {
        onLogout();
        return;
      }

      setInvitationError(
        err?.response?.data?.detail || "Invitation could not be declined."
      );
    } finally {
      setInvitationActionId("");
    }
  };

  const handleSaveConfiguration = ({
    autoBudget: nextAutoBudget,
    paydayStartDay: nextPaydayStartDay,
    privacyMode: nextPrivacyMode,
    googleSheetId,
  }) => {
    setAutoBudget(nextAutoBudget);
    setPaydayStartDay(nextPaydayStartDay);
    setPrivacyMode(nextPrivacyMode);

    if (googleSheetId === "") {
      clearDashboardData();
      return;
    }

    if (googleSheetId) {
      setHasActiveGoogleSheet(true);
      loadInitialData();
    }
  };

  const handleRefreshData = async () => {
    try {
      setLoading(true);
      await refreshDashboardData(selectedYear);
      await fetchDashboardData(selectedYear, selectedMonth);
    } catch (err) {
      console.error("Failed to refresh dashboard data.");

      if (err?.response?.status === 401) {
        onLogout();
        return;
      }

      setError("Failed to refresh dashboard data.");
    } finally {
      setLoading(false);
    }
  };

  // =========================
  // FETCH ALL DASHBOARD DATA
  // =========================
  const fetchDashboardData = useCallback(async (
    year = "",
    month = ""
  ) => {
    try {
      setLoading(true);
      const analyticsUserName = selectedAnalyticsUser === "all"
        ? ""
        : selectedAnalyticsUser;

      const summaryData = await getSummary(
        year,
        month
      );
      const spendingData = await getMonthlySpending(year, month);
      const savingData = await getMonthlySaving(year, month);
      const incomeData = await getMonthlyIncome(year, month);
      const topSpendingData = await getTopSpending(year, month);
      const categoryDataRes = await getSpendingByCategory(year, month);
      setFinancialInsightsLoading(true);
      setFinancialInsightsError("");
      const [
        financialTypesResult,
        monthlyFinancialTypesResult,
        ruleBasedInsightsResult,
      ] = await Promise.allSettled([
        getFinancialTypes({ year, month }),
        getMonthlyFinancialTypes({ year }),
        getRuleBasedInsights({ year, month }),
      ]);

      if (financialTypesResult.status === "fulfilled") {
        setFinancialTypes(financialTypesResult.value);
      } else {
        setFinancialTypes([]);
      }

      if (monthlyFinancialTypesResult.status === "fulfilled") {
        setMonthlyFinancialTypes(monthlyFinancialTypesResult.value);
      } else {
        setMonthlyFinancialTypes([]);
      }

      if (ruleBasedInsightsResult.status === "fulfilled") {
        setRuleBasedInsights(ruleBasedInsightsResult.value);
        setFinancialInsightsError("");
      } else {
        setRuleBasedInsights({});
        setFinancialInsightsError("Failed to load rule-based insights.");
      }

      setFinancialInsightsLoading(false);
      const groceryVsFoodData = hasPremiumAccess
        ? await getGroceryVsFood(year, month, analyticsUserName)
        : [];
      const categoryHeatmapData = hasPremiumAccess
        ? await getCategoryHeatmap(year, month, analyticsUserName)
        : {};
      const transactionsData = hasPremiumAccess
        ? await getTransactions(year, month, analyticsUserName)
        : [];
      const categoryTrendsData = hasPremiumAccess
        ? await getCategoryTrends(year, month, analyticsUserName)
        : {};
      const personalAnalyticsData = hasPremiumAccess
        ? await getPersonalAnalytics(year, month)
        : {};
      const budgetForecastData = hasPremiumAccess
        ? await getBudgetForecast(year, month)
        : {};
      const anomaliesData = hasPremiumAccess
        ? await getAnomalies(year, month)
        : [];

      setSummary(summaryData);
      setCurrentSheetName(
        summaryData?.data_source?.name
        || (year ? `Google Sheet ${year}` : "")
      );
      setSpending(spendingData);
      setSaving(savingData);
      setIncome(incomeData);
      setTopSpending(topSpendingData);
      setCategoryData(categoryDataRes);
      setGroceryVsFood(groceryVsFoodData);
      setCategoryHeatmap(categoryHeatmapData);
      setRawTransactions(transactionsData);
      setCategoryTrends(categoryTrendsData);
      setPersonalAnalytics(personalAnalyticsData);
      setBudgetForecast(budgetForecastData);
      setAnomalies(anomaliesData);

      setError("");
    } catch (err) {
      console.error("Failed to fetch dashboard data.");

      if (err?.response?.status === 401) {
        onLogout();
        return;
      }

      setError("Failed to fetch dashboard data.");
    } finally {
      setFinancialInsightsLoading(false);
      setLoading(false);
    }
  }, [hasPremiumAccess, onLogout, selectedAnalyticsUser]);

  // =========================
  // INITIAL DATA
  // =========================
  const loadInitialData = useCallback(async () => {
    try {
      setLoading(true);

      const [
        workspaceConfiguration,
        dataSourcesResponse,
        googleConnectionResponse,
      ] = await Promise.all([
        getWorkspaceConfiguration(),
        getGoogleSheetSources(),
        getGoogleOAuthConnectionStatus(),
      ]);
      const googleSheetSources = workspaceConfiguration?.configuration?.google_sheet_sources || [];
      const googleSheetId = workspaceConfiguration?.configuration?.google_sheet_id;
      const syncedSources = dataSourcesResponse?.sources || [];
      const isGoogleConnected = Boolean(googleConnectionResponse?.connected);
      const hasGoogleSheet = (
        googleSheetSources.length > 0
        || syncedSources.length > 0
        || Boolean(googleSheetId)
      );

      setGoogleConnection(googleConnectionResponse || { connected: false });
      setGoogleSheetSources(syncedSources);
      setHasActiveGoogleSheet(hasGoogleSheet);

      const availableYearsPayload = await getAvailableYears();
      const availableYears = Array.isArray(availableYearsPayload)
        ? availableYearsPayload
        : availableYearsPayload?.years || [];

      setYears(availableYears);

      if (availableYears.length > 0) {
        setSelectedYear(availableYears[0]);
      } else {
        setSelectedYear("");
        setSelectedMonth("");
      }

      if (!isGoogleConnected && !hasGoogleSheet) {
        setSummary({});
        setSpending([]);
        setSaving([]);
        setIncome([]);
        setTopSpending([]);
        setCategoryData([]);
        setFinancialTypes([]);
        setMonthlyFinancialTypes([]);
        setRuleBasedInsights({});
        setGroceryVsFood([]);
        setCategoryHeatmap({});
        setRawTransactions([]);
        setCategoryTrends({});
        setSourceDanaAnalytics({});
        setMonthlyAllocation([]);
        setPersonalAnalytics({});
        setBudgetForecast({});
        setAnomalies([]);
        setCurrentSheetName("");
      }
    } catch (err) {
      console.error("Failed to load initial dashboard data.");

      if (err?.response?.status === 401) {
        onLogout();
        return;
      }

      setError("Failed to load available years.");
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  // =========================
  // LOAD AVAILABLE YEARS
  // =========================
  useEffect(() => {
    if (workspaceReady) {
      loadInitialData();
    }
  }, [activeWorkspaceId, loadInitialData, workspaceReady]);

  // =========================
  // FETCH DASHBOARD WHEN YEAR CHANGES
  // =========================
  useEffect(() => {
    if (activeView === "dashboard" && selectedYear !== "") {
      fetchDashboardData(
        selectedYear,
        selectedMonth
      );
    }
  }, [activeView, fetchDashboardData, selectedYear, selectedMonth]);

  // =========================
  // LAZY FETCH ANALYTICS DATA
  // =========================
  useEffect(() => {
    if (
      activeView !== "analytics"
      || selectedYear === ""
      || !hasPremiumAccess
    ) {
      return;
    }

    let isMounted = true;
    const analyticsUserName = selectedAnalyticsUser === "all"
      ? ""
      : selectedAnalyticsUser;

    const fetchAnalyticsData = async () => {
      try {
        const [
          personalAnalyticsData,
          sourceDanaAnalyticsData,
          monthlyAllocationData,
          groceryVsFoodData,
          categoryHeatmapData,
          transactionsData,
          categoryTrendsData,
          anomaliesData,
        ] = await Promise.all([
          getPersonalAnalytics(selectedYear, selectedMonth),
          getSourceDanaAnalytics(
            selectedYear,
            selectedMonth,
            analyticsUserName
          ),
          getMonthlyAllocation(
            selectedYear,
            selectedMonth,
            analyticsUserName
          ),
          getGroceryVsFood(selectedYear, selectedMonth, analyticsUserName),
          getCategoryHeatmap(selectedYear, selectedMonth, analyticsUserName),
          getTransactions(selectedYear, selectedMonth, analyticsUserName),
          getCategoryTrends(selectedYear, selectedMonth, analyticsUserName),
          getAnomalies(selectedYear, selectedMonth),
        ]);

        if (isMounted) {
          setPersonalAnalytics(personalAnalyticsData);
          setSourceDanaAnalytics(sourceDanaAnalyticsData);
          setMonthlyAllocation(monthlyAllocationData);
          setGroceryVsFood(groceryVsFoodData);
          setCategoryHeatmap(categoryHeatmapData);
          setRawTransactions(transactionsData);
          setCategoryTrends(categoryTrendsData);
          setAnomalies(anomaliesData);
        }
      } catch (err) {
        console.error("Failed to fetch analytics data.");

        if (err?.response?.status === 401) {
          onLogout();
          return;
        }

        if (isMounted) {
          setPersonalAnalytics({});
          setSourceDanaAnalytics({});
          setMonthlyAllocation([]);
          setGroceryVsFood([]);
          setCategoryHeatmap({});
          setRawTransactions([]);
          setCategoryTrends({});
          setAnomalies([]);
        }
      }
    };

    fetchAnalyticsData();

    return () => {
      isMounted = false;
    };
  }, [
    activeView,
    hasPremiumAccess,
    onLogout,
    selectedAnalyticsUser,
    selectedMonth,
    selectedYear,
  ]);

  // =========================
  // LOADING SCREEN
  // =========================
  if (loading) {
    return (
      <div className="dashboard-screen h-screen flex items-center justify-center text-2xl">
        Loading Dashboard...
      </div>
    );
  }

  // =========================
  // ERROR SCREEN
  // =========================
  if (error) {
    return (
      <div className="dashboard-screen h-screen flex items-center justify-center text-red-500 text-xl">
        {error}
      </div>
    );
  }

  const hasSavedSource = hasActiveGoogleSheet || googleSheetSources.length > 0;
  const hasSyncedSource = googleSheetSources.some((source) => source.last_synced_at)
    || years.length > 0;
  const onboardingState = !googleConnection.connected
    ? "google_not_connected"
    : !hasSavedSource
      ? "no_data_source"
      : !hasSyncedSource
        ? "data_source_not_synced"
        : "ready";
  const hasDashboardPeriodData = (
    hasSummaryData(summary)
    || hasPositiveTotal(spending)
    || hasPositiveTotal(saving)
    || hasPositiveTotal(income)
    || topSpending.length > 0
    || categoryData.length > 0
    || hasFinancialTypeData(financialTypes)
    || hasMonthlyFinancialTypeData(monthlyFinancialTypes)
  );
  const hasAnalyticsData = (
    hasDashboardPeriodData
    || rawTransactions.length > 0
    || Object.keys(personalAnalytics?.kpis || {}).length > 0
    || (personalAnalytics?.comparison || []).length > 0
  );

  const onboardingCopy = {
    google_not_connected: {
      title: "Connect Google Sheets to start syncing your financial data.",
      description: "Connect your Google account, then add a spreadsheet source from Configuration.",
      actionLabel: "Go to Configuration",
      icon: Cloud,
    },
    no_data_source: {
      title: "Add your spreadsheet source to import transactions.",
      description: "Paste your Google Sheet URL, test access, save the source, then run Sync Now.",
      actionLabel: "Add Google Sheet Source",
      icon: Database,
    },
    data_source_not_synced: {
      title: "Sync your Google Sheet to populate this dashboard.",
      description: "Your source is saved. Run Sync Now from Configuration to import valid transactions.",
      actionLabel: "Go to Configuration",
      secondaryLabel: "Refresh Dashboard",
      icon: RefreshCw,
    },
  };

  const renderOnboardingState = (state = onboardingState) => {
    const copy = onboardingCopy[state] || onboardingCopy.google_not_connected;

    return (
      <EmptyState
        title={copy.title}
        description={copy.description}
        actionLabel={copy.actionLabel}
        onAction={() => setActiveView("configuration")}
        secondaryLabel={copy.secondaryLabel}
        onSecondaryAction={handleRefreshData}
        icon={copy.icon}
      />
    );
  };

  // =========================
  // UI
  // =========================
  return (
    <div className="dashboard-screen min-h-screen flex">
      {/* SIDEBAR */}
      <aside
        className={`
          dashboard-sidebar
          hidden
          border-r
          min-h-screen
          flex-col
          ${isSidebarCollapsed ? "px-4 py-6" : "p-6"}
          transition-[width]
          duration-300
          lg:flex
          ${isSidebarCollapsed ? "w-24" : "w-64"}
        `}
      >
        <div className={`mb-10 flex gap-3 ${
          isSidebarCollapsed
            ? "justify-center"
            : "items-start justify-between"
        }`}>
          {!isSidebarCollapsed && (
            <h1 className="text-2xl font-bold text-white leading-tight">
              Menu
            </h1>
          )}

          <button
            type="button"
            onClick={() => setIsSidebarCollapsed((current) => !current)}
            className="theme-toggle h-10 w-10 shrink-0 rounded-xl p-0"
            aria-label={isSidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={isSidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isSidebarCollapsed
              ? <ChevronRight size={18} />
              : <ChevronLeft size={18} />
            }
          </button>
        </div>

        <nav className="space-y-4">
          <button
            type="button"
            onClick={() => setActiveView("dashboard")}
            className={`nav-link flex min-h-11 w-full items-center rounded-xl border border-transparent text-left transition-colors ${
              isSidebarCollapsed
                ? "justify-center px-0"
                : "justify-start gap-3 px-3 py-2"
            } ${
              activeView === "dashboard"
                ? "bg-[var(--color-accent-bg)] text-accent"
                : "bg-transparent"
            }`}
            aria-label="Dashboard"
            title="Dashboard"
          >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl">
              <LayoutDashboard size={18} />
            </span>
            {!isSidebarCollapsed && (
              <span className="min-w-0 flex-1 truncate font-semibold">
                Dashboard
              </span>
            )}
          </button>

          <button
            type="button"
            onClick={() => setActiveView("analytics")}
            className={`nav-link flex min-h-11 w-full items-center rounded-xl border border-transparent text-left transition-colors ${
              isSidebarCollapsed
                ? "justify-center px-0"
                : "justify-start gap-3 px-3 py-2"
            } ${
              activeView === "analytics"
                ? "bg-[var(--color-accent-bg)] text-accent"
                : "bg-transparent"
            }`}
            aria-label="Analytics"
            title="Analytics"
          >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl">
              <BarChart3 size={18} />
            </span>
            {!isSidebarCollapsed && (
              <span className="min-w-0 flex-1 truncate font-semibold">
                Analytics
              </span>
            )}
            {!isSidebarCollapsed && !hasPremiumAccess && (
              <span className="ml-auto rounded-full bg-[var(--color-alert-bg)] px-2 py-0.5 text-xs font-bold text-[var(--color-alert-text)]">
                Locked
              </span>
            )}
          </button>

          <button
            type="button"
            onClick={() => setActiveView("budgeting")}
            className={`nav-link flex min-h-11 w-full items-center rounded-xl border border-transparent text-left transition-colors ${
              isSidebarCollapsed
                ? "justify-center px-0"
                : "justify-start gap-3 px-3 py-2"
            } ${
              activeView === "budgeting"
                ? "bg-[var(--color-accent-bg)] text-accent"
                : "bg-transparent"
            }`}
            aria-label="Budgeting & Alerts"
            title="Budgeting & Alerts"
          >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl">
              <BellRing size={18} />
            </span>
            {!isSidebarCollapsed && (
              <span className="min-w-0 flex-1 truncate font-semibold">
                Budgeting & Alerts
              </span>
            )}
            {!isSidebarCollapsed && !hasPremiumAccess && (
              <span className="ml-auto rounded-full bg-[var(--color-alert-bg)] px-2 py-0.5 text-xs font-bold text-[var(--color-alert-text)]">
                Locked
              </span>
            )}
          </button>

          <button
            type="button"
            onClick={() => setActiveView("import")}
            className={`nav-link flex min-h-11 w-full items-center rounded-xl border border-transparent text-left transition-colors ${
              isSidebarCollapsed
                ? "justify-center px-0"
                : "justify-start gap-3 px-3 py-2"
            } ${
              activeView === "import"
                ? "bg-[var(--color-accent-bg)] text-accent"
                : "bg-transparent"
            }`}
            aria-label="Import Transaksi"
            title="Import Transaksi"
          >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl">
              <Upload size={18} />
            </span>
            {!isSidebarCollapsed && (
              <span className="min-w-0 flex-1 truncate font-semibold">
                Import Transaksi
              </span>
            )}
          </button>

          {isSidebarCollapsed ? (
            <div className="group relative">
              <button
                type="button"
                onClick={() => setActiveView("configuration")}
                className={`nav-link flex min-h-11 w-full items-center justify-center rounded-xl border border-transparent text-left transition-colors duration-200 ${
                  activeView === "configuration" || activeView === "admin"
                    ? "bg-[var(--color-accent-bg)] text-accent"
                    : "bg-transparent"
                }`}
                aria-label="Settings"
                title="Settings"
              >
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl">
                  <Settings size={18} />
                </span>
              </button>

              <div className="invisible absolute left-full top-0 z-50 ml-3 w-56 translate-x-1 rounded-xl border border-[var(--color-border)] bg-[var(--color-panel)] p-2 opacity-0 shadow-xl transition-all duration-200 group-hover:visible group-hover:translate-x-0 group-hover:opacity-100">
                <p className="px-3 py-2 text-sm font-bold text-main">
                  Settings
                </p>

                <p className="mt-3 mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.16em] text-subtle">
                  USER CONTROL
                </p>

                {isSuperAdmin && (
                  <button
                    type="button"
                    onClick={() => setActiveView("admin")}
                    className="w-full rounded-lg px-3 py-2 text-left text-sm text-soft transition-colors duration-200 hover:bg-[var(--color-panel-hover)] hover:text-accent"
                  >
                    User Management
                  </button>
                )}

                {(isSuperAdmin || auth?.role === "owner") && (
                  <button
                    type="button"
                    onClick={() => setActiveView("configuration")}
                    className="w-full rounded-lg px-3 py-2 text-left text-sm text-soft transition-colors duration-200 hover:bg-[var(--color-panel-hover)] hover:text-accent"
                  >
                    Invite Member
                  </button>
                )}

                <p className="mt-3 mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.16em] text-subtle">
                  INTEGRATIONS
                </p>

                <button
                  type="button"
                  onClick={() => setActiveView("configuration")}
                  className="w-full rounded-lg px-3 py-2 text-left text-sm text-soft transition-colors duration-200 hover:bg-[var(--color-panel-hover)] hover:text-accent"
                >
                  Google Sheets
                </button>

              </div>
            </div>
          ) : (
            <div className="group">
              <button
                type="button"
                onClick={() => setActiveView("configuration")}
                className={`nav-link flex min-h-11 w-full items-center rounded-xl border border-transparent py-2.5 px-4 text-left transition-colors duration-200 ${
                  activeView === "configuration" || activeView === "admin"
                    ? "bg-[var(--color-accent-bg)] text-accent"
                    : "bg-transparent"
                }`}
                aria-label="Settings"
                title="Settings"
              >
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl">
                    <Settings size={18} />
                  </span>
                <span className="min-w-0 flex-1 truncate font-semibold">
                  Settings
                </span>
                <ChevronRight
                  size={16}
                  className="shrink-0 transition-transform duration-200 group-hover:rotate-90"
                />
              </button>

              <div className={`overflow-hidden transition-all duration-300 ease-out ${
                activeView === "configuration" || activeView === "admin"
                  ? "max-h-80 opacity-100"
                  : "max-h-0 opacity-0 group-hover:max-h-80 group-hover:opacity-100"
              }`}>
                <p className="mt-5 mb-2 px-4 text-[10px] font-bold uppercase tracking-[0.16em] text-subtle">
                  USER CONTROL
                </p>

                <div className="space-y-1">
                  {isSuperAdmin && (
                    <button
                      type="button"
                      onClick={() => setActiveView("admin")}
                      className={`w-full rounded-lg pl-9 pr-4 py-2 text-left text-sm transition-colors duration-200 ${
                        activeView === "admin"
                          ? "bg-[var(--color-accent-bg)] text-accent"
                          : "text-[rgba(255,255,255,0.72)] hover:bg-[rgba(255,255,255,0.08)] hover:text-white"
                      }`}
                    >
                      User Management
                    </button>
                  )}

                  {(isSuperAdmin || auth?.role === "owner") && (
                    <button
                      type="button"
                      onClick={() => setActiveView("configuration")}
                      className="w-full rounded-lg pl-9 pr-4 py-2 text-left text-sm text-[rgba(255,255,255,0.72)] transition-colors duration-200 hover:bg-[rgba(255,255,255,0.08)] hover:text-white"
                    >
                      Invite Member
                    </button>
                  )}
                </div>

                <p className="mt-5 mb-2 px-4 text-[10px] font-bold uppercase tracking-[0.16em] text-subtle">
                  INTEGRATIONS
                </p>

                <button
                  type="button"
                  onClick={() => setActiveView("configuration")}
                  className={`w-full rounded-lg pl-9 pr-4 py-2 text-left text-sm transition-colors duration-200 ${
                  activeView === "configuration"
                    ? "bg-[var(--color-accent-bg)] text-accent"
                    : "text-[rgba(255,255,255,0.72)] hover:bg-[rgba(255,255,255,0.08)] hover:text-white"
                }`}
              >
                  Google Sheets
                </button>

              </div>
            </div>
          )}
        </nav>

        <SidebarDataSourceIndicator
          sheetName={currentSheetName}
          isCollapsed={isSidebarCollapsed}
        />
      </aside>

      {/* MAIN */}
      <main className="min-w-0 flex-1 px-4 pb-24 pt-5 sm:px-5 lg:p-6">
        {/* HEADER */}
        <div className="mb-8 flex flex-col gap-4 xl:mb-10 xl:flex-row xl:items-center xl:justify-between">
          <div className="min-w-0">
            <h1 className="text-2xl font-bold sm:text-4xl">
              [Belum ada namanya]
            </h1>

            <p className="text-muted mt-1 text-sm sm:text-base">
              Apa atuh ya namanya? 🥲
            </p>
          </div>

          <div className="grid w-full grid-cols-2 gap-3 sm:grid-cols-[minmax(180px,260px)_minmax(120px,140px)_minmax(150px,170px)_auto_auto_auto] sm:items-center xl:w-auto xl:grid-cols-[minmax(220px,280px)_minmax(120px,140px)_minmax(150px,170px)_auto_auto_auto_auto]">

          <WorkspaceSwitcher
            workspaces={workspaces}
            activeWorkspaceId={activeWorkspaceId}
            onChange={handleWorkspaceChange}
          />

          <WorkspaceInvitationNotification
            invitations={pendingInvitations}
            actionInvitationId={invitationActionId}
            error={invitationError}
            onAccept={handleAcceptInvitation}
            onDecline={handleDeclineInvitation}
          />

          {/* YEAR FILTER */}
          <select
            value={selectedYear}
            onChange={(e) => setSelectedYear(e.target.value)}
            className="form-control w-full rounded-xl px-3 py-2 text-sm sm:px-4 sm:text-base"
          >
            {years.length === 0 && (
              <option value="">
                No synced data
              </option>
            )}
            {years.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>

          {/* MONTH FILTER */}
          <select
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(e.target.value)}
            className="form-control w-full rounded-xl px-3 py-2 text-sm sm:px-4 sm:text-base"
          >
            <option value="">All Month</option>

            <option value="1">January</option>
            <option value="2">February</option>
            <option value="3">March</option>
            <option value="4">April</option>
            <option value="5">May</option>
            <option value="6">June</option>
            <option value="7">July</option>
            <option value="8">August</option>
            <option value="9">September</option>
            <option value="10">October</option>
            <option value="11">November</option>
            <option value="12">December</option>
          </select>

            <button
              type="button"
              onClick={toggleTheme}
              className="theme-toggle h-11 w-full rounded-lg px-3 py-2 font-semibold sm:w-auto sm:px-4"
              aria-label={`Switch to ${isDarkMode ? "light" : "dark"} mode`}
              title={`Switch to ${isDarkMode ? "light" : "dark"} mode`}
            >
              {isDarkMode ? <Sun size={18} /> : <Moon size={18} />}
              <span className="hidden sm:inline">{isDarkMode ? "Light" : "Dark"}</span>
            </button>

            {/* REFRESH BUTTON */}
            <button
              type="button"
              onClick={handleRefreshData}
              className="primary-button h-11 min-w-11 w-full rounded-lg px-4 py-2 font-semibold sm:w-11 sm:px-0"
              aria-label="Refresh data"
              title="Refresh data"
            >
              <RefreshCw size={18} />
            </button>

            <div className="col-span-2 flex justify-end sm:col-span-6 xl:col-span-1">
              <ProfileWidget auth={auth} onLogout={onLogout} />
            </div>
          </div>
        </div>

        {isTestMode && (
          <div className="mb-6 flex flex-col gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <p className="text-sm font-bold">
                Test User Mode
              </p>
              <p className="mt-1 truncate text-xs">
                Anda sedang melihat dashboard sebagai {auth?.username || auth?.email || "test user"}.
              </p>
            </div>

            <button
              type="button"
              onClick={onExitImpersonation}
              className="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-lg border border-amber-300 bg-white px-4 text-sm font-bold text-amber-900 transition-colors hover:bg-amber-100 dark:border-amber-800 dark:bg-gray-800 dark:text-amber-200 dark:hover:bg-amber-950/50"
            >
              <LogOut size={16} />
              Exit Test Mode
            </button>
          </div>
        )}

        {activeView === "dashboard" && onboardingState !== "ready" ? (
          renderOnboardingState()
        ) : activeView === "dashboard" ? (
          <>
            {!hasDashboardPeriodData && (
              <div className="mb-8">
                <EmptyState
                  title="No data available for this period."
                  description="Try another month or sync your Google Sheet after checking the required transaction columns."
                  actionLabel="Go to Configuration"
                  onAction={() => setActiveView("configuration")}
                  icon={Database}
                  compact
                />
              </div>
            )}

            {/* SUMMARY */}
            {hasDashboardPeriodData && (
              <div className="mb-8 grid grid-cols-1 items-stretch gap-4 md:grid-cols-2 xl:grid-cols-3 xl:gap-6">
                <SummaryCard
                  title="Total Expenses"
                  value={summary.total_pengeluaran}
                  trend={
                    summary.total_expenses_change_pct
                    ?? summary.trend_pengeluaran
                  }
                  trendDirection={summary.total_expenses_trend}
                  comparisonLabel={
                    summary.comparison?.total_expenses_label
                    || summary.comparison?.label
                  }
                  privacyMode={privacyMode}
                />

                <SummaryCard
                  title="Total Saving"
                  value={summary.total_saving}
                  trend={
                    summary.total_saving_change_pct
                    ?? summary.trend_saving
                  }
                  trendDirection={summary.total_saving_trend}
                  comparisonLabel={
                    summary.comparison?.total_saving_label
                    || summary.comparison?.label
                  }
                  privacyMode={privacyMode}
                />

                <SummaryCard
                  title="Total Income"
                  value={summary.total_income}
                  trend={
                    summary.total_income_change_pct
                    ?? summary.trend_income
                  }
                  trendDirection={summary.total_income_trend}
                  comparisonLabel={
                    summary.comparison?.total_income_label
                    || summary.comparison?.label
                  }
                  privacyMode={privacyMode}
                />
              </div>
            )}

            <div className="mb-8">
              <FinancialInsights
                data={ruleBasedInsights}
                loading={financialInsightsLoading}
                error={financialInsightsError}
                privacyMode={privacyMode}
              />
            </div>

            {/* CHARTS */}
            <div className="mb-8 grid grid-cols-1 gap-5 xl:grid-cols-2 xl:gap-6">
              <FinancialTypeChart
                data={financialTypes}
                theme={theme}
                privacyMode={privacyMode}
              />

              <MonthlyFinancialTypeTrend
                data={monthlyFinancialTypes}
                theme={theme}
                privacyMode={privacyMode}
              />

              <MonthlyChart
                title="Monthly Spending"
                data={spending}
                dataKey="total"
                theme={theme}
                privacyMode={privacyMode}
              />

              <MonthlyChart
                title="Monthly Saving"
                data={saving}
                dataKey="total"
                theme={theme}
                privacyMode={privacyMode}
              />

              <MonthlyChart
                title="Monthly Income"
                data={income}
                dataKey="total"
                theme={theme}
                privacyMode={privacyMode}
              />

              <PieCategoryChart
                data={categoryData}
                theme={theme}
                privacyMode={privacyMode}
              />
            </div>

            {/* TABLES */}
            <div className="mb-8 grid grid-cols-1 gap-5 xl:grid-cols-2 xl:gap-6">
              <TopSpendingTable
                data={topSpending}
                privacyMode={privacyMode}
              />

              {hasPremiumAccess ? (
                <AnomalyTable
                  data={anomalies}
                  privacyMode={privacyMode}
                />
              ) : (
                <LockedFeature
                  title="Decision Alert Terkunci"
                  message="Anomaly detection dan decision alert tersedia untuk Owner dan Member premium."
                />
              )}
            </div>

          </>
        ) : activeView === "analytics" && onboardingState !== "ready" ? (
          renderOnboardingState()
        ) : activeView === "analytics" && !hasPremiumAccess ? (
          <LockedFeature
            title="Advanced Analytics Terkunci"
            message="Role User Free Plan hanya mendapat grafik dan analisis dasar. Upgrade ke Owner atau Member premium untuk membuka advanced analytics."
          />
        ) : activeView === "analytics" ? (
          <div className="grid grid-cols-1 gap-6">
            {!hasAnalyticsData && (
              <EmptyState
                title="Analytics will appear after you sync transactions."
                description="Sync a Google Sheet with valid transactions, then choose a year or month to review personal finance trends."
                actionLabel="Go to Configuration"
                onAction={() => setActiveView("configuration")}
                icon={BarChart3}
                compact
              />
            )}

            {hasAnalyticsData && (
              <>
                <div className="panel rounded-2xl p-3 shadow-lg">
                  <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
                    <button
                      type="button"
                      onClick={() => setActiveAnalyticsSubTab("overview")}
                      className={`rounded-xl px-4 py-2 text-sm font-bold transition-colors ${
                        activeAnalyticsSubTab === "overview"
                          ? "bg-[var(--color-accent-strong)] text-white"
                          : "text-muted hover:bg-[var(--color-panel-hover)] hover:text-accent"
                      }`}
                    >
                      Overview
                    </button>

                    <button
                      type="button"
                      onClick={() => setActiveAnalyticsSubTab("velocity")}
                      className={`rounded-xl px-4 py-2 text-sm font-bold transition-colors ${
                        activeAnalyticsSubTab === "velocity"
                          ? "bg-[var(--color-accent-strong)] text-white"
                          : "text-muted hover:bg-[var(--color-panel-hover)] hover:text-accent"
                      }`}
                    >
                      Income Velocity
                    </button>
                  </div>
                </div>

                <PersonalAnalytics
                  data={personalAnalytics}
                  selectedUser={selectedAnalyticsUser}
                  onSelectedUserChange={setSelectedAnalyticsUser}
                  privacyMode={privacyMode}
                  variant="summary"
                />

                <div className="grid grid-cols-1 gap-6">
                  {activeAnalyticsSubTab === "overview" && (
                    <>
                      <PersonalAnalytics
                        data={personalAnalytics}
                        selectedUser={selectedAnalyticsUser}
                        onSelectedUserChange={setSelectedAnalyticsUser}
                        privacyMode={privacyMode}
                        variant="breakdown"
                      />

                      <SourceDanaAnalytics
                        data={sourceDanaAnalytics}
                        theme={theme}
                        privacyMode={privacyMode}
                      />

                      <MonthlyAllocationTrend
                        data={monthlyAllocation}
                        privacyMode={privacyMode}
                      />

                      <GroceryVsFoodChart
                        data={groceryVsFood}
                        theme={theme}
                        privacyMode={privacyMode}
                      />

                      <CategoryTrendChart
                        data={categoryTrends}
                        theme={theme}
                        privacyMode={privacyMode}
                      />

                      <CategoryHeatmap
                        data={categoryHeatmap}
                        rawTransactions={rawTransactions}
                        theme={theme}
                        privacyMode={privacyMode}
                      />
                    </>
                  )}

                  {activeAnalyticsSubTab === "velocity" && (
                    <IncomeVelocityDashboard
                      rawTransactions={rawTransactions}
                      privacyMode={privacyMode}
                    />
                  )}
                </div>
              </>
            )}
          </div>
        ) : activeView === "budgeting" && !hasPremiumAccess ? (
          <LockedFeature
            title="Decision Alert Terkunci"
            message="Budgeting alerts dan decision alert adalah fitur premium untuk Owner dan Member. User Free Plan tetap bisa melihat dashboard dasar."
          />
        ) : activeView === "budgeting" ? (
          <BudgetingAlerts
            data={budgetForecast}
            theme={theme}
            privacyMode={privacyMode}
            autoBudget={autoBudget}
          />
        ) : activeView === "admin" && isSuperAdmin ? (
          <AdminUsers
            onImpersonate={onImpersonate}
            onUnauthorized={onLogout}
          />
        ) : activeView === "import" ? (
          <ImportTransactions />
        ) : (
          <Configuration
            key={activeWorkspaceId || "default-workspace"}
            autoBudget={autoBudget}
            paydayStartDay={paydayStartDay}
            selectedYear={selectedYear}
            currentSheetName={currentSheetName}
            privacyMode={privacyMode}
            userRole={auth?.role}
            onSaveChanges={handleSaveConfiguration}
            onUnauthorized={onLogout}
          />
        )}
      </main>

      <nav className={`fixed inset-x-0 bottom-0 z-50 grid gap-1 border-t border-[var(--color-border)] bg-[var(--color-panel)] px-2 py-2 shadow-none lg:hidden ${
        isSuperAdmin ? "grid-cols-6" : "grid-cols-5"
      }`}>
        <button
          type="button"
          onClick={() => setActiveView("dashboard")}
          className={`flex min-h-14 flex-col items-center justify-center gap-1 rounded-xl text-xs font-semibold ${
            activeView === "dashboard"
              ? "bg-[var(--color-accent-bg)] text-accent"
              : "text-muted"
          }`}
        >
          <LayoutDashboard size={18} />
          Dashboard
        </button>

        <button
          type="button"
          onClick={() => setActiveView("analytics")}
          className={`flex min-h-14 flex-col items-center justify-center gap-1 rounded-xl text-xs font-semibold ${
            activeView === "analytics"
              ? "bg-[var(--color-accent-bg)] text-accent"
              : "text-muted"
          }`}
        >
          <BarChart3 size={18} />
          Analytics
          {!hasPremiumAccess && (
            <span className="text-[9px] font-bold text-[var(--color-alert-text)]">
              Locked
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setActiveView("budgeting")}
          className={`flex min-h-14 flex-col items-center justify-center gap-1 rounded-xl text-xs font-semibold ${
            activeView === "budgeting"
              ? "bg-[var(--color-accent-bg)] text-accent"
              : "text-muted"
          }`}
        >
          <BellRing size={18} />
          Budgeting
          {!hasPremiumAccess && (
            <span className="text-[9px] font-bold text-[var(--color-alert-text)]">
              Locked
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setActiveView("import")}
          className={`flex min-h-14 flex-col items-center justify-center gap-1 rounded-xl text-[11px] font-semibold sm:text-xs ${
            activeView === "import"
              ? "bg-[var(--color-accent-bg)] text-accent"
              : "text-muted"
          }`}
        >
          <Upload size={18} />
          Import
        </button>

        <button
          type="button"
          onClick={() => setActiveView("configuration")}
          className={`flex min-h-14 flex-col items-center justify-center gap-1 rounded-xl text-[11px] font-semibold sm:text-xs ${
            activeView === "configuration"
              ? "bg-[var(--color-accent-bg)] text-accent"
              : "text-muted"
          }`}
        >
          <Settings size={18} />
          Settings
        </button>

        {isSuperAdmin && (
          <button
            type="button"
            onClick={() => setActiveView("admin")}
            className={`flex min-h-14 flex-col items-center justify-center gap-1 rounded-xl text-xs font-semibold ${
              activeView === "admin"
                ? "bg-[var(--color-accent-bg)] text-accent"
                : "text-muted"
            }`}
          >
            <ShieldCheck size={18} />
            Admin
          </button>
        )}
      </nav>
    </div>
  );
};

export default Dashboard;
