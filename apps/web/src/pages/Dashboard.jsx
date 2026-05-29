import {
  BarChart3,
  BellRing,
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  LogOut,
  Moon,
  RefreshCw,
  Settings,
  Sun,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import SummaryCard from "../components/SummaryCard";
import MonthlyChart from "../components/charts/MonthlyChart";
import PieCategoryChart from "../components/charts/PieCategoryChart";
import GroceryVsFoodChart from "../components/charts/GroceryVsFoodChart";
import CategoryHeatmap from "../components/charts/CategoryHeatmap";
import CategoryTrendChart from "../components/charts/CategoryTrendChart";
import PersonalAnalytics from "../components/analytics/PersonalAnalytics";
import IncomeVelocityDashboard from "../components/analytics/IncomeVelocityDashboard";
import SourceDanaAnalytics from "../components/analytics/SourceDanaAnalytics";
import MonthlyAllocationTrend from "../components/analytics/MonthlyAllocationTrend";
import SidebarDataSourceIndicator from "../components/SidebarDataSourceIndicator";
import TopSpendingTable from "../components/tables/TopSpendingTable";
import AnomalyTable from "../components/tables/AnomalyTable";
import BudgetingAlerts from "./BudgetingAlerts";
import Configuration from "./Configuration";
import {
  formatPrivateRupiah,
  PRIVACY_MODES,
} from "../utils/privacy";

import {
  getSummary,
  refreshDashboardData,
  getMonthlySpending,
  getMonthlySaving,
  getMonthlyIncome,
  getTopSpending,
  getSpendingByCategory,
  getGroceryVsFood,
  getCategoryHeatmap,
  getTransactions,
  getCategoryTrends,
  getSourceDanaAnalytics,
  getMonthlyAllocation,
  getPersonalAnalytics,
  getAnomalies,
  getLatestInsight,
  getAvailableYears,
  getBudgetForecast,
  getWorkspaceConfiguration,
} from "../api/dashboardApi";

const Dashboard = ({ onLogout }) => {
  // =========================
  // STATE
  // =========================
  const [summary, setSummary] = useState({});
  const [spending, setSpending] = useState([]);
  const [saving, setSaving] = useState([]);
  const [income, setIncome] = useState([]);
  const [topSpending, setTopSpending] = useState([]);
  const [categoryData, setCategoryData] = useState([]);
  const [groceryVsFood, setGroceryVsFood] = useState([]);
  const [categoryHeatmap, setCategoryHeatmap] = useState({});
  const [rawTransactions, setRawTransactions] = useState([]);
  const [categoryTrends, setCategoryTrends] = useState({});
  const [sourceDanaAnalytics, setSourceDanaAnalytics] = useState({});
  const [monthlyAllocation, setMonthlyAllocation] = useState([]);
  const [personalAnalytics, setPersonalAnalytics] = useState({});
  const [budgetForecast, setBudgetForecast] = useState({});
  const [anomalies, setAnomalies] = useState([]);
  const [insight, setInsight] = useState("");
  const [currentSheetName, setCurrentSheetName] = useState("");
  const [hasActiveGoogleSheet, setHasActiveGoogleSheet] = useState(false);

  const [years, setYears] = useState([]);
  const [selectedYear, setSelectedYear] = useState("");
  const [selectedMonth, setSelectedMonth] = useState("");
  const [activeView, setActiveView] = useState("dashboard");
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

  const toggleTheme = () => {
    setTheme((currentTheme) => (
      currentTheme === "dark" ? "light" : "dark"
    ));
  };

  const clearDashboardData = () => {
    setSummary({});
    setSpending([]);
    setSaving([]);
    setIncome([]);
    setTopSpending([]);
    setCategoryData([]);
    setGroceryVsFood([]);
    setCategoryHeatmap({});
    setRawTransactions([]);
    setCategoryTrends({});
    setSourceDanaAnalytics({});
    setMonthlyAllocation([]);
    setPersonalAnalytics({});
    setBudgetForecast({});
    setAnomalies([]);
    setInsight("");
    setCurrentSheetName("");
    setHasActiveGoogleSheet(false);
    setYears([]);
    setSelectedYear("");
    setSelectedMonth("");
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
      console.error(err);

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
      const groceryVsFoodData = await getGroceryVsFood(
        year,
        month,
        analyticsUserName
      );
      const categoryHeatmapData = await getCategoryHeatmap(
        year,
        month,
        analyticsUserName
      );
      const transactionsData = await getTransactions(
        year,
        month,
        analyticsUserName
      );
      const categoryTrendsData = await getCategoryTrends(
        year,
        month,
        analyticsUserName
      );
      const personalAnalyticsData = await getPersonalAnalytics(year, month);
      const budgetForecastData = await getBudgetForecast(year, month);
      const anomaliesData = await getAnomalies(year, month);
      const insightData = await getLatestInsight(year, month);

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

      setInsight(
        `Month ${insightData.bulan} has spending of ${
          formatPrivateRupiah(insightData.spending, privacyMode)
        } with a saving ratio of ${
          insightData.saving_ratio
        }%. Financial status: ${insightData.status}`
      );

      setError("");
    } catch (err) {
      console.error(err);

      if (err?.response?.status === 401) {
        onLogout();
        return;
      }

      setError("Failed to fetch dashboard data.");
    } finally {
      setLoading(false);
    }
  }, [onLogout, privacyMode, selectedAnalyticsUser]);

  // =========================
  // INITIAL DATA
  // =========================
  const loadInitialData = useCallback(async () => {
    try {
      setLoading(true);

      const workspaceConfiguration = await getWorkspaceConfiguration();
      const googleSheetSources = workspaceConfiguration?.configuration?.google_sheet_sources || [];
      const googleSheetId = workspaceConfiguration?.configuration?.google_sheet_id;
      const hasGoogleSheet = googleSheetSources.length > 0 || Boolean(googleSheetId);

      setHasActiveGoogleSheet(hasGoogleSheet);

      if (!hasGoogleSheet) {
        clearDashboardData();
        return;
      }

      const availableYears = await getAvailableYears();

      setYears(availableYears);

      if (availableYears.length > 0) {
        setSelectedYear(availableYears[0]);
      } else {
        setSelectedYear("");
        setSelectedMonth("");
      }
    } catch (err) {
      console.error(err);

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
    loadInitialData();
  }, [loadInitialData]);

  // =========================
  // FETCH DASHBOARD WHEN YEAR CHANGES
  // =========================
  useEffect(() => {
    if (selectedYear !== "") {
      fetchDashboardData(
        selectedYear,
        selectedMonth
      );
    }
  }, [fetchDashboardData, selectedYear, selectedMonth]);

  // =========================
  // LAZY FETCH ANALYTICS DATA
  // =========================
  useEffect(() => {
    if (activeView !== "analytics" || selectedYear === "") {
      return;
    }

    let isMounted = true;
    const analyticsUserName = selectedAnalyticsUser === "all"
      ? ""
      : selectedAnalyticsUser;

    const fetchSourceDanaAnalytics = async () => {
      try {
        const data = await getSourceDanaAnalytics(
          selectedYear,
          selectedMonth,
          analyticsUserName
        );
        const monthlyAllocationData = await getMonthlyAllocation(
          selectedYear,
          selectedMonth,
          analyticsUserName
        );

        if (isMounted) {
          setSourceDanaAnalytics(data);
          setMonthlyAllocation(monthlyAllocationData);
        }
      } catch (err) {
        console.error(err);

        if (err?.response?.status === 401) {
          onLogout();
          return;
        }

        if (isMounted) {
          setSourceDanaAnalytics({});
          setMonthlyAllocation([]);
        }
      }
    };

    fetchSourceDanaAnalytics();

    return () => {
      isMounted = false;
    };
  }, [
    activeView,
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

  const shouldShowEmptyDashboard = activeView === "dashboard" && !hasActiveGoogleSheet;

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
              Operasional Rumah Tangga Dashboard
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
          </button>

          <button
            type="button"
            onClick={() => setActiveView("configuration")}
            className={`nav-link flex min-h-11 w-full items-center rounded-xl border border-transparent text-left transition-colors ${
              isSidebarCollapsed
                ? "justify-center px-0"
                : "justify-start gap-3 px-3 py-2"
            } ${
              activeView === "configuration"
                ? "bg-[var(--color-accent-bg)] text-accent"
                : "bg-transparent"
            }`}
            aria-label="Configuration"
            title="Configuration"
          >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl">
              <Settings size={18} />
            </span>
            {!isSidebarCollapsed && (
              <span className="min-w-0 flex-1 truncate font-semibold">
                Configuration
              </span>
            )}
          </button>
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
              Financial Dashboard
            </h1>

            <p className="text-muted mt-1 text-sm sm:text-base">
              Monitoring household financial analytics
            </p>
          </div>

          <div className="grid w-full grid-cols-2 gap-3 sm:grid-cols-[minmax(120px,140px)_minmax(150px,170px)_auto_auto_auto] sm:items-center xl:w-auto">

          {/* YEAR FILTER */}
          <select
            value={selectedYear}
            onChange={(e) => setSelectedYear(e.target.value)}
            className="form-control w-full rounded-xl px-3 py-2 text-sm sm:px-4 sm:text-base"
          >
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

            <button
              type="button"
              onClick={onLogout}
              className="theme-toggle h-11 w-full rounded-lg px-3 py-2 font-semibold sm:w-auto sm:px-4"
            >
              <LogOut size={18} />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </div>

        {shouldShowEmptyDashboard ? (
          <div className="panel rounded-lg p-6 shadow-lg">
            <div className="mx-auto flex max-w-2xl flex-col items-center py-12 text-center">
              <div className="icon-badge rounded-xl p-4">
                <Settings size={28} />
              </div>

              <h2 className="mt-5 text-2xl font-bold text-main">
                Dashboard masih kosong
              </h2>

              <p className="mt-3 text-sm leading-7 text-muted sm:text-base">
                Tambahkan Google Spreadsheet ID di Configuration, lalu klik Add
                Connection. Setelah source terhubung, dashboard akan menganalisa
                data dari spreadsheet dan menampilkan chart finansial di sini.
              </p>

              <button
                type="button"
                onClick={() => setActiveView("configuration")}
                className="primary-button mt-6 inline-flex rounded-lg px-5 py-2.5 font-semibold"
              >
                <Settings size={18} />
                Buka Configuration
              </button>
            </div>
          </div>
        ) : activeView === "dashboard" ? (
          <>
            {/* SUMMARY */}
            <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 md:gap-6">
              <SummaryCard
                title="Total Expenses"
                value={summary.total_pengeluaran}
                trend={summary.trend_pengeluaran}
                privacyMode={privacyMode}
              />

              <SummaryCard
                title="Total Saving"
                value={summary.total_saving}
                trend={summary.trend_saving}
                privacyMode={privacyMode}
              />

              <SummaryCard
                title="Total Income"
                value={summary.total_income}
                trend={summary.trend_income}
                privacyMode={privacyMode}
              />
            </div>

            {/* CHARTS */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-8">
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
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-8">
              <TopSpendingTable
                data={topSpending}
                privacyMode={privacyMode}
              />

              <AnomalyTable
                data={anomalies}
                privacyMode={privacyMode}
              />
            </div>

            {/* AI INSIGHT */}
            <div className="panel p-6 rounded-2xl">
              <h2 className="text-2xl font-bold mb-4 text-accent">
                AI Financial Insight
              </h2>

              <p className="text-soft leading-8">
                {insight}
              </p>
            </div>
          </>
        ) : activeView === "analytics" ? (
          <div className="grid grid-cols-1 gap-6">
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
          </div>
        ) : activeView === "budgeting" ? (
          <BudgetingAlerts
            data={budgetForecast}
            theme={theme}
            privacyMode={privacyMode}
            autoBudget={autoBudget}
          />
        ) : (
          <Configuration
            autoBudget={autoBudget}
            paydayStartDay={paydayStartDay}
            selectedYear={selectedYear}
            currentSheetName={currentSheetName}
            privacyMode={privacyMode}
            onSaveChanges={handleSaveConfiguration}
            onUnauthorized={onLogout}
          />
        )}
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-50 grid grid-cols-4 gap-1 border-t border-[var(--color-border)] bg-[var(--color-panel)] px-2 py-2 shadow-none lg:hidden">
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
          Configuration
        </button>
      </nav>
    </div>
  );
};

export default Dashboard;
