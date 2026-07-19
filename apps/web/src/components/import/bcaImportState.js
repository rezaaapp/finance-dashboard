export const BCA_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;

export const BCA_IMPORT_STATUS = Object.freeze({
  IDLE: "idle",
  FILE_SELECTED: "file_selected",
  UPLOADING: "uploading",
  SECTION_SELECTION_REQUIRED: "section_selection_required",
  SECTION_SELECTED: "section_selected",
  PARSING_SELECTED_SECTION: "parsing_selected_section",
  REVIEW_READY: "review_ready",
  ERROR: "error",
  CANCELLED: "cancelled",
});

export const createInitialBcaImportState = () => ({
  status: BCA_IMPORT_STATUS.IDLE,
  file: null,
  fileValidation: null,
  candidates: [],
  selectedSectionId: "",
  error: null,
  retryStatus: BCA_IMPORT_STATUS.FILE_SELECTED,
  emptyResult: null,
});

const maskSensitiveNumber = (value) => (
  String(value || "").replace(
    /\d(?:[\s-]?\d){5,19}/g,
    (match) => {
      const digits = match.replace(/\D/g, "");
      return digits.length >= 6 ? `**** ${digits.slice(-4)}` : match;
    }
  )
);

export const normalizeBcaSectionCandidates = (candidates = []) => (
  candidates.map((candidate, index) => {
    const sectionId = String(candidate?.section_id || "").trim();
    const sectionType = candidate?.section_type === "pocket" ? "pocket" : "account";
    const genericLabel = sectionType === "pocket"
      ? `Pocket ${index || 1}`
      : `Rekening ${index + 1}`;
    const rawTransactionCount = Number(candidate?.transaction_count_estimate || 0);
    const transactionCountEstimate = Number.isFinite(rawTransactionCount)
      ? Math.max(0, Math.trunc(rawTransactionCount))
      : 0;

    return {
      sectionId,
      displayLabel: maskSensitiveNumber(candidate?.display_label) || genericLabel,
      maskedIdentity: maskSensitiveNumber(candidate?.masked_identity) || "Identity dimasking",
      sectionType,
      transactionCountEstimate,
      isSelectable: Boolean(candidate?.is_selectable && sectionId),
    };
  })
);

export const validateBcaPdfFile = (file) => {
  if (!file) {
    return {
      valid: false,
      errorCode: "missing_file",
      message: "Pilih file PDF BCA terlebih dahulu.",
    };
  }

  const filename = String(file.name || "");
  const contentType = String(file.type || "").toLowerCase();
  const hasPdfExtension = filename.toLowerCase().endsWith(".pdf");
  const hasPdfContentType = !contentType || [
    "application/pdf",
    "application/x-pdf",
  ].includes(contentType);

  if (!hasPdfExtension || !hasPdfContentType) {
    return {
      valid: false,
      errorCode: "invalid_file_type",
      message: "File harus berupa PDF statement BCA.",
    };
  }

  if (Number(file.size || 0) <= 0) {
    return {
      valid: false,
      errorCode: "empty_file",
      message: "File PDF kosong dan tidak dapat diperiksa.",
    };
  }

  if (Number(file.size) > BCA_MAX_FILE_SIZE_BYTES) {
    return {
      valid: false,
      errorCode: "file_too_large",
      message: "Ukuran PDF melebihi batas 10 MB.",
    };
  }

  return {
    valid: true,
    errorCode: null,
    message: "File PDF siap diperiksa.",
  };
};

