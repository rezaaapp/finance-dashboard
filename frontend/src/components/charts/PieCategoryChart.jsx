import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

const COLORS = [
  "#06b6d4",
  "#3b82f6",
  "#8b5cf6",
  "#14b8a6",
  "#22c55e",
  "#f59e0b",
  "#ef4444",
  "#ec4899",
];

const formatRupiah = (value) => {
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    maximumFractionDigits: 0,
  }).format(value);
};

const chartTheme = {
  dark: {
    tooltipBg: "#0f172a",
    tooltipBorder: "#334155",
    tooltipText: "#f8fafc",
    legendText: "#cbd5e1",
  },
  light: {
    tooltipBg: "#ffffff",
    tooltipBorder: "#cbd5e1",
    tooltipText: "#0f172a",
    legendText: "#475569",
  },
};

const PieCategoryChart = ({ data, theme = "dark" }) => {
  const colors = chartTheme[theme] || chartTheme.dark;

  return (
    <div className="panel rounded-2xl p-5 shadow-lg">

      <h2 className="text-xl font-bold text-main mb-6">
        Spending by Category
      </h2>

      <div className="h-[320px]">

        <ResponsiveContainer width="100%" height="100%">

          <PieChart>

            <Pie
              data={data}
              dataKey="Harga"
              nameKey="Kategori"
              cx="50%"
              cy="50%"
              innerRadius={70}
              outerRadius={110}
              paddingAngle={3}
            >
              {data.map((entry, index) => (
                <Cell
                  key={index}
                  fill={COLORS[index % COLORS.length]}
                />
              ))}
            </Pie>

            <Tooltip
              formatter={(value) => formatRupiah(value)}
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

    </div>
  );
};

export default PieCategoryChart;
