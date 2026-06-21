import {
  Cloud,
  FileClock,
  FileText,
  LoaderCircle,
  RefreshCw,
} from "lucide-react";

import {
  getOmonApprovalStatus,
  getReadableSyncStatus,
  getSpreadsheetDeliveryStatus,
} from "./deliveryStatusUx";

const formatDateTime = (value) => {
  if (!value) {
    return "-";
  }

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return String(value);
  }

  return new Intl.DateTimeFormat("id-ID", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
};

const StatusBadge = ({ children, tone = "default" }) => (
  <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${
    tone === "success"
      ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300"
      : tone === "warning"
      ? "bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
      : tone === "danger"
      ? "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300"
      : "bg-[var(--color-panel-hover)] text-muted"
  }`}>
    {children}
  </span>
);

const formatAmount = (amount) => new Intl.NumberFormat("id-ID", {
  style: "currency",
  currency: "IDR",
  maximumFractionDigits: 0,
}).format(Number(amount || 0));

const RetryResultBanner = ({ retryResult }) => {
  if (!retryResult) {
    return null;
  }

  return (
    <div className={`rounded-lg border px-4 py-3 text-sm ${
      retryResult.tone === "success"
        ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-950/30 dark:text-emerald-200"
        : "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200"
    }`}>
      <p className="font-semibold text-main">{retryResult.title}</p>
      <p className="mt-1">{retryResult.message}</p>
      {retryResult.detail && (
        <p className="mt-1 text-xs">{retryResult.detail}</p>
      )}
    </div>
  );
};

const ImportHistory = ({
  historyRows,
  selectedDetail,
  loading,
  detailLoading,
  error,
  actionLoading,
  pagination = null,
  onRefresh,
  onPageChange,
  onRetrySync,
  onViewDetail,
  onContinueReview,
  onReconnectGoogle,
  sheetSources = [],
  sheetSourcesLoading = false,
  sheetSourcesError = "",
  targetSourceId = "",
  targetSheetName = "",
  worksheets = [],
  worksheetsLoading = false,
  worksheetsError = "",
  retryResult = null,
  onTargetSourceChange,
  onTargetSheetChange,
}) => {
  const hasRetryTarget = Boolean(targetSourceId && targetSheetName);
  const approvalStatus = selectedDetail ? getOmonApprovalStatus(selectedDetail) : null;
  const deliveryStatus = selectedDetail ? getSpreadsheetDeliveryStatus(selectedDetail) : null;

  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
      <div className="grid grid-cols-1 gap-6">
        <section className="panel rounded-lg p-5 shadow-lg sm:p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="flex items-center gap-3">
                <span className="flex h-12 w-12 items-center justify-center rounded-lg bg-[var(--color-accent-bg)] text-accent">
                  <FileClock size={22} />
                </span>
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted">
                    Import Transaksi
                  </p>
                  <h2 className="text-2xl font-bold text-main">
                    History
                  </h2>
                </div>
              </div>
              <p className="mt-4 max-w-3xl text-sm leading-6 text-muted">
                Riwayat approval di Omon dan status pengiriman salinan ke Google Spreadsheet dipantau terpisah, walau file PDF sementara sudah dihapus.
              </p>
            </div>

            <button
              type="button"
              onClick={onRefresh}
              disabled={loading}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-[var(--color-border)] px-4 py-2 text-sm font-semibold text-accent transition-colors hover:bg-[var(--color-panel-hover)] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? (
                <LoaderCircle size={16} className="animate-spin" />
              ) : (
                <RefreshCw size={16} />
              )}
              Refresh
            </button>
          </div>
        </section>

        {error && (
          <section className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/20 dark:text-red-300">
            {error}
          </section>
        )}

        <section className="panel rounded-lg p-4 shadow-lg sm:p-5">
          {loading && historyRows.length > 0 && (
            <div className="mb-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-4 text-sm text-muted">
              Memuat halaman riwayat import...
            </div>
          )}

          {loading && historyRows.length === 0 ? (
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-5 text-sm text-muted">
              Memuat riwayat import...
            </div>
          ) : historyRows.length === 0 ? (
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-5 text-sm text-muted">
              Belum ada riwayat import.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1080px] border-collapse text-sm">
                <thead>
                  <tr className="table-header table-border text-muted">
                    <th className="px-4 py-3 text-left font-semibold">Waktu</th>
                    <th className="px-4 py-3 text-left font-semibold">File</th>
                    <th className="px-4 py-3 text-left font-semibold">Provider</th>
                    <th className="px-4 py-3 text-left font-semibold">Status Omon</th>
                    <th className="px-4 py-3 text-left font-semibold">Baru</th>
                    <th className="px-4 py-3 text-left font-semibold">Sudah Tercatat</th>
                    <th className="px-4 py-3 text-left font-semibold">Disetujui</th>
                    <th className="px-4 py-3 text-left font-semibold">Ditolak</th>
                    <th className="px-4 py-3 text-left font-semibold">Status Spreadsheet</th>
                    <th className="px-4 py-3 text-left font-semibold">Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  {historyRows.map((job) => {
                    const rowApprovalStatus = getOmonApprovalStatus(job);
                    const rowDeliveryStatus = getSpreadsheetDeliveryStatus(job);
                    const canRetry = job.retryable_sync_count > 0;
                    const canContinueReview = (
                      job.status === "review"
                      && Number(job.new_transactions || 0) > 0
                    );

                    return (
                      <tr key={job.job_id} className="table-row table-border">
                        <td className="px-4 py-3 text-muted">{formatDateTime(job.import_time)}</td>
                        <td className="px-4 py-3">
                          <div className="min-w-0">
                            <p className="truncate font-semibold text-main">{job.filename}</p>
                          </div>
                        </td>
                        <td className="px-4 py-3 uppercase text-muted">{job.provider}</td>
                        <td className="px-4 py-3">
                          <StatusBadge tone={rowApprovalStatus.tone}>
                            {rowApprovalStatus.label}
                          </StatusBadge>
                        </td>
                        <td className="px-4 py-3 font-semibold text-main">{job.new_transactions}</td>
                        <td className="px-4 py-3 text-muted">{job.existing_transactions}</td>
                        <td className="px-4 py-3 text-main">{job.approved_transactions}</td>
                        <td className="px-4 py-3 text-muted">{job.rejected_transactions}</td>
                        <td className="px-4 py-3">
                          <div className="flex flex-col gap-1">
                            <StatusBadge tone={rowDeliveryStatus.tone}>
                              {rowDeliveryStatus.label}
                            </StatusBadge>
                            <span className="text-xs text-muted">
                              {job.sync_success} berhasil / {job.sync_failed} belum terkirim
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-2">
                            {canContinueReview && (
                              <button
                                type="button"
                                onClick={() => onContinueReview(job.job_id)}
                                className="primary-button inline-flex min-h-10 items-center justify-center px-3 py-2 text-xs font-semibold"
                              >
                                Lanjutkan Review
                              </button>
                            )}
                            <button
                              type="button"
                              onClick={() => onViewDetail(job.job_id)}
                              className="inline-flex min-h-10 items-center justify-center rounded-lg border border-[var(--color-border)] px-3 py-2 text-xs font-semibold text-accent transition-colors hover:bg-[var(--color-panel-hover)]"
                            >
                              Lihat Detail
                            </button>
                            {canRetry && (
                              <button
                                type="button"
                                onClick={() => {
                                  onViewDetail(job.job_id);
                                }}
                                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-amber-200 px-3 py-2 text-xs font-semibold text-amber-800 transition-colors hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-amber-900/40 dark:text-amber-200 dark:hover:bg-amber-950/20"
                              >
                                <RefreshCw size={14} />
                                Retry
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {pagination && pagination.total > pagination.limit && historyRows.length > 0 && (
            <div className="mt-4 flex flex-col gap-3 border-t border-[var(--color-border)] pt-4 text-sm sm:flex-row sm:items-center sm:justify-between">
              <p className="text-muted">
                Menampilkan {pagination.offset + 1}-{Math.min(pagination.offset + historyRows.length, pagination.total)} dari {pagination.total} job import.
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

      <aside className="panel min-h-[320px] rounded-lg p-5 shadow-lg xl:sticky xl:top-6 xl:h-fit">
        {detailLoading ? (
          <p className="text-sm text-muted">Memuat detail import...</p>
        ) : selectedDetail ? (
          <div className="grid grid-cols-1 gap-5">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted">
                Import Detail
              </p>
              <h3 className="mt-2 text-xl font-bold text-main">
                {selectedDetail.filename}
              </h3>
              <p className="mt-1 text-sm uppercase text-muted">
                {selectedDetail.provider}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Waktu Import</p>
                <p className="mt-2 font-semibold text-main">{formatDateTime(selectedDetail.import_time)}</p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Status Omon</p>
                <p className="mt-2 font-semibold text-main">{approvalStatus.label}</p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Transaksi Dibaca</p>
                <p className="mt-2 font-semibold text-main">{selectedDetail.transactions_found}</p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Transaksi Baru</p>
                <p className="mt-2 font-semibold text-main">{selectedDetail.new_transactions}</p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Sudah Tercatat</p>
                <p className="mt-2 font-semibold text-main">{selectedDetail.existing_transactions}</p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Disetujui di Omon</p>
                <p className="mt-2 font-semibold text-main">{selectedDetail.approved_transactions}</p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Ditolak</p>
                <p className="mt-2 font-semibold text-main">{selectedDetail.rejected_transactions}</p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Terkirim ke Spreadsheet</p>
                <p className="mt-2 font-semibold text-main">{selectedDetail.sync_success}</p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Belum Terkirim</p>
                <p className="mt-2 font-semibold text-main">{selectedDetail.sync_failed}</p>
              </div>
            </div>

            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-4">
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Status Spreadsheet</p>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <StatusBadge tone={deliveryStatus.tone}>{deliveryStatus.label}</StatusBadge>
              </div>
              <p className="mt-3 text-sm text-muted">
                {deliveryStatus.summary}
              </p>
            </div>

            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-4">
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">PDF</p>
              <p className="mt-2 font-semibold text-main">
                {selectedDetail.pdf_status === "already_deleted" ? "Sudah Dihapus" : "Masih Tersedia"}
              </p>
            </div>

            {selectedDetail.unsynced_count > 0 && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200">
                <p className="font-semibold text-main">
                  Ada transaksi yang sudah disetujui dan menjadi data utama di Omon, tetapi salinannya belum terkirim ke Google Spreadsheet.
                </p>
                <p className="mt-1">
                  {selectedDetail.unsynced_count} transaksi perlu Retry pengiriman tanpa membuat ulang transaksi final di Omon.
                </p>
              </div>
            )}

            {selectedDetail.unsynced_transactions?.length > 0 && (
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-4">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">
                  Pengiriman Spreadsheet Belum Selesai
                </p>
                <div className="mt-3 grid grid-cols-1 gap-2">
                  {selectedDetail.unsynced_transactions.slice(0, 5).map((transaction) => (
                    <div
                      key={transaction.id}
                      className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel)] p-3 text-sm"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate font-semibold text-main">
                            {transaction.transaction_name}
                          </p>
                          <p className="mt-1 text-xs text-muted">
                            {transaction.date} · {transaction.category || "Tanpa kategori"}
                          </p>
                        </div>
                        <p className="shrink-0 font-semibold text-main">
                          {formatAmount(transaction.amount)}
                        </p>
                      </div>
                      <p className="mt-2 text-xs text-muted">
                        {getReadableSyncStatus(transaction)}
                        {transaction.sync_error_message ? ` · ${transaction.sync_error_message}` : ""}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selectedDetail.unsynced_count > 0 && (
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-4">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">
                  Retry Pengiriman Spreadsheet
                </p>
                <p className="mt-2 text-sm text-muted">
                  Retry hanya mencoba mengirim ulang salinan ke Google Spreadsheet. Transaksi yang sudah tersimpan di Omon tidak dibuat ulang.
                </p>
                <div className="mt-3 grid grid-cols-1 gap-3">
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

                  {(sheetSourcesError || worksheetsError || !hasRetryTarget) && (
                    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel)] px-4 py-3 text-sm text-muted">
                      {sheetSourcesError || worksheetsError || "Pilih spreadsheet dan tab tujuan sebelum retry pengiriman agar sistem bisa mengirim ulang salinan transaksi."}
                    </div>
                  )}

                  <RetryResultBanner retryResult={retryResult} />

                  <button
                    type="button"
                    onClick={() => onRetrySync(selectedDetail.job_id)}
                    disabled={!hasRetryTarget || actionLoading === `retry:${selectedDetail.job_id}`}
                    className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-amber-200 px-4 py-2 text-sm font-semibold text-amber-800 transition-colors hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-amber-900/40 dark:text-amber-200 dark:hover:bg-amber-950/20"
                  >
                    {actionLoading === `retry:${selectedDetail.job_id}` ? (
                      <LoaderCircle size={16} className="animate-spin" />
                    ) : (
                      <RefreshCw size={16} />
                    )}
                    Retry Pengiriman
                  </button>
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 gap-3">
              {selectedDetail.status === "review" && Number(selectedDetail.new_transactions || 0) > 0 && (
                <button
                  type="button"
                  onClick={() => onContinueReview(selectedDetail.job_id)}
                  className="primary-button inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold"
                >
                  <FileText size={16} />
                  Lanjutkan Review
                </button>
              )}
              {selectedDetail.needs_reconnect && (
                <button
                  type="button"
                  onClick={onReconnectGoogle}
                  className="primary-button inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold"
                >
                  <Cloud size={16} />
                  Hubungkan Ulang Google
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="flex h-full min-h-[280px] flex-col items-center justify-center text-center">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-[var(--color-accent-bg)] text-accent">
              <FileText size={24} />
            </span>
            <h3 className="mt-4 text-lg font-bold text-main">Pilih riwayat import</h3>
            <p className="mt-2 max-w-xs text-sm leading-6 text-muted">
              Klik View Detail untuk melihat ringkasan approval di Omon dan status pengiriman Spreadsheet.
            </p>
          </div>
        )}
      </aside>
    </div>
  );
};

export default ImportHistory;
