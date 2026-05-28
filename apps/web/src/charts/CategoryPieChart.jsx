import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer
} from "recharts";

const COLORS = [
  "#002B45",
  "#4A5D4E",
  "#F4D35E",
  "#7A8D82",
  "#335C67",
  "#A3ADB8",
];

function CategoryPieChart({ data }) {
  return (
    <div className="panel rounded-lg p-6">
      <h2 className="text-xl font-bold mb-4 text-main">
        Spending by Category
      </h2>

      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            dataKey="Harga"
            nameKey="Kategori"
            outerRadius={100}
            label
          >
            {data.map((entry, index) => (
              <Cell
                key={index}
                fill={COLORS[index % COLORS.length]}
              />
            ))}
          </Pie>

          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

export default CategoryPieChart;
