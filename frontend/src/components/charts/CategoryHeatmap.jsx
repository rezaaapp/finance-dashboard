import { X } from "lucide-react";
import { memo, useCallback, useEffect, useMemo, useState } from "react";

import {
  formatPrivateCompact,
  formatPrivateRupiah,
  maskNumber,
} from "../../utils/privacy";

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

const formatDate = (value) => new Date(value).toLocaleDateString("id-ID", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

const formatPeriod = (periodString = "") => {
  const [year, month] = periodString.split("-");

  if (!year || !month) {
    return periodString;
  }

  return new Date(Number(year), Number(month) - 1, 1).toLocaleDateString(
    "id-ID",
    {
      month: "long",
      year: "numeric",
    }
  );
};

const TransactionDetailModal = memo(({
  isOpen,
  onClose,
  category,
  period,
  transactions,
  privacyMode,
}) => {
  const totalAmount = useMemo(() => (
    transactions.reduce((sum, transaction) => (
      sum + Number(transaction.amount || 0)
    ), 0)
  ), [transactions]);

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    document.body.classList.add("overflow-hidden");

    return () => {
      document.body.classList.remove("overflow-hidden");
    };
  }, [isOpen]);

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[70] flex items-end justify-center bg-black/70 px-4 py-5 backdrop-blur-sm sm:items-center">
      <div className="w-full max-w-2xl overflow-hidden rounded-2xl border border-slate-800 bg-[#111827] shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-800 px-5 py-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Detail Heat Map
            </p>
            <h3 className="mt-1 break-words text-lg font-bold text-cyan-400 sm:text-xl">
              Rincian Transaksi: {category} - {formatPeriod(period)}
            </h3>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="theme-toggle h-10 w-10 shrink-0 rounded-xl p-0"
            aria-label="Tutup rincian transaksi"
            title="Tutup"
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-5 py-4">
          {transactions.length === 0 ? (
            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 text-center text-sm text-slate-300">
              Tidak ada catatan transaksi pada periode ini.
            </div>
          ) : (
            <div className="max-h-[60vh] space-y-3 overflow-y-auto pr-1">
              {transactions.map((transaction, index) => {
                const isDivya = transaction.user === "Divya";

                return (
                  <div
                    key={`${transaction.date}-${transaction.item_name}-${index}`}
                    className="rounded-xl border border-slate-800 bg-slate-900/70 p-4"
                  >
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div className="min-w-0">
                        <p className="break-words font-bold text-white">
                          {transaction.item_name}
                        </p>

                        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                          <span>{formatDate(transaction.date)}</span>
                          <span
                            className={`rounded-full px-2.5 py-1 font-bold ${
                              isDivya
                                ? "bg-fuchsia-500/15 text-fuchsia-300"
                                : "bg-cyan-500/15 text-cyan-300"
                            }`}
                          >
                            {transaction.user}
                          </span>
                        </div>
                      </div>

                      <p className="shrink-0 text-left font-mono text-sm font-bold text-emerald-400 sm:text-right">
                        {formatPrivateRupiah(transaction.amount, privacyMode)}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="border-t border-slate-800 px-5 py-4">
          <div className="mb-4 rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
              <span className="text-sm font-semibold text-slate-300">
                Total Pengeluaran Periode Ini
              </span>
              <span className="font-mono text-lg font-bold text-emerald-400">
                {formatPrivateRupiah(totalAmount, privacyMode)}
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="primary-button w-full rounded-xl px-4 py-3 font-bold"
          >
            Tutup
          </button>
        </div>
      </div>
    </div>
  );
});

TransactionDetailModal.displayName = "TransactionDetailModal";

const CategoryHeatmap = ({
  data,
  rawTransactions = [],
  theme = "dark",
  privacyMode,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedPeriod, setSelectedPeriod] = useState("");
  const [selectedTransactions, setSelectedTransactions] = useState([]);
  const displayPrivacyMode = privacyMode === "guest" ? "normal" : privacyMode;
  const rows = useMemo(() => (
    (data?.rows ?? []).map((row) => ({
      ...row,
      total: maskNumber(row.total, privacyMode),
      months: row.months.map((month) => ({
        ...month,
        total: maskNumber(month.total, privacyMode),
      })),
    }))
  ), [data?.rows, privacyMode]);
  const months = useMemo(() => data?.months ?? [], [data?.months]);
  const visualScaleLimit = useMemo(() => getVisualScaleLimit(rows), [rows]);
  const summary = useMemo(() => {
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

    return {
      topCategory: rows[0],
      peak,
    };
  }, [rows]);

  const transactionsByCell = useMemo(() => {
    const grouped = new Map();

    rawTransactions.forEach((transaction) => {
      const periodString = transaction.date.slice(0, 7);
      const key = `${transaction.category}__${periodString}`;
      const currentTransactions = grouped.get(key) ?? [];

      currentTransactions.push(transaction);
      grouped.set(key, currentTransactions);
    });

    return grouped;
  }, [rawTransactions]);

  const closeModal = useCallback(() => {
    setIsOpen(false);
  }, []);

  const handleCellClick = useCallback((category, periodString) => {
    const filtered = transactionsByCell.get(`${category}__${periodString}`)
      ?? [];

    setSelectedCategory(category);
    setSelectedPeriod(periodString);
    setSelectedTransactions(filtered);
    setIsOpen(true);
  }, [transactionsByCell]);

  const handleCellKeyDown = useCallback((event, category, periodString) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      handleCellClick(category, periodString);
    }
  }, [handleCellClick]);

  return (
    <div className="panel rounded-2xl p-4 shadow-lg sm:p-5">
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
              {formatPrivateRupiah(summary.topCategory?.total, displayPrivacyMode)}
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
              {formatPrivateRupiah(summary.peak?.total, displayPrivacyMode)}
            </p>
          </div>
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="flex h-48 items-center justify-center text-muted">
          No category data available
        </div>
      ) : (
        <>
        <div className="hidden overflow-x-auto md:block">
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

                {row.months.map((month) => {
                  const hasTransactions = month.total > 0;

                  return (
                    <div
                      key={`${row.kategori}-${month.bulan}`}
                      role={hasTransactions ? "button" : undefined}
                      tabIndex={hasTransactions ? 0 : undefined}
                      onClick={hasTransactions
                        ? () => handleCellClick(row.kategori, month.bulan)
                        : undefined}
                      onKeyDown={hasTransactions
                        ? (event) => handleCellKeyDown(
                            event,
                            row.kategori,
                            month.bulan
                          )
                        : undefined}
                      className={`flex min-h-12 items-center justify-center rounded-lg px-2 text-xs font-semibold transition-all duration-200 ${
                        hasTransactions
                          ? "cursor-pointer hover:scale-[1.02] hover:brightness-125 focus:outline-none focus:ring-2 focus:ring-cyan-400/70"
                          : "cursor-default"
                      }`}
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
                      title={`${row.kategori} ${month.bulan}: ${formatPrivateRupiah(month.total, displayPrivacyMode)}`}
                    >
                      {hasTransactions
                        ? formatPrivateCompact(month.total, displayPrivacyMode)
                        : "-"}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 md:hidden">
          {rows.map((row) => (
            <div
              key={row.kategori}
              className="rounded-xl border border-[var(--color-border)] p-4"
            >
              <div className="mb-3 flex items-start justify-between gap-3">
                <p className="break-words font-semibold text-main">
                  {row.kategori}
                </p>
                <p className="shrink-0 text-right text-sm font-bold text-accent">
                  {formatPrivateRupiah(row.total, displayPrivacyMode)}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2">
                {row.months.map((month) => {
                  const hasTransactions = month.total > 0;

                  return (
                    <div
                      key={`${row.kategori}-${month.bulan}`}
                      role={hasTransactions ? "button" : undefined}
                      tabIndex={hasTransactions ? 0 : undefined}
                      onClick={hasTransactions
                        ? () => handleCellClick(row.kategori, month.bulan)
                        : undefined}
                      onKeyDown={hasTransactions
                        ? (event) => handleCellKeyDown(
                            event,
                            row.kategori,
                            month.bulan
                          )
                        : undefined}
                      className={`rounded-lg px-3 py-2 text-xs font-semibold transition-all duration-200 ${
                        hasTransactions
                          ? "cursor-pointer hover:scale-[1.02] hover:brightness-125 focus:outline-none focus:ring-2 focus:ring-cyan-400/70"
                          : "cursor-default"
                      }`}
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
                      title={`${row.kategori} ${month.bulan}: ${formatPrivateRupiah(month.total, displayPrivacyMode)}`}
                    >
                      <span className="block opacity-80">
                        {month.bulan}
                      </span>
                      <span className="mt-1 block">
                        {hasTransactions
                          ? formatPrivateCompact(month.total, displayPrivacyMode)
                          : "-"}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
        </>
      )}

      <TransactionDetailModal
        isOpen={isOpen}
        onClose={closeModal}
        category={selectedCategory}
        period={selectedPeriod}
        transactions={selectedTransactions}
        privacyMode={privacyMode}
      />
    </div>
  );
};

export default CategoryHeatmap;
