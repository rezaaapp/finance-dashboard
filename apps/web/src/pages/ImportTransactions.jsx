import { useState } from "react";

import { startGoogleOAuth } from "../api/googleOAuthApi";
import {
  getImportHistory,
  getImportHistoryDetail,
  retryImportSync,
} from "../api/importApi";
import ImportLanding from "../components/import/ImportLanding";
import ImportHistory from "../components/import/ImportHistory";
import ImportReview from "../components/import/ImportReview";
import {
  approveImportReview,
  getImportReview,
  rejectImportReview,
} from "../api/importApi";

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

  const loadReview = async (jobId) => {
    setLoading(true);
    setError("");
    setActiveJobId(jobId);

    try {
      const review = await getImportReview(jobId);
      setReviewData(review);
    } catch (reviewError) {
      setError(
        reviewError?.response?.data?.detail
        || "Review import belum bisa dimuat."
      );
      setReviewData(null);
    } finally {
      setLoading(false);
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

    const response = await approveImportReview(activeJobId, payload);
    setReviewData(response.review);
    await loadHistory();
  };

  const handleReject = async (payload) => {
    if (!activeJobId) {
      return;
    }

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
            onApprove={handleApprove}
            onReject={handleReject}
            onBack={() => {
              setActiveJobId("");
              setReviewData(null);
              setError("");
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
