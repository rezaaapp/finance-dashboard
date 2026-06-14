import {
  AlertTriangle,
  BellRing,
  Plus,
  Save,
  Trash2,
  Wallet,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  createBudget,
  deleteBudget,
  updateBudget,
} from "../api/budgetsApi";
import {
  formatPrivateCompact,
  formatPrivateRupiah,
  maskChartRows,
} from "../utils/privacy";
import { dashboardChartPalette } from "../theme/chartTheme";

const parseRupiahInput = (value) => (
  Number(String(value || "").replace(/\D/g, ""))
);

const formatInputValue = (value) => (
  Number(value || 0).toLocaleString("id-ID")
);

const getSeverityClassName = (severity) => {
  if (severity === "danger") {
    return "border-red-200 bg-red-50 text-red-800 dark:border-red-400/30 dark:bg-red-500/10 dark:text-red-200";
  }

  if (severity === "warning") {
    return "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-400/30 dark:bg-amber-500/10 dark:text-amber-200";
  }

  if (severity === "info") {
    return "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-400/30 dark:bg-blue-500/10 dark:text-blue-200";
  }

  return "border-[var(--color-border)] bg-[var(--color-panel-hover)] text-soft";
};

const BudgetingAlerts = ({
  data,
  privacyMode,
  selectedYear,
  selectedMonth,
  onRefresh,
}) => {
  const categories = useMemo(() => (
    data?.categories ?? data?.forecast ?? []
  ), [data?.categories, data?.forecast]);
  const alerts = useMemo(() => (
    data?.alerts ?? []
  ), [data?.alerts]);
  const summary = data?.summary ?? {};
  const [draftBudgets, setDraftBudgets] = useState({});
  const [newCategory, setNewCategory] = useState("");
  const [newAmount, setNewAmount] = useState("");
  const [savingKey, setSavingKey] = useState("");
  const [error, setError] = useState("");
  const [isMobileChart, setIsMobileChart] = useState(() => (
    typeof window !== "undefined"
      ? window.matchMedia("(max-width: 767px)").matches
      : false
  ));
  const hasPeriod = Boolean(selectedYear && selectedMonth);

  useEffect(() => {
    const nextDrafts = {};

    categories.forEach((item) => {
      nextDrafts[item.category] = Number(item.budget ?? item.forecast_budget ?? 0);
    });

    setDraftBudgets(nextDrafts);
  }, [categories]);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 767px)");
    const handleChange = (event) => {
      setIsMobileChart(event.matches);
    };

    setIsMobileChart(mediaQuery.matches);
    mediaQuery.addEventListener("change", handleChange);

    return () => {
      mediaQuery.removeEventListener("change", handleChange);
    };
  }, []);

  const chartData = useMemo(() => (
    maskChartRows(
      categories,
      ["budget", "current_spending"],
      privacyMode
    )
  ), [categories, privacyMode]);

  const handleDraftChange = (category, value) => {
    setDraftBudgets((current) => ({
      ...current,
      [category]: parseRupiahInput(value),
    }));
  };

  const refreshBudgeting = async () => {
    if (onRefresh) {
      await onRefresh();
    }
  };

  const handleSaveCategory = async (item) => {
    if (!hasPeriod) {
      return;
    }

    const amount = Number(draftBudgets[item.category] || 0);

    try {
      setSavingKey(item.category);
      setError("");

      if (item.id) {
        await updateBudget(item.id, {
          category: item.category,
          amount,
        });
      } else {
        await createBudget({
          year: Number(selectedYear),
          month: Number(selectedMonth),
          category: item.category,
          amount,
        });
      }

      await refreshBudgeting();
    } catch (err) {
      console.error("Failed to save budget.");
      setError(err?.response?.data?.detail || "Budget belum berhasil disimpan.");
    } finally {
      setSavingKey("");
    }
  };

  const handleAddCategory = async (event) => {
    event.preventDefault();

    const category = newCategory.trim();
    const amount = parseRupiahInput(newAmount);

    if (!category || !hasPeriod) {
      return;
    }

    try {
      setSavingKey("new-budget");
      setError("");
      await createBudget({
        year: Number(selectedYear),
        month: Number(selectedMonth),
        category,
        amount,
      });
      setNewCategory("");
      setNewAmount("");
      await refreshBudgeting();
    } catch (err) {
      console.error("Failed to add budget.");
      setError(err?.response?.data?.detail || "Kategori budget belum berhasil ditambahkan.");
    } finally {
      setSavingKey("");
    }
  };

  const handleDeleteCategory = async (item) => {
    if (!item.id) {
      return;
    }

    try {
      setSavingKey(item.category);
      setError("");
      await deleteBudget(item.id);
      await refreshBudgeting();
    } catch (err) {
      console.error("Failed to delete budget.");
      setError(err?.response?.data?.detail || "Budget belum berhasil dihapus.");
    } finally {
      setSavingKey("");
    }
  };

  const renderUsageProgress = (usageRate) => {
    const cappedUsage = Math.min(Math.max(Number(usageRate || 0), 0), 100);
    const progressColor = usageRate >= 100
      ? "bg-red-500"
      : usageRate >= 90
        ? "bg-amber-500"
        : usageRate >= 80
          ? "bg-blue-500"
          : "bg-[var(--color-accent)]";

    return (
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-[var(--color-panel-hover)]">
        <div
          className={`h-full rounded-full ${progressColor}`}
          style={{ width: `${cappedUsage}%` }}
        />
      </div>
    );
  };

  if (!hasPeriod) {
    return (
      <section className="panel rounded-2xl p-6 text-center shadow-lg">
        <BellRing className="mx-auto text-accent" size={28} />
        <h2 className="mt-3 text-xl font-bold text-main">
          Pilih bulan untuk mengatur budget
        </h2>
        <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-muted">
          Budget disimpan per workspace, tahun, bulan, dan kategori. Pilih tahun
          serta bulan tertentu supaya anggaran tidak tercampur dengan periode lain.
        </p>
      </section>
    );
  }

  return (
    <div className="grid min-w-0 grid-cols-1 gap-5 sm:gap-6">
      <section className="panel rounded-2xl p-4 shadow-lg sm:p-5">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-[var(--color-border)] p-4">
            <div className="mb-4 flex items-center justify-between">
              <p className="text-sm font-semibold text-muted">
                Total Budget
              </p>
              <Wallet size={20} className="text-accent" />
            </div>
            <p className="break-words text-[clamp(1.25rem,6vw,1.5rem)] font-bold text-main">
              {formatPrivateRupiah(summary.total_budget || 0, privacyMode)}
            </p>
          </div>

          <div className="rounded-xl border border-[var(--color-border)] p-4">
            <p className="mb-4 text-sm font-semibold text-muted">
              Sudah Terpakai
            </p>
            <p className="break-words text-[clamp(1.25rem,6vw,1.5rem)] font-bold text-main">
              {formatPrivateRupiah(summary.current_spending || 0, privacyMode)}
            </p>
          </div>

          <div className="rounded-xl border border-[var(--color-border)] p-4">
            <p className="mb-4 text-sm font-semibold text-muted">
              Sisa Budget
            </p>
            <p className={`break-words text-[clamp(1.25rem,6vw,1.5rem)] font-bold ${
              Number(summary.remaining_budget || 0) < 0
                ? "metric-warning"
                : "text-main"
            }`}>
              {formatPrivateRupiah(summary.remaining_budget || 0, privacyMode)}
            </p>
          </div>

          <div className="rounded-xl border border-[rgba(244,211,94,0.55)] bg-[var(--color-alert-bg)] p-4">
            <p className="mb-4 text-sm font-semibold text-muted">
              Alert Aktif
            </p>
            <p className="text-[clamp(1.5rem,7vw,1.875rem)] font-bold text-main">
              {alerts.length}
            </p>
          </div>
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-800 dark:border-red-400/30 dark:bg-red-500/10 dark:text-red-200">
            {error}
          </div>
        )}

        <form
          onSubmit={handleAddCategory}
          className="mt-6 grid grid-cols-1 gap-3 rounded-xl border border-[var(--color-border)] p-4 md:grid-cols-[1fr_220px_auto]"
        >
          <input
            value={newCategory}
            onChange={(event) => setNewCategory(event.target.value)}
            className="form-control rounded-xl px-4 py-3"
            placeholder="Nama kategori, contoh: Groceries"
          />
          <input
            value={newAmount}
            onChange={(event) => setNewAmount(event.target.value)}
            className="form-control rounded-xl px-4 py-3 text-right"
            inputMode="numeric"
            placeholder="Budget"
          />
          <button
            type="submit"
            disabled={!newCategory.trim() || savingKey === "new-budget"}
            className="primary-button inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Plus size={16} />
            Tambah
          </button>
        </form>
      </section>

      <section className="panel rounded-2xl p-4 shadow-lg sm:p-5">
        <div className="mb-5 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-xl font-bold text-main">
              Budget per Kategori
            </h2>
            <p className="text-sm text-muted">
              Kategori tanpa budget tetap tampil sebagai Belum dianggarkan.
            </p>
          </div>
          <p className="text-sm font-semibold text-muted">
            Periode {data?.period || `${selectedYear}-${String(selectedMonth).padStart(2, "0")}`}
          </p>
        </div>

        {categories.length === 0 ? (
          <div className="rounded-xl border border-dashed border-[var(--color-border)] p-6 text-center text-sm text-muted">
            Belum ada budget atau transaksi expense untuk bulan ini.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3">
            {categories.map((item) => {
              const budgetValue = Number(draftBudgets[item.category] ?? item.budget ?? 0);
              const isSaving = savingKey === item.category;
              const remaining = Number(item.remaining_budget || 0);

              return (
                <div
                  key={item.category}
                  className="rounded-xl border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-4"
                >
                  <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1.1fr_180px_180px_180px_auto] lg:items-center">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="break-words text-base font-bold text-main">
                          {item.category}
                        </h3>
                        {item.status === "unbudgeted" && (
                          <span className="rounded-full bg-[var(--color-panel)] px-2.5 py-1 text-xs font-bold text-muted">
                            Belum dianggarkan
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-sm text-muted">
                        Terpakai {Number(item.usage_rate || 0).toFixed(1)}%
                      </p>
                      {renderUsageProgress(item.usage_rate)}
                    </div>

                    <div>
                      <p className="text-xs font-semibold uppercase text-muted">
                        Budget
                      </p>
                      <input
                        value={formatInputValue(budgetValue)}
                        onChange={(event) => (
                          handleDraftChange(item.category, event.target.value)
                        )}
                        className="form-control mt-2 w-full rounded-xl px-3 py-2 text-right font-semibold"
                        inputMode="numeric"
                        aria-label={`Budget ${item.category}`}
                      />
                    </div>

                    <div>
                      <p className="text-xs font-semibold uppercase text-muted">
                        Terpakai
                      </p>
                      <p className="mt-2 break-words font-semibold text-main">
                        {formatPrivateRupiah(item.current_spending, privacyMode)}
                      </p>
                    </div>

                    <div>
                      <p className="text-xs font-semibold uppercase text-muted">
                        Sisa
                      </p>
                      <p className={`mt-2 break-words font-semibold ${
                        remaining < 0 ? "metric-warning" : "text-main"
                      }`}>
                        {formatPrivateRupiah(remaining, privacyMode)}
                      </p>
                    </div>

                    <div className="flex gap-2 lg:justify-end">
                      <button
                        type="button"
                        onClick={() => handleSaveCategory(item)}
                        disabled={isSaving}
                        className="secondary-button inline-flex min-h-10 items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        <Save size={15} />
                        Simpan
                      </button>
                      {item.id && (
                        <button
                          type="button"
                          onClick={() => handleDeleteCategory(item)}
                          disabled={isSaving}
                          className="inline-flex min-h-10 items-center justify-center rounded-xl border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 transition-colors hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-red-400/30 dark:text-red-200 dark:hover:bg-red-500/10"
                          aria-label={`Hapus budget ${item.category}`}
                        >
                          <Trash2 size={15} />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      <section className="panel rounded-2xl p-4 shadow-lg sm:p-5">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-xl font-bold text-main">
            Alert Budget
          </h2>
          <BellRing size={22} className="text-[var(--color-alert-text)]" />
        </div>

        <div className="space-y-3">
          {alerts.length === 0 && (
            <div className="rounded-xl border border-[rgba(74,93,78,0.24)] bg-[var(--color-accent-bg)] p-4 text-sm text-accent">
              Belum ada kategori yang mendekati batas budget.
            </div>
          )}

          {alerts.map((alert) => (
            <div
              key={`${alert.category}-${alert.severity}`}
              className={`rounded-xl border p-4 text-sm ${getSeverityClassName(alert.severity)}`}
            >
              <div className="flex items-start gap-3">
                <AlertTriangle size={18} className="mt-0.5 shrink-0" />
                <div>
                  <p className="font-semibold">
                    {alert.message}
                  </p>
                  <p className="mt-1 opacity-80">
                    Terpakai {Number(alert.usage_rate || 0).toFixed(1)}% dari budget.
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel rounded-2xl p-4 shadow-lg sm:p-5">
        <div className="mb-6">
          <h2 className="text-xl font-bold text-main">
            Perbandingan Budget dan Pengeluaran
          </h2>
          <p className="mt-1 text-sm text-muted">
            Hanya transaksi expense yang dihitung sebagai pengeluaran budget.
          </p>
        </div>

        {categories.length === 0 ? (
          <div className="flex h-64 items-center justify-center rounded-xl border border-dashed border-[var(--color-border)] px-4 text-center text-sm text-muted">
            Belum ada data untuk divisualisasikan.
          </div>
        ) : (
          <div className="h-[460px] md:h-[380px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                layout={isMobileChart ? "vertical" : "horizontal"}
                margin={isMobileChart
                  ? { top: 8, right: 12, bottom: 8, left: 12 }
                  : { top: 8, right: 16, bottom: 8, left: 0 }}
              >
                <CartesianGrid
                  stroke="var(--color-border)"
                  strokeDasharray="3 3"
                />
                {isMobileChart ? (
                  <>
                    <XAxis
                      type="number"
                      stroke="var(--color-muted)"
                      tick={{ fill: "var(--color-muted)", fontSize: 11 }}
                      tickFormatter={(value) => formatPrivateCompact(value, privacyMode)}
                    />
                    <YAxis
                      type="category"
                      dataKey="category"
                      width={126}
                      stroke="var(--color-muted)"
                      tick={{ fill: "var(--color-muted)", fontSize: 11 }}
                      tickLine={false}
                      interval={0}
                    />
                  </>
                ) : (
                  <>
                    <XAxis
                      dataKey="category"
                      stroke="var(--color-muted)"
                      tick={{ fill: "var(--color-muted)", fontSize: 12 }}
                    />
                    <YAxis
                      stroke="var(--color-muted)"
                      tick={{ fill: "var(--color-muted)", fontSize: 12 }}
                      tickFormatter={(value) => formatPrivateCompact(value, privacyMode)}
                    />
                  </>
                )}
                <Tooltip
                  formatter={(value) => formatPrivateRupiah(value, privacyMode)}
                  contentStyle={{
                    backgroundColor: "#ffffff",
                    border: "1px solid var(--color-border)",
                    borderRadius: "12px",
                    color: "var(--color-text)",
                  }}
                />
                <Bar
                  dataKey="budget"
                  name="Budget"
                  fill={dashboardChartPalette.navy}
                  radius={isMobileChart ? [0, 6, 6, 0] : [6, 6, 0, 0]}
                />
                <Bar
                  dataKey="current_spending"
                  name="Terpakai"
                  fill={dashboardChartPalette.sage}
                  radius={isMobileChart ? [0, 6, 6, 0] : [6, 6, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>
    </div>
  );
};

export default BudgetingAlerts;
