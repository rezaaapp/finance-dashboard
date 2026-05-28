import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import {
  formatPrivateRupiah,
  maskChartRows,
} from "../../utils/privacy";
import { categoricalChartColors, chartTheme } from "../../theme/chartTheme";

const brandColors = {
  BCA: "#0066AE",
  BLU: "#00B4D8",
  Gopay: "#4A5D4E",
  Ovo: "#4C2A86",
  Seabank: "#FF5722",
  Jago: "#FFB800",
};

const fallbackColors = categoricalChartColors;

const normalizedBrandColors = Object.fromEntries(
  Object.entries(brandColors).map(([source, color]) => [
    source.trim().toLowerCase(),
    color,
  ])
);

const getSourceColor = (source, index) => {
  const normalizedSource = String(source || "").trim().toLowerCase();

  return normalizedBrandColors[normalizedSource]
    || fallbackColors[index % fallbackColors.length];
};

const chartSections = [
  {
    title: "Income Sources",
    key: "income_sources",
    accent: "text-accent",
  },
  {
    title: "Expense Methods",
    key: "spending_sources",
    accent: "text-[var(--color-alert-text)]",
  },
  {
    title: "Saving Allocations",
    key: "saving_sources",
    accent: "text-accent",
  },
];

const SourceDanaDonut = ({
  title,
  accent,
  rows = [],
  theme = "dark",
  privacyMode,
}) => {
  const colors = chartTheme[theme] || chartTheme.dark;
  const chartData = maskChartRows(rows, ["total"], privacyMode);
  const total = chartData.reduce((sum, row) => sum + Number(row.total || 0), 0);
  const sourceCounterText = `${rows.length} dynamic source${
    rows.length === 1 ? "" : "s"
  } detected`;

  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel)] p-5">
      <div className="mb-4">
        <h3 className={`text-base font-bold ${accent}`}>
          {title}
        </h3>

        <p className="text-muted mt-1 text-xs">
          {sourceCounterText}
        </p>
      </div>

      {chartData.length === 0 ? (
        <div className="flex h-[280px] items-center justify-center rounded-xl border border-dashed border-[var(--color-border)] text-sm text-muted">
          No Source Dana data available.
        </div>
      ) : (
        <div className="h-[280px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                dataKey="total"
                nameKey="source"
                cx="50%"
                cy="45%"
                innerRadius="48%"
                outerRadius="72%"
                paddingAngle={3}
              >
                {chartData.map((entry, index) => (
                  <Cell
                    key={entry.source}
                    fill={getSourceColor(entry.source, index)}
                  />
                ))}
              </Pie>

              <Tooltip
                formatter={(value, name) => [
                  formatPrivateRupiah(value, privacyMode),
                  name,
                ]}
                contentStyle={{
                  backgroundColor: colors.tooltipBg,
                  border: `1px solid ${colors.tooltipBorder}`,
                  borderRadius: "12px",
                  color: colors.tooltipText,
                }}
              />

              <Legend
                iconType="circle"
                wrapperStyle={{
                  color: colors.legendText,
                  fontSize: "12px",
                  lineHeight: "18px",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="mt-4 rounded-xl bg-[var(--color-panel-hover)] px-4 py-3">
        <p className="text-muted text-xs font-semibold uppercase tracking-wide">
          Total
        </p>
        <p className="mt-1 font-mono text-sm font-bold text-main">
          {formatPrivateRupiah(total, privacyMode)}
        </p>
      </div>
    </div>
  );
};

const SourceDanaAnalytics = ({
  data = {},
  theme = "dark",
  privacyMode,
}) => (
  <section className="panel rounded-lg p-5 shadow-lg">
    <div className="mb-5">
      <h2 className="text-xl font-bold text-main">
        Fund Source Analytics
      </h2>

      <p className="text-muted mt-1 text-sm">
        Dynamic accumulation based on the Source Dana column in Google Sheets.
      </p>
    </div>

    <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
      {chartSections.map((section) => (
        <SourceDanaDonut
          key={section.key}
          title={section.title}
          accent={section.accent}
          rows={data?.[section.key] || []}
          theme={theme}
          privacyMode={privacyMode}
        />
      ))}
    </div>
  </section>
);

export default SourceDanaAnalytics;
