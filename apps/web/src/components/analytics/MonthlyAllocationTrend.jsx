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
} from "../../utils/privacy";
import { allocationChartColors, chartTheme } from "../../theme/chartTheme";

const allocationKeys = [
  { key: "Needs", color: allocationChartColors.Needs },
  { key: "Wants", color: allocationChartColors.Wants },
  { key: "Savings", color: allocationChartColors.Savings },
];

const formatMonthLabel = (month) => {
  const [year, monthNumber] = String(month || "").split("-");

  if (!year || !monthNumber) {
    return month;
  }

  return new Date(Number(year), Number(monthNumber) - 1, 1).toLocaleDateString(
    "en-US",
    {
      month: "short",
      year: "2-digit",
    }
  );
};

const enrichWithPercentages = (rows) => (
  rows.map((row) => {
    const total = allocationKeys.reduce(
      (sum, item) => sum + Number(row[item.key] || 0),
      0
    );
    const enrichedRow = {
      ...row,
      allocationTotal: total,
    };

    allocationKeys.forEach((item) => {
      enrichedRow[`${item.key}Percentage`] = total > 0
        ? Number(row[item.key] || 0) / total * 100
        : 0;
    });

    return enrichedRow;
  })
);

const AllocationTooltip = ({
  active,
  label,
  payload,
  privacyMode,
}) => {
  if (!active || !payload?.length) {
    return null;
  }

  const row = payload[0]?.payload ?? {};

  return (
    <div className="dialog-panel p-4 text-sm text-main">
      <p className="mb-3 font-bold">
        {formatMonthLabel(label)}
      </p>

      <div className="space-y-2">
        {allocationKeys.map((item) => {
          const value = row[item.key] || 0;
          const percentage = row[`${item.key}Percentage`] || 0;

          return (
            <div
              key={item.key}
              className="flex min-w-56 items-center justify-between gap-4"
            >
              <span className="flex items-center gap-2 text-muted">
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                {item.key}
              </span>
              <span className="text-right font-semibold">
                {formatPrivateRupiah(value, privacyMode)}
                <span className="ml-2 text-xs text-muted">
                  ({percentage.toFixed(1)}%)
                </span>
              </span>
            </div>
          );
        })}
      </div>

      <div className="mt-3 border-t border-[var(--color-border)] pt-3">
        <div className="flex justify-between gap-4 font-bold">
          <span>Total</span>
          <span>{formatPrivateRupiah(row.allocationTotal, privacyMode)}</span>
        </div>
      </div>
    </div>
  );
};

const MonthlyAllocationTrend = ({
  data = [],
  theme = "dark",
  privacyMode,
}) => {
  const colors = chartTheme[theme] || chartTheme.dark;
  const maskedRows = maskChartRows(
    data,
    allocationKeys.map((item) => item.key),
    privacyMode
  );
  const chartData = enrichWithPercentages(maskedRows);

  return (
    <section className="panel rounded-2xl p-5 shadow-lg">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-main">
          Pola alokasi bulanan
        </h2>
        <p className="mt-1 text-sm text-muted">
          Membandingkan kebutuhan, keinginan, dan simpanan dari data transaksi yang tersinkron.
        </p>
      </div>

      {chartData.length === 0 ? (
        <div className="empty-state-panel flex h-64 items-center justify-center text-sm">
          Belum ada data alokasi untuk periode ini.
        </div>
      ) : (
        <div className="h-[360px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid
                stroke={colors.grid}
                strokeDasharray="3 3"
              />
              <XAxis
                dataKey="month"
                tickFormatter={formatMonthLabel}
                stroke={colors.tick}
                tick={{ fill: colors.tick, fontSize: 12 }}
              />
              <YAxis
                stroke={colors.tick}
                tick={{ fill: colors.tick, fontSize: 12 }}
                tickFormatter={(value) => formatPrivateCompact(value, privacyMode)}
              />
              <Tooltip
                content={(props) => (
                  <AllocationTooltip
                    {...props}
                    privacyMode={privacyMode}
                  />
                )}
              />
              {allocationKeys.map((item) => (
                <Bar
                  key={item.key}
                  dataKey={item.key}
                  stackId="allocation"
                  fill={item.color}
                  name={item.key}
                  radius={item.key === "Savings" ? [6, 6, 0, 0] : [0, 0, 0, 0]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
};

export default MonthlyAllocationTrend;
