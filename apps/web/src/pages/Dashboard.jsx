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
  Search as SearchIcon,
  Settings,
  ShieldCheck,
  Sun,
  UserRound,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import EmptyState from "../components/EmptyState";
import AppShell from "../components/AppShell";
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
import EnvironmentBadge from "../components/environment/EnvironmentBadge";
import TopSpendingTable from "../components/tables/TopSpendingTable";
import AnomalyTable from "../components/tables/AnomalyTable";
import AdminUsers from "./AdminUsers";
import BudgetingAlerts from "./BudgetingAlerts";
import Configuration from "./Configuration";
import ImportTransactions from "./ImportTransactions";
import SearchPage from "./Search";
import { PRIVACY_MODES } from "../utils/privacy";

import {
  getDashboardViewModel,
  refreshDashboardData,
  getGroceryVsFood,
  getCategoryHeatmap,
  getTransactions,
  getCategoryTrends,
  getSourceDanaAnalytics,
  getMonthlyAllocation,
  getPersonalAnalytics,
  getAnomalies,
  getBudgetForecast,
} from "../api/dashboardApi";
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

const getInitialView = () => {
  if (window.location.pathname.startsWith("/import")) {
    return "import";
  }

  if (window.location.pathname.startsWith("/search")) {
    return "search";
  }

  if (window.location.pathname.startsWith("/settings")) {
    return "configuration";
  }

  return "dashboard";
};

const PRIMARY_NAVIGATION_ITEMS = [
  {
    id: "dashboard",
    label: "Dashboard",
    title: "Dashboard",
    description: "Ringkasan kondisi keuanganmu dalam satu tempat.",
    icon: LayoutDashboard,
  },
  {
    id: "analytics",
    label: "Analytics",
    title: "Analytics",
    description: "Pahami pola pemasukan, pengeluaran, dan kebiasaan finansial.",
    icon: BarChart3,
    requiresPremium: true,
  },
  {
    id: "budgeting",
    label: "Budget",
    title: "Budget",
    description: "Rencanakan batas pengeluaran dan pantau area yang perlu diperhatikan.",
    icon: BellRing,
    requiresPremium: true,
  },
  {
    id: "search",
    label: "Search",
    title: "Search",
    description: "Temukan transaksi dari merchant, kategori, catatan, atau sumber dana.",
    icon: SearchIcon,
  },
  {
    id: "import",
    label: "Import",
    title: "Import",
    description: "Masukkan dan tinjau data transaksi sebelum digunakan di Omon.",
    icon: Upload,
  },
  {
    id: "configuration",
    label: "Settings",
    title: "Settings",
    description: "Kelola workspace, koneksi, dan preferensi penggunaan Omon.",
    icon: Settings,
    isActive: (activeView) => activeView === "configuration" || activeView === "admin",
  },
];

const ADMIN_PAGE_METADATA = {
  title: "User Management",
  description: "Kelola akses pengguna untuk kebutuhan operasional internal.",
};

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
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef(null);
  const hasSessionEmail = Boolean(auth?.email);
  const displayName = hasSessionEmail
    ? auth?.username || auth?.name || "Reza Putra Pratama"
    : "Reza Putra Pratama";
  const displayEmail = auth?.email || "rezaaapp@gmail.com";
  const initial = (displayName || displayEmail || "R").trim().charAt(0).toUpperCase();

  useEffect(() => {
    if (!isMenuOpen) {
      return undefined;
    }

    const handlePointerDown = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsMenuOpen(false);
      }
    };

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        setIsMenuOpen(false);
      }
    };

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isMenuOpen]);

  const handleLogout = () => {
    setIsMenuOpen(false);
    onLogout();
  };

  return (
    <div ref={menuRef} className="group relative inline-flex">
      <button
        type="button"
        onClick={() => setIsMenuOpen((current) => !current)}
        className="flex h-10 w-10 items-center justify-center rounded-full border border-gray-200 bg-gray-50 text-sm font-bold text-gray-800 shadow-sm transition-colors hover:border-amber-300 hover:bg-white dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:hover:border-amber-700"
        aria-label={`Profile menu ${displayName}`}
        aria-expanded={isMenuOpen}
        aria-haspopup="menu"
        title={`${displayName} (${displayEmail})`}
      >
        {initial || <UserRound size={18} />}
      </button>

      <div
        className={`absolute right-0 top-full z-50 mt-2 w-40 transition-all ${
          isMenuOpen
            ? "visible translate-y-0 opacity-100"
            : "invisible translate-y-1 opacity-0 group-hover:visible group-hover:translate-y-0 group-hover:opacity-100"
        }`}
        role="menu"
      >
        <button
          type="button"
          onClick={handleLogout}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm font-semibold text-red-600 shadow-lg transition-colors hover:bg-red-50 dark:border-gray-600 dark:bg-gray-700 dark:text-red-300 dark:hover:bg-red-950/30"
          role="menuitem"
        >
          <LogOut size={16} />
          Logout
        </button>
      </div>
    </div>
  );
};

