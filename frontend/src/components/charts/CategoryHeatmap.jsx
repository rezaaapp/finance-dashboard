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

const getVisualScaleLimit = (rows) => {
  const values = rows
    .flatMap((row) => row.months.map((month) => month.total))
    .filter((value) => value > 0)
    .sort((a, b) => a - b);

  if (values.length === 0) {
    return 0;
  }

  const percentileIndex = Math.max(
    0,
    Math.ceil(values.length * 0.9) - 1
  );

  return values[percentileIndex];
};

const getVisualIntensity = (value, scaleLimit) => {
  if (!value || scaleLimit <= 0) {
    return 0;
  }

  return Math.min(
    1,
    Math.log1p(value) / Math.log1p(scaleLimit)
  );
};

const interpolateColor = (start, end, ratio) => {
  const color = start.map((channel, index) => (
    Math.round(channel + (end[index] - channel) * ratio)
  ));

  return `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
};

const getCellColor = (value, scaleLimit, theme) => {
  const intensity = getVisualIntensity(value, scaleLimit);

  if (intensity === 0) {
    return theme === "light"
      ? "rgba(226, 232, 240, 0.72)"
      : "rgba(30, 41, 59, 0.72)";
  }

  const stops = theme === "light"
    ? [
        [224, 242, 254],
        [103, 232, 249],
        [20, 184, 166],
        [245, 158, 11],
      ]
    : [
        [15, 23, 42],
        [8, 145, 178],
        [20, 184, 166],
        [251, 191, 36],
      ];

  if (intensity < 0.34) {
    return interpolateColor(stops[0], stops[1], intensity / 0.34);
  }

  if (intensity < 0.68) {
    return interpolateColor(stops[1], stops[2], (intensity - 0.34) / 0.34);
  }

  return interpolateColor(stops[2], stops[3], (intensity - 0.68) / 0.32);
};

const getCellTextColor = (value, scaleLimit, theme) => {
  const intensity = getVisualIntensity(value, scaleLimit);

  if (theme === "light") {
    return intensity > 0.5 ? "#082f49" : "var(--color-text)";
  }

  return intensity > 0.2 ? "#f8fafc" : "var(--color-text)";
};

const CategoryHeatmap = ({ data, theme = "dark" }) => {
  const rows = data?.rows ?? [];
  const months = data?.months ?? [];
  const visualScaleLimit = getVisualScaleLimit(rows);

  let peak = null;

  rows.forEach((row) => {
    row.months.forEach((month) => {
      if (!peak || month.total > peak.total) {
        peak = {
          kategori: row.kategori,
          bulan: month.bulan,
          total: month.total,
        };
      }
    });
  });

  const summary = {
    topCategory: rows[0],
    peak,
  };

  return (
    <div className="panel rounded-2xl p-5 shadow-lg">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-main">
            Category Transaction Heat Map
          </h2>
        </div>

        <div className="grid gap-3 text-sm sm:grid-cols-2">
          <div className="rounded-lg border border-[var(--color-border)] px-4 py-3">
            <p className="text-muted text-xs mb-1">
              Top Category
            </p>
            <p className="font-semibold text-main">
              {summary.topCategory?.kategori ?? "-"}
            </p>
            <p className="text-subtle">
              {formatRupiah(summary.topCategory?.total)}
            </p>
          </div>

          <div className="rounded-lg border border-[var(--color-border)] px-4 py-3">
            <p className="text-muted text-xs mb-1">
              Peak Spending
            </p>
            <p className="font-semibold text-main">
              {summary.peak
                ? `${summary.peak.kategori} - ${summary.peak.bulan}`
                : "-"}
            </p>
            <p className="text-subtle">
              {formatRupiah(summary.peak?.total)}
            </p>
          </div>
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="flex h-48 items-center justify-center text-muted">
          No category data available
        </div>
      ) : (
        <div className="overflow-x-auto">
          <div
            className="grid min-w-[720px] gap-2"
            style={{
              gridTemplateColumns: `minmax(160px, 1.2fr) repeat(${months.length}, minmax(86px, 1fr))`,
            }}
          >
            <div className="text-xs font-semibold uppercase text-muted">
              Category
            </div>

            {months.map((month) => (
              <div
                key={month}
                className="text-center text-xs font-semibold uppercase text-muted"
              >
                {month}
              </div>
            ))}

            {rows.map((row) => (
              <div key={row.kategori} className="contents">
                <div className="flex min-h-12 items-center text-sm font-semibold text-main">
                  {row.kategori}
                </div>

                {row.months.map((month) => (
                  <div
                    key={`${row.kategori}-${month.bulan}`}
                    className="flex min-h-12 items-center justify-center rounded-lg px-2 text-xs font-semibold transition-transform hover:scale-[1.03]"
                    style={{
                      backgroundColor: getCellColor(
                        month.total,
                        visualScaleLimit,
                        theme
                      ),
                      color: getCellTextColor(
                        month.total,
                        visualScaleLimit,
                        theme
                      ),
                    }}
                    title={`${row.kategori} ${month.bulan}: ${formatRupiah(month.total)}`}
                  >
                    {month.total > 0 ? formatCompactRupiah(month.total) : "-"}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default CategoryHeatmap;
