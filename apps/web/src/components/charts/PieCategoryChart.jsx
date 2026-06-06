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
    <div className="panel rounded-lg p-4 shadow-lg sm:p-5">

      <h2 className="text-xl font-bold text-main mb-6">
        Spending by Category
      </h2>

      {!hasData ? (
        <div className="flex h-[320px] items-center justify-center rounded-xl border border-dashed border-[var(--color-border)] px-4 text-center text-sm text-muted">
          No expense categories available for this period.
        </div>
      ) : (
        <div className="h-[340px] min-w-0 sm:h-[360px]">

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
                maxWidth: "min(260px, calc(100vw - 32px))",
              }}
              wrapperStyle={{ zIndex: 20 }}
            />

            <Legend
              wrapperStyle={{
                color: colors.legendText,
                fontSize: 12,
                lineHeight: "18px",
              }}
            />

          </PieChart>

        </ResponsiveContainer>

        </div>
      )}

    </div>
  );
};

export default PieCategoryChart;