const getNavigationItemActive = (item, activeView) => (
  item.isActive ? item.isActive(activeView) : activeView === item.id
);

const DesktopNavigation = ({
  activeView,
  auth,
  hasPremiumAccess,
  isSidebarCollapsed,
  isSuperAdmin,
  onNavigate,
}) => (
  <nav className="space-y-2" aria-label="Primary navigation">
    {PRIMARY_NAVIGATION_ITEMS.map((item) => {
      const Icon = item.icon;
      const isActive = getNavigationItemActive(item, activeView);
      const isLocked = item.requiresPremium && !hasPremiumAccess;

      if (item.id === "configuration") {
        return isSidebarCollapsed ? (
          <div key={item.id} className="group relative">
            <button
              type="button"
              onClick={() => onNavigate(item.id)}
              className={`nav-link flex min-h-11 w-full items-center justify-center rounded-lg border border-transparent text-left transition-colors duration-200 ${
                isActive
                  ? "is-active bg-[var(--color-accent-bg)] text-accent"
                  : "bg-transparent"
              }`}
              aria-current={isActive ? "page" : undefined}
              aria-label={item.label}
              title={item.label}
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg">
                <Icon size={18} />
              </span>
            </button>

            <div className="invisible absolute left-full top-0 z-50 ml-3 w-56 translate-x-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-panel)] p-2 opacity-0 shadow-xl transition-all duration-200 group-hover:visible group-hover:translate-x-0 group-hover:opacity-100">
              <p className="px-3 py-2 text-sm font-bold text-main">
                Settings
              </p>

              <p className="mt-3 mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.12em] text-subtle">
                Account
              </p>

              {isSuperAdmin && (
                <button
                  type="button"
                  onClick={() => onNavigate("admin")}
                  className="w-full rounded-lg px-3 py-2 text-left text-sm text-soft transition-colors duration-200 hover:bg-[var(--color-panel-hover)] hover:text-accent"
                  aria-current={activeView === "admin" ? "page" : undefined}
                >
                  User Management
                </button>
              )}

              {(isSuperAdmin || auth?.role === "owner") && (
                <button
                  type="button"
                  onClick={() => onNavigate("configuration")}
                  className="w-full rounded-lg px-3 py-2 text-left text-sm text-soft transition-colors duration-200 hover:bg-[var(--color-panel-hover)] hover:text-accent"
                >
                  Invite Member
                </button>
              )}

              <p className="mt-3 mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.12em] text-subtle">
                Connections
              </p>

              <button
                type="button"
                onClick={() => onNavigate("configuration")}
                className="w-full rounded-lg px-3 py-2 text-left text-sm text-soft transition-colors duration-200 hover:bg-[var(--color-panel-hover)] hover:text-accent"
              >
                Google Sheets
              </button>
            </div>
          </div>
        ) : (
          <div key={item.id} className="group">
            <button
              type="button"
              onClick={() => onNavigate(item.id)}
              className={`nav-link flex min-h-11 w-full items-center rounded-lg border border-transparent px-3 py-2 text-left transition-colors duration-200 ${
                isActive
                  ? "is-active bg-[var(--color-accent-bg)] text-accent"
                  : "bg-transparent"
              }`}
              aria-current={isActive ? "page" : undefined}
              aria-label={item.label}
              title={item.label}
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg">
                <Icon size={18} />
              </span>
              <span className="min-w-0 flex-1 truncate font-semibold">
                {item.label}
              </span>
              <ChevronRight
                size={16}
                className="shrink-0 transition-transform duration-200 group-hover:rotate-90"
              />
            </button>

            <div className={`overflow-hidden transition-all duration-300 ease-out ${
              isActive
                ? "max-h-80 opacity-100"
                : "max-h-0 opacity-0 group-hover:max-h-80 group-hover:opacity-100"
            }`}>
              <p className="mt-4 mb-2 px-4 text-[10px] font-bold uppercase tracking-[0.12em] text-subtle">
                Account
              </p>

              <div className="space-y-1">
                {isSuperAdmin && (
                  <button
                    type="button"
                    onClick={() => onNavigate("admin")}
                    className={`w-full rounded-lg py-2 pl-9 pr-4 text-left text-sm transition-colors duration-200 ${
                      activeView === "admin"
                        ? "bg-[var(--color-accent-bg)] text-accent"
                        : "text-[rgba(255,255,255,0.72)] hover:bg-[rgba(255,255,255,0.08)] hover:text-white"
                    }`}
                    aria-current={activeView === "admin" ? "page" : undefined}
                  >
                    User Management
                  </button>
                )}

                {(isSuperAdmin || auth?.role === "owner") && (
                  <button
                    type="button"
                    onClick={() => onNavigate("configuration")}
                    className="w-full rounded-lg py-2 pl-9 pr-4 text-left text-sm text-[rgba(255,255,255,0.72)] transition-colors duration-200 hover:bg-[rgba(255,255,255,0.08)] hover:text-white"
                  >
                    Invite Member
                  </button>
                )}
              </div>

              <p className="mt-4 mb-2 px-4 text-[10px] font-bold uppercase tracking-[0.12em] text-subtle">
                Connections
              </p>

              <button
                type="button"
                onClick={() => onNavigate("configuration")}
                className={`w-full rounded-lg py-2 pl-9 pr-4 text-left text-sm transition-colors duration-200 ${
                activeView === "configuration"
                  ? "bg-[var(--color-accent-bg)] text-accent"
                  : "text-[rgba(255,255,255,0.72)] hover:bg-[rgba(255,255,255,0.08)] hover:text-white"
              }`}
              >
                Google Sheets
              </button>
            </div>
          </div>
        );
      }

      return (
        <button
          key={item.id}
          type="button"
          onClick={() => onNavigate(item.id)}
          className={`nav-link flex min-h-11 w-full items-center rounded-lg border border-transparent text-left transition-colors ${
            isSidebarCollapsed
              ? "justify-center px-0"
              : "justify-start gap-3 px-3 py-2"
          } ${
            isActive
              ? "is-active bg-[var(--color-accent-bg)] text-accent"
              : "bg-transparent"
          }`}
          aria-current={isActive ? "page" : undefined}
          aria-label={item.label}
          title={item.label}
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg">
            <Icon size={18} />
          </span>
          {!isSidebarCollapsed && (
            <span className="min-w-0 flex-1 truncate font-semibold">
              {item.label}
            </span>
          )}
          {!isSidebarCollapsed && isLocked && (
            <span className="ml-auto rounded-full bg-[var(--color-alert-bg)] px-2 py-0.5 text-xs font-bold text-[var(--color-alert-text)]">
              Locked
            </span>
          )}
        </button>
      );
    })}
  </nav>
);

