import {
  CircleAlert,
  FileCheck2,
  LoaderCircle,
  RotateCcw,
  Upload,
  X,
} from "lucide-react";
import { useEffect, useMemo, useReducer, useRef } from "react";

import { uploadImportFile } from "../../api/importApi";
import {
  BCA_IMPORT_STATUS,
  bcaImportReducer,
  createInitialBcaImportState,
  formatBcaFileSize,
  isBcaRequestPending,
  validateBcaPdfFile,
} from "./bcaImportState";

const BcaImportPanel = ({
  onReviewReady,
  ownerOptions,
  statementOwner,
  onStatementOwnerChange,
  uploadFile = uploadImportFile,
}) => {
  const fileInputRef = useRef(null);
  const selectionHeadingRef = useRef(null);
  const errorRef = useRef(null);
  const abortControllerRef = useRef(null);
  const requestInFlightRef = useRef(false);
  const requestTokenRef = useRef(0);
  const [state, dispatch] = useReducer(
    bcaImportReducer,
    undefined,
    createInitialBcaImportState
  );

  const requestPending = isBcaRequestPending(state.status);
  const selectedCandidate = useMemo(
    () => state.candidates.find(
      (candidate) => candidate.sectionId === state.selectedSectionId
    ) || null,
    [state.candidates, state.selectedSectionId]
  );

  useEffect(() => {
    if (state.status === BCA_IMPORT_STATUS.SECTION_SELECTION_REQUIRED) {
      selectionHeadingRef.current?.focus();
    }
    if (state.status === BCA_IMPORT_STATUS.ERROR) {
      errorRef.current?.focus();
    }
  }, [state.status]);

  const resetFileInput = () => {
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleFileChange = (event) => {
    const selectedFile = event.target.files?.[0];
    if (!selectedFile) {
      return;
    }

    dispatch({
      type: "FILE_SELECTED",
      file: selectedFile,
      validation: validateBcaPdfFile(selectedFile),
    });
    resetFileInput();
  };

  const runUpload = async ({ selectedSectionId = "" } = {}) => {
    if (!state.file || requestInFlightRef.current) {
      return;
    }

    const requestToken = requestTokenRef.current + 1;
    requestTokenRef.current = requestToken;
    requestInFlightRef.current = true;
    abortControllerRef.current = new AbortController();
    dispatch({
      type: selectedSectionId ? "START_SELECTED_PARSE" : "START_UPLOAD",
    });

    try {
      const response = await uploadFile(state.file, statementOwner, {
        expectedProvider: "bca",
        expectedSectionId: selectedSectionId || undefined,
        signal: abortControllerRef.current.signal,
      });

      if (requestToken !== requestTokenRef.current) {
        return;
      }

      if (response.error_code === "section_selection_required") {
        dispatch({
          type: "SELECTION_REQUIRED",
          candidates: response.section_candidates || [],
        });
        return;
      }

      if (response.status === "failed") {
        const shouldReturnToSelection = [
          "invalid_section_selection",
          "no_parseable_transactions",
        ].includes(response.error_code) && state.candidates.length > 0;
        dispatch({
          type: "FAIL",
          errorCode: response.error_code,
          message: response.message || response.error,
          retryStatus: shouldReturnToSelection
            ? BCA_IMPORT_STATUS.SECTION_SELECTION_REQUIRED
            : selectedSectionId
              ? BCA_IMPORT_STATUS.SECTION_SELECTED
              : BCA_IMPORT_STATUS.FILE_SELECTED,
        });
        return;
      }

      if (
        response.no_new_transactions
        || (
          Number(response.transactions_found || 0) > 0
          && Number(response.new_transactions || 0) === 0
        )
      ) {
        dispatch({
          type: "REVIEW_READY",
          emptyResult: {
            message: response.message || "Tidak ada transaksi baru pada rekening ini.",
            transactionsFound: Number(response.transactions_found || 0),
          },
        });
        return;
      }

      dispatch({ type: "REVIEW_READY" });
      await onReviewReady({
        ...response,
        filename: state.file.name,
        statement_owner: response.statement_owner || statementOwner,
      });
    } catch (uploadError) {
      if (
        requestToken !== requestTokenRef.current
        || uploadError?.code === "ERR_CANCELED"
        || uploadError?.name === "CanceledError"
      ) {
        return;
      }

      const responsePayload = uploadError?.response?.data || {};
      dispatch({
        type: "FAIL",
        errorCode: responsePayload.error_code || "network_error",
        message: responsePayload.message || responsePayload.detail,
        retryStatus: selectedSectionId
          ? BCA_IMPORT_STATUS.SECTION_SELECTED
          : BCA_IMPORT_STATUS.FILE_SELECTED,
      });
    } finally {
      if (requestToken === requestTokenRef.current) {
        requestInFlightRef.current = false;
        abortControllerRef.current = null;
      }
    }
  };

  const handleCancel = () => {
    requestTokenRef.current += 1;
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    requestInFlightRef.current = false;
    resetFileInput();
    dispatch({ type: "CANCEL" });
  };

  const handleRetry = () => {
    const retryStatus = state.retryStatus;
    dispatch({ type: "RETRY" });

    if (retryStatus === BCA_IMPORT_STATUS.SECTION_SELECTION_REQUIRED) {
      return;
    }

    runUpload({
      selectedSectionId: retryStatus === BCA_IMPORT_STATUS.SECTION_SELECTED
        ? state.selectedSectionId
        : "",
    });
  };

  const renderFileSummary = () => state.file && (
    <div className="mt-5 rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="break-words text-sm font-semibold text-main">
            {state.file.name}
          </p>
          <p className="mt-1 text-xs text-muted">
            {formatBcaFileSize(state.file.size)} · PDF
          </p>
          <p
            id="bca-file-validation"
            className={`mt-2 text-xs font-semibold ${
              state.fileValidation?.valid ? "text-emerald-700 dark:text-emerald-300" : "text-red-700 dark:text-red-300"
            }`}
          >
            {state.fileValidation?.message}
          </p>
        </div>
        <button
          type="button"
          onClick={handleCancel}
          disabled={requestPending}
          className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-lg border border-[var(--color-border)] px-3 py-2 text-sm font-semibold text-muted hover:text-accent disabled:cursor-not-allowed disabled:opacity-60"
        >
          <X size={16} />
          Hapus file
        </button>
      </div>
    </div>
  );

  const showSelection = [
    BCA_IMPORT_STATUS.SECTION_SELECTION_REQUIRED,
    BCA_IMPORT_STATUS.SECTION_SELECTED,
    BCA_IMPORT_STATUS.PARSING_SELECTED_SECTION,
  ].includes(state.status);

  return (
    <article className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm dark:border-[var(--color-border)] dark:bg-[var(--color-panel)] lg:col-span-2 xl:col-span-2">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-11 w-24 shrink-0 items-center justify-center rounded-lg bg-blue-50 px-1 dark:bg-white">
            <img
              src="/brands/bca-logo-blue.png"
              alt=""
              aria-hidden="true"
              className="h-10 w-full object-contain"
            />
          </span>
          <div className="min-w-0">
            <h3 className="text-base font-bold text-main">BCA PDF</h3>
            <p className="mt-1 text-sm font-semibold text-emerald-700 dark:text-emerald-300">
              Didukung
            </p>
          </div>
        </div>
        <span className="status-badge status-badge--success self-start">Tersedia</span>
      </div>

      <p className="mt-4 text-sm leading-6 text-muted">
        Unggah e-Statement BCA, lalu pilih tepat satu rekening atau Pocket untuk direview.
      </p>

      <label className="mt-5 block">
        <span className="text-sm font-semibold text-muted">
          Pemilik transaksi dalam file ini
        </span>
        <select
          value={statementOwner}
          onChange={(event) => onStatementOwnerChange(event.target.value)}
          disabled={requestPending}
          className="form-control mt-2 w-full rounded-xl px-4 py-3 text-sm"
        >
          {ownerOptions.map((ownerOption) => (
            <option key={ownerOption} value={ownerOption}>
              {ownerOption}
            </option>
          ))}
        </select>
      </label>

      {state.status === BCA_IMPORT_STATUS.IDLE && (
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="primary-button mt-6 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold sm:w-auto"
        >
          <Upload size={18} />
          Pilih PDF BCA
        </button>
      )}

      {state.status === BCA_IMPORT_STATUS.FILE_SELECTED && (
        <>
          {renderFileSummary()}
          <button
            type="button"
            onClick={() => runUpload()}
            disabled={!state.fileValidation?.valid || requestPending}
            aria-describedby="bca-file-validation"
            className="primary-button mt-4 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
          >
            <FileCheck2 size={18} />
            Unggah dan periksa rekening
          </button>
        </>
      )}

      {state.status === BCA_IMPORT_STATUS.UPLOADING && (
        <div className="mt-5" role="status" aria-live="polite">
          {renderFileSummary()}
          <p className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-main">
            <LoaderCircle size={18} className="animate-spin" />
            Memeriksa rekening dan Pocket dalam PDF...
          </p>
          <button
            type="button"
            onClick={handleCancel}
            className="mt-4 block min-h-11 rounded-lg border border-[var(--color-border)] px-4 py-2 text-sm font-semibold text-muted"
          >
            Batalkan pemeriksaan
          </button>
        </div>
      )}

      {showSelection && (
        <section className="mt-6 border-t border-[var(--color-border)] pt-5">
          <h4
            ref={selectionHeadingRef}
            tabIndex={-1}
            className="text-lg font-bold text-main outline-none"
          >
            Pilih rekening atau Pocket
          </h4>
          <p id="bca-section-help" className="mt-2 text-sm leading-6 text-muted">
            File ini berisi beberapa rekening. Pilih satu rekening untuk dilanjutkan.
            Transaksi dari rekening lain tidak akan ikut diimpor.
          </p>

          {state.candidates.length === 0 && (
            <div
              className="mt-4 rounded-lg border border-[var(--color-danger)] bg-[var(--color-danger-bg)] p-4 text-sm text-main"
              role="alert"
            >
              Tidak dapat menentukan rekening dari file ini. Coba unggah ulang PDF BCA
              yang valid atau batalkan proses ini.
            </div>
          )}

          <fieldset
            className="mt-4 grid grid-cols-1 gap-3"
            aria-describedby="bca-section-help"
            disabled={state.status === BCA_IMPORT_STATUS.PARSING_SELECTED_SECTION}
          >
            <legend className="sr-only">Rekening atau Pocket yang akan diimpor</legend>
            {state.candidates.map((candidate) => (
              <label
                key={candidate.sectionId}
                className={`flex min-w-0 cursor-pointer items-start gap-3 rounded-lg border p-4 transition-colors ${
                  state.selectedSectionId === candidate.sectionId
                    ? "border-[var(--color-accent)] bg-[var(--color-accent-bg)]"
                    : "border-[var(--color-border)] bg-[var(--color-panel)]"
                } ${candidate.isSelectable ? "" : "cursor-not-allowed opacity-60"}`}
              >
                <input
                  type="radio"
                  name="bca-section"
                  value={candidate.sectionId}
                  checked={state.selectedSectionId === candidate.sectionId}
                  disabled={!candidate.isSelectable}
                  onChange={() => dispatch({
                    type: "SELECT_SECTION",
                    sectionId: candidate.sectionId,
                  })}
                  className="mt-1 h-4 w-4 shrink-0"
                  aria-label={`${candidate.displayLabel}, ${candidate.maskedIdentity}, ${candidate.transactionCountEstimate} transaksi`}
                />
                <span className="min-w-0 flex-1">
                  <span className="block break-words text-sm font-bold text-main">
                    {candidate.displayLabel}
                  </span>
                  <span className="mt-1 block break-words text-xs text-muted">
                    {candidate.maskedIdentity}
                  </span>
                  <span className="mt-2 block text-xs font-semibold text-muted">
                    {candidate.transactionCountEstimate} transaksi
                    {!candidate.isSelectable ? " · Tidak tersedia untuk dipilih" : ""}
                  </span>
                </span>
              </label>
            ))}
          </fieldset>

          {selectedCandidate && (
            <div className="mt-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-4 text-sm">
              <p className="font-bold text-main">Rekening terpilih</p>
              <p className="mt-1 break-words text-muted">
                {selectedCandidate.displayLabel} · {selectedCandidate.maskedIdentity} · {selectedCandidate.transactionCountEstimate} transaksi
              </p>
            </div>
          )}

          <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <button
              type="button"
              onClick={() => runUpload({ selectedSectionId: state.selectedSectionId })}
              disabled={!selectedCandidate || requestPending}
              aria-describedby="bca-section-help"
              className="primary-button inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
            >
              {state.status === BCA_IMPORT_STATUS.PARSING_SELECTED_SECTION ? (
                <LoaderCircle size={18} className="animate-spin" />
              ) : (
                <FileCheck2 size={18} />
              )}
              {state.status === BCA_IMPORT_STATUS.PARSING_SELECTED_SECTION
                ? "Menyiapkan review..."
                : "Lanjutkan dengan rekening ini"}
            </button>
            {selectedCandidate && !requestPending && (
              <button
                type="button"
                onClick={() => dispatch({ type: "CHANGE_SELECTION" })}
                className="min-h-11 w-full rounded-lg border border-[var(--color-border)] px-4 py-2 text-sm font-semibold text-accent sm:w-auto"
              >
                Ubah pilihan
              </button>
            )}
            <button
              type="button"
              onClick={handleCancel}
              className="min-h-11 w-full rounded-lg border border-[var(--color-border)] px-4 py-2 text-sm font-semibold text-muted sm:w-auto"
            >
              Batalkan
            </button>
          </div>
        </section>
      )}

      {state.status === BCA_IMPORT_STATUS.ERROR && state.error && (
        <section
          ref={errorRef}
          tabIndex={-1}
          role="alert"
          className="alert-panel alert-panel--danger mt-5 px-4 py-4 outline-none"
        >
          <div className="flex items-start gap-3">
            <CircleAlert size={18} className="mt-0.5 shrink-0" />
            <div className="min-w-0">
              <h4 className="font-bold text-main">{state.error.title}</h4>
              <p className="mt-1 break-words text-sm leading-6">{state.error.message}</p>
              <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                <button
                  type="button"
                  onClick={handleRetry}
                  className="primary-button inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold"
                >
                  <RotateCcw size={16} />
                  {state.retryStatus === BCA_IMPORT_STATUS.SECTION_SELECTION_REQUIRED
                    ? "Kembali ke pilihan"
                    : "Coba lagi"}
                </button>
                <button
                  type="button"
                  onClick={handleCancel}
                  className="min-h-11 rounded-lg border border-[var(--color-border)] px-4 py-2 text-sm font-semibold text-muted"
                >
                  Batalkan import
                </button>
              </div>
            </div>
          </div>
        </section>
      )}

      {state.status === BCA_IMPORT_STATUS.REVIEW_READY && state.emptyResult && (
        <section className="alert-panel alert-panel--info mt-5 px-4 py-4" role="status">
          <p className="font-bold text-main">Tidak ada transaksi baru.</p>
          <p className="mt-1 text-sm leading-6">{state.emptyResult.message}</p>
          <p className="mt-2 text-xs font-semibold text-muted">
            {state.emptyResult.transactionsFound} transaksi dibaca
          </p>
          <button
            type="button"
            onClick={() => dispatch({ type: "RESET" })}
            className="mt-4 min-h-11 rounded-lg border border-[var(--color-border)] px-4 py-2 text-sm font-semibold text-accent"
          >
            Pilih file lain
          </button>
        </section>
      )}

      {state.status === BCA_IMPORT_STATUS.CANCELLED && (
        <section className="alert-panel alert-panel--info mt-5 px-4 py-4" role="status">
          <p className="font-semibold text-main">Import BCA dibatalkan.</p>
          <button
            type="button"
            onClick={() => dispatch({ type: "RESET" })}
            className="mt-3 min-h-11 rounded-lg border border-[var(--color-border)] px-4 py-2 text-sm font-semibold text-accent"
          >
            Mulai lagi
          </button>
        </section>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept="application/pdf,.pdf"
        onChange={handleFileChange}
        className="hidden"
        aria-label="Pilih PDF statement BCA"
      />
    </article>
  );
};

export default BcaImportPanel;