export const formatBcaFileSize = (size) => {
  const bytes = Math.max(0, Number(size || 0));
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const errorDefinitions = {
  invalid_section_selection: {
    title: "Pilihan rekening tidak valid",
    message: "Pilih ulang rekening atau Pocket dari daftar hasil pemeriksaan file.",
  },
  unsupported_statement: {
    title: "Format statement belum didukung",
    message: "Gunakan e-Statement rekening BCA personal yang didukung.",
  },
  no_parseable_transactions: {
    title: "Tidak ada transaksi yang dapat diproses",
    message: "Pilih rekening lain atau gunakan statement dengan transaksi yang tersedia.",
  },
  provider_mismatch: {
    title: "File bukan statement BCA yang sesuai",
    message: "Periksa kembali file dan pilih PDF statement dari provider yang benar.",
  },
  encrypted_pdf: {
    title: "PDF dilindungi password",
    message: "Gunakan salinan PDF tanpa password, lalu coba lagi.",
  },
  scan_only_pdf: {
    title: "Teks PDF tidak dapat dibaca",
    message: "Gunakan e-Statement asli, bukan hasil scan atau foto.",
  },
  unreadable_pdf: {
    title: "PDF tidak dapat dibaca",
    message: "Unduh ulang statement BCA dan coba lagi.",
  },
  malformed_transaction_row: {
    title: "Ada transaksi yang tidak dapat dibaca",
    message: "Gunakan statement asli dengan format tabel yang lengkap.",
  },
  network_error: {
    title: "Koneksi terputus",
    message: "File tetap tersedia. Periksa koneksi dan coba lagi.",
  },
};

export const getBcaImportError = (errorCode, fallbackMessage = "") => {
  const safeError = errorDefinitions[errorCode] || {
    title: "Import BCA belum berhasil",
    message: "Coba lagi atau pilih file PDF BCA lain.",
  };

  return {
    errorCode: errorCode || "upload_failed",
    title: safeError.title,
    message: safeError.message || fallbackMessage,
  };
};

export const isBcaRequestPending = (status) => [
  BCA_IMPORT_STATUS.UPLOADING,
  BCA_IMPORT_STATUS.PARSING_SELECTED_SECTION,
].includes(status);

export const bcaImportReducer = (state, event) => {
  switch (event.type) {
    case "FILE_SELECTED":
      return {
        ...createInitialBcaImportState(),
        status: BCA_IMPORT_STATUS.FILE_SELECTED,
        file: event.file,
        fileValidation: event.validation,
      };
    case "START_UPLOAD":
      return {
        ...state,
        status: BCA_IMPORT_STATUS.UPLOADING,
        error: null,
        emptyResult: null,
      };
    case "SELECTION_REQUIRED":
      return {
        ...state,
        status: BCA_IMPORT_STATUS.SECTION_SELECTION_REQUIRED,
        candidates: normalizeBcaSectionCandidates(event.candidates),
        selectedSectionId: "",
        error: null,
      };
    case "SELECT_SECTION": {
      const selectedCandidate = state.candidates.find(
        (candidate) => candidate.sectionId === event.sectionId
      );
      if (!selectedCandidate?.isSelectable) {
        return state;
      }
      return {
        ...state,
        status: BCA_IMPORT_STATUS.SECTION_SELECTED,
        selectedSectionId: selectedCandidate.sectionId,
        error: null,
      };
    }
    case "CHANGE_SELECTION":
      return {
        ...state,
        status: BCA_IMPORT_STATUS.SECTION_SELECTION_REQUIRED,
        selectedSectionId: "",
        error: null,
      };
    case "START_SELECTED_PARSE":
      return {
        ...state,
        status: BCA_IMPORT_STATUS.PARSING_SELECTED_SECTION,
        error: null,
      };
    case "REVIEW_READY":
      return {
        ...state,
        status: BCA_IMPORT_STATUS.REVIEW_READY,
        error: null,
        emptyResult: event.emptyResult || null,
      };
    case "FAIL":
      return {
        ...state,
        status: BCA_IMPORT_STATUS.ERROR,
        error: getBcaImportError(event.errorCode, event.message),
        retryStatus: event.retryStatus || BCA_IMPORT_STATUS.FILE_SELECTED,
      };
    case "RETRY":
      return {
        ...state,
        status: state.retryStatus,
        error: null,
        selectedSectionId: state.retryStatus === BCA_IMPORT_STATUS.SECTION_SELECTION_REQUIRED
          ? ""
          : state.selectedSectionId,
      };
    case "CANCEL":
      return {
        ...createInitialBcaImportState(),
        status: BCA_IMPORT_STATUS.CANCELLED,
      };
    case "RESET":
      return createInitialBcaImportState();
    default:
      return state;
  }
};
