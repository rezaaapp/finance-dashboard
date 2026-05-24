import { Moon, RefreshCw, Sun } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import SummaryCard from "../components/SummaryCard";
import MonthlyChart from "../components/charts/MonthlyChart";
import PieCategoryChart from "../components/charts/PieCategoryChart";
import TopSpendingTable from "../components/tables/TopSpendingTable";
import AnomalyTable from "../components/tables/AnomalyTable";

import {
  getSummary,
  getMonthlySpending,
  getMonthlySaving,
  getMonthlyIncome,
  getTopSpending,
  getSpendingByCategory,
  getAnomalies,
  getLatestInsight,
  getAvailableYears,
} from "../api/dashboardApi";

const Dashboard = () => {
  // =========================
  // STATE
  // =========================
  const [summary, setSummary] = useState({});
  const [spending, setSpending] = useState([]);
  const [saving, setSaving] = useState([]);
  const [income, setIncome] = useState([]);
  const [topSpending, setTopSpending] = useState([]);
  const [categoryData, setCategoryData] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [insight, setInsight] = useState("");

  const [years, setYears] = useState([]);
  const [selectedYear, setSelectedYear] = useState("");
  const [selectedMonth, setSelectedMonth] = useState("");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [theme, setTheme] = useState(() => {
    const savedTheme = localStorage.getItem("finance-dashboard-theme");

    if (savedTheme === "light" || savedTheme === "dark") {
      return savedTheme;
    }

    return window.matchMedia("(prefers-color-scheme: light)").matches
      ? "light"
      : "dark";
  });

  const isDarkMode = theme === "dark";

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("finance-dashboard-theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((currentTheme) => (
      currentTheme === "dark" ? "light" : "dark"
    ));
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

      const summaryData = await getSummary(
        year,
        month
      );
      const spendingData = await getMonthlySpending(year, month);
      const savingData = await getMonthlySaving(year, month);
      const incomeData = await getMonthlyIncome(year, month);
      const topSpendingData = await getTopSpending(year, month);
      const categoryDataRes = await getSpendingByCategory(year, month);
      const anomaliesData = await getAnomalies(year, month);
      const insightData = await getLatestInsight(year, month);

      setSummary(summaryData);
      setSpending(spendingData);
      setSaving(savingData);
      setIncome(incomeData);
      setTopSpending(topSpendingData);
      setCategoryData(categoryDataRes);
      setAnomalies(anomaliesData);

      setInsight(
        `Bulan ${insightData.bulan} memiliki spending Rp ${Number(
          insightData.spending
        ).toLocaleString("id-ID")} dengan saving ratio ${
          insightData.saving_ratio
        }%. Status keuangan: ${insightData.status}`
      );

      setError("");
    } catch (err) {
      console.error(err);
      setError("Failed to fetch dashboard data.");
    } finally {
      setLoading(false);
    }
  }, []);

  // =========================
  // INITIAL DATA
  // =========================
  const loadInitialData = useCallback(async () => {
    try {
      setLoading(true);

      const availableYears = await getAvailableYears();

      setYears(availableYears);

      if (availableYears.length > 0) {
        setSelectedYear(availableYears[0]);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to load available years.");
    } finally {
      setLoading(false);
    }
  }, []);

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

  // =========================
  // UI
  // =========================
  return (
    <div className="dashboard-screen min-h-screen flex">
      {/* SIDEBAR */}
      <aside className="dashboard-sidebar w-64 border-r p-6 hidden lg:block">
        <h1 className="text-2xl font-bold text-accent mb-10">
          Finance AI
        </h1>

        <nav className="space-y-4">
          <div className="nav-link cursor-pointer">
            Dashboard
          </div>

          <div className="nav-link cursor-pointer">
            Analytics
          </div>

          <div className="nav-link cursor-pointer">
            Spending
          </div>

          <div className="nav-link cursor-pointer">
            Saving
          </div>
        </nav>
      </aside>

      {/* MAIN */}
      <main className="flex-1 p-6">
        {/* HEADER */}
        <div className="flex flex-col gap-5 xl:flex-row xl:justify-between xl:items-center mb-8">
          <div>
            <h1 className="text-4xl font-bold">
              Financial Dashboard
            </h1>

            <p className="text-muted mt-1">
              Monitoring household financial analytics
            </p>
          </div>

          <div className="flex flex-wrap gap-3">

          {/* YEAR FILTER */}
          <select
            value={selectedYear}
            onChange={(e) => setSelectedYear(e.target.value)}
            className="form-control px-4 py-2 rounded-xl"
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
            className="form-control px-4 py-2 rounded-xl"
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
              className="theme-toggle px-4 py-2 rounded-xl font-semibold"
              aria-label={`Switch to ${isDarkMode ? "light" : "dark"} mode`}
              title={`Switch to ${isDarkMode ? "light" : "dark"} mode`}
            >
              {isDarkMode ? <Sun size={18} /> : <Moon size={18} />}
              <span>{isDarkMode ? "Light" : "Dark"}</span>
            </button>

            {/* REFRESH BUTTON */}
            <button
              onClick={() => fetchDashboardData(selectedYear, selectedMonth)}
              className="primary-button px-4 py-2 rounded-xl font-semibold"
            >
              <RefreshCw size={18} />
              Refresh Data
            </button>
          </div>
        </div>

        {/* SUMMARY */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <SummaryCard
            title="Total Pengeluaran"
            value={summary.total_pengeluaran}
            trend={summary.trend_pengeluaran}
          />

          <SummaryCard
            title="Total Saving"
            value={summary.total_saving}
            trend={summary.trend_saving}
          />

          <SummaryCard
            title="Total Income"
            value={summary.total_income}
            trend={summary.trend_income}
          />
        </div>

        {/* CHARTS */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-8">
          <MonthlyChart
            title="Monthly Spending"
            data={spending}
            dataKey="total"
            theme={theme}
          />

          <MonthlyChart
            title="Monthly Saving"
            data={saving}
            dataKey="total"
            theme={theme}
          />

          <MonthlyChart
            title="Monthly Income"
            data={income}
            dataKey="total"
            theme={theme}
          />

          <PieCategoryChart data={categoryData} theme={theme} />
        </div>

        {/* TABLES */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-8">
          <TopSpendingTable data={topSpending} />

          <AnomalyTable data={anomalies} />
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
      </main>
    </div>
  );
};

export default Dashboard;
