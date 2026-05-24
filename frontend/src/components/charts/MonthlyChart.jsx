import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";

import { formatRupiah } from "../../utils/currency";

const MonthlyChart = ({ title, data }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
      
      <h2 className="text-xl font-bold mb-6">
        {title}
      </h2>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>

          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />

          <XAxis dataKey="bulan" stroke="#94a3b8" />

          <YAxis
            stroke="#94a3b8"
            tickFormatter={(value) =>
              `${(value / 1000000).toFixed(0)}jt`
            }
          />

          <Tooltip
            formatter={(value) => formatRupiah(value)}
          />

          <Bar
            dataKey="total"
            fill="#06b6d4"
            radius={[10, 10, 0, 0]}
          />

        </BarChart>
      </ResponsiveContainer>

    </div>
  );
};

export default MonthlyChart;