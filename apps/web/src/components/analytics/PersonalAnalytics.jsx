import {
  DollarSign,
  Minus,
  PiggyBank,
  TrendingDown,
  TrendingUp,
  Users,
} from "lucide-react";
import { useEffect, useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  formatPrivateCompact,
  formatPrivateRupiah,
  maskChartRows,
  maskNumber,
} from "../../utils/privacy";
import { categoricalChartColors } from "../../theme/chartTheme";

const fallbackKpi = {
  income: 0,
  spending: 0,
  saving: 0,
  saving_rate: 0,
};

const fallbackUsers = [{ label: "All Data", value: "all" }];

const getUserDisplayLabel = (user) => (
  user?.value === "all" ? "All Data" : user?.label
);

const formatTrendValue = (value, suffix = "%") => {
  const numericValue = Number(value);

  if (!Number.isFinite(numericValue)) {
    return "N/A";
  }

  const prefix = numericValue > 0 ? "+" : "";

  return `${prefix}${numericValue.toFixed(1)}${suffix}`;
};

const getTrendTone = (direction, isSpending = false) => {
  if (direction === "unavailable") {
    return "text-muted";
  }

  if (direction === "flat") {
    return "text-subtle";
  }

  const isHealthy = isSpending
    ? direction === "down"
    : direction === "up";

  return isHealthy ? "metric-positive" : "metric-negative";
};

const getComparisonLabel = (metricLabel, periodLabel) => (
  metricLabel === "no previous data"
    ? metricLabel
    : periodLabel || metricLabel || "vs last period"
);

const PerformanceKpiCard = ({
  title,
  value,
  icon: Icon,
  iconClassName,
  trendValue,
  trendDirection,
  trendLabel,
  trendSuffix = "%",
  isSpending = false,
}) => {
  const direction = trendDirection || "unavailable";
  const hasTrend = Number.isFinite(Number(trendValue));

  return (
    <div className="panel flex min-h-[178px] flex-col rounded-lg p-4 shadow-lg sm:p-5">
      <div className="mb-5 flex items-start justify-between gap-3">
        <p className="min-w-0 text-sm font-semibold text-muted">
          {title}
        </p>
        <div className={`shrink-0 rounded-lg p-3 ${iconClassName}`}>
          <Icon size={22} />
        </div>
      </div>

      <p className="max-w-full break-words text-[clamp(1.35rem,4vw,1.875rem)] font-bold leading-tight text-main tabular-nums">
        {value}
      </p>

      <div className="mt-auto flex flex-wrap items-center gap-x-2 gap-y-1 pt-4">
        <span
          className={`inline-flex items-center gap-1 text-sm font-bold ${getTrendTone(
            direction,
            isSpending
          )}`}
        >
          {direction === "up" && <TrendingUp size={15} strokeWidth={2.5} />}
          {direction === "down" && <TrendingDown size={15} strokeWidth={2.5} />}
          {direction !== "up" && direction !== "down" && (
            <Minus size={15} strokeWidth={2.5} />
          )}
          {hasTrend ? formatTrendValue(trendValue, trendSuffix) : "N/A"}
        </span>
        <span className="text-sm text-subtle">
          {trendLabel}
        </span>
      </div>
    </div>
  );
};

