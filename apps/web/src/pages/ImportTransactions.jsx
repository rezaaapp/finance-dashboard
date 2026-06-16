import { useState } from "react";

import ImportLanding from "../components/import/ImportLanding";
import ImportReview from "../components/import/ImportReview";
import {
  approveImportReview,
  getImportReview,
  rejectImportReview,
} from "../api/importApi";

const ImportTransactions = () => {
  const [activeJobId, setActiveJobId] = useState("");
  const [reviewData, setReviewData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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

  const handleReviewReady = async (uploadResult) => {
    await loadReview(uploadResult.job_id);
  };

  const handleApprove = async (payload) => {
    if (!activeJobId) {
      return;
    }

    const response = await approveImportReview(activeJobId, payload);
    setReviewData(response.review);
  };

  const handleReject = async (payload) => {
    if (!activeJobId) {
      return;
    }

    const response = await rejectImportReview(activeJobId, payload);
    setReviewData(response.review);
  };

  if (!activeJobId) {
    return (
      <ImportLanding onReviewReady={handleReviewReady} />
    );
  }

  return (
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
      }}
    />
  );
};

export default ImportTransactions;
