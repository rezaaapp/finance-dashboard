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
  deleteBudgetsByPeriod,
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

const addCategoryOption = (optionMap, category) => {
  const normalizedCategory = String(category || "").trim();

  if (!normalizedCategory) {
    return;
  }

  optionMap.set(normalizedCategory.toLocaleLowerCase("id-ID"), normalizedCategory);
};

const normalizeCategoryOptions = (categories) => {
  const optionMap = new Map();

  categories.forEach((category) => {
    addCategoryOption(optionMap, category);
  });

  return Array.from(optionMap.values()).sort((first, second) => (
    first.localeCompare(second, "id-ID")
  ));
};

const DEFAULT_BUDGET_CATEGORIES = [
  "Food",
  "Groceries",
  "Transport",
  "Shopping",
  "Entertainment",
  "Health",
  "Bills",
  "Education",
  "Family",
  "Household",
  "Subscription",
  "Other",
];

const MONTH_NAMES = [
  "Januari",
  "Februari",
  "Maret",
  "April",
  "Mei",
  "Juni",
  "Juli",
  "Agustus",
  "September",
  "Oktober",
  "November",
  "Desember",
];

const getPeriodStatus = (year, month) => {
  const today = new Date();
  const currentPeriod = (today.getFullYear() * 100) + today.getMonth() + 1;
  const selectedPeriod = (Number(year) * 100) + Number(month);

  if (selectedPeriod < currentPeriod) {
    return "past";
  }

  if (selectedPeriod > currentPeriod) {
    return "future";
  }

  return "current";
};

