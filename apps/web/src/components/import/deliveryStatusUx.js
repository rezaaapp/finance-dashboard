const normalizeText = (value) => String(value || "").trim().toLowerCase();

const collectSyncMessages = (job = {}) => {
  const messages = new Set();

  const directMessage = normalizeText(job.sync_error_message);
  if (directMessage) {
    messages.add(directMessage);
  }

  (job.unsynced_transactions || []).forEach((transaction) => {
    const message = normalizeText(transaction?.sync_error_message);
    if (message) {
      messages.add(message);
    }
  });

  return Array.from(messages);
};

export const isMissingTargetSheetMessage = (message = "") => {
  const normalized = normalizeText(message);

  return [
    "tab tujuan",
    "target spreadsheet",
    "target sheet",
    "format kolom transaksi",
    "kolom transaksi yang sesuai",
    "sheet header",
  ].some((keyword) => normalized.includes(keyword));
};

export const isUnconfiguredSpreadsheetMessage = (message = "") => (
  normalizeText(message).includes("target spreadsheet belum dikonfigurasi")
);

export const getSpreadsheetDeliveryStatus = (job = {}) => {
  const approvedCount = Number(job.approved_transactions || 0);
  const syncSuccess = Number(job.sync_success ?? job.sync_success_count ?? 0);
  const syncFailed = Number(job.sync_failed ?? job.sync_failed_count ?? 0);
  const retryableCount = Number(job.retryable_sync_count ?? job.unsynced_count ?? syncFailed ?? 0);
  const needsReconnect = Boolean(job.needs_reconnect);
  const spreadsheetUnconfigured = Boolean(job.spreadsheet_unconfigured);
  const syncMessages = collectSyncMessages(job);
  const isUnconfigured = spreadsheetUnconfigured || syncMessages.some((message) => isUnconfiguredSpreadsheetMessage(message));
  const hasMissingTargetSheet = syncMessages.some((message) => isMissingTargetSheetMessage(message));

  if (approvedCount <= 0) {
    return {
      key: "not_started",
      tone: "default",
      label: "Belum ada pengiriman",
      summary: "Belum ada transaksi yang disimpan di Omon, jadi belum ada salinan yang dikirim ke Spreadsheet.",
    };
  }

  if (needsReconnect) {
    return {
      key: "needs_reconnect",
      tone: "warning",
      label: "Perlu hubungkan ulang Google",
      summary: "Transaksi sudah tersimpan di Omon, tetapi akses Google perlu dihubungkan ulang sebelum pengiriman Spreadsheet dilanjutkan.",
    };
  }

  if (isUnconfigured) {
    return {
      key: "not_configured",
      tone: "warning",
      label: "Spreadsheet belum terhubung",
      summary: "Transaksi sudah tersimpan di Omon. Sinkronisasi Spreadsheet dapat dilakukan setelah Google Sheet terhubung.",
    };
  }

  if (hasMissingTargetSheet) {
    return {
      key: "missing_target_sheet",
      tone: "warning",
      label: "Tab tujuan belum siap",
      summary: "Transaksi sudah tersimpan di Omon, tetapi tab tujuan Spreadsheet belum tersedia atau format kolomnya belum sesuai.",
    };
  }

  if (syncSuccess > 0 && retryableCount <= 0 && syncFailed <= 0) {
    return {
      key: "succeeded",
      tone: "success",
      label: "Spreadsheet berhasil",
      summary: `${syncSuccess} transaksi sudah berhasil dikirim ke Google Spreadsheet.`,
    };
  }

  if (syncSuccess > 0 && retryableCount > 0) {
    return {
      key: "pending",
      tone: "warning",
      label: "Spreadsheet pending",
      summary: `${syncSuccess} transaksi sudah terkirim, tetapi ${retryableCount} transaksi masih perlu dikirim ulang ke Google Spreadsheet.`,
    };
  }

  if (syncFailed > 0 || retryableCount > 0) {
    return {
      key: "failed",
      tone: "danger",
      label: "Spreadsheet gagal",
      summary: "Transaksi sudah tersimpan di Omon, tetapi pengiriman ke Google Spreadsheet gagal dan perlu retry pengiriman.",
    };
  }

  return {
    key: "pending",
    tone: "warning",
    label: "Spreadsheet pending",
    summary: "Transaksi sudah tersimpan di Omon, tetapi status pengiriman ke Google Spreadsheet masih menunggu tindak lanjut.",
  };
};

