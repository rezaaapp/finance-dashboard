import { useEffect, useState } from "react";

import { startGoogleOAuth } from "../api/googleOAuthApi";
import {
  getGoogleSheetSources,
  getGoogleSheetSourceWorksheets,
} from "../api/googleSheetSourcesApi";
import {
  approveImportReview,
  getImportCategoryOptions,
  getImportHistory,
  getImportHistoryDetail,
  getImportReview,
  rejectImportReview,
  retryImportSync,
} from "../api/importApi";
import ImportLanding from "../components/import/ImportLanding";
import ImportHistory from "../components/import/ImportHistory";
import ImportReview from "../components/import/ImportReview";
import {
  buildApproveFeedback,
  buildRetryFeedback,
} from "../components/import/deliveryStatusUx";

const REVIEW_PAGE_SIZE = 100;
const HISTORY_PAGE_SIZE = 20;

const suggestTargetSheetName = ({ filename = "", worksheets = [], source = null }) => {
  const normalizedFilename = String(filename || "").toLowerCase();

  if (/(juni|jun)/i.test(normalizedFilename)) {
    const juneMatch = worksheets.find((worksheet) => (
      /(juni|jun)/i.test(String(worksheet || ""))
    ));

    if (juneMatch) {
      return juneMatch;
    }
  }

  if (source?.sheet_name && worksheets.includes(source.sheet_name)) {
    return source.sheet_name;
  }

  if (worksheets.length === 1) {
    return worksheets[0];
  }

  return "";
};

