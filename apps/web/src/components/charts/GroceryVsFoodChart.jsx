import {
  ResponsiveContainer,
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
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
    legendText: "#cbd5e1",
  },
  light: {
    grid: "#dbe4ef",
    tick: "#64748b",
    tooltipBg: "#ffffff",
    tooltipBorder: "#cbd5e1",
    tooltipText: "#0f172a",
    legendText: "#475569",
  },
};

const CustomTooltip = ({
  active,
  payload,
  label,
  colors,
  privacyMode,
}) => {
  if (!active || !payload?.length) {
    return null;
  }

  const total = payload.reduce((sum, item) => (
    sum + Number(item.value || 0)
  ), 0);

  return (
    <div
      style={{
        backgroundColor: colors.tooltipBg,
        border: `1px solid ${colors.tooltipBorder}`,
        borderRadius: "12px",
        color: colors.tooltipText,
        padding: "12px",
      }}
    >
      <p className="mb-2 text-sm font-semibold">
        {label}
      </p>

      {payload.map((item) => (
        <div
          key={item.dataKey}
          className="mb-1 flex items-center justify-between gap-6 text-sm"
        >
          <span style={{ color: item.color }}>
            {item.name}
          </span>
          <span>
            {formatPrivateRupiah(item.value, privacyMode)}
          </span>
        </div>
      ))}

      <div
        style={{ borderTop: `1px solid ${colors.tooltipBorder}` }}
        className="mt-2 pt-2 flex items-center justify-between gap-6 text-sm font-semibold"
      >
        <span>Total</span>
        <span>{formatPrivateRupiah(total, privacyMode)}</span>
      </div>
    </div>
  );
};

const GroceryVsFoodChart = ({ data = [], theme = "dark", privacyMode }) => {
  const colors = chartTheme[theme] || chartTheme.dark;
  const chartData = maskChartRows(data, ["Grocery", "Makanan"], privacyMode);
  const hasData = chartData.some((row) => (
    Number(row.Grocery || 0) > 0 || Number(row.Makanan || 0) > 0
  ));

  return (
    <div className="panel rounded-2xl p-5 shadow-lg">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-main">
          Grocery vs Food
        </h2>

        <div className="text-xs text-muted">
          {data.length} months
        </div>
      </div>

      {!hasData ? (
        <div className="flex h-[360px] items-center justify-center rounded-xl border border-dashed border-[var(--color-border)] px-4 text-center text-sm text-muted">
          No grocery or food expenses available for this period.
        </div>
      ) : (
        <div className="h-[360px] min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            margin={{ top: 8, right: 16, bottom: 8, left: 8 }}
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
              content={(
                <CustomTooltip
                  colors={colors}
                  privacyMode={privacyMode}
                />
              )}
            />

            <Legend wrapperStyle={{ color: colors.legendText }} />

            <Bar
              dataKey="Grocery"
              fill="#14b8a6"
              radius={[6, 6, 0, 0]}
            />

            <Bar
              dataKey="Makanan"
              name="Food"
              fill="#f59e0b"
              radius={[6, 6, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

export default GroceryVsFoodChart;
