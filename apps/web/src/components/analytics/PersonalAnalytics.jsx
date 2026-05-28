import {
  DollarSign,
  PiggyBank,
  TrendingDown,
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

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="panel rounded-lg p-5 shadow-lg">
          <div className="mb-6 flex items-center justify-between">
            <p className="text-sm font-semibold text-muted">
              Total Income
            </p>
            <div className="rounded-lg bg-[var(--color-accent-bg)] p-3 text-accent">
              <DollarSign size={22} />
            </div>
          </div>
          <p className="text-3xl font-bold text-main">
            {formatPrivateRupiah(kpis.income, privacyMode)}
          </p>
        </div>

        <div className="panel rounded-lg p-5 shadow-lg">
          <div className="mb-6 flex items-center justify-between">
            <p className="text-sm font-semibold text-muted">
              Total Spending
            </p>
            <div className="rounded-lg bg-[var(--color-alert-bg)] p-3 text-[var(--color-alert-text)]">
              <TrendingDown size={22} />
            </div>
          </div>
          <p className="text-3xl font-bold text-main">
            {formatPrivateRupiah(kpis.spending, privacyMode)}
          </p>
        </div>

        <div className="panel rounded-lg p-5 shadow-lg">
          <div className="mb-6 flex items-center justify-between">
            <p className="text-sm font-semibold text-muted">
              Total Saving
            </p>
            <div className="rounded-lg bg-[var(--color-accent-bg)] p-3 text-accent">
              <PiggyBank size={22} />
            </div>
          </div>
          <p className="text-3xl font-bold text-main">
            {formatPrivateRupiah(kpis.saving, privacyMode)}
          </p>
          <p className="mt-2 text-sm font-semibold metric-positive">
            {Number(kpis.saving_rate || 0).toFixed(1)}% Saving Rate
          </p>
        </div>
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
