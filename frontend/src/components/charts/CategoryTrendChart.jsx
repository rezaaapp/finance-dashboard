import { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
} from "recharts";

const formatRupiah = (value) => {
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    maximumFractionDigits: 0,
  }).format(value || 0);
};

const formatCompactRupiah = (value) => {
  return new Intl.NumberFormat("id-ID", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value || 0);
};

const chartTheme = {
  dark: {
    grid: "#1e293b",
    tick: "#94a3b8",
    tooltipBg: "#0f172a",
    tooltipBorder: "#334155",
    tooltipText: "#f8fafc",
    average: "#f59e0b",
  },
  light: {
    grid: "#dbe4ef",
    tick: "#64748b",
    tooltipBg: "#ffffff",
    tooltipBorder: "#cbd5e1",
    tooltipText: "#0f172a",
    average: "#d97706",
  },
};

const CustomTooltip = ({
  active,
  payload,
  label,
  average,
  colors,
}) => {
  if (!active || !payload?.length) {
    return null;
  }

  const value = payload[0]?.value ?? 0;
  const difference = value - average;

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

      <div className="mb-1 flex items-center justify-between gap-6 text-sm">
        <span>Monthly Total</span>
        <span>{formatRupiah(value)}</span>
      </div>

      <div className="mb-1 flex items-center justify-between gap-6 text-sm">
        <span>Average</span>
        <span>{formatRupiah(average)}</span>
      </div>

      <div
        style={{ borderTop: `1px solid ${colors.tooltipBorder}` }}
        className="mt-2 pt-2 flex items-center justify-between gap-6 text-sm font-semibold"
      >
        <span>Vs Average</span>
        <span>
          {difference >= 0 ? "+" : ""}
          {formatRupiah(difference)}
        </span>
      </div>
    </div>
  );
};

const CategoryTrendChart = ({ data, theme = "dark" }) => {
  const colors = chartTheme[theme] || chartTheme.dark;
  const categories = useMemo(() => (
    data?.categories ?? []
  ), [data?.categories]);
  const [selectedCategory, setSelectedCategory] = useState("");

  useEffect(() => {
    if (
      categories.length > 0
      && !categories.some((category) => category.kategori === selectedCategory)
    ) {
      setSelectedCategory(categories[0].kategori);
    }
  }, [categories, selectedCategory]);

  const selectedData = useMemo(() => (
    categories.find((category) => category.kategori === selectedCategory)
  ), [categories, selectedCategory]);

  const chartData = selectedData?.values ?? [];
  const average = selectedData?.average ?? 0;

  return (
    <div className="panel rounded-2xl p-5 shadow-lg">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-main">
            Category Trend Analysis
          </h2>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="rounded-lg border border-[var(--color-border)] px-4 py-3 text-sm">
            <p className="text-muted text-xs mb-1">
              Average
            </p>
            <p className="font-semibold text-main">
              {formatRupiah(average)}
            </p>
          </div>

          <select
            value={selectedCategory}
            onChange={(event) => setSelectedCategory(event.target.value)}
            className="form-control px-4 py-2 rounded-xl"
          >
            {categories.map((category) => (
              <option
                key={category.kategori}
                value={category.kategori}
              >
                {category.kategori}
              </option>
            ))}
          </select>
        </div>
      </div>

      {chartData.length === 0 ? (
        <div className="flex h-56 items-center justify-center text-muted">
          No category trend data available
        </div>
      ) : (
        <div className="h-[360px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
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
                tickFormatter={(value) => formatCompactRupiah(value)}
              />

              <Tooltip
                content={(
                  <CustomTooltip
                    average={average}
                    colors={colors}
                  />
                )}
              />

              <ReferenceLine
                y={average}
                stroke={colors.average}
                strokeDasharray="6 6"
                label={{
                  value: `Avg ${formatCompactRupiah(average)}`,
                  fill: colors.average,
                  fontSize: 12,
                  position: "insideTopRight",
                }}
              />

              <Line
                type="monotone"
                dataKey="total"
                stroke="#06b6d4"
                strokeWidth={3}
                dot={{ r: 4 }}
                activeDot={{ r: 7 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

export default CategoryTrendChart;
