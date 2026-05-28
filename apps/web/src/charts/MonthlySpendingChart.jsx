import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from "recharts";

function MonthlySpendingChart({ data }) {
  return (
    <div className="panel rounded-lg p-6">
      <h2 className="text-xl font-bold mb-4 text-main">
        Monthly Spending
      </h2>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" />
          <XAxis dataKey="Bulan" stroke="var(--color-muted)" />
          <YAxis stroke="var(--color-muted)" />
          <Tooltip />

          <Bar
            dataKey="Harga"
            fill="#002B45"
            radius={[10, 10, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default MonthlySpendingChart;
