import { useState } from "react";

import { startGoogleOAuth } from "../api/googleOAuthApi";
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

const ImportTransactions = () => {
  const [activeTab, setActiveTab] = useState("upload");
  const [activeJobId, setActiveJobId] = useState("");
  const [reviewData, setReviewData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [historyRows, setHistoryRows] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [historyDetail, setHistoryDetail] = useState(null);
  const [historyDetailLoading, setHistoryDetailLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState("");
  const [categoryOptions, setCategoryOptions] = useState([]);
  const [categoryOptionsLoading, setCategoryOptionsLoading] = useState(false);
  const [categoryOptionsError, setCategoryOptionsError] = useState("");
  const [reviewActionError, setReviewActionError] = useState(null);

  const loadReview = async (jobId) => {
    setLoading(true);
    setError("");
    setReviewActionError(null);
    setActiveJobId(jobId);
    setCategoryOptionsLoading(true);
    setCategoryOptionsError("");

    try {
      const [reviewResult, categoryResult] = await Promise.allSettled([
        getImportReview(jobId),
        getImportCategoryOptions(),
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
    } catch (reviewError) {
      setError(
        reviewError?.response?.data?.detail
        || "Review import belum bisa dimuat."
      );
      setReviewData(null);
    } finally {
      setLoading(false);
      setCategoryOptionsLoading(false);
    }
  };

  const loadHistory = async () => {
    setHistoryLoading(true);
    setHistoryError("");

    try {
      const response = await getImportHistory();
      setHistoryRows(response.jobs || []);
    } catch (historyLoadError) {
      setHistoryError(
        historyLoadError?.response?.data?.detail
        || "Riwayat import belum bisa dimuat."
      );
    } finally {
      setHistoryLoading(false);
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

    try {
      const response = await approveImportReview(activeJobId, payload);
      setReviewData(response.review);
      await loadHistory();
    } catch (approveError) {
      const responsePayload = approveError?.response?.data || {};

      setReviewActionError({
        errorCode: responsePayload.error_code || "approval_failed",
        message: responsePayload.message || "Approval import belum bisa diproses.",
      });
    }
  };

  const handleReject = async (payload) => {
    if (!activeJobId) {
      return;
    }

    setReviewActionError(null);

    const response = await rejectImportReview(activeJobId, payload);
    setReviewData(response.review);
    await loadHistory();
  };

  const handleRetrySync = async (jobId) => {
    setActionLoading(`retry:${jobId}`);

    try {
      await retryImportSync(jobId);
      await loadHistory();

      if (historyDetail?.job_id === jobId) {
        await loadHistoryDetail(jobId);
      }
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
            onApprove={handleApprove}
            onReject={handleReject}
            categoryOptions={categoryOptions}
            categoryOptionsLoading={categoryOptionsLoading}
            categoryOptionsError={categoryOptionsError}
            onBack={() => {
              setActiveJobId("");
              setReviewData(null);
              setError("");
              setReviewActionError(null);
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
          onRefresh={loadHistory}
          onRetrySync={handleRetrySync}
          onViewDetail={loadHistoryDetail}
          onReconnectGoogle={handleReconnectGoogle}
        />
      )}
    </div>
  );
};

export default ImportTransactions;
