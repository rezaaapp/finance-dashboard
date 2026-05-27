import {
  AlertTriangle,
  BellRing,
  Bot,
  Info,
  SlidersHorizontal,
  Wallet,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
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
  formatPrivateCompact,
  formatPrivateRupiah,
  maskChartRows,
} from "../utils/privacy";

const BudgetingAlerts = ({
  data,
  theme = "dark",
  privacyMode,
  autoBudget,
  onAutoBudgetChange,
}) => {
  const alerts = useMemo(() => (
    data?.alerts ?? []
  ), [data?.alerts]);
  const forecast = useMemo(() => (
    data?.forecast ?? []
  ), [data?.forecast]);
  const summary = data?.summary ?? {};
  const [isMobileChart, setIsMobileChart] = useState(() => (
    typeof window !== "undefined"
      ? window.matchMedia("(max-width: 767px)").matches
      : false
  ));
  const [manualBudgets, setManualBudgets] = useState(() => {
    try {
      return JSON.parse(
        localStorage.getItem("finance-dashboard-manual-budgets") || "{}"
      );
    } catch {
      return {};
    }
  });

  useEffect(() => {
    localStorage.setItem(
      "finance-dashboard-manual-budgets",
      JSON.stringify(manualBudgets)
    );
  }, [manualBudgets]);

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

  const budgetRows = useMemo(() => (
    forecast.map((item) => {
      const manualBudget = manualBudgets[item.category];

      return {
        ...item,
        effective_budget: autoBudget
          ? item.forecast_budget
          : Number(manualBudget ?? item.forecast_budget),
      };
    })
  ), [autoBudget, forecast, manualBudgets]);

  const chartData = useMemo(() => (
    maskChartRows(
      budgetRows,
      ["effective_budget", "current_spending"],
      privacyMode
    )
  ), [budgetRows, privacyMode]);

  const budgetSummary = useMemo(() => (
    budgetRows.reduce((summaryValues, item) => ({
      totalBudget: summaryValues.totalBudget + Number(item.effective_budget || 0),
      totalSpending: summaryValues.totalSpending + Number(item.current_spending || 0),
    }), {
      totalBudget: 0,
      totalSpending: 0,
    })
  ), [budgetRows]);

  const budgetRowsByCategory = useMemo(() => {
    const rowsByCategory = new Map();

    budgetRows.forEach((item) => {
      rowsByCategory.set(item.category, item);
    });

    return rowsByCategory;
  }, [budgetRows]);

  const activeAlerts = useMemo(() => (
    budgetRows.filter((item) => {
      if (!item.effective_budget) {
        return false;
      }

      return item.current_spending / item.effective_budget >= 0.85;
    })
  ), [budgetRows]);

  const alertRows = useMemo(() => (
    autoBudget
      ? alerts.map((alert) => {
          const budgetRow = budgetRowsByCategory.get(alert.category);

          return {
            ...alert,
            current_spending: alert.current_spending
              ?? budgetRow?.current_spending
              ?? 0,
            budget: alert.budget
              ?? alert.forecast_budget
              ?? budgetRow?.effective_budget
              ?? 0,
          };
        })
      : activeAlerts.map((item) => {
          const usageRate = item.effective_budget > 0
            ? item.current_spending / item.effective_budget * 100
            : 0;

          return {
            severity: usageRate >= 100 ? "high" : "medium",
            category: item.category,
            message: `${item.category} has used ${Math.round(usageRate)}% of the manual budget.`,
            usage_rate: usageRate,
            current_spending: item.current_spending,
            budget: item.effective_budget,
          };
        })
  ), [activeAlerts, alerts, autoBudget, budgetRowsByCategory]);

  const handleManualBudgetChange = useCallback((category, value) => {
    const numericValue = Number(String(value).replace(/\D/g, ""));

    setManualBudgets((current) => ({
      ...current,
      [category]: numericValue,
    }));
  }, []);

  const renderHeaderWithTooltip = (label, tooltip, align = "left") => (
    <span
      className={`
        group
        relative
        inline-flex
        items-center
        gap-1.5
        ${align === "right" ? "justify-end" : "justify-start"}
      `}
    >
      <span>{label}</span>
      <Info size={13} className="text-subtle" />
      <span
        className="
          pointer-events-none
          absolute
          top-full
          z-40
          mt-2
          hidden
          w-64
          rounded-lg
          border
          border-[var(--color-border)]
          bg-[var(--color-panel)]
          p-3
          text-left
          text-xs
          font-medium
          leading-5
          text-soft
          shadow-2xl
          group-hover:block
          group-focus-within:block
        "
      >
        {tooltip}
      </span>
    </span>
  );

  const renderUsageProgress = (usageRate) => {
    const cappedUsage = Math.min(Math.max(usageRate, 0), 100);
    const progressColor = usageRate >= 100
      ? "bg-red-500"
      : usageRate >= 85
        ? "bg-amber-400"
        : "bg-emerald-400";

    return (
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-[var(--color-panel-hover)]">
        <div
          className={`h-full rounded-full ${progressColor}`}
          style={{ width: `${cappedUsage}%` }}
        />
      </div>
    );
  };

  return (
    <div className="grid min-w-0 grid-cols-1 gap-5 sm:gap-6">
      <section className="panel rounded-2xl p-4 shadow-lg sm:p-5">
        <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-xl font-bold text-main">
              Budget Configuration Panel
            </h2>
            <p className="mt-1 text-sm text-muted">
              Historical average is used for local forecasting.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-2 rounded-xl border border-[var(--color-border)] p-1">
            <button
              type="button"
              onClick={() => onAutoBudgetChange(false)}
              className={`rounded-lg px-4 py-2 text-sm font-semibold ${
                !autoBudget
                  ? "bg-[var(--color-accent-strong)] text-white"
                  : "text-muted hover:text-accent"
              }`}
            >
              <SlidersHorizontal size={16} className="mr-2 inline" />
              Manual
            </button>

            <button
              type="button"
              onClick={() => onAutoBudgetChange(true)}
              className={`rounded-lg px-4 py-2 text-sm font-semibold ${
                autoBudget
                  ? "bg-[var(--color-accent-strong)] text-white"
                  : "text-muted hover:text-accent"
              }`}
            >
              <Bot size={16} className="mr-2 inline" />
              AI Auto
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 md:gap-4">
          <div className="rounded-xl border border-[var(--color-border)] p-4">
            <div className="mb-4 flex items-center justify-between">
              <p className="text-sm font-semibold text-muted">
                Forecast Budget
              </p>
              <Wallet size={20} className="text-accent" />
            </div>
            <p className="break-words text-[clamp(1.25rem,6vw,1.5rem)] font-bold text-main">
              {formatPrivateRupiah(
                budgetSummary.totalBudget || summary.total_forecast,
                privacyMode
              )}
            </p>
          </div>

          <div className="rounded-xl border border-[var(--color-border)] p-4">
            <div className="mb-4 flex items-center justify-between">
              <p className="text-sm font-semibold text-muted">
                Current Spending
              </p>
              <SlidersHorizontal size={20} className="text-orange-400" />
            </div>
            <p className="break-words text-[clamp(1.25rem,6vw,1.5rem)] font-bold text-main">
              {formatPrivateRupiah(
                budgetSummary.totalSpending || summary.current_spending,
                privacyMode
              )}
            </p>
          </div>

          <div className="rounded-xl border border-orange-400/40 bg-orange-500/10 p-4 sm:col-span-2 md:col-span-1">
            <div className="mb-4 flex items-center justify-between">
              <p className="text-sm font-semibold text-muted">
                Active Alerts
              </p>
              <BellRing size={20} className="text-amber-400" />
            </div>
            <p className="text-[clamp(1.5rem,7vw,1.875rem)] font-bold text-main">
              {activeAlerts.length || summary.alert_count || 0}
            </p>
          </div>
        </div>

        <div className="mt-6">
          <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h3 className="text-base font-bold text-main">
                Manual Budget Editor
              </h3>
              <p className="text-sm text-muted">
                {autoBudget
                  ? "Switch to Manual to edit the budget amount per category."
                  : "Edit the budget per category; alerts and charts will follow the manual amount."}
              </p>
            </div>
          </div>

          <div className="hidden overflow-x-auto md:block">
            <table className="w-full min-w-[720px] text-sm">
              <thead>
                <tr className="table-border text-muted">
                  <th className="py-3 text-left">
                    {renderHeaderWithTooltip(
                      "Category",
                      "Transaction category used to group expenses, for example Grocery, Makanan, Tagihan, or Transportasi."
                    )}
                  </th>
                  <th className="py-3 text-right">
                    {renderHeaderWithTooltip(
                      "Historical Suggestion",
                      "Budget suggestion from the historical average per category. The system uses all months before the active period; if no previous month exists, it uses the available month data.",
                      "right"
                    )}
                  </th>
                  <th className="py-3 text-right">
                    {renderHeaderWithTooltip(
                      "Manual Budget",
                      "Budget amount you can edit when Manual mode is active. This value is stored in the browser and used to calculate alerts and charts.",
                      "right"
                    )}
                  </th>
                  <th className="py-3 text-right">
                    {renderHeaderWithTooltip(
                      "Current Spending",
                      "Actual total expenses for the currently selected year and month filter period.",
                      "right"
                    )}
                  </th>
                  <th className="py-3 text-right">
                    {renderHeaderWithTooltip(
                      "Usage",
                      "Budget usage percentage: Current Spending divided by the active budget. Amber means near the limit, red means over budget.",
                      "right"
                    )}
                  </th>
                </tr>
              </thead>

              <tbody>
                {budgetRows.map((item) => {
                  const usageRate = item.effective_budget > 0
                    ? item.current_spending / item.effective_budget * 100
                    : 0;

                  return (
                    <tr key={item.category} className="table-row table-border">
                      <td className="py-3 font-semibold text-main">
                        {item.category}
                      </td>

                      <td className="py-3 text-right text-soft">
                        {formatPrivateRupiah(item.forecast_budget, privacyMode)}
                      </td>

                      <td className="py-3 text-right">
                        <input
                          value={Number(
                            manualBudgets[item.category]
                            ?? item.forecast_budget
                            ?? 0
                          ).toLocaleString("id-ID")}
                          onChange={(event) => (
                            handleManualBudgetChange(
                              item.category,
                              event.target.value
                            )
                          )}
                          disabled={autoBudget}
                          className="form-control ml-auto w-40 rounded-lg px-3 py-2 text-right disabled:cursor-not-allowed disabled:opacity-60"
                          inputMode="numeric"
                          aria-label={`Manual budget ${item.category}`}
                        />
                      </td>

                      <td className="py-3 text-right text-soft">
                        {formatPrivateRupiah(item.current_spending, privacyMode)}
                      </td>

                      <td className={`py-3 text-right font-semibold ${
                        usageRate >= 100
                          ? "text-red-400"
                          : usageRate >= 85
                            ? "text-amber-400"
                            : "text-emerald-400"
                      }`}>
                        {usageRate.toFixed(1)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="grid grid-cols-1 gap-3 md:hidden">
            {budgetRows.map((item) => {
              const usageRate = item.effective_budget > 0
                ? item.current_spending / item.effective_budget * 100
                : 0;

              return (
                <div
                  key={item.category}
                  className="rounded-xl border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-4"
                >
                  <div className="mb-4 flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="break-words text-base font-bold text-main">
                        {item.category}
                      </p>
                      <p className="mt-1 text-xs text-muted">
                        Historical: {formatPrivateRupiah(item.forecast_budget, privacyMode)}
                      </p>
                    </div>

                    <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-bold ${
                      usageRate >= 100
                        ? "bg-red-500/15 text-red-300"
                        : usageRate >= 85
                          ? "bg-amber-500/15 text-amber-300"
                          : "bg-emerald-500/15 text-emerald-300"
                    }`}>
                      {usageRate.toFixed(1)}%
                    </span>
                  </div>

                  <label className="block text-xs font-semibold uppercase text-muted">
                    Manual Budget
                  </label>
                  <input
                    value={Number(
                      manualBudgets[item.category]
                      ?? item.forecast_budget
                      ?? 0
                    ).toLocaleString("id-ID")}
                    onChange={(event) => (
                      handleManualBudgetChange(
                        item.category,
                        event.target.value
                      )
                    )}
                    disabled={autoBudget}
                    className="form-control mt-2 w-full rounded-xl px-4 py-3 text-right text-base font-semibold disabled:cursor-not-allowed disabled:opacity-60"
                    inputMode="numeric"
                    aria-label={`Manual budget ${item.category}`}
                  />

                  <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-xs text-muted">
                        Current Spending
                      </p>
                      <p className="mt-1 break-words font-semibold text-main">
                        {formatPrivateRupiah(item.current_spending, privacyMode)}
                      </p>
                    </div>

                    <div className="text-right">
                      <p className="text-xs text-muted">
                        Usage
                      </p>
                      <p className={`mt-1 font-semibold ${
                        usageRate >= 100
                          ? "text-red-400"
                          : usageRate >= 85
                            ? "text-amber-400"
                            : "text-emerald-400"
                      }`}>
                        {usageRate.toFixed(1)}%
                      </p>
                    </div>
                  </div>

                  {renderUsageProgress(usageRate)}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="panel rounded-2xl p-4 shadow-lg sm:p-5">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-xl font-bold text-main">
            Live Smart Alert Stream
          </h2>
          <BellRing size={22} className="text-amber-400" />
        </div>

        <div className="space-y-3">
          {alertRows.length === 0 && (
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-300">
              All categories are still within the safe limit.
            </div>
          )}

          {alertRows.map((alert) => {
            const remaining = Number(alert.budget || 0)
              - Number(alert.current_spending || 0);

            return (
            <div
              key={`${alert.category}-${alert.usage_rate}`}
              className={`group relative rounded-xl border p-4 text-sm ${
                alert.severity === "high"
                  ? "border-red-500/35 bg-red-500/10 text-red-300"
                  : "border-amber-500/35 bg-amber-500/10 text-amber-300"
              }`}
            >
              <div className="flex items-start gap-3">
                <AlertTriangle size={18} className="mt-0.5 shrink-0" />
                <div>
                  <p className="font-semibold">
                    {alert.message}
                  </p>
                  <p className="mt-1 opacity-80">
                    Usage rate {Number(alert.usage_rate || 0).toFixed(1)}%
                  </p>
                </div>
              </div>

              <div className="pointer-events-none absolute right-0 top-full z-40 mt-2 hidden w-[min(18rem,calc(100vw-32px))] rounded-xl border border-[var(--color-border)] bg-[var(--color-panel)] p-4 text-left text-xs text-soft shadow-2xl group-hover:block sm:right-4">
                <p className="mb-3 font-bold text-main">
                  {alert.category}
                </p>

                <div className="space-y-2">
                  <div className="flex justify-between gap-4">
                    <span>Current spending</span>
                    <span className="font-semibold text-main">
                      {formatPrivateRupiah(alert.current_spending, privacyMode)}
                    </span>
                  </div>

                  <div className="flex justify-between gap-4">
                    <span>Active budget</span>
                    <span className="font-semibold text-main">
                      {formatPrivateRupiah(alert.budget, privacyMode)}
                    </span>
                  </div>

                  <div className="flex justify-between gap-4 border-t border-[var(--color-border)] pt-2">
                    <span>{remaining >= 0 ? "Remaining budget" : "Over budget"}</span>
                    <span className={`font-semibold ${
                      remaining >= 0 ? "text-emerald-400" : "text-red-400"
                    }`}>
                      {formatPrivateRupiah(Math.abs(remaining), privacyMode)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          );
          })}
        </div>
      </section>

      <section className="panel rounded-2xl p-4 shadow-lg sm:p-5">
        <div className="mb-6">
          <h2 className="text-xl font-bold text-main">
            Next Month Budget Forecast
          </h2>
          <p className="mt-1 text-sm text-muted">
            Method: {data?.method ?? "historical_average"}
          </p>
        </div>

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
                  backgroundColor: theme === "light" ? "#ffffff" : "#0f172a",
                  border: "1px solid var(--color-border)",
                  borderRadius: "12px",
                  color: "var(--color-text)",
                }}
              />
              <Bar
                dataKey="effective_budget"
                name={autoBudget ? "AI Forecast Budget" : "Manual Budget"}
                fill="#06b6d4"
                radius={isMobileChart ? [0, 6, 6, 0] : [6, 6, 0, 0]}
              />
              <Bar
                dataKey="current_spending"
                name="Current Spending"
                fill="#f59e0b"
                radius={isMobileChart ? [0, 6, 6, 0] : [6, 6, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
};

export default BudgetingAlerts;