export const getOmonApprovalStatus = (job = {}) => {
  const approvedCount = Number(job.approved_transactions || 0);
  const rejectedCount = Number(job.rejected_transactions || 0);

  if (approvedCount > 0) {
    return {
      tone: "success",
      label: "Tersimpan di Omon",
      summary: `${approvedCount} transaksi final sudah tersimpan di Omon.`,
    };
  }

  if (rejectedCount > 0) {
    return {
      tone: "warning",
      label: "Tidak disimpan",
      summary: `${rejectedCount} transaksi ditolak saat review dan tidak disimpan ke Omon.`,
    };
  }

  return {
    tone: "default",
    label: "Menunggu review",
    summary: "Belum ada transaksi final yang disimpan ke Omon untuk import ini.",
  };
};

export const buildApproveFeedback = (response = {}) => {
  const syncStatus = response.sync_status;
  const syncSuccess = Number(response.sync_success || 0);
  const syncFailed = Number(response.sync_failed || 0);
  const detail = response.sync_error_message || "";

  if (syncStatus === "success" && syncFailed === 0) {
    return {
      tone: "success",
      title: "Approval selesai dan transaksi tersimpan di Omon.",
      message: syncSuccess > 0
        ? "Salinan transaksi juga berhasil dikirim ke Google Spreadsheet."
        : "Tidak ada salinan Spreadsheet yang perlu dikirim untuk approval ini.",
      detail,
    };
  }

  if (syncStatus === "skipped") {
    return {
      tone: "warning",
      title: "Approval selesai dan transaksi tersimpan di Omon.",
      message: "Sinkronisasi Spreadsheet dapat dilakukan setelah Google Sheet terhubung.",
      detail,
    };
  }

  if (syncStatus === "needs_reconnect") {
    return {
      tone: "warning",
      title: "Approval selesai dan transaksi tersimpan di Omon.",
      message: "Pengiriman ke Google Spreadsheet tertunda karena akun Google perlu dihubungkan ulang.",
      detail,
    };
  }

  return {
      tone: "warning",
      title: "Approval selesai dan transaksi tersimpan di Omon.",
      message: syncSuccess > 0
        ? `Sebagian salinan Spreadsheet berhasil dikirim, tetapi ${syncFailed} transaksi masih perlu retry pengiriman.`
        : "Salinan ke Google Spreadsheet belum berhasil dikirim. Lanjutkan dari Import History dengan retry pengiriman.",
      detail,
    };
};

export const buildRetryFeedback = (response = {}) => {
  const syncStatus = response.sync_status || response.status;
  const syncSuccess = Number(response.sync_success || 0);
  const syncFailed = Number(response.sync_failed || 0);
  const detail = response.sync_error_message || response.message || "";

  if (syncStatus === "skipped") {
    return {
      tone: "default",
      title: "Tidak ada pengiriman ulang yang diperlukan.",
      message: response.message || "Semua transaksi yang disetujui sudah sinkron ke Google Spreadsheet.",
      detail: "",
    };
  }

  if (syncStatus === "success" || response.status === "completed") {
    return {
      tone: "success",
      title: "Retry pengiriman selesai.",
      message: syncFailed > 0
        ? `${syncSuccess} transaksi berhasil dikirim, ${syncFailed} transaksi masih belum berhasil.`
        : `${syncSuccess} transaksi berhasil dikirim ke Google Spreadsheet.`,
      detail: syncFailed > 0 ? detail : "",
    };
  }

  if (syncStatus === "needs_reconnect") {
    return {
      tone: "warning",
      title: "Retry pengiriman tertunda.",
      message: "Transaksi di Omon tetap aman, tetapi akun Google perlu dihubungkan ulang sebelum pengiriman Spreadsheet dilanjutkan.",
      detail,
    };
  }

    return {
      tone: "warning",
      title: "Retry pengiriman belum berhasil.",
      message: "Transaksi di Omon tetap aman, tetapi pengiriman ke Google Spreadsheet masih gagal.",
      detail,
    };
};

export const getReadableSyncStatus = (transaction = {}) => {
  const syncStatus = normalizeText(transaction.sync_status);
  const syncMessage = normalizeText(transaction.sync_error_message);

  if (syncStatus === "success") {
    return "Spreadsheet berhasil";
  }

  if (syncStatus === "needs_reconnect" || syncMessage === "needs_reconnect") {
    return "Perlu hubungkan ulang Google";
  }

  if (isUnconfiguredSpreadsheetMessage(syncMessage)) {
    return "Spreadsheet belum terhubung";
  }

  if (isMissingTargetSheetMessage(syncMessage)) {
    return "Tab tujuan belum siap";
  }

  if (syncStatus === "failed") {
    return "Spreadsheet gagal";
  }

  if (syncStatus === "pending") {
    return "Spreadsheet pending";
  }

  return transaction.sync_status || "Spreadsheet pending";
};
