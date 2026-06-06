import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  formatPrivateRupiah,
  maskChartRows,
  maskNumber,
} from "../../utils/privacy";
import { chartTheme } from "../../theme/chartTheme";

const series = [
  { key: "need", label: "Need", color: "#335C67" },
  { key: "want", label: "Want", color: "#D9895B" },
  { key: "saving", label: "Saving", color: "#4A5D4E" },
  { key: "income", label: "Income", color: "#2F80A7" },
  { key: "uncategorized", label: "Uncategorized", color: "#A3ADB8" },
];

const MonthlyFinancialTypeTrend = ({
  data = [],
  theme = "dark",
  privacyMode,
}) => {
  const colors = chartTheme[theme] || chartTheme.dark;
  const chartData = maskChartRows(
    data.map((row) => ({
      ...row,
      monthLabel: `M${row.month}`,
    })),
    series.map((item) => item.key),
    privacyMode
  );
  const hasData = chartData.some((row) => (
    series.some((item) => Number(row[item.key] || 0) > 0)
  ));

  return (
    <div className="panel rounded-lg p-5 shadow-lg">
      <div className="mb-6 flex items-center justify-between gap-3">
        <h2 className="text-xl font-bold text-main">
          Monthly Financial Type Trend
        </h2>

        <div className="text-xs text-muted">
          {data.length} months
        </div>
      </div>

      {!hasData ? (
        <div className="flex h-[320px] items-center justify-center rounded-xl border border-dashed border-[var(--color-border)] px-4 text-center text-sm text-muted">
          No monthly financial type trend available for this year.
        </div>
      ) : (
        <div className="h-[320px] min-w-0">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 8, right: 16, bottom: 8, left: 8 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke={colors.grid}
              />

              <XAxis
                dataKey="monthLabel"
                stroke={colors.tick}
                tick={{ fill: colors.tick, fontSize: 12 }}
              />

              <YAxis
                stroke={colors.tick}
                tick={{ fill: colors.tick, fontSize: 12 }}
                tickFormatter={(value) =>
                  `${(maskNumber(value, privacyMode) / 1000000).toFixed(0)}jt`
                }
              />

              <Tooltip
                contentStyle={{
                  backgroundColor: colors.tooltipBg,
                  border: `1px solid ${colors.tooltipBorder}`,
                  borderRadius: "12px",
                  color: colors.tooltipText,
                }}
                formatter={(value) => formatPrivateRupiah(value, privacyMode)}
              />

              <Legend wrapperStyle={{ color: colors.legendText }} />

              {series.map((item) => (
                <Line
                  key={item.key}
                  type="monotone"
                  dataKey={item.key}
                  name={item.label}
                  stroke={item.color}
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: item.color }}
                  activeDot={{ r: 6, fill: item.color }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

export default MonthlyFinancialTypeTrend;
