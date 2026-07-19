import { CircleAlert, FileText, LoaderCircle, Upload } from "lucide-react";
import { useRef, useState } from "react";

import { uploadImportFile } from "../../api/importApi";
import { isBcaImportEnabled } from "../../utils/featureFlags";
import BcaImportPanel from "./BcaImportPanel";

const comingSoonProviders = [
  "SeaBank PDF",
  "GoPay PDF",
  "OVO PDF",
];
const ownerOptions = ["Reza", "Divya"];

const ProviderBadge = ({ children, variant = "default" }) => (
  <span className={`status-badge ${
    variant === "success"
      ? "status-badge--success"
      : "status-badge--info"
  }`}>
    {children}
  </span>
);

const ImportLanding = ({ onReviewReady }) => {
  const fileInputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("idle");
  const [error, setError] = useState("");
  const [emptyResult, setEmptyResult] = useState(null);
  const [statementOwner, setStatementOwner] = useState("Reza");
  const [bcaStatementOwner, setBcaStatementOwner] = useState("Reza");
  const bcaImportEnabled = isBcaImportEnabled(import.meta.env);

  const openFilePicker = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event) => {
    const selectedFile = event.target.files?.[0];

    if (!selectedFile) {
      return;
    }

    setUploading(true);
    setUploadStatus("uploading");
    setError("");
    setEmptyResult(null);

    try {
      const response = await uploadImportFile(selectedFile, statementOwner);

      if (response.status === "failed") {
        setUploadStatus("upload_error");
        setError(
          response.message
          || response.error
          || "Upload import belum berhasil. Coba lagi."
        );
        return;
      }

      if (
        response.no_new_transactions
        || (Number(response.transactions_found || 0) > 0 && Number(response.new_transactions || 0) === 0)
      ) {
        setUploadStatus("upload_no_new");
        setEmptyResult({
          filename: selectedFile.name,
          statementOwner,
          transactionsFound: Number(response.transactions_found || 0),
          newTransactions: Number(response.new_transactions || 0),
          existingTransactions: Number(response.existing_transactions || 0),
          rejectedTransactions: Number(response.rejected_transactions || 0),
          message: response.message || "Semua transaksi dalam PDF ini sudah pernah diproses atau ditolak.",
        });
        return;
      }

      setUploadStatus("upload_success");
      onReviewReady({
        ...response,
        filename: selectedFile.name,
        statement_owner: response.statement_owner || statementOwner,
      });
    } catch (uploadError) {
      const responsePayload = uploadError?.response?.data || {};
      setUploadStatus("upload_error");
      setError(
        responsePayload.message
        || responsePayload.detail
        || "Upload import belum berhasil. Coba lagi."
      );
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  return (
    <div className="grid grid-cols-1 gap-6">
      <section>
        <h2 className="text-2xl font-bold text-main">
          Unggah mutasi bank
        </h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted sm:text-base">
          Pilih pemilik transaksi, unggah PDF e-Statement Blu atau BCA, lalu
          Omon akan memeriksa transaksi baru sebelum Anda menyimpannya ke ledger Omon.
        </p>
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
        <article className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm dark:border-[var(--color-border)] dark:bg-[var(--color-panel)]">
          <div className="flex items-start justify-between gap-4">
            <div className="flex min-w-0 items-center gap-3">
              <span className="flex h-11 w-16 shrink-0 items-center justify-center rounded-lg bg-[#00a6a6] px-2">
                <img
                  src="/brands/blu-logo-white.png"
                  alt=""
                  aria-hidden="true"
                  className="h-5 w-auto max-w-full object-contain"
                />
              </span>
              <div className="min-w-0">
                <h3 className="truncate text-base font-bold text-main">
                  Blu PDF Statement
                </h3>
                <p className="mt-1 text-sm font-semibold text-emerald-700 dark:text-emerald-300">
                  Didukung
                </p>
              </div>
            </div>

            <ProviderBadge variant="success">Tersedia</ProviderBadge>
          </div>

          <label className="mt-5 block">
            <span className="text-sm font-semibold text-muted">
              Pemilik transaksi dalam file ini
            </span>
            <select
              value={statementOwner}
              onChange={(event) => setStatementOwner(event.target.value)}
              disabled={uploading}
              className="form-control mt-2 w-full rounded-xl px-4 py-3 text-sm"
            >
              {ownerOptions.map((ownerOption) => (
                <option key={ownerOption} value={ownerOption}>
                  {ownerOption}
                </option>
              ))}
            </select>
          </label>

          <button
            type="button"
            onClick={openFilePicker}
            disabled={uploading}
            className="primary-button mt-6 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold sm:w-auto"
          >
            {uploading ? (
              <LoaderCircle size={18} className="animate-spin" />
            ) : (
              <Upload size={18} />
            )}
            {uploading ? "Memeriksa PDF..." : "Unggah dan periksa PDF"}
          </button>

          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,.pdf"
            onChange={handleFileChange}
            className="hidden"
          />
        </article>

        {bcaImportEnabled ? (
          <BcaImportPanel
            onReviewReady={onReviewReady}
            ownerOptions={ownerOptions}
            statementOwner={bcaStatementOwner}
            onStatementOwnerChange={setBcaStatementOwner}
          />
        ) : (
          <article
            aria-disabled="true"
            className="rounded-lg border border-gray-200 bg-white p-5 opacity-70 shadow-sm dark:border-[var(--color-border)] dark:bg-[var(--color-panel)]"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex min-w-0 items-center gap-3">
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-gray-100 text-muted dark:bg-[var(--color-panel-hover)]">
                  <FileText size={22} />
                </span>
                <div className="min-w-0">
                  <h3 className="truncate text-base font-bold text-main">BCA PDF</h3>
                  <p className="mt-1 text-sm font-semibold text-muted">Belum tersedia</p>
                </div>
              </div>
              <ProviderBadge>Coming Soon</ProviderBadge>
            </div>
            <button
              type="button"
              disabled
              className="mt-6 inline-flex min-h-11 w-full cursor-not-allowed items-center justify-center gap-2 rounded-lg border border-gray-200 px-4 py-2 text-sm font-semibold text-muted dark:border-[var(--color-border)] sm:w-auto"
            >
              Belum tersedia
            </button>
          </article>
        )}

        {comingSoonProviders.map((provider) => (
          <article
            key={provider}
            className="rounded-lg border border-gray-200 bg-white p-5 opacity-70 shadow-sm dark:border-[var(--color-border)] dark:bg-[var(--color-panel)]"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex min-w-0 items-center gap-3">
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-gray-100 text-muted dark:bg-[var(--color-panel-hover)]">
                  <FileText size={22} />
                </span>
                <div className="min-w-0">
                  <h3 className="truncate text-base font-bold text-main">
                    {provider}
                  </h3>
                  <p className="mt-1 text-sm font-semibold text-muted">
                    Belum tersedia
                  </p>
                </div>
              </div>

              <ProviderBadge>Coming Soon</ProviderBadge>
            </div>

            <button
              type="button"
              disabled
              className="mt-6 inline-flex min-h-11 w-full cursor-not-allowed items-center justify-center gap-2 rounded-lg border border-gray-200 px-4 py-2 text-sm font-semibold text-muted dark:border-[var(--color-border)] sm:w-auto"
            >
              Belum tersedia
            </button>
          </article>
        ))}
      </section>

      {error && (
        <section className="alert-panel alert-panel--danger px-4 py-3 text-sm leading-6">
          <div className="flex items-start gap-3">
            <CircleAlert size={18} className="mt-0.5 shrink-0" />
            <p>{error}</p>
          </div>
        </section>
      )}

      {uploadStatus === "upload_success" && (
        <section className="alert-panel alert-panel--success px-4 py-3 text-sm leading-6">
          PDF berhasil diperiksa. Menyiapkan review transaksi baru...
        </section>
      )}

      {uploadStatus === "upload_no_new" && emptyResult && (
        <section className="alert-panel alert-panel--info px-4 py-4 text-sm leading-6">
          <div className="flex items-start gap-3">
            <CircleAlert size={18} className="mt-0.5 shrink-0" />
            <div className="min-w-0">
              <p className="font-semibold text-main">Tidak ada transaksi baru.</p>
              <p className="mt-1">
                {emptyResult.message}
              </p>
              <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel)] px-3 py-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted">Pemilik</p>
                  <p className="mt-1 font-semibold text-main">{emptyResult.statementOwner}</p>
                </div>
                <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel)] px-3 py-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted">Dibaca</p>
                  <p className="mt-1 font-semibold text-main">{emptyResult.transactionsFound}</p>
                </div>
                <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel)] px-3 py-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted">Baru</p>
                  <p className="mt-1 font-semibold text-main">{emptyResult.newTransactions}</p>
                </div>
                <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel)] px-3 py-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted">Sudah diproses</p>
                  <p className="mt-1 font-semibold text-main">{emptyResult.existingTransactions}</p>
                </div>
                <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel)] px-3 py-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted">Pernah Ditolak</p>
                  <p className="mt-1 font-semibold text-main">{emptyResult.rejectedTransactions}</p>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      <section className="alert-panel alert-panel--warning px-4 py-3 text-sm leading-6">
        Import mendukung PDF e-Statement Blu dan BCA. Untuk BCA, pilih tepat
        satu rekening atau Pocket yang ingin direview. File akan diperiksa dulu;
        transaksi baru baru disimpan setelah Anda menyetujuinya.
      </section>
    </div>
  );
};

export default ImportLanding;
