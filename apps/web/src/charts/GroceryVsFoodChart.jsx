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
    <div className="panel rounded-lg p-6">

      <h2 className="text-xl font-bold mb-4 text-main">
        Grocery vs Food
      </h2>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>

          <XAxis dataKey="Bulan" />
          <YAxis />
          <Tooltip />
          <Legend />

          <Bar dataKey="Grocery" fill="#4A5D4E" stackId="a" />
          <Bar dataKey="Makanan" fill="#F4D35E" stackId="a" />

        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default GroceryVsFoodChart;