const MobileNavigation = ({
  activeView,
  hasPremiumAccess,
  onNavigate,
}) => (
  <nav
    className="app-shell__mobile-nav grid-cols-6"
    aria-label="Primary mobile navigation"
  >
    {PRIMARY_NAVIGATION_ITEMS.map((item) => {
      const Icon = item.icon;
      const isActive = getNavigationItemActive(item, activeView);
      const isLocked = item.requiresPremium && !hasPremiumAccess;

      return (
        <button
          key={item.id}
          type="button"
          onClick={() => onNavigate(item.id)}
          className={`app-shell__mobile-nav-item ${
            isActive
              ? "is-active bg-[var(--color-accent-bg)] text-accent"
              : "text-muted"
          }`}
          aria-current={isActive ? "page" : undefined}
          aria-label={item.label}
          title={item.label}
        >
          <Icon size={18} />
          <span>{item.label}</span>
          {isLocked && (
            <span className="text-[9px] font-bold text-[var(--color-alert-text)]">
              Locked
            </span>
          )}
        </button>
      );
    })}
  </nav>
);

const Dashboard = ({
  auth,
  onExitImpersonation,
  onImpersonate,
  onLogout,
  systemInfoState,
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
  const [activeView, commitActiveView] = useState(() => getInitialView());
  const [settingsDirty, setSettingsDirty] = useState(false);
  const [pendingSettingsNavigation, setPendingSettingsNavigation] = useState("");
  const setActiveView = (nextView) => {
    if (
      activeView === "configuration"
      && settingsDirty
      && nextView !== "configuration"
    ) {
      setPendingSettingsNavigation(nextView);
      return;
    }
    commitActiveView(nextView);
  };
  const finishSettingsNavigation = () => {
    if (pendingSettingsNavigation) commitActiveView(pendingSettingsNavigation);
    setPendingSettingsNavigation("");
    setSettingsDirty(false);
  };
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

      setError("Dashboard belum dapat diperbarui. Periksa koneksi, lalu coba lagi.");
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
      setFinancialInsightsLoading(true);
      setFinancialInsightsError("");

      const viewModel = await getDashboardViewModel(
        year,
        month,
        analyticsUserName
      );
      const dashboardData = viewModel?.dashboard || {};
      const summaryData = dashboardData.summary || {};

      setSummary(summaryData);
      setCurrentSheetName(
        viewModel?.current_sheet_name
        || summaryData?.data_source?.name
        || (year ? `Google Sheet ${year}` : "")
      );
      setSpending(dashboardData.monthly_spending || []);
      setSaving(dashboardData.monthly_saving || []);
      setIncome(dashboardData.monthly_income || []);
      setTopSpending(dashboardData.top_spending || []);
      setCategoryData(dashboardData.spending_by_category || []);
      setFinancialTypes(dashboardData.financial_types || []);
      setMonthlyFinancialTypes(dashboardData.monthly_financial_types || []);
      setRuleBasedInsights(dashboardData.rule_based_insights || {});
      setGroceryVsFood(dashboardData.grocery_vs_food || []);
      setCategoryHeatmap(dashboardData.category_heatmap || {});
      setRawTransactions(dashboardData.transactions || []);
      setCategoryTrends(dashboardData.category_trends || {});
      setPersonalAnalytics(dashboardData.personal_analytics || {});
      setBudgetForecast(dashboardData.budget_forecast || {});
      setAnomalies(dashboardData.anomalies || []);
      setFinancialInsightsError("");

      setError("");
    } catch (err) {
      console.error("Failed to fetch dashboard data.");

      if (err?.response?.status === 401) {
        onLogout();
        return;
      }

      setError("Data Dashboard belum dapat dimuat. Periksa koneksi, lalu coba lagi.");
    } finally {
      setFinancialInsightsLoading(false);
      setLoading(false);
    }
  }, [onLogout, selectedAnalyticsUser]);

  const refreshBudgetForecast = useCallback(async () => {
    if (!hasPremiumAccess || selectedYear === "" || selectedMonth === "") {
      setBudgetForecast({});
      return;
    }

    try {
      const budgetForecastData = await getBudgetForecast(
        selectedYear,
        selectedMonth
      );
      setBudgetForecast(budgetForecastData);
    } catch (err) {
      console.error("Failed to fetch budgeting data.");

      if (err?.response?.status === 401) {
        onLogout();
        return;
      }

      setBudgetForecast({});
    }
  }, [hasPremiumAccess, onLogout, selectedMonth, selectedYear]);

  // =========================
  // INITIAL DATA
  // =========================
  const loadInitialData = useCallback(async () => {
    try {
      setLoading(true);
      const viewModel = await getDashboardViewModel();
      const availableYears = viewModel?.available_years || [];
      const syncedSources = viewModel?.google_sheet_sources || [];
      const googleConnectionResponse = viewModel?.google_connection || { connected: false };
      const hasGoogleSheet = Boolean(viewModel?.has_active_google_sheet);

      setGoogleConnection(googleConnectionResponse);
      setGoogleSheetSources(syncedSources);
      setHasActiveGoogleSheet(hasGoogleSheet);
      setYears(availableYears);

      if (availableYears.length > 0) {
        setSelectedYear(viewModel?.selected_period?.year || availableYears[0]);
      } else {
        setSelectedYear("");
        setSelectedMonth("");
      }

      if (!googleConnectionResponse.connected && !hasGoogleSheet) {
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

      setError("Dashboard belum dapat disiapkan. Periksa koneksi, lalu coba lagi.");
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

  useEffect(() => {
    if (activeView === "budgeting") {
      refreshBudgetForecast();
    }
  }, [activeView, refreshBudgetForecast]);

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
      <div className="dashboard-screen flex min-h-screen items-center justify-center p-6" role="status" aria-live="polite">
        <div className="panel w-full max-w-md rounded-2xl p-8 text-center shadow-lg">
          <RefreshCw size={28} className="mx-auto animate-spin text-accent" />
          <h1 className="mt-4 text-2xl font-bold text-main">Belum ada namanya</h1>
          <p className="mt-2 text-sm text-muted">Omon sedang menyiapkan Dashboard kamu...</p>
        </div>
      </div>
    );
  }

  // =========================
  // ERROR SCREEN
  // =========================
  if (error) {
    return (
      <div className="dashboard-screen flex min-h-screen items-center justify-center p-6" role="alert">
        <div className="panel w-full max-w-lg rounded-2xl p-8 text-center shadow-lg">
          <h1 className="text-2xl font-bold text-main">Dashboard belum dapat dibuka</h1>
          <p className="mt-3 text-sm leading-6 text-muted">{error}</p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
            <button type="button" onClick={() => { setError(""); loadInitialData(); }} className="primary-button rounded-xl px-5 py-2.5 font-bold">Coba Lagi</button>
            <button type="button" onClick={() => { setError(""); commitActiveView("configuration"); }} className="secondary-button rounded-xl px-5 py-2.5 font-bold">Buka Settings</button>
            <button type="button" onClick={onLogout} className="secondary-button rounded-xl px-5 py-2.5 font-bold">Logout</button>
          </div>
        </div>
      </div>
    );
  }

  const hasSavedSource = hasActiveGoogleSheet || googleSheetSources.length > 0;
  const hasSyncedSource = googleSheetSources.some((source) => source.last_synced_at)
    || years.length > 0;
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
  const onboardingState = hasDashboardPeriodData || rawTransactions.length > 0
    ? "ready"
    : !googleConnection.connected
      ? "google_not_connected"
      : !hasSavedSource
        ? "no_data_source"
        : !hasSyncedSource
          ? "data_source_not_synced"
          : "ready";

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

  const currentPage = activeView === "admin"
    ? ADMIN_PAGE_METADATA
    : PRIMARY_NAVIGATION_ITEMS.find((item) => getNavigationItemActive(item, activeView))
      || PRIMARY_NAVIGATION_ITEMS[0];

  // =========================
  // UI
  // =========================
  return (
    <AppShell
      sidebar={
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

        <DesktopNavigation
          activeView={activeView}
          auth={auth}
          hasPremiumAccess={hasPremiumAccess}
          isSidebarCollapsed={isSidebarCollapsed}
          isSuperAdmin={isSuperAdmin}
          onNavigate={setActiveView}
        />

        <SidebarDataSourceIndicator
          sheetName={currentSheetName}
          isCollapsed={isSidebarCollapsed}
        />
      </aside>
      }
      header={
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="min-w-0">
            <h1 className="text-2xl font-bold sm:text-4xl">
              {currentPage.title}
            </h1>

            <p className="text-muted mt-1 text-sm sm:text-base">
              {currentPage.description}
            </p>

            <EnvironmentBadge systemInfoState={systemInfoState} />
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

            <select
              value={selectedYear}
              onChange={(event) => setSelectedYear(event.target.value)}
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

            <select
              value={selectedMonth}
              onChange={(event) => setSelectedMonth(event.target.value)}
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
      }
      banner={isTestMode && (
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
    >
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
        ) : activeView === "search" ? (
          <SearchPage
            availableYears={years}
            selectedYear={selectedYear}
            selectedMonth={selectedMonth}
            onUnauthorized={onLogout}
          />
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
            selectedYear={selectedYear}
            selectedMonth={selectedMonth}
            onRefresh={refreshBudgetForecast}
          />
        ) : activeView === "admin" && isSuperAdmin ? (
          <AdminUsers
            onImpersonate={onImpersonate}
            onUnauthorized={onLogout}
            systemInfoState={systemInfoState}
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
            systemInfoState={systemInfoState}
            pendingNavigation={pendingSettingsNavigation}
            onDirtyStateChange={setSettingsDirty}
            onCancelNavigation={() => setPendingSettingsNavigation("")}
            onDiscardAndNavigate={finishSettingsNavigation}
            onSaveAndNavigate={finishSettingsNavigation}
          />
        )}
      <MobileNavigation
        activeView={activeView}
        hasPremiumAccess={hasPremiumAccess}
        onNavigate={setActiveView}
      />
    </AppShell>
  );
};

export default Dashboard;
