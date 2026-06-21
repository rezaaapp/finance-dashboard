import {
  CheckCheck,
  ChevronRight,
  CircleAlert,
  FileText,
  Inbox,
  Search,
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
    merchant_display: row.merchant_display || row.merchant_normalized || row.merchant_original || "",
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
  actionError,
  actionFeedback,
  onApprove,
  onReject,
  sheetSources = [],
  sheetSourcesLoading = false,
  sheetSourcesError = "",
  targetSourceId = "",
  targetSheetName = "",
  worksheets = [],
  worksheetsLoading = false,
  worksheetsError = "",
  onTargetSourceChange,
  onTargetSheetChange,
  categoryOptions = [],
  categoryOptionsLoading = false,
  categoryOptionsError = "",
  pagination = null,
  onPageChange,
  onBack,
}) => {
  const [activeFilter, setActiveFilter] = useState("all");
  const [selectedIds, setSelectedIds] = useState([]);
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
        row.merchant_display,
        row.merchant_original,
        row.merchant_normalized,
        row.category,
      ].some((value) => String(value || "").toLowerCase().includes(normalizedSearch));
    });
  }, [activeFilter, draftRows, searchTerm]);

  const visibleSelectedCount = filteredRows.filter((row) => selectedIds.includes(row.id)).length;
  const allFilteredSelected = filteredRows.length > 0 && visibleSelectedCount === filteredRows.length;
  const hasTargetSheet = Boolean(targetSourceId && targetSheetName);
  const isActionLoading = actionLoading !== "";

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
        sheet_source_id: targetSourceId,
        sheet_name: targetSheetName,
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

  if (loading && !reviewData) {
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
  const totalDraftRows = pagination?.total ?? draftRows.length;

  return (
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
              <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold text-muted">
                <span className="rounded-full bg-[var(--color-panel-hover)] px-3 py-1">
                  Pemilik: {summary.statement_owner || "-"}
                </span>
                <span className="rounded-full bg-[var(--color-panel-hover)] px-3 py-1">
                  Source Dana: {summary.source_fund || "Blu"}
                </span>
              </div>
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
              label="Transaksi Dibaca"
              value={`${summary.transactions_found || 0} transaksi`}
            />
            <ReviewMetricCard
              icon={CheckCheck}
              label="Siap Direview"
              value={`${totalDraftRows} transaksi`}
              tone="success"
            />
            <ReviewMetricCard
              icon={CircleAlert}
              label="Sudah Tercatat"
              value={`${summary.existing_transactions || 0} transaksi`}
              tone="muted"
            />
          </div>
        </section>

        <section className="panel rounded-lg p-4 shadow-lg sm:p-5">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted">
                Target Tujuan Spreadsheet
              </p>
              <p className="mt-2 text-sm text-muted">
                Setelah transaksi disetujui dan tersimpan di Omon, sistem akan mencoba
                mengirim salinannya ke tab ini sebagai projection/export layer.
              </p>
              <p className="mt-2 text-xs text-muted">
                PostgreSQL di Omon adalah source of truth. Google Spreadsheet dipakai
                sebagai input dan projection/export layer, jadi status approval dan
                status pengiriman Spreadsheet dipantau terpisah.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <label className="block">
                <span className="text-sm font-semibold text-muted">
                  Spreadsheet
                </span>
                <select
                  value={targetSourceId}
                  onChange={(event) => onTargetSourceChange?.(event.target.value)}
                  disabled={sheetSourcesLoading}
                  className="form-control mt-2 w-full rounded-xl px-4 py-3 text-sm disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <option value="">
                    {sheetSourcesLoading ? "Memuat spreadsheet..." : "Pilih spreadsheet"}
                  </option>
                  {sheetSources.map((source) => (
                    <option key={source.source_id} value={source.source_id}>
                      {source.spreadsheet_title || source.sheet_id}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="text-sm font-semibold text-muted">
                  Tab Tujuan
                </span>
                <select
                  value={targetSheetName}
                  onChange={(event) => onTargetSheetChange?.(event.target.value)}
                  disabled={!targetSourceId || worksheetsLoading}
                  className="form-control mt-2 w-full rounded-xl px-4 py-3 text-sm disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <option value="">
                    {worksheetsLoading ? "Memuat tab..." : "Pilih tab tujuan"}
                  </option>
                  {worksheets.map((worksheet) => (
                    <option key={worksheet} value={worksheet}>
                      {worksheet}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>

          {(sheetSourcesError || worksheetsError || !hasTargetSheet) && (
            <div className="mt-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] px-4 py-3 text-sm text-muted">
              {sheetSourcesError || worksheetsError || (
                hasTargetSheet
                  ? "Target Spreadsheet siap digunakan setelah transaksi tersimpan di Omon."
                  : "Transaksi akan disimpan di Omon. Sinkronisasi Spreadsheet dapat dilakukan setelah Google Sheet terhubung."
              )}
            </div>
          )}
        </section>

        <section className="panel rounded-lg p-4 shadow-lg sm:p-5">
          <div className="flex flex-col gap-4">
            {loading && reviewData && (
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] px-4 py-3 text-sm text-muted">
                Memuat halaman transaksi review berikutnya...
              </div>
            )}

            {error && reviewData && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/20 dark:text-red-300">
                {error}
              </div>
            )}

            {actionError && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="font-semibold text-main">
                      Approval belum dijalankan
                    </p>
                    <p className="mt-1">
                      {actionError.message}
                    </p>
                    {actionError.errorCode === "missing_google_sheet_source" && (
                      <p className="mt-1">
                        Omon belum menyimpan approval karena koneksi tujuan Google Spreadsheet belum siap.
                      </p>
                    )}
                    {actionError.errorCode === "missing_target_sheet" && (
                      <p className="mt-1">
                        Pilih spreadsheet dan tab tujuan lebih dulu. Setelah approval tersimpan di Omon, salinannya akan dicoba dikirim ke tujuan ini.
                      </p>
                    )}
                    {actionError.errorCode === "needs_reconnect" && (
                      <p className="mt-1">
                        Hubungkan ulang Google terlebih dahulu agar approval bisa dilanjutkan dengan target spreadsheet yang valid.
                      </p>
                    )}
                    {actionError.errorCode === "invalid_target_sheet_header" && (
                      <p className="mt-1">
                        Tab tujuan sudah dipilih, tetapi format kolomnya belum sesuai untuk menerima salinan transaksi dari Omon.
                      </p>
                    )}
                    {actionError.errorCode === "sync_failed" && (
                      <p className="mt-1">
                        Cek tab tujuan atau koneksi Google Sheets, lalu lanjutkan lagi setelah target pengiriman siap.
                      </p>
                    )}
                  </div>
                  {["missing_google_sheet_source", "needs_reconnect", "invalid_target_sheet_header"].includes(actionError.errorCode) && (
                    <a
                      href="/settings"
                      className="inline-flex min-h-10 shrink-0 items-center justify-center rounded-lg border border-amber-300 px-4 py-2 text-sm font-semibold text-amber-900 transition-colors hover:bg-amber-100 dark:border-amber-700 dark:text-amber-100 dark:hover:bg-amber-900/40"
                    >
                      Buka Settings Integrasi
                    </a>
                  )}
                </div>
              </div>
            )}

            {actionFeedback && (
              <div className={`rounded-lg border px-4 py-3 text-sm ${
                actionFeedback.tone === "success"
                  ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-950/30 dark:text-emerald-200"
                  : "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200"
              }`}>
                <p className="font-semibold text-main">
                  {actionFeedback.title}
                </p>
                <p className="mt-1">{actionFeedback.message}</p>
                {actionFeedback.detail && (
                  <p className="mt-1 text-xs">{actionFeedback.detail}</p>
                )}
                {actionFeedback.tone !== "success" && (
                  <p className="mt-2 text-xs">
                    Lanjutkan monitoring status pengiriman salinan di tab History.
                  </p>
                )}
              </div>
            )}

            {actionLoading === "approve-selected" && (
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] px-4 py-3 text-sm text-muted">
                Sedang menyimpan approval ke Omon, lalu mencoba mengirim salinannya ke Google Spreadsheet...
              </div>
            )}

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
                  placeholder="Cari nama transaksi atau kategori..."
                  className="form-control w-full rounded-xl py-3 pl-11 pr-4 text-sm"
                />
              </label>

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={handleToggleSelectAll}
                  disabled={isActionLoading}
                  className="inline-flex min-h-11 items-center justify-center rounded-lg border border-[var(--color-border)] px-4 py-2 text-sm font-semibold text-accent transition-colors hover:bg-[var(--color-panel-hover)]"
                >
                  {allFilteredSelected ? "Hapus Pilihan" : "Pilih Semua"}
                </button>
                <button
                  type="button"
                  onClick={handleApproveSelected}
                  disabled={selectedIds.length === 0 || actionLoading !== ""}
                  className="primary-button inline-flex min-h-11 items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {actionLoading === "approve-selected" ? "Menyimpan ke Omon..." : "Setujui & Simpan di Omon"}
                </button>
                <button
                  type="button"
                  onClick={handleRejectSelected}
                  disabled={selectedIds.length === 0 || actionLoading !== ""}
                  className="inline-flex min-h-11 items-center justify-center rounded-lg border border-red-200 px-4 py-2 text-sm font-semibold text-red-600 transition-colors hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-red-900/40 dark:text-red-300 dark:hover:bg-red-950/30"
                >
                  {actionLoading === "reject-selected" ? "Menolak..." : "Tolak Pilihan"}
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

            {pagination && pagination.total > pagination.limit && (
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] px-4 py-3 text-xs text-muted">
                Filter dan pencarian berlaku untuk transaksi yang sedang tampil di halaman ini. Total transaksi review: {pagination.total}.
              </div>
            )}
          </div>
        </section>

        <section className="panel rounded-lg p-4 shadow-lg sm:p-5">
          {draftRows.length === 0 ? (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-5 text-sm text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-950/30 dark:text-emerald-200">
              <div className="flex items-center gap-3">
                <CheckCheck size={20} className="shrink-0" />
                <p className="font-semibold">Semua transaksi baru untuk file ini sudah diproses.</p>
              </div>
            </div>
          ) : filteredRows.length === 0 ? (
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-5 text-sm text-muted">
              Tidak ada transaksi baru yang perlu direview untuk filter ini.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[860px] border-collapse text-sm">
                <thead>
                  <tr className="table-header table-border text-muted">
                    <th className="px-4 py-3 text-left">
                      <input
                        type="checkbox"
                        checked={allFilteredSelected}
                        onChange={handleToggleSelectAll}
                        aria-label="Pilih semua transaksi yang terlihat"
                      />
                    </th>
                    <th className="px-4 py-3 text-left font-semibold">Tanggal</th>
                    <th className="px-4 py-3 text-left font-semibold">Jam</th>
                    <th className="px-4 py-3 text-left font-semibold">Nama Transaksi</th>
                    <th className="px-4 py-3 text-left font-semibold">Nominal</th>
                    <th className="px-4 py-3 text-left font-semibold">Kategori</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRows.map((row) => {
                    const { date, time } = splitDateTime(row.datetime);
                    const isSelected = selectedIds.includes(row.id);

                    return (
                      <tr
                        key={row.id}
                        className="table-row table-border transition"
                      >
                        <td className="px-4 py-3">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleToggleRow(row.id)}
                            aria-label={`Pilih ${row.merchant_display}`}
                          />
                        </td>
                        <td className="px-4 py-3 text-main">{date}</td>
                        <td className="px-4 py-3 text-muted">{time}</td>
                        <td className="px-4 py-3">
                          <div className="min-w-0">
                            <p className="truncate font-semibold text-main">
                              {row.merchant_display}
                            </p>
                          </div>
                        </td>
                        <td className="px-4 py-3 font-semibold text-main">
                          {formatAmount(row.amount)}
                        </td>
                        <td className="px-4 py-3">
                          <select
                            value={row.category}
                            disabled={isActionLoading && isSelected}
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
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {pagination && pagination.total > pagination.limit && (
            <div className="mt-4 flex flex-col gap-3 border-t border-[var(--color-border)] pt-4 text-sm sm:flex-row sm:items-center sm:justify-between">
              <p className="text-muted">
                Menampilkan {pagination.offset + 1}-{Math.min(pagination.offset + draftRows.length, pagination.total)} dari {pagination.total} transaksi review.
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => onPageChange?.(Math.max(0, pagination.offset - pagination.limit))}
                  disabled={!pagination.has_previous || loading}
                  className="inline-flex min-h-10 items-center justify-center rounded-lg border border-[var(--color-border)] px-4 py-2 text-sm font-semibold text-accent transition-colors hover:bg-[var(--color-panel-hover)] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Sebelumnya
                </button>
                <button
                  type="button"
                  onClick={() => onPageChange?.(pagination.offset + pagination.limit)}
                  disabled={!pagination.has_next || loading}
                  className="inline-flex min-h-10 items-center justify-center rounded-lg border border-[var(--color-border)] px-4 py-2 text-sm font-semibold text-accent transition-colors hover:bg-[var(--color-panel-hover)] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Berikutnya
                </button>
              </div>
            </div>
          )}
        </section>
    </div>
  );
};

export default ImportReview;
