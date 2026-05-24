import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend
} from "recharts";

function GroceryVsFoodChart({ data }) {
  return (
    <div className="bg-slate-800 p-6 rounded-2xl">

      <h2 className="text-xl font-bold mb-4">
        Grocery vs Food
      </h2>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>

          <XAxis dataKey="Bulan" />
          <YAxis />
          <Tooltip />
          <Legend />

          <Bar dataKey="Grocery" stackId="a" />
          <Bar dataKey="Makanan" stackId="a" />

        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default GroceryVsFoodChart;