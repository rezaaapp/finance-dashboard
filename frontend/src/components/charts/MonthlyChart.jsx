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

const chartTheme = {
  dark: {
    grid: "#1e293b",
    tick: "#94a3b8",
    tooltipBg: "#0f172a",
    tooltipBorder: "#334155",
    tooltipText: "#f8fafc",
  },
  light: {
    grid: "#dbe4ef",
    tick: "#64748b",
    tooltipBg: "#ffffff",
    tooltipBorder: "#cbd5e1",
    tooltipText: "#0f172a",
  },
};

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
    <div className="panel rounded-2xl p-5 shadow-lg">

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
              stroke="#06b6d4"
              strokeWidth={3}
              dot={{ r: 4 }}
              activeDot={{ r: 7 }}
            />

          </LineChart>

        </ResponsiveContainer>

      </div>

    </div>
  );
};

export default MonthlyChart;