const formatPeriodLabel = (year, month) => {
  const monthName = MONTH_NAMES[Number(month) - 1] || `Bulan ${month}`;

  return `${monthName} ${year}`;
};

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
  const availableCategories = useMemo(() => (
    normalizeCategoryOptions(data?.available_categories ?? [])
  ), [data?.available_categories]);
  const categoryRecommendations = useMemo(() => {
    const recommendations = data?.category_recommendations ?? {};
    const recommendationMap = new Map();

    Object.entries(recommendations).forEach(([category, recommendation]) => {
      const normalizedCategory = String(
        recommendation?.category || category || ""
      ).trim();

      if (normalizedCategory) {
        recommendationMap.set(
          normalizedCategory.toLocaleLowerCase("id-ID"),
          {
            category: normalizedCategory,
            historical_average: Number(recommendation?.historical_average || 0),
            recommended_budget: Number(recommendation?.recommended_budget || 0),
            history_months_count: Number(recommendation?.history_months_count || 0),
            history_periods: recommendation?.history_periods ?? [],
          }
        );
      }
    });

    return recommendationMap;
  }, [data?.category_recommendations]);
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
  const periodStatus = hasPeriod
    ? getPeriodStatus(selectedYear, selectedMonth)
    : "current";
  const periodLabel = hasPeriod
    ? formatPeriodLabel(selectedYear, selectedMonth)
    : "";
  const pageTitle = periodStatus === "past"
    ? `Review Anggaran ${periodLabel}`
    : periodStatus === "future"
      ? `Rencana Anggaran ${periodLabel}`
      : "Budgeting & Alerts";
  const alertSectionTitle = periodStatus === "past"
    ? "Hasil Evaluasi"
    : periodStatus === "future"
      ? "Rencana Anggaran"
      : "Alert Budget";
  const alertEmptyMessage = periodStatus === "past"
    ? "Tidak ada kategori yang melewati batas anggaran pada periode ini."
    : periodStatus === "future"
      ? "Belum ada alert karena periode belum berjalan."
      : "Belum ada kategori yang mendekati batas budget.";
  const periodBanner = periodStatus === "past"
    ? "Periode ini sudah lewat. Data ditampilkan sebagai evaluasi anggaran."
    : periodStatus === "future"
      ? "Periode ini belum berjalan. Budget dapat disiapkan, transaksi aktual mungkin belum tersedia."
      : "";
  const visibleAlerts = periodStatus === "future" ? [] : alerts;
  const budgetedCategoryCount = Number(
    summary.budgeted_category_count
      ?? categories.filter((item) => item.is_budgeted).length
  );
  const hasSavedBudgets = budgetedCategoryCount > 0;
  const overBudgetCategoryCount = Number(
    summary.over_budget_category_count
      ?? categories.filter((item) => (
        item.is_budgeted
        && Number(item.budget || item.forecast_budget || 0) > 0
        && Number(item.usage_percentage ?? item.usage_rate ?? 0) >= 100
      )).length
  );
  const unbudgetedCategoryCount = Number(
    summary.unbudgeted_category_count
      ?? categories.filter((item) => !item.is_budgeted).length
  );

  const categoryOptions = useMemo(() => {
    const optionMap = new Map();
    const baseCategories = availableCategories.length > 0
      ? availableCategories
      : DEFAULT_BUDGET_CATEGORIES;

    baseCategories.forEach((category) => {
      addCategoryOption(optionMap, category);
    });

    categories.forEach((item) => {
      if (item.is_budgeted || item.budget_id || item.id) {
        addCategoryOption(optionMap, item.category);
      }
    });

    return Array.from(optionMap.values()).sort((first, second) => (
      first.localeCompare(second, "id-ID")
    ));
  }, [availableCategories, categories]);

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
    const budgetId = item.budget_id ?? item.id;

    try {
      setSavingKey(item.category);
      setError("");

      if (budgetId) {
        await updateBudget(budgetId, {
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

  const handleBudgetUnbudgetedCategory = (item) => {
    setNewCategory(item.category);
    setNewAmount(
      item.recommended_budget > 0
        ? formatInputValue(item.recommended_budget)
        : ""
    );
  };

  const handleUseRecommendationForForm = () => {
    const selectedCategory = categoryRecommendations.get(
      newCategory.trim().toLocaleLowerCase("id-ID")
    );

    if (!selectedCategory?.recommended_budget) {
      return;
    }

    setNewAmount(formatInputValue(selectedCategory.recommended_budget));
  };

  const handleUseRecommendationForRow = (item) => {
    if (!item.recommended_budget) {
      return;
    }

    setDraftBudgets((current) => ({
      ...current,
      [item.category]: Number(item.recommended_budget || 0),
    }));
  };

  const handleDeleteCategory = async (item) => {
    const budgetId = item.budget_id ?? item.id;

    if (!item.is_budgeted || !budgetId) {
      return;
    }

    const confirmed = window.confirm(
      "Hapus budget kategori ini?\n\nBudget akan dihapus tetapi transaksi tetap tersimpan."
    );

    if (!confirmed) {
      return;
    }

    try {
      setSavingKey(item.category);
      setError("");
      await deleteBudget(budgetId);
      await refreshBudgeting();
    } catch (err) {
      console.error("Failed to delete budget.");
      setError(err?.response?.data?.detail || "Budget belum berhasil dihapus.");
    } finally {
      setSavingKey("");
    }
  };

  const handleDeleteAllBudgets = async () => {
    if (!hasPeriod || !hasSavedBudgets) {
      return;
    }

    const message = "Reset seluruh budget periode ini?\n\nBudget akan dihapus.\n\nTransaksi tetap aman dan tidak akan dihapus.";

    if (!window.confirm(message)) {
      return;
    }

    try {
      setSavingKey("delete-all-budgets");
      setError("");
      await deleteBudgetsByPeriod(Number(selectedYear), Number(selectedMonth));
      await refreshBudgeting();
    } catch (err) {
      console.error("Failed to delete budgets by period.");
      setError(err?.response?.data?.detail || "Semua budget belum berhasil dihapus.");
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

  const getCategoryStatus = (item) => {
    const usageRate = Number(item.usage_percentage ?? item.usage_rate ?? 0);

    if (!item.is_budgeted) {
      return {
        label: "Belum dianggarkan",
        className: "border-[var(--color-border)] bg-[var(--color-panel)] text-muted",
      };
    }

    if (usageRate >= 100) {
      return {
        label: "Melewati budget",
        className: "border-red-200 bg-red-50 text-red-700 dark:border-red-400/30 dark:bg-red-500/10 dark:text-red-200",
      };
    }

    if (usageRate >= 90) {
      return {
        label: "Hampir habis",
        className: "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-400/30 dark:bg-amber-500/10 dark:text-amber-200",
      };
    }

    if (usageRate >= 80) {
      return {
        label: "Perlu dipantau",
        className: "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-400/30 dark:bg-blue-500/10 dark:text-blue-200",
      };
    }

    return {
      label: "Aman",
      className: "border-[rgba(74,93,78,0.24)] bg-[var(--color-accent-bg)] text-accent",
    };
  };

  const renderStatusBadge = (item) => {
    const status = getCategoryStatus(item);

    return (
      <span className={`inline-flex w-fit items-center rounded-full border px-2.5 py-1 text-xs font-bold ${status.className}`}>
        {status.label}
      </span>
    );
  };

  const renderBudgetProgress = (item) => {
    const budgetAmount = Number(item.budget ?? item.forecast_budget ?? 0);
    const spending = Number(item.spent ?? item.current_spending ?? 0);
    const usageRate = Number(item.usage_percentage ?? item.usage_rate ?? 0);

    if (budgetAmount <= 0 && spending > 0) {
      return (
        <p className="text-xs font-bold text-muted">
          Belum dianggarkan
        </p>
      );
    }

    return (
      <div>
        {renderUsageProgress(usageRate)}
        <p className="mt-1 text-xs font-semibold text-muted">
          {usageRate.toFixed(1)}%
        </p>
      </div>
    );
  };

  const renderMetricBlock = (label, value, className = "text-main") => (
    <div className="min-w-0">
      <p className="text-xs font-semibold uppercase text-muted">
        {label}
      </p>
      <p className={`mt-1 break-words text-sm font-bold ${className}`}>
        {value}
      </p>
    </div>
  );

  const selectedNewCategory = categoryRecommendations.get(
    newCategory.trim().toLocaleLowerCase("id-ID")
  );

  const renderSelectedCategoryReference = () => {
    if (!newCategory) {
      return (
        <p className="text-xs font-semibold text-muted">
          Pilih kategori untuk melihat estimasi dari 3 bulan sebelumnya.
        </p>
      );
    }

    if (!selectedNewCategory?.history_months_count) {
      return (
        <p className="text-xs font-semibold text-muted">
          Belum ada histori untuk kategori ini
        </p>
      );
    }

    return (
      <div className="grid grid-cols-1 gap-2 text-xs text-muted sm:grid-cols-3">
        <div>
          <p className="font-semibold">Estimasi 3 bulan</p>
          <p className="mt-1 font-bold text-main">
            {formatPrivateRupiah(selectedNewCategory.historical_average, privacyMode)}
          </p>
        </div>
        <div>
          <p className="font-semibold">Rekomendasi</p>
          <p className="mt-1 font-bold text-main">
            {formatPrivateRupiah(selectedNewCategory.recommended_budget, privacyMode)}
          </p>
        </div>
        <div>
          <p className="font-semibold">Histori</p>
          <p className="mt-1 font-bold text-main">
            {selectedNewCategory.history_months_count} bulan
          </p>
        </div>
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
        <div className="mb-5">
          <p className="text-sm font-semibold text-muted">
            Periode {periodLabel}
          </p>
          <h1 className="mt-1 text-2xl font-bold text-main">
            {pageTitle}
          </h1>
          {periodBanner && (
            <div className="mt-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3 text-sm font-semibold text-muted">
              {periodBanner}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
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
              Kategori Melewati Budget
            </p>
            <p className="text-[clamp(1.5rem,7vw,1.875rem)] font-bold text-main">
              {overBudgetCategoryCount}
            </p>
          </div>

          <div className="rounded-xl border border-[var(--color-border)] p-4">
            <p className="mb-4 text-sm font-semibold text-muted">
              Kategori Belum Dianggarkan
            </p>
            <p className="text-[clamp(1.5rem,7vw,1.875rem)] font-bold text-main">
              {unbudgetedCategoryCount}
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
          className="mt-6 grid grid-cols-1 gap-3 rounded-xl border border-[var(--color-border)] p-4 md:grid-cols-[minmax(0,1fr)_220px_auto]"
        >
          <div>
            <select
              value={newCategory}
              onChange={(event) => setNewCategory(event.target.value)}
              className="form-control w-full rounded-xl px-4 py-3"
              aria-label="Pilih kategori budget"
            >
              <option value="">Pilih kategori</option>
              {categoryOptions.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
            <p className="mt-2 text-xs font-semibold text-muted">
              Sumber kategori mengikuti transaksi dari spreadsheet.
            </p>
          </div>
          <div>
            <input
              value={newAmount}
              onChange={(event) => setNewAmount(event.target.value)}
              className="form-control w-full rounded-xl px-4 py-3 text-right"
              inputMode="numeric"
              placeholder="Budget"
            />
            {selectedNewCategory?.recommended_budget > 0 && (
              <button
                type="button"
                onClick={handleUseRecommendationForForm}
                className="mt-2 text-xs font-bold text-accent hover:underline"
              >
                Pakai rekomendasi
              </button>
            )}
          </div>
          <button
            type="submit"
            disabled={!newCategory.trim() || savingKey === "new-budget"}
            className="primary-button inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Plus size={16} />
            Tambah
          </button>
          <div className="md:col-span-2">
            {renderSelectedCategoryReference()}
          </div>
        </form>

        {periodStatus === "past" && (
          <p className="mt-3 text-xs font-semibold text-muted">
            Mengubah budget periode lampau akan mengubah hasil evaluasi.
          </p>
        )}
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
          <div className="flex flex-col gap-2 sm:items-end">
            <p className="text-sm font-semibold text-muted">
              Periode {data?.period || `${selectedYear}-${String(selectedMonth).padStart(2, "0")}`}
            </p>
            <button
              type="button"
              onClick={handleDeleteAllBudgets}
              disabled={!hasSavedBudgets || savingKey === "delete-all-budgets"}
              className="inline-flex min-h-10 items-center justify-center rounded-xl border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 transition-colors hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-red-400/30 dark:text-red-200 dark:hover:bg-red-500/10"
            >
              Reset Budget Bulan Ini
            </button>
          </div>
        </div>

        {categories.length === 0 ? (
          <div className="rounded-xl border border-dashed border-[var(--color-border)] p-6 text-center text-sm text-muted">
            Belum ada budget atau transaksi expense untuk bulan ini.
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-[var(--color-border)]">
            <div className="hidden bg-[var(--color-panel-hover)] px-4 py-3 text-xs font-bold uppercase text-muted xl:grid xl:grid-cols-[minmax(140px,1.4fr)_112px_130px_120px_120px_120px_120px_130px_132px] xl:gap-3">
              <span>Kategori</span>
              <span>Status</span>
              <span>Budget</span>
              <span>Terpakai</span>
              <span>Sisa</span>
              <span>Estimasi</span>
              <span>Rekomendasi</span>
              <span>Progress</span>
              <span className="text-right">Action</span>
            </div>
            {categories.map((item) => {
              const budgetValue = Number(draftBudgets[item.category] ?? item.budget ?? 0);
              const isSaving = savingKey === item.category;
              const remaining = Number(item.remaining_budget || 0);
              const budgetId = item.budget_id ?? item.id;
              const canDeleteBudget = Boolean(item.is_budgeted && budgetId);
              const spentValue = item.spent ?? item.current_spending;
              const estimation = Number(item.historical_average || 0);
              const recommendation = Number(item.recommended_budget || 0);
              const remainingClassName = remaining < 0 ? "metric-warning" : "text-main";
              const rowActions = canDeleteBudget ? (
                <>
                  <button
                    type="button"
                    onClick={() => handleSaveCategory(item)}
                    disabled={isSaving}
                    className="secondary-button inline-flex min-h-10 items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <Save size={15} />
                    Simpan
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteCategory(item)}
                    disabled={isSaving}
                    className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 transition-colors hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-red-400/30 dark:text-red-200 dark:hover:bg-red-500/10"
                    aria-label={`Hapus budget ${item.category}`}
                  >
                    <Trash2 size={15} />
                    Hapus
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  onClick={() => handleBudgetUnbudgetedCategory(item)}
                  disabled={isSaving}
                  className="secondary-button inline-flex min-h-10 items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Plus size={15} />
                  Anggarkan
                </button>
              );

              return (
                <div
                  key={item.category}
                  className="border-t border-[var(--color-border)] bg-[var(--color-panel)] first:border-t-0"
                >
                  <div className="hidden px-4 py-3 xl:grid xl:grid-cols-[minmax(140px,1.4fr)_112px_130px_120px_120px_120px_120px_130px_132px] xl:items-center xl:gap-3">
                    <div className="min-w-0 font-bold text-main">
                      <span className="block truncate" title={item.category}>
                        {item.category}
                      </span>
                    </div>
                    <div>{renderStatusBadge(item)}</div>
                    <div>
                      <input
                        value={formatInputValue(budgetValue)}
                        onChange={(event) => (
                          handleDraftChange(item.category, event.target.value)
                        )}
                        className="form-control w-full rounded-xl px-3 py-2 text-right text-sm font-semibold"
                        inputMode="numeric"
                        aria-label={`Budget ${item.category}`}
                      />
                    </div>
                    <p className="break-words text-sm font-semibold text-main">
                      {formatPrivateRupiah(spentValue, privacyMode)}
                    </p>
                    <p className={`break-words text-sm font-semibold ${remainingClassName}`}>
                      {formatPrivateRupiah(remaining, privacyMode)}
                    </p>
                    <p className="break-words text-sm font-semibold text-main">
                      {formatPrivateRupiah(estimation, privacyMode)}
                    </p>
                    <div>
                      <p className="break-words text-sm font-semibold text-main">
                        {formatPrivateRupiah(recommendation, privacyMode)}
                      </p>
                      {recommendation > 0 && (
                        <button
                          type="button"
                          onClick={() => handleUseRecommendationForRow(item)}
                          className="mt-1 text-xs font-bold text-accent hover:underline"
                        >
                          Pakai
                        </button>
                      )}
                    </div>
                    <div>{renderBudgetProgress(item)}</div>
                    <div className="flex flex-wrap justify-end gap-2">
                      {rowActions}
                    </div>
                  </div>

                  <div className="grid gap-4 p-4 xl:hidden">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="min-w-0">
                        <h3 className="break-words text-base font-bold text-main">
                          {item.category}
                        </h3>
                      </div>
                      {renderStatusBadge(item)}
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="col-span-2">
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
                      {renderMetricBlock(
                        "Terpakai",
                        formatPrivateRupiah(spentValue, privacyMode)
                      )}
                      {renderMetricBlock(
                        "Sisa",
                        formatPrivateRupiah(remaining, privacyMode),
                        remainingClassName
                      )}
                      {renderMetricBlock(
                        "Estimasi",
                        formatPrivateRupiah(estimation, privacyMode)
                      )}
                      <div>
                        {renderMetricBlock(
                          "Rekomendasi",
                          formatPrivateRupiah(recommendation, privacyMode)
                        )}
                        {recommendation > 0 && (
                          <button
                            type="button"
                            onClick={() => handleUseRecommendationForRow(item)}
                            className="mt-1 text-xs font-bold text-accent hover:underline"
                          >
                            Pakai rekomendasi
                          </button>
                        )}
                      </div>
                    </div>

                    <div>
                      <p className="mb-2 text-xs font-semibold uppercase text-muted">
                        Progress
                      </p>
                      {renderBudgetProgress(item)}
                    </div>

                    <div className="flex flex-wrap gap-2">
                      {rowActions}
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
            {alertSectionTitle}
          </h2>
          <BellRing size={22} className="text-[var(--color-alert-text)]" />
        </div>

        <div className="space-y-3">
          {visibleAlerts.length === 0 && (
            <div className="rounded-xl border border-[rgba(74,93,78,0.24)] bg-[var(--color-accent-bg)] p-4 text-sm text-accent">
              {alertEmptyMessage}
            </div>
          )}

          {visibleAlerts.map((alert) => (
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
