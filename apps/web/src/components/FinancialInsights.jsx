import { formatPrivateRupiah } from "../utils/privacy";

const severityStyles = {
  positive: "status-badge--success",
  neutral: "status-badge--neutral",
  info: "status-badge--info",
  warning: "status-badge--warning",
  danger: "status-badge--danger shadow-sm",
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
    <section className="panel rounded-lg p-4 shadow-lg sm:p-5">
      <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h2 className="text-xl font-bold text-main">
            Financial Insights
          </h2>

          {data?.summary && (
            <p className="mt-1 max-w-4xl text-sm leading-6 text-muted">
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
        <div className="empty-state-panel flex min-h-36 items-center justify-center text-sm">
          Loading insights...
        </div>
      ) : error ? (
        <div className="alert-panel alert-panel--danger px-4 py-3 text-sm font-semibold">
          {error}
        </div>
      ) : highlights.length === 0 ? (
        <div className="empty-state-panel flex min-h-36 items-center justify-center px-4 text-center text-sm">
          Not enough classified transaction data to show financial insights yet.
        </div>
      ) : (
        <div className="grid grid-cols-1 items-stretch gap-4 md:grid-cols-2 2xl:grid-cols-3">
          {highlights.map((highlight) => {
            const ratio = formatRatio(highlight.ratio);
            const severity = highlight.severity || "neutral";

            return (
              <article
                key={`${highlight.type}-${highlight.label}`}
                className="flex h-full min-h-[220px] flex-col rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-4"
              >
                <div className="mb-4 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-bold text-main" title={highlight.label}>
                      {highlight.label}
                    </p>

                    <p className="mt-1 text-xs uppercase text-subtle">
                      {highlight.type}
                    </p>
                  </div>

                  <span
                    className={`status-badge shrink-0 text-[11px] uppercase ${
                      severityStyles[severity] || severityStyles.neutral
                    }`}
                  >
                    {severity}
                  </span>
                </div>

                <p className="text-sm leading-6 text-muted">
                  {highlight.message}
                </p>

                <div className="mt-auto flex flex-wrap items-end gap-x-4 gap-y-3 pt-4">
                  <div className="min-w-0">
                    <p className="text-xs text-subtle">
                      Amount
                    </p>
                    <p className="break-words text-base font-bold text-main">
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
