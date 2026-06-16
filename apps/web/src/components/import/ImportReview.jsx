import {
  CheckCheck,
  ChevronRight,
  CircleAlert,
  FileText,
  Inbox,
  Search,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

const formatAmount = (amount) => new Intl.NumberFormat("id-ID", {
  style: "currency",
  currency: "IDR",
  maximumFractionDigits: 0,
}).format(Number(amount || 0));

const splitDateTime = (datetimeValue) => {
  const [date = "-", time = "-"] = String(datetimeValue || "").split(" ");
  return { date, time };
};

const normalizeRowsForState = (rows = []) => (
  rows.map((row) => ({
    ...row,
    category: row.category || "",
    notes: row.notes || "",
  }))
);

const ReviewMetricCard = ({ icon: Icon, label, value, tone = "default" }) => (
  <div className={`rounded-lg border p-4 ${
    tone === "success"
      ? "border-emerald-200 bg-emerald-50 dark:border-emerald-900/50 dark:bg-emerald-950/30"
      : tone === "muted"
      ? "border-gray-200 bg-gray-50 dark:border-[var(--color-border)] dark:bg-[var(--color-panel-hover)]"
      : "border-[var(--color-border)] bg-[var(--color-panel-hover)]"
  }`}>
    <div className="flex items-center gap-3">
      <span className={`flex h-10 w-10 items-center justify-center rounded-lg ${
        tone === "success"
          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
          : tone === "muted"
          ? "bg-white text-muted dark:bg-[var(--color-panel)]"
          : "bg-[var(--color-panel)] text-accent"
      }`}>
        <Icon size={18} />
      </span>
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted">
          {label}
        </p>
        <p className="mt-1 text-lg font-bold text-main">
          {value}
        </p>
      </div>
    </div>
  </div>
);

const ImportReview = ({
  reviewData,
  loading,
  error,
  onApprove,
  onReject,
  categoryOptions = [],
  categoryOptionsLoading = false,
  categoryOptionsError = "",
  onBack,
}) => {
  const [activeFilter, setActiveFilter] = useState("all");
  const [selectedIds, setSelectedIds] = useState([]);
  const [selectedTransactionId, setSelectedTransactionId] = useState("");
  const [draftRows, setDraftRows] = useState(() => (
    normalizeRowsForState(reviewData?.draft_transactions)
  ));
  const [searchTerm, setSearchTerm] = useState("");
  const [actionLoading, setActionLoading] = useState("");

  const normalizedCategoryOptions = useMemo(() => {
    const options = new Set();

    categoryOptions.forEach((option) => {
      const normalizedOption = String(option || "").trim();
      if (normalizedOption) {
        options.add(normalizedOption);
      }
    });

    draftRows.forEach((row) => {
      const currentCategory = String(row.category || "").trim();
      if (currentCategory) {
        options.add(currentCategory);
      }
    });

    return Array.from(options).sort((first, second) => first.localeCompare(second, "id"));
  }, [categoryOptions, draftRows]);

  const categoryNotice = useMemo(() => {
    if (categoryOptionsLoading) {
      return {
        tone: "info",
        message: "Memuat kategori transaksi...",
      };
    }

    if (categoryOptionsError) {
      return {
        tone: "warning",
        message: categoryOptionsError,
      };
    }

    if (normalizedCategoryOptions.length === 0) {
      return {
        tone: "muted",
        message: "Belum ada kategori dari data transaksi",
      };
    }

    return null;
  }, [categoryOptionsError, categoryOptionsLoading, normalizedCategoryOptions.length]);

  useEffect(() => {
    const normalizedRows = normalizeRowsForState(reviewData?.draft_transactions);
    setDraftRows(normalizedRows);
    setSelectedIds([]);
    setSelectedTransactionId((current) => (
      normalizedRows.some((row) => row.id === current)
        ? current
        : normalizedRows[0]?.id || ""
    ));
  }, [reviewData]);

  const filteredRows = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase();

    return draftRows.filter((row) => {
      const matchesFilter = (
        activeFilter === "all"
        || (activeFilter === "needs-review" && !row.category.trim())
        || (activeFilter.startsWith("group:") && row.review_group === activeFilter.slice(6))
      );

      if (!matchesFilter) {
        return false;
      }

      if (!normalizedSearch) {
        return true;
      }

      return [
        row.merchant_original,
        row.merchant_normalized,
        row.review_group,
        row.category,
      ].some((value) => String(value || "").toLowerCase().includes(normalizedSearch));
    });
  }, [activeFilter, draftRows, searchTerm]);

  const selectedTransaction = draftRows.find((row) => row.id === selectedTransactionId) || null;
  const visibleSelectedCount = filteredRows.filter((row) => selectedIds.includes(row.id)).length;
  const allFilteredSelected = filteredRows.length > 0 && visibleSelectedCount === filteredRows.length;

  const handleToggleRow = (draftId) => {
    setSelectedIds((current) => (
      current.includes(draftId)
        ? current.filter((id) => id !== draftId)
        : [...current, draftId]
    ));
  };

  const handleToggleSelectAll = () => {
    if (allFilteredSelected) {
      setSelectedIds((current) => current.filter((id) => !filteredRows.some((row) => row.id === id)));
      return;
    }

    setSelectedIds((current) => {
      const nextIds = new Set(current);
      filteredRows.forEach((row) => nextIds.add(row.id));
      return Array.from(nextIds);
    });
  };

  const handleDraftFieldChange = (draftId, field, value) => {
    setDraftRows((current) => current.map((row) => (
      row.id === draftId
        ? { ...row, [field]: value }
        : row
    )));
  };

  const handleApproveSelected = async () => {
    if (selectedIds.length === 0) {
      return;
    }

    setActionLoading("approve-selected");
    try {
      await onApprove({
        draft_ids: selectedIds,
        item_updates: draftRows
          .filter((row) => selectedIds.includes(row.id))
          .map((row) => ({
            draft_id: row.id,
            category: row.category,
            notes: row.notes,
          })),
      });
    } finally {
      setActionLoading("");
    }
  };

  const handleRejectSelected = async () => {
    if (selectedIds.length === 0) {
      return;
    }

    setActionLoading("reject-selected");
    try {
      await onReject({
        draft_ids: selectedIds,
        item_updates: [],
      });
    } finally {
      setActionLoading("");
    }
  };

  const handleApproveSingle = async () => {
    if (!selectedTransaction) {
      return;
    }

    setActionLoading("approve-single");
    try {
      await onApprove({
        draft_ids: [selectedTransaction.id],
        item_updates: [{
          draft_id: selectedTransaction.id,
          category: selectedTransaction.category,
          notes: selectedTransaction.notes,
        }],
      });
    } finally {
      setActionLoading("");
    }
  };

  const handleRejectSingle = async () => {
    if (!selectedTransaction) {
      return;
    }

    setActionLoading("reject-single");
    try {
      await onReject({
        draft_ids: [selectedTransaction.id],
        item_updates: [],
      });
    } finally {
      setActionLoading("");
    }
  };

  if (loading) {
    return (
      <div className="panel rounded-lg p-6 shadow-lg">
        <p className="text-sm text-muted">
          Menyiapkan review import transaksi...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel rounded-lg p-6 shadow-lg">
        <div className="flex items-start gap-3 text-red-600 dark:text-red-300">
          <CircleAlert size={20} className="mt-0.5 shrink-0" />
          <div>
            <p className="font-bold text-main">
              Review import belum bisa dibuka
            </p>
            <p className="mt-2 text-sm text-muted">
              {error}
            </p>
            <button
              type="button"
              onClick={onBack}
              className="mt-4 inline-flex items-center gap-2 rounded-lg border border-[var(--color-border)] px-4 py-2 text-sm font-semibold text-accent transition-colors hover:bg-[var(--color-panel-hover)]"
            >
              <ChevronRight size={16} className="rotate-180" />
              Kembali ke Upload
            </button>
          </div>
        </div>
      </div>
    );
  }

  const summary = reviewData?.summary || {};
  const filters = reviewData?.filters || [];

  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
      <div className="grid grid-cols-1 gap-6">
        <section className="panel rounded-lg p-5 shadow-lg sm:p-6">
          <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
            <div className="min-w-0">
              <div className="flex items-center gap-3">
                <span className="flex h-12 w-12 items-center justify-center rounded-lg bg-[var(--color-accent-bg)] text-accent">
                  <FileText size={22} />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted">
                    Import Transaksi
                  </p>
                  <h2 className="truncate text-2xl font-bold text-main">
                    Review
                  </h2>
                </div>
              </div>

              <p className="mt-4 text-sm text-muted">
                {summary.filename || "-"}
              </p>
              <p className="mt-1 text-sm leading-6 text-muted">
                {summary.transactions_found || 0} transaksi dibaca
              </p>
            </div>

            <button
              type="button"
              onClick={onBack}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-[var(--color-border)] px-4 py-2 text-sm font-semibold text-accent transition-colors hover:bg-[var(--color-panel-hover)]"
            >
              <ChevronRight size={16} className="rotate-180" />
              Upload Lain
            </button>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
            <ReviewMetricCard
              icon={Inbox}
              label="Transactions Found"
              value={`${summary.transactions_found || 0} transaksi`}
            />
            <ReviewMetricCard
              icon={CheckCheck}
              label="New Transactions"
              value={`🟢 ${summary.new_transactions || 0} Baru`}
              tone="success"
            />
            <ReviewMetricCard
              icon={CircleAlert}
              label="Existing Transactions"
              value={`⚪ ${summary.existing_transactions || 0} Sudah Pernah Diimport`}
              tone="muted"
            />
          </div>
        </section>

        <section className="panel rounded-lg p-4 shadow-lg sm:p-5">
          <div className="flex flex-col gap-4">
            <div className="flex flex-wrap gap-2">
              {filters.map((filter) => (
                <button
                  key={filter.id}
                  type="button"
                  onClick={() => setActiveFilter(filter.id)}
                  className={`inline-flex min-h-10 items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-colors ${
                    activeFilter === filter.id
                      ? "bg-[var(--color-accent-strong)] text-white"
                      : "bg-[var(--color-panel-hover)] text-muted hover:text-accent"
                  }`}
                >
                  <span>{filter.label}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs ${
                    activeFilter === filter.id
                      ? "bg-white/15 text-white"
                      : "bg-[var(--color-panel)] text-main"
                  }`}>
                    {filter.count}
                  </span>
                </button>
              ))}
            </div>

            <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
              <label className="relative block w-full xl:max-w-md">
                <Search size={16} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-muted" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  placeholder="Cari merchant atau review group..."
                  className="form-control w-full rounded-xl py-3 pl-11 pr-4 text-sm"
                />
              </label>

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={handleToggleSelectAll}
                  className="inline-flex min-h-11 items-center justify-center rounded-lg border border-[var(--color-border)] px-4 py-2 text-sm font-semibold text-accent transition-colors hover:bg-[var(--color-panel-hover)]"
                >
                  {allFilteredSelected ? "Clear Select" : "Select All"}
                </button>
                <button
                  type="button"
                  onClick={handleApproveSelected}
                  disabled={selectedIds.length === 0 || actionLoading !== ""}
                  className="primary-button inline-flex min-h-11 items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {actionLoading === "approve-selected" ? "Approving..." : "Approve Selected"}
                </button>
                <button
                  type="button"
                  onClick={handleRejectSelected}
                  disabled={selectedIds.length === 0 || actionLoading !== ""}
                  className="inline-flex min-h-11 items-center justify-center rounded-lg border border-red-200 px-4 py-2 text-sm font-semibold text-red-600 transition-colors hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-red-900/40 dark:text-red-300 dark:hover:bg-red-950/30"
                >
                  {actionLoading === "reject-selected" ? "Rejecting..." : "Reject Selected"}
                </button>
              </div>
            </div>

            {categoryNotice && (
              <div className={`rounded-lg border px-4 py-3 text-sm ${
                categoryNotice.tone === "warning"
                  ? "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200"
                  : "border-[var(--color-border)] bg-[var(--color-panel-hover)] text-muted"
              }`}>
                {categoryNotice.message}
              </div>
            )}
          </div>
        </section>

        <section className="panel rounded-lg p-4 shadow-lg sm:p-5">
          {filteredRows.length === 0 ? (
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-5 text-sm text-muted">
              Tidak ada transaksi baru yang perlu direview untuk filter ini.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1080px] border-collapse text-sm">
                <thead>
                  <tr className="table-header table-border text-muted">
                    <th className="px-4 py-3 text-left">
                      <input
                        type="checkbox"
                        checked={allFilteredSelected}
                        onChange={handleToggleSelectAll}
                        aria-label="Select all visible transactions"
                      />
                    </th>
                    <th className="px-4 py-3 text-left font-semibold">Tanggal</th>
                    <th className="px-4 py-3 text-left font-semibold">Jam</th>
                    <th className="px-4 py-3 text-left font-semibold">Merchant</th>
                    <th className="px-4 py-3 text-left font-semibold">Nominal</th>
                    <th className="px-4 py-3 text-left font-semibold">Kategori</th>
                    <th className="px-4 py-3 text-left font-semibold">Review Group</th>
                    <th className="px-4 py-3 text-left font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRows.map((row) => {
                    const { date, time } = splitDateTime(row.datetime);
                    const isSelected = selectedIds.includes(row.id);
                    const isActive = row.id === selectedTransactionId;

                    return (
                      <tr
                        key={row.id}
                        className={`table-row table-border cursor-pointer transition ${
                          isActive ? "bg-[var(--color-accent-bg)]" : ""
                        }`}
                        onClick={() => setSelectedTransactionId(row.id)}
                      >
                        <td className="px-4 py-3">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleToggleRow(row.id)}
                            onClick={(event) => event.stopPropagation()}
                            aria-label={`Select ${row.merchant_original}`}
                          />
                        </td>
                        <td className="px-4 py-3 text-main">{date}</td>
                        <td className="px-4 py-3 text-muted">{time}</td>
                        <td className="px-4 py-3">
                          <div className="min-w-0">
                            <p className="truncate font-semibold text-main">
                              {row.merchant_normalized || row.merchant_original}
                            </p>
                            <p className="truncate text-xs text-muted">
                              {row.merchant_original}
                            </p>
                          </div>
                        </td>
                        <td className="px-4 py-3 font-semibold text-main">
                          {formatAmount(row.amount)}
                        </td>
                        <td className="px-4 py-3">
                          <select
                            value={row.category}
                            onChange={(event) => handleDraftFieldChange(
                              row.id,
                              "category",
                              event.target.value
                            )}
                            onClick={(event) => event.stopPropagation()}
                            className="form-control w-44 rounded-lg px-3 py-2 text-xs"
                          >
                            <option value="">Pilih kategori</option>
                            {normalizedCategoryOptions.map((option) => (
                              <option key={option} value={option}>
                                {option}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="px-4 py-3 text-muted">
                          {row.review_group || "-"}
                        </td>
                        <td className="px-4 py-3">
                          <span className="inline-flex rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
                            New
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      <aside className="panel min-h-[320px] rounded-lg p-5 shadow-lg xl:sticky xl:top-6 xl:h-fit">
        {selectedTransaction ? (
          <div className="grid grid-cols-1 gap-5">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted">
                Detail Review
              </p>
              <h3 className="mt-2 text-xl font-bold text-main">
                {selectedTransaction.merchant_normalized || selectedTransaction.merchant_original}
              </h3>
              <p className="mt-1 text-sm text-muted">
                {selectedTransaction.merchant_original}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">
                  Datetime
                </p>
                <p className="mt-2 font-semibold text-main">
                  {selectedTransaction.datetime}
                </p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">
                  Amount
                </p>
                <p className="mt-2 font-semibold text-main">
                  {formatAmount(selectedTransaction.amount)}
                </p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">
                  Direction
                </p>
                <p className="mt-2 font-semibold capitalize text-main">
                  {selectedTransaction.direction}
                </p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">
                  Transaction Type
                </p>
                <p className="mt-2 font-semibold text-main">
                  {selectedTransaction.transaction_type}
                </p>
              </div>
            </div>

            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-4">
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">
                Review Group
              </p>
              <p className="mt-2 font-semibold text-main">
                {selectedTransaction.review_group || "bluAccount"}
              </p>
            </div>

            <label className="block">
              <span className="text-sm font-semibold text-muted">
                Kategori
              </span>
              <select
                value={selectedTransaction.category}
                onChange={(event) => handleDraftFieldChange(
                  selectedTransaction.id,
                  "category",
                  event.target.value
                )}
                className="form-control mt-2 w-full rounded-xl px-4 py-3 text-sm"
              >
                <option value="">Pilih kategori</option>
                {normalizedCategoryOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              {normalizedCategoryOptions.length === 0 && !categoryOptionsLoading && (
                <p className="mt-2 text-xs text-muted">
                  Belum ada kategori dari data transaksi
                </p>
              )}
            </label>

            <label className="block">
              <span className="text-sm font-semibold text-muted">
                Notes
              </span>
              <textarea
                value={selectedTransaction.notes}
                onChange={(event) => handleDraftFieldChange(
                  selectedTransaction.id,
                  "notes",
                  event.target.value
                )}
                rows={4}
                placeholder="Tambahkan catatan bila perlu"
                className="form-control mt-2 w-full rounded-xl px-4 py-3 text-sm"
              />
            </label>

            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-4">
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">
                Raw Review Data
              </p>
              <p className="mt-2 break-words text-sm leading-6 text-muted">
                {selectedTransaction.raw_text}
              </p>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <button
                type="button"
                onClick={handleApproveSingle}
                disabled={actionLoading !== ""}
                className="primary-button inline-flex min-h-11 items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
              >
                {actionLoading === "approve-single" ? "Approving..." : "Approve"}
              </button>
              <button
                type="button"
                onClick={handleRejectSingle}
                disabled={actionLoading !== ""}
                className="inline-flex min-h-11 items-center justify-center rounded-lg border border-red-200 px-4 py-2 text-sm font-semibold text-red-600 transition-colors hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-red-900/40 dark:text-red-300 dark:hover:bg-red-950/30"
              >
                {actionLoading === "reject-single" ? "Rejecting..." : "Reject"}
              </button>
            </div>
          </div>
        ) : (
          <div className="flex h-full min-h-[280px] flex-col items-center justify-center text-center">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-[var(--color-accent-bg)] text-accent">
              <XCircle size={24} />
            </span>
            <h3 className="mt-4 text-lg font-bold text-main">
              Belum ada transaksi dipilih
            </h3>
            <p className="mt-2 max-w-xs text-sm leading-6 text-muted">
              Klik salah satu baris transaksi baru untuk membuka detail review di panel ini.
            </p>
          </div>
        )}
      </aside>
    </div>
  );
};

export default ImportReview;