const ImportTransactions = () => {
  const [activeTab, setActiveTab] = useState("upload");
  const [activeJobId, setActiveJobId] = useState("");
  const [reviewData, setReviewData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [reviewPagination, setReviewPagination] = useState(null);
  const [historyRows, setHistoryRows] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [historyPagination, setHistoryPagination] = useState(null);
  const [historyDetail, setHistoryDetail] = useState(null);
  const [historyDetailLoading, setHistoryDetailLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState("");
  const [categoryOptions, setCategoryOptions] = useState([]);
  const [categoryOptionsLoading, setCategoryOptionsLoading] = useState(false);
  const [categoryOptionsError, setCategoryOptionsError] = useState("");
  const [reviewActionError, setReviewActionError] = useState(null);
  const [reviewActionFeedback, setReviewActionFeedback] = useState(null);
  const [sheetSources, setSheetSources] = useState([]);
  const [sheetSourcesLoading, setSheetSourcesLoading] = useState(false);
  const [sheetSourcesError, setSheetSourcesError] = useState("");
  const [targetSourceId, setTargetSourceId] = useState("");
  const [worksheets, setWorksheets] = useState([]);
  const [worksheetsLoading, setWorksheetsLoading] = useState(false);
  const [worksheetsError, setWorksheetsError] = useState("");
  const [targetSheetName, setTargetSheetName] = useState("");
  const [historyRetryResult, setHistoryRetryResult] = useState(null);

  useEffect(() => {
    if (!targetSourceId) {
      setWorksheets([]);
      setTargetSheetName("");
      return;
    }

    let ignore = false;
    const selectedSource = sheetSources.find((source) => source.source_id === targetSourceId) || null;

    const loadWorksheets = async () => {
      setWorksheetsLoading(true);
      setWorksheetsError("");

      try {
        const response = await getGoogleSheetSourceWorksheets(targetSourceId);
        const nextWorksheets = response.worksheets || [];

        if (ignore) {
          return;
        }

        setWorksheets(nextWorksheets);
        setTargetSheetName((current) => (
          current && nextWorksheets.includes(current)
            ? current
            : suggestTargetSheetName({
              filename: reviewData?.summary?.filename,
              worksheets: nextWorksheets,
              source: selectedSource,
            })
        ));
      } catch (worksheetError) {
        if (ignore) {
          return;
        }

        setWorksheets([]);
        setTargetSheetName("");
        setWorksheetsError(
          worksheetError?.response?.data?.detail
          || "Daftar tab Google Sheets belum bisa dimuat."
        );
      } finally {
        if (!ignore) {
          setWorksheetsLoading(false);
        }
      }
    };

    loadWorksheets();

    return () => {
      ignore = true;
    };
  }, [targetSourceId, sheetSources, reviewData?.summary?.filename]);

  const loadReview = async (jobId, options = {}) => {
    const nextOffset = options.offset ?? 0;
    const preserveData = Boolean(options.preserveData);

    setLoading(true);
    if (!preserveData) {
      setError("");
      setReviewActionError(null);
      setReviewActionFeedback(null);
    }
    setActiveJobId(jobId);
    setCategoryOptionsLoading(true);
    setCategoryOptionsError("");
    setSheetSourcesLoading(true);
    if (!preserveData) {
      setSheetSourcesError("");
      setWorksheets([]);
      setWorksheetsError("");
      setTargetSheetName("");
    }

    try {
      const [reviewResult, categoryResult, sourcesResult] = await Promise.allSettled([
        getImportReview(jobId, {
          limit: REVIEW_PAGE_SIZE,
          offset: nextOffset,
        }),
        getImportCategoryOptions(),
        getGoogleSheetSources(),
      ]);

      if (categoryResult.status === "fulfilled") {
        setCategoryOptions(categoryResult.value.categories || []);
      } else {
        setCategoryOptions([]);
        setCategoryOptionsError(
          categoryResult.reason?.response?.data?.detail
          || "Kategori transaksi belum bisa dimuat. Review tetap bisa dilanjutkan."
        );
      }

      if (reviewResult.status === "rejected") {
        throw reviewResult.reason;
      }

      setReviewData(reviewResult.value);
      setReviewPagination(reviewResult.value.pagination || null);

      if (sourcesResult.status === "fulfilled") {
        const sources = sourcesResult.value.sources || [];
        const defaultSource = (
          sources.find((source) => source.status === "active")
          || sources[0]
          || null
        );

        setSheetSources(sources);
        setTargetSourceId(defaultSource?.source_id || "");
      } else {
        setSheetSources([]);
        setTargetSourceId("");
        setSheetSourcesError(
          sourcesResult.reason?.response?.data?.detail
          || "Daftar Google Sheets belum bisa dimuat."
        );
      }
    } catch (reviewError) {
      setError(
        reviewError?.response?.data?.detail
        || "Review import belum bisa dimuat."
      );
      if (!preserveData) {
        setReviewData(null);
        setReviewPagination(null);
      }
    } finally {
      setLoading(false);
      setCategoryOptionsLoading(false);
      setSheetSourcesLoading(false);
    }
  };

  const loadHistory = async (options = {}) => {
    const nextOffset = options.offset ?? 0;
    const preserveData = Boolean(options.preserveData);

    setHistoryLoading(true);
    if (!preserveData) {
      setHistoryError("");
    }
    setSheetSourcesLoading(true);
    if (!preserveData) {
      setSheetSourcesError("");
    }

    try {
      const [historyResult, sourcesResult] = await Promise.allSettled([
        getImportHistory({
          limit: HISTORY_PAGE_SIZE,
          offset: nextOffset,
        }),
        getGoogleSheetSources(),
      ]);

      if (historyResult.status === "rejected") {
        throw historyResult.reason;
      }

      setHistoryRows(historyResult.value.jobs || []);
      setHistoryPagination(historyResult.value.pagination || null);

      if (sourcesResult.status === "fulfilled") {
        const sources = sourcesResult.value.sources || [];
        const defaultSource = (
          sources.find((source) => source.status === "active")
          || sources[0]
          || null
        );

        setSheetSources(sources);
        setTargetSourceId((current) => current || defaultSource?.source_id || "");
      } else {
        setSheetSources([]);
        setTargetSourceId("");
        setSheetSourcesError(
          sourcesResult.reason?.response?.data?.detail
          || "Daftar Google Sheets belum bisa dimuat."
        );
      }
    } catch (historyLoadError) {
      setHistoryError(
        historyLoadError?.response?.data?.detail
        || "Riwayat import belum bisa dimuat."
      );
      if (!preserveData) {
        setHistoryRows([]);
        setHistoryPagination(null);
      }
    } finally {
      setHistoryLoading(false);
      setSheetSourcesLoading(false);
    }
  };

  const loadHistoryDetail = async (jobId) => {
    setHistoryDetailLoading(true);

    try {
      const response = await getImportHistoryDetail(jobId);
      setHistoryDetail(response);
    } catch (historyDetailError) {
      setHistoryError(
        historyDetailError?.response?.data?.detail
        || "Detail import belum bisa dimuat."
      );
      setHistoryDetail(null);
    } finally {
      setHistoryDetailLoading(false);
    }
  };

  const handleReviewReady = async (uploadResult) => {
    await loadReview(uploadResult.job_id);
    setActiveTab("review");
  };

  const handleSwitchTab = async (tabId) => {
    setActiveTab(tabId);

    if (tabId === "history") {
      await loadHistory();
    }
  };

  const handleApprove = async (payload) => {
    if (!activeJobId) {
      return;
    }

    setReviewActionError(null);
    setReviewActionFeedback(null);

    try {
      const response = await approveImportReview(activeJobId, payload);
      setReviewData(response.review);
      setReviewPagination(response.review?.pagination || null);
      setReviewActionFeedback(buildApproveFeedback(response));

      await loadHistory();
      return response;
    } catch (approveError) {
      const responsePayload = approveError?.response?.data || {};

      setReviewActionError({
        errorCode: responsePayload.error_code || "approval_failed",
        message: responsePayload.message || "Approval import belum bisa diproses.",
      });
      return null;
    }
  };

  const handleReject = async (payload) => {
    if (!activeJobId) {
      return;
    }

    setReviewActionError(null);
    setReviewActionFeedback(null);

    const response = await rejectImportReview(activeJobId, payload);
    setReviewData(response.review);
    setReviewPagination(response.review?.pagination || null);
    await loadHistory();
  };

  const handleRetrySync = async (jobId) => {
    setActionLoading(`retry:${jobId}`);
    setHistoryRetryResult(null);

    try {
      const response = await retryImportSync(jobId, {
        sheet_source_id: targetSourceId,
        sheet_name: targetSheetName,
      });
      setHistoryRetryResult(buildRetryFeedback(response));
      await loadHistory();

      if (historyDetail?.job_id === jobId) {
        await loadHistoryDetail(jobId);
      }
    } catch (retryError) {
      const responsePayload = retryError?.response?.data || {};

        setHistoryRetryResult({
          ...buildRetryFeedback({
            status: "failed",
            sync_status: responsePayload.sync_status || "failed",
            message: responsePayload.message || responsePayload.detail || "Retry pengiriman belum berhasil.",
            sync_error_message: responsePayload.message || responsePayload.detail || "Retry pengiriman belum berhasil.",
          }),
        });
    } finally {
      setActionLoading("");
    }
  };

  const handleReconnectGoogle = async () => {
    const response = await startGoogleOAuth();

    if (response?.auth_url) {
      window.location.href = response.auth_url;
    }
  };

  const tabs = [
    { id: "upload", label: "Upload" },
    { id: "review", label: "Review" },
    { id: "history", label: "History" },
  ];

  return (
    <div className="grid grid-cols-1 gap-6">
      <section className="panel rounded-lg p-3 shadow-lg">
        <div className="flex flex-wrap gap-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => handleSwitchTab(tab.id)}
              className={`inline-flex min-h-11 items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold transition-colors ${
                activeTab === tab.id
                  ? "bg-[var(--color-accent-strong)] text-white"
                  : "bg-[var(--color-panel-hover)] text-muted hover:text-accent"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </section>

      {activeTab === "upload" && (
        <ImportLanding onReviewReady={handleReviewReady} />
      )}

      {activeTab === "review" && (
        activeJobId ? (
          <ImportReview
            reviewData={reviewData}
            loading={loading}
            error={error}
            actionError={reviewActionError}
            actionFeedback={reviewActionFeedback}
            onApprove={handleApprove}
            onReject={handleReject}
            sheetSources={sheetSources}
            sheetSourcesLoading={sheetSourcesLoading}
            sheetSourcesError={sheetSourcesError}
            targetSourceId={targetSourceId}
            targetSheetName={targetSheetName}
            worksheets={worksheets}
            worksheetsLoading={worksheetsLoading}
            worksheetsError={worksheetsError}
            onTargetSourceChange={(nextSourceId) => {
              setTargetSourceId(nextSourceId);
              setTargetSheetName("");
              setReviewActionError(null);
              setReviewActionFeedback(null);
            }}
            onTargetSheetChange={(nextSheetName) => {
              setTargetSheetName(nextSheetName);
              setReviewActionError(null);
              setReviewActionFeedback(null);
            }}
            categoryOptions={categoryOptions}
            categoryOptionsLoading={categoryOptionsLoading}
            categoryOptionsError={categoryOptionsError}
            pagination={reviewPagination}
            onPageChange={(nextOffset) => loadReview(activeJobId, {
              offset: nextOffset,
              preserveData: true,
            })}
            onBack={() => {
              setActiveJobId("");
              setReviewData(null);
              setReviewPagination(null);
              setError("");
              setReviewActionError(null);
              setSheetSources([]);
              setTargetSourceId("");
              setWorksheets([]);
              setTargetSheetName("");
              setSheetSourcesError("");
              setWorksheetsError("");
              setCategoryOptions([]);
              setCategoryOptionsError("");
              setActiveTab("upload");
            }}
          />
        ) : (
          <div className="panel rounded-lg p-6 shadow-lg">
            <p className="text-sm text-muted">
              Belum ada job review aktif. Upload PDF dulu untuk mulai review.
            </p>
          </div>
        )
      )}

      {activeTab === "history" && (
        <ImportHistory
          historyRows={historyRows}
          selectedDetail={historyDetail}
          loading={historyLoading}
          detailLoading={historyDetailLoading}
          error={historyError}
          actionLoading={actionLoading}
          pagination={historyPagination}
          onRefresh={() => loadHistory({
            offset: historyPagination?.offset || 0,
            preserveData: historyRows.length > 0,
          })}
          onPageChange={(nextOffset) => loadHistory({
            offset: nextOffset,
            preserveData: true,
          })}
          onRetrySync={handleRetrySync}
          onViewDetail={loadHistoryDetail}
          onReconnectGoogle={handleReconnectGoogle}
          sheetSources={sheetSources}
          sheetSourcesLoading={sheetSourcesLoading}
          sheetSourcesError={sheetSourcesError}
          targetSourceId={targetSourceId}
          targetSheetName={targetSheetName}
          worksheets={worksheets}
          worksheetsLoading={worksheetsLoading}
          worksheetsError={worksheetsError}
          retryResult={historyRetryResult}
          onTargetSourceChange={(nextSourceId) => {
            setTargetSourceId(nextSourceId);
            setTargetSheetName("");
            setHistoryRetryResult(null);
          }}
          onTargetSheetChange={(nextSheetName) => {
            setTargetSheetName(nextSheetName);
            setHistoryRetryResult(null);
          }}
        />
      )}
    </div>
  );
};

export default ImportTransactions;
