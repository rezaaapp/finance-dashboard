import { useEffect, useState } from "react";

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

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // =========================
  // LOAD AVAILABLE YEARS
  // =========================
  useEffect(() => {
    loadInitialData();
  }, []);

  // =========================
  // FETCH DASHBOARD WHEN YEAR CHANGES
  // =========================
  useEffect(() => {
    if (selectedYear !== "") {
      fetchDashboardData(selectedYear);
    }
  }, [selectedYear]);

  // =========================
  // INITIAL DATA
  // =========================
  const loadInitialData = async () => {
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
  };

  // =========================
  // FETCH ALL DASHBOARD DATA
  // =========================
  const fetchDashboardData = async (year = "") => {
    try {
      setLoading(true);

      const summaryData = await getSummary(year);
      const spendingData = await getMonthlySpending(year);
      const savingData = await getMonthlySaving(year);
      const incomeData = await getMonthlyIncome(year);
      const topSpendingData = await getTopSpending(year);
      const categoryDataRes = await getSpendingByCategory(year);
      const anomaliesData = await getAnomalies(year);
      const insightData = await getLatestInsight(year);

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
  };

  // =========================
  // LOADING SCREEN
  // =========================
  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-950 text-white text-2xl">
        Loading Dashboard...
      </div>
    );
  }

  // =========================
  // ERROR SCREEN
  // =========================
  if (error) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-950 text-red-400 text-xl">
        {error}
      </div>
    );
  }

  // =========================
  // UI
  // =========================
  return (
    <div className="min-h-screen bg-slate-950 text-white flex">
      {/* SIDEBAR */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800 p-6 hidden lg:block">
        <h1 className="text-2xl font-bold text-cyan-400 mb-10">
          Finance AI
        </h1>

        <nav className="space-y-4">
          <div className="text-slate-300 hover:text-cyan-400 cursor-pointer">
            Dashboard
          </div>

          <div className="text-slate-300 hover:text-cyan-400 cursor-pointer">
            Analytics
          </div>

          <div className="text-slate-300 hover:text-cyan-400 cursor-pointer">
            Spending
          </div>

          <div className="text-slate-300 hover:text-cyan-400 cursor-pointer">
            Saving
          </div>
        </nav>
      </aside>

      {/* MAIN */}
      <main className="flex-1 p-6">
        {/* HEADER */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-bold">
              Financial Dashboard
            </h1>

            <p className="text-slate-400 mt-1">
              Monitoring household financial analytics
            </p>
          </div>

          <div className="flex gap-3">
            {/* YEAR FILTER */}
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(e.target.value)}
              className="bg-slate-900 border border-slate-700 px-4 py-2 rounded-xl"
            >
              {years.map((year) => (
                <option key={year} value={year}>
                  {year}
                </option>
              ))}
            </select>

            {/* REFRESH BUTTON */}
            <button
              onClick={() => fetchDashboardData(selectedYear)}
              className="bg-cyan-500 hover:bg-cyan-600 px-4 py-2 rounded-xl font-semibold"
            >
              Refresh Data
            </button>
          </div>
        </div>

        {/* SUMMARY */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <SummaryCard
            title="Total Pengeluaran"
            value={summary.total_pengeluaran}
          />

          <SummaryCard
            title="Total Saving"
            value={summary.total_saving}
          />

          <SummaryCard
            title="Total Income"
            value={summary.total_income}
          />
        </div>

        {/* CHARTS */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-8">
          <MonthlyChart
            title="Monthly Spending"
            data={spending}
            dataKey="total"
          />

          <MonthlyChart
            title="Monthly Saving"
            data={saving}
            dataKey="total"
          />

          <MonthlyChart
            title="Monthly Income"
            data={income}
            dataKey="total"
          />

          <PieCategoryChart data={categoryData} />
        </div>

        {/* TABLES */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-8">
          <TopSpendingTable data={topSpending} />

          <AnomalyTable data={anomalies} />
        </div>

        {/* AI INSIGHT */}
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
          <h2 className="text-2xl font-bold mb-4 text-cyan-400">
            AI Financial Insight
          </h2>

          <p className="text-slate-300 leading-8">
            {insight}
          </p>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;