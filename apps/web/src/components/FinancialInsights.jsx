import { formatPrivateRupiah } from "../utils/privacy";

const severityStyles = {
  positive: "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-300",
  neutral: "border-gray-200 bg-gray-50 text-gray-700 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300",
  info: "border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-900/60 dark:bg-sky-950/30 dark:text-sky-300",
  warning: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-300",
  danger: "border-red-200 bg-red-50 text-red-700 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-300",
};

const formatRatio = (value) => {
  if (value === undefined || value === null) {
    return null;
  }

  return `${(Number(value || 0) * 100).toFixed(1)}%`;
};

const FinancialInsights = ({
  data,
  loading = false,
  error = "",
  privacyMode,
}) => {
  const highlights = Array.isArray(data?.highlights)
    ? data.highlights
    : [];

  return (
    <section className="panel rounded-lg p-5 shadow-lg">
      <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-xl font-bold text-main">
            Financial Insights
          </h2>

          {data?.summary && (
            <p className="mt-1 text-sm text-muted">
              {data.summary}
            </p>
          )}
        </div>

        {data?.period && (
          <span className="w-fit rounded-full border border-[var(--color-border)] px-3 py-1 text-xs font-bold text-muted">
            {data.period}
          </span>
        )}
      </div>

      {loading ? (
        <div className="flex min-h-36 items-center justify-center rounded-lg border border-dashed border-[var(--color-border)] text-sm text-muted">
          Loading insights...
        </div>
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-300">
          {error}
        </div>
      ) : highlights.length === 0 ? (
        <div className="flex min-h-36 items-center justify-center rounded-lg border border-dashed border-[var(--color-border)] px-4 text-center text-sm text-muted">
          Not enough classified transaction data to show financial insights yet.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {highlights.map((highlight) => {
            const ratio = formatRatio(highlight.ratio);
            const severity = highlight.severity || "neutral";

            return (
              <article
                key={`${highlight.type}-${highlight.label}`}
                className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-4"
              >
                <div className="mb-4 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-bold text-main">
                      {highlight.label}
                    </p>

                    <p className="mt-1 text-xs uppercase text-subtle">
                      {highlight.type}
                    </p>
                  </div>

                  <span
                    className={`shrink-0 rounded-full border px-2.5 py-1 text-[11px] font-bold uppercase ${
                      severityStyles[severity] || severityStyles.neutral
                    }`}
                  >
                    {severity}
                  </span>
                </div>

                <p className="min-h-10 text-sm leading-6 text-muted">
                  {highlight.message}
                </p>

                <div className="mt-4 flex flex-wrap items-end gap-x-4 gap-y-2">
                  <div>
                    <p className="text-xs text-subtle">
                      Amount
                    </p>
                    <p className="text-base font-bold text-main">
                      {formatPrivateRupiah(highlight.amount, privacyMode)}
                    </p>
                  </div>

                  {ratio && (
                    <div>
                      <p className="text-xs text-subtle">
                        Ratio
                      </p>
                      <p className="text-base font-bold text-main">
                        {ratio}
                      </p>
                    </div>
                  )}

                  {highlight.count !== undefined && (
                    <div>
                      <p className="text-xs text-subtle">
                        Count
                      </p>
                      <p className="text-base font-bold text-main">
                        {highlight.count}
                      </p>
                    </div>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
};

export default FinancialInsights;
