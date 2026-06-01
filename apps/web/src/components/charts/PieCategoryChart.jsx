import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

import {
  formatPrivateRupiah,
  maskChartRows,
} from "../../utils/privacy";
import { categoricalChartColors, chartTheme } from "../../theme/chartTheme";

const PieCategoryChart = ({ data = [], theme = "dark", privacyMode }) => {
  const colors = chartTheme[theme] || chartTheme.dark;
  const chartData = maskChartRows(data, ["Harga"], privacyMode);
  const hasData = chartData.some((row) => Number(row.Harga || 0) > 0);

  return (
    <div className="panel rounded-lg p-5 shadow-lg">

      <h2 className="text-xl font-bold text-main mb-6">
        Spending by Category
      </h2>

      {!hasData ? (
        <div className="flex h-[320px] items-center justify-center rounded-xl border border-dashed border-[var(--color-border)] px-4 text-center text-sm text-muted">
          No expense categories available for this period.
        </div>
      ) : (
        <div className="h-[320px] min-w-0">

        <ResponsiveContainer width="100%" height="100%">

          <PieChart>

            <Pie
              data={chartData}
              dataKey="Harga"
              nameKey="Kategori"
              cx="50%"
              cy="50%"
              innerRadius={70}
              outerRadius={110}
              paddingAngle={3}
            >
              {chartData.map((entry, index) => (
                <Cell
                  key={index}
                  fill={categoricalChartColors[index % categoricalChartColors.length]}
                />
              ))}
            </Pie>

            <Tooltip
              formatter={(value) => formatPrivateRupiah(value, privacyMode)}
              contentStyle={{
                backgroundColor: colors.tooltipBg,
                border: `1px solid ${colors.tooltipBorder}`,
                borderRadius: "12px",
                color: colors.tooltipText,
              }}
            />

            <Legend wrapperStyle={{ color: colors.legendText }} />

          </PieChart>

        </ResponsiveContainer>

        </div>
      )}

    </div>
  );
};

export default PieCategoryChart;
