import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
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

const typeLabels = {
  need: "Need",
  want: "Want",
  saving: "Saving",
  income: "Income",
  uncategorized: "Uncategorized",
};

const FinancialTypeChart = ({
  data = [],
  theme = "dark",
  privacyMode,
}) => {
  const colors = chartTheme[theme] || chartTheme.dark;
  const chartData = maskChartRows(
    data.map((row) => ({
      ...row,
      label: typeLabels[row.type] || row.type,
    })),
    ["amount"],
    privacyMode
  );
  const hasData = chartData.some((row) => Number(row.amount || 0) > 0);

  return (
    <div className="panel rounded-lg p-4 shadow-lg sm:p-5">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <h2 className="text-xl font-bold text-main">
          Financial Type Breakdown
        </h2>

        <div className="text-xs text-muted">
          {data.length} types
        </div>
      </div>

      {!hasData ? (
        <div className="flex h-[320px] items-center justify-center rounded-xl border border-dashed border-[var(--color-border)] px-4 text-center text-sm text-muted">
          No classified financial type data available for this period.
        </div>
      ) : (
        <div className="h-[340px] min-w-0 sm:h-[360px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              margin={{ top: 8, right: 14, bottom: 18, left: 0 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke={colors.grid}
              />

              <XAxis
                dataKey="label"
                stroke={colors.tick}
                interval={0}
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
                  maxWidth: "min(260px, calc(100vw - 32px))",
                }}
                wrapperStyle={{ zIndex: 20 }}
                formatter={(value, _name, item) => [
                  formatPrivateRupiah(value, privacyMode),
                  `${item?.payload?.count || 0} transactions`,
                ]}
                labelFormatter={(label) => label}
              />

              <Bar
                dataKey="amount"
                radius={[8, 8, 0, 0]}
              >
                {chartData.map((entry) => (
                  <Cell
                    key={entry.type}
                    fill={financialTypeChartColors[entry.type] || colors.primary}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

export default FinancialTypeChart;
