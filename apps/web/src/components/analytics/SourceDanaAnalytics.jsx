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
import {
  categoricalChartColors,
  chartTheme,
  sourceDanaChartColors,
} from "../../theme/chartTheme";

const fallbackColors = categoricalChartColors;

const normalizedBrandColors = Object.fromEntries(
  Object.entries(sourceDanaChartColors).map(([source, color]) => [
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
    title: "Sumber pemasukan",
    key: "income_sources",
    accent: "text-accent",
  },
  {
    title: "Sumber pengeluaran",
    key: "spending_sources",
    accent: "text-[var(--color-alert-text)]",
  },
  {
    title: "Alokasi simpanan",
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
  const sourceCounterText = `${rows.length} sumber terdeteksi`;

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
        <div className="empty-state-panel flex h-[280px] items-center justify-center text-sm">
          Belum ada data sumber dana untuk bagian ini.
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
          Total bagian ini
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
        Komposisi sumber dana
      </h2>

      <p className="text-muted mt-1 text-sm">
        Membantu melihat sumber pemasukan, pengeluaran, dan simpanan dari kolom Source Dana.
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
