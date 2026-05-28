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
    <div className="bg-slate-800 p-6 rounded-2xl">
      <h2 className="text-xl font-bold mb-4">
        Monthly Spending
      </h2>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="Bulan" />
          <YAxis />
          <Tooltip />

          <Bar
            dataKey="Harga"
            radius={[10, 10, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default MonthlySpendingChart;