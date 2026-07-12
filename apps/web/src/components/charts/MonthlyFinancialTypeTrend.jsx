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
  formatPrivateCompact,
  formatPrivateRupiah,
  maskChartRows,
} from "../../utils/privacy";
import { chartTheme, financialTypeChartColors } from "../../theme/chartTheme";

const series = [
  { key: "need", label: "Need", color: financialTypeChartColors.need },
  { key: "want", label: "Want", color: financialTypeChartColors.want },
  { key: "saving", label: "Saving", color: financialTypeChartColors.saving },
  { key: "income", label: "Income", color: financialTypeChartColors.income },
  { key: "uncategorized", label: "Uncategorized", color: financialTypeChartColors.uncategorized },
];

const monthLabels = [
  "",
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
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
      monthLabel: monthLabels[Number(row.month)] || `M${row.month}`,
    })),
    series.map((item) => item.key),
    privacyMode
  );
  const hasData = chartData.some((row) => (
    series.some((item) => Number(row[item.key] || 0) > 0)
  ));

  return (
    <div className="panel rounded-lg p-4 shadow-lg sm:p-5">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
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
        <div className="h-[360px] min-w-0 sm:h-[380px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 8, right: 14, bottom: 28, left: 0 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke={colors.grid}
              />

              <XAxis
                dataKey="monthLabel"
                stroke={colors.tick}
                interval="preserveStartEnd"
                minTickGap={8}
                tick={{ fill: colors.tick, fontSize: 11 }}
              />

              <YAxis
                stroke={colors.tick}
                tick={{ fill: colors.tick, fontSize: 12 }}
                tickFormatter={(value) => formatPrivateCompact(value, privacyMode)}
              />

              <Tooltip
                contentStyle={{
                  backgroundColor: colors.tooltipBg,
                  border: `1px solid ${colors.tooltipBorder}`,
                  borderRadius: "12px",
                  color: colors.tooltipText,
                  maxWidth: "min(280px, calc(100vw - 32px))",
                }}
                wrapperStyle={{ zIndex: 20 }}
                formatter={(value) => formatPrivateRupiah(value, privacyMode)}
              />

              <Legend
                verticalAlign="bottom"
                height={30}
                wrapperStyle={{
                  color: colors.legendText,
                  fontSize: 12,
                  lineHeight: "18px",
                }}
              />

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
