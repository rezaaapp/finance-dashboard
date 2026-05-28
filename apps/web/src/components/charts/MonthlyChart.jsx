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
  data,
  dataKey = "total",
  theme = "dark",
  privacyMode,
}) => {
  const colors = chartTheme[theme] || chartTheme.dark;
  const chartData = maskChartRows(data, [dataKey], privacyMode);

  return (
    <div className="panel rounded-lg p-5 shadow-lg">

      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-main">
          {title}
        </h2>

        <div className="text-xs text-muted">
          {data.length} months
        </div>
      </div>

      <div className="h-[320px]">

        <ResponsiveContainer width="100%" height="100%">

          <LineChart data={chartData}>

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
              }}
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

    </div>
  );
};

export default MonthlyChart;
