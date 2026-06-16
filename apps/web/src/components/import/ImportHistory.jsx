import {
  Cloud,
  FileClock,
  FileText,
  LoaderCircle,
  RefreshCw,
} from "lucide-react";

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

const ImportHistory = ({
  historyRows,
  selectedDetail,
  loading,
  detailLoading,
  error,
  actionLoading,
  onRefresh,
  onRetrySync,
  onViewDetail,
  onReconnectGoogle,
}) => {
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
                Riwayat import tetap tersedia walau file PDF sementara sudah dihapus.
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
          {loading ? (
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
                    <th className="px-4 py-3 text-left font-semibold">Date</th>
                    <th className="px-4 py-3 text-left font-semibold">Filename</th>
                    <th className="px-4 py-3 text-left font-semibold">Provider</th>
                    <th className="px-4 py-3 text-left font-semibold">Status</th>
                    <th className="px-4 py-3 text-left font-semibold">New</th>
                    <th className="px-4 py-3 text-left font-semibold">Existing</th>
                    <th className="px-4 py-3 text-left font-semibold">Approved</th>
                    <th className="px-4 py-3 text-left font-semibold">Rejected</th>
                    <th className="px-4 py-3 text-left font-semibold">Sync</th>
                    <th className="px-4 py-3 text-left font-semibold">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {historyRows.map((job) => {
                    const syncLabel = `${job.sync_success} ok / ${job.sync_failed} fail`;
                    const needsReconnect = job.needs_reconnect;
                    const canRetry = job.retryable_sync_count > 0;

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
                          <StatusBadge tone={
                            job.status === "completed" ? "success" :
                            job.status === "cleanup_completed" ? "warning" :
                            job.status === "failed" ? "danger" :
                            "default"
                          }>
                            {job.status}
                          </StatusBadge>
                        </td>
                        <td className="px-4 py-3 font-semibold text-main">{job.new_transactions}</td>
                        <td className="px-4 py-3 text-muted">{job.existing_transactions}</td>
                        <td className="px-4 py-3 text-main">{job.approved_transactions}</td>
                        <td className="px-4 py-3 text-muted">{job.rejected_transactions}</td>
                        <td className="px-4 py-3">
                          <div className="flex flex-col gap-1">
                            <span className="text-main">{syncLabel}</span>
                            {needsReconnect && (
                              <StatusBadge tone="warning">needs_reconnect</StatusBadge>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-2">
                            <button
                              type="button"
                              onClick={() => onViewDetail(job.job_id)}
                              className="inline-flex min-h-10 items-center justify-center rounded-lg border border-[var(--color-border)] px-3 py-2 text-xs font-semibold text-accent transition-colors hover:bg-[var(--color-panel-hover)]"
                            >
                              View Detail
                            </button>
                            {canRetry && (
                              <button
                                type="button"
                                onClick={() => onRetrySync(job.job_id)}
                                disabled={actionLoading === `retry:${job.job_id}`}
                                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-amber-200 px-3 py-2 text-xs font-semibold text-amber-800 transition-colors hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-amber-900/40 dark:text-amber-200 dark:hover:bg-amber-950/20"
                              >
                                {actionLoading === `retry:${job.job_id}` ? (
                                  <LoaderCircle size={14} className="animate-spin" />
                                ) : (
                                  <RefreshCw size={14} />
                                )}
                                Retry Sync
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
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Import Time</p>
                <p className="mt-2 font-semibold text-main">{formatDateTime(selectedDetail.import_time)}</p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Status</p>
                <p className="mt-2 font-semibold text-main">{selectedDetail.status}</p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Found</p>
                <p className="mt-2 font-semibold text-main">{selectedDetail.transactions_found}</p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">New</p>
                <p className="mt-2 font-semibold text-main">{selectedDetail.new_transactions}</p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Existing</p>
                <p className="mt-2 font-semibold text-main">{selectedDetail.existing_transactions}</p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Approved</p>
                <p className="mt-2 font-semibold text-main">{selectedDetail.approved_transactions}</p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Rejected</p>
                <p className="mt-2 font-semibold text-main">{selectedDetail.rejected_transactions}</p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Sync Success</p>
                <p className="mt-2 font-semibold text-main">{selectedDetail.sync_success}</p>
              </div>
              <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-3">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Sync Failed</p>
                <p className="mt-2 font-semibold text-main">{selectedDetail.sync_failed}</p>
              </div>
            </div>

            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-4">
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">PDF</p>
              <p className="mt-2 font-semibold text-main">
                {selectedDetail.pdf_status === "already_deleted" ? "Already Deleted" : "Available"}
              </p>
            </div>

            <div className="grid grid-cols-1 gap-3">
              {selectedDetail.retryable_sync_count > 0 && (
                <button
                  type="button"
                  onClick={() => onRetrySync(selectedDetail.job_id)}
                  disabled={actionLoading === `retry:${selectedDetail.job_id}`}
                  className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-amber-200 px-4 py-2 text-sm font-semibold text-amber-800 transition-colors hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-amber-900/40 dark:text-amber-200 dark:hover:bg-amber-950/20"
                >
                  {actionLoading === `retry:${selectedDetail.job_id}` ? (
                    <LoaderCircle size={16} className="animate-spin" />
                  ) : (
                    <RefreshCw size={16} />
                  )}
                  Retry Sync
                </button>
              )}

              {selectedDetail.needs_reconnect && (
                <button
                  type="button"
                  onClick={onReconnectGoogle}
                  className="primary-button inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold"
                >
                  <Cloud size={16} />
                  Reconnect Google
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
              Klik View Detail untuk melihat ringkasan lifecycle import dan status sync.
            </p>
          </div>
        )}
      </aside>
    </div>
  );
};

export default ImportHistory;
