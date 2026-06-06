import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

import {
  formatPrivateRupiah,
  maskChartRows,
  maskNumber,
} from "../../utils/privacy";
import { chartTheme } from "../../theme/chartTheme";

const MonthlyChart = ({
  title,
  data = [],
  dataKey = "total",
  theme = "dark",
  privacyMode,
}) => {
  const colors = chartTheme[theme] || chartTheme.dark;
  const chartData = maskChartRows(data, [dataKey], privacyMode);
  const hasData = chartData.some((row) => Number(row[dataKey] || 0) > 0);

  return (
    <div className="panel rounded-lg p-4 shadow-lg sm:p-5">

      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <h2 className="text-xl font-bold text-main">
          {title}
        </h2>

        <div className="text-xs text-muted">
          {data.length} months
        </div>
      </div>

      {!hasData ? (
        <div className="flex h-[320px] items-center justify-center rounded-xl border border-dashed border-[var(--color-border)] px-4 text-center text-sm text-muted">
          No synced transactions available for this period.
        </div>
      ) : (
        <div className="h-[320px] min-w-0 sm:h-[340px]">

        <ResponsiveContainer width="100%" height="100%">

          <LineChart
            data={chartData}
            margin={{ top: 8, right: 14, bottom: 8, left: 0 }}
          >

            <CartesianGrid
              strokeDasharray="3 3"
              stroke={colors.grid}
            />

            <XAxis
              dataKey="bulan"
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
                maxWidth: "min(260px, calc(100vw - 32px))",
              }}
              wrapperStyle={{ zIndex: 20 }}
              formatter={(value) => formatPrivateRupiah(value, privacyMode)}
            />

            <Line
              type="monotone"
              dataKey={dataKey}
              stroke={title.includes("Saving") ? colors.secondary : colors.primary}
              strokeWidth={3}
              dot={{
                r: 4,
                fill: title.includes("Saving") ? colors.secondary : colors.primary,
                stroke: colors.tooltipBg,
                strokeWidth: 2,
              }}
              activeDot={{
                r: 7,
                fill: title.includes("Saving") ? colors.secondary : colors.primary,
              }}
            />

          </LineChart>

        </ResponsiveContainer>

        </div>
      )}

    </div>
  );
};

export default MonthlyChart;