const PersonalAnalytics = ({
  data,
  selectedUser,
  onSelectedUserChange,
  privacyMode,
  variant = "full",
}) => {
  const users = useMemo(() => (
    data?.users ?? fallbackUsers
  ), [data?.users]);
  const comparisonData = data?.comparison ?? [];
  const topCategoryMap = useMemo(() => (
    data?.top_categories ?? {}
  ), [data?.top_categories]);

  useEffect(() => {
    if (!users.some((user) => user.value === selectedUser)) {
      onSelectedUserChange("all");
    }
  }, [onSelectedUserChange, selectedUser, users]);

  const kpis = data?.kpis?.[selectedUser] ?? fallbackKpi;
  const periodLabel = data?.comparison_period?.label || "vs last period";

  const topCategories = useMemo(() => (
    topCategoryMap[selectedUser] ?? []
  ), [selectedUser, topCategoryMap]);

  const comparisonUsers = users.filter((user) => user.value !== "all");
  const comparisonKeys = comparisonUsers.map((user) => user.value);
  const maskedComparisonData = maskChartRows(
    comparisonData,
    comparisonKeys,
    privacyMode
  );

  const maxCategoryTotal = Math.max(
    ...topCategories.map((item) => maskNumber(item.total, privacyMode)),
    1
  );

  const selectedUserLabel = users.find((user) => (
    user.value === selectedUser
  ));

  const renderTopCategoryBreakdown = () => (
    <div className="panel rounded-lg p-5 shadow-lg">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-main">
          Top Spending Category Breakdown
        </h2>
      </div>

      <div className="space-y-5">
        {topCategories.length === 0 && (
          <div className="flex h-28 items-center justify-center text-muted">
            No spending category data available
          </div>
        )}

        {topCategories.map((item, index) => {
          const maskedTotal = maskNumber(item.total, privacyMode);
          const percentage = maskedTotal / maxCategoryTotal * 100;

          return (
            <div key={item.category}>
              <div className="mb-2 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--color-accent-bg)] text-sm font-bold text-accent">
                    {index + 1}
                  </span>
                  <p className="font-semibold text-main">
                    {item.category}
                  </p>
                </div>
                <p className="text-sm font-semibold text-soft">
                  {formatPrivateRupiah(item.total, privacyMode)}
                </p>
              </div>

              <div className="h-3 overflow-hidden rounded-full bg-[var(--color-panel-hover)]">
                <div
                  className="h-full rounded-full bg-[var(--color-accent-strong)]"
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  if (variant === "breakdown") {
    return renderTopCategoryBreakdown();
  }

  return (
    <section className="grid grid-cols-1 gap-6">
      <div className="panel rounded-lg p-5 shadow-lg">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex min-w-0 flex-col">
            <h2 className="text-xl font-bold text-main">
              Personal Finance Performance
            </h2>
            <p className="mt-1 truncate text-sm text-muted">
              {getUserDisplayLabel(selectedUserLabel)}
            </p>
          </div>

          <div className="flex max-w-full shrink-0 flex-row flex-nowrap items-center gap-2 overflow-x-auto rounded-xl border border-[var(--color-border)] p-1">
            {users.map((user) => {
              const isActive = selectedUser === user.value;

              return (
                <button
                  key={user.value}
                  type="button"
                  onClick={() => onSelectedUserChange(user.value)}
                  className={`
                    rounded-lg
                    px-4
                    py-2
                    text-sm
                    font-semibold
                    whitespace-nowrap
                    flex-none
                    transition-colors
                    ${isActive
                      ? "bg-[var(--color-accent-strong)] text-white"
                      : "text-muted hover:text-accent"}
                  `}
                >
                  {getUserDisplayLabel(user)}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 2xl:grid-cols-4">
        <PerformanceKpiCard
          title="Total Income"
          value={formatPrivateRupiah(kpis.income, privacyMode)}
          icon={DollarSign}
          iconClassName="bg-[var(--color-accent-bg)] text-accent"
          trendValue={kpis.income_change_pct}
          trendDirection={kpis.income_trend}
          trendLabel={getComparisonLabel(
            kpis.income_comparison_label,
            periodLabel
          )}
        />

        <PerformanceKpiCard
          title="Total Spending"
          value={formatPrivateRupiah(kpis.spending, privacyMode)}
          icon={TrendingDown}
          iconClassName="bg-[var(--color-alert-bg)] text-[var(--color-alert-text)]"
          trendValue={kpis.spending_change_pct}
          trendDirection={kpis.spending_trend}
          trendLabel={getComparisonLabel(
            kpis.spending_comparison_label,
            periodLabel
          )}
          isSpending
        />

        <PerformanceKpiCard
          title="Total Saving"
          value={formatPrivateRupiah(kpis.saving, privacyMode)}
          icon={PiggyBank}
          iconClassName="bg-[var(--color-accent-bg)] text-accent"
          trendValue={kpis.saving_change_pct}
          trendDirection={kpis.saving_trend}
          trendLabel={getComparisonLabel(
            kpis.saving_comparison_label,
            periodLabel
          )}
        />

      </div>

      {variant === "full" && selectedUser === "all" && (
        <div className="panel rounded-lg p-5 shadow-lg">
          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-xl font-bold text-main">
              Monthly Spending Contribution
            </h2>
            <div className="icon-badge rounded-xl p-3">
              <Users size={22} />
            </div>
          </div>

          <div className="h-[360px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={maskedComparisonData}>
                <CartesianGrid
                  stroke="var(--color-border)"
                  strokeDasharray="3 3"
                />
                <XAxis
                  dataKey="month"
                  stroke="var(--color-muted)"
                  tick={{ fill: "var(--color-muted)", fontSize: 12 }}
                />
                <YAxis
                  stroke="var(--color-muted)"
                  tick={{ fill: "var(--color-muted)", fontSize: 12 }}
                  tickFormatter={(value) => formatPrivateCompact(value, privacyMode)}
                />
                <Tooltip
                  formatter={(value) => formatPrivateRupiah(value, privacyMode)}
                  contentStyle={{
                    backgroundColor: "var(--color-panel)",
                    border: "1px solid var(--color-border)",
                    borderRadius: "12px",
                    color: "var(--color-text)",
                  }}
                />
                <Legend />
                {comparisonUsers.map((user, index) => (
                  <Bar
                    key={user.value}
                    dataKey={user.value}
                    fill={categoricalChartColors[index % categoricalChartColors.length]}
                    radius={[6, 6, 0, 0]}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {variant === "full" && renderTopCategoryBreakdown()}
    </section>
  );
};

export default PersonalAnalytics;
