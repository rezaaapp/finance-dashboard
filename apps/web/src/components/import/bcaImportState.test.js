import assert from "node:assert/strict";
import test from "node:test";

import {
  BCA_IMPORT_STATUS,
  BCA_MAX_FILE_SIZE_BYTES,
  bcaImportReducer,
  createInitialBcaImportState,
  getBcaImportError,
  isBcaRequestPending,
  normalizeBcaSectionCandidates,
  validateBcaPdfFile,
} from "./bcaImportState.js";
import { isBcaImportEnabled } from "../../utils/featureFlags.js";

const syntheticPdf = {
  name: "bca-synthetic.pdf",
  type: "application/pdf",
  size: 2048,
};

const rawCandidates = [
  {
    section_id: "bca-section-main",
    display_label: "Rekening 1234567890",
    masked_identity: "1234567890",
    section_type: "account",
    transaction_count_estimate: 4,
    is_selectable: true,
  },
  {
    section_id: "bca-section-pocket",
    display_label: "Pocket 1",
    masked_identity: "**** 4321",
    section_type: "pocket",
    transaction_count_estimate: 2,
    is_selectable: true,
  },
  {
    section_id: "bca-section-empty",
    display_label: "Pocket kosong",
    masked_identity: "**** 0000",
    section_type: "pocket",
    transaction_count_estimate: 0,
    is_selectable: false,
  },
];

test("BCA feature flag is enabled by default and supports emergency rollback", () => {
  assert.equal(true, isBcaImportEnabled({}));
  assert.equal(false, isBcaImportEnabled({ VITE_BCA_IMPORT_ENABLED: "false" }));
  assert.equal(true, isBcaImportEnabled({ VITE_BCA_IMPORT_ENABLED: "true" }));
});

test("BCA file validation accepts PDF and rejects invalid or oversized files", () => {
  assert.equal(true, validateBcaPdfFile(syntheticPdf).valid);
  assert.equal(
    "invalid_file_type",
    validateBcaPdfFile({ ...syntheticPdf, name: "statement.csv", type: "text/csv" }).errorCode
  );
  assert.equal(
    "file_too_large",
    validateBcaPdfFile({ ...syntheticPdf, size: BCA_MAX_FILE_SIZE_BYTES + 1 }).errorCode
  );
});

test("candidate normalization masks full account identity and keeps empty section disabled", () => {
  const candidates = normalizeBcaSectionCandidates(rawCandidates);

  assert.equal("Rekening **** 7890", candidates[0].displayLabel);
  assert.equal("**** 7890", candidates[0].maskedIdentity);
  assert.equal(false, candidates[0].displayLabel.includes("1234567890"));
  assert.equal(false, candidates[0].maskedIdentity.includes("1234567890"));
  assert.equal(false, candidates[2].isSelectable);
  assert.equal(0, candidates[2].transactionCountEstimate);
});

test("candidate normalization disables missing ids and safely handles invalid counts", () => {
  const [candidate] = normalizeBcaSectionCandidates([{
    display_label: "Pocket synthetic",
    section_type: "pocket",
    transaction_count_estimate: "not-a-number",
    is_selectable: true,
  }]);

  assert.equal("", candidate.sectionId);
  assert.equal(0, candidate.transactionCountEstimate);
  assert.equal(false, candidate.isSelectable);
});

test("multi-section state requires an explicit single selection", () => {
  let state = bcaImportReducer(createInitialBcaImportState(), {
    type: "FILE_SELECTED",
    file: syntheticPdf,
    validation: validateBcaPdfFile(syntheticPdf),
  });
  state = bcaImportReducer(state, { type: "START_UPLOAD" });
  state = bcaImportReducer(state, {
    type: "SELECTION_REQUIRED",
    candidates: rawCandidates,
  });

  assert.equal(BCA_IMPORT_STATUS.SECTION_SELECTION_REQUIRED, state.status);
  assert.equal("", state.selectedSectionId);

  state = bcaImportReducer(state, {
    type: "SELECT_SECTION",
    sectionId: "bca-section-main",
  });
  assert.equal(BCA_IMPORT_STATUS.SECTION_SELECTED, state.status);
  assert.equal("bca-section-main", state.selectedSectionId);

  state = bcaImportReducer(state, {
    type: "SELECT_SECTION",
    sectionId: "bca-section-pocket",
  });
  assert.equal("bca-section-pocket", state.selectedSectionId);
  assert.equal(1, [state.selectedSectionId].length);
});

test("non-selectable empty section cannot replace the current selection", () => {
  let state = {
    ...createInitialBcaImportState(),
    status: BCA_IMPORT_STATUS.SECTION_SELECTION_REQUIRED,
    candidates: normalizeBcaSectionCandidates(rawCandidates),
  };
  const unchanged = bcaImportReducer(state, {
    type: "SELECT_SECTION",
    sectionId: "bca-section-empty",
  });

  assert.equal(state, unchanged);
  assert.equal("", unchanged.selectedSectionId);
});

test("invalid selection returns to candidate list without fallback selection", () => {
  let state = {
    ...createInitialBcaImportState(),
    status: BCA_IMPORT_STATUS.SECTION_SELECTED,
    file: syntheticPdf,
    candidates: normalizeBcaSectionCandidates(rawCandidates),
    selectedSectionId: "bca-section-main",
  };
  state = bcaImportReducer(state, {
    type: "FAIL",
    errorCode: "invalid_section_selection",
    retryStatus: BCA_IMPORT_STATUS.SECTION_SELECTION_REQUIRED,
  });
  state = bcaImportReducer(state, { type: "RETRY" });

  assert.equal(BCA_IMPORT_STATUS.SECTION_SELECTION_REQUIRED, state.status);
  assert.equal("", state.selectedSectionId);
});

test("cancel clears file, candidates, and selected section", () => {
  const cancelled = bcaImportReducer({
    ...createInitialBcaImportState(),
    status: BCA_IMPORT_STATUS.SECTION_SELECTED,
    file: syntheticPdf,
    candidates: normalizeBcaSectionCandidates(rawCandidates),
    selectedSectionId: "bca-section-main",
  }, { type: "CANCEL" });

  assert.equal(BCA_IMPORT_STATUS.CANCELLED, cancelled.status);
  assert.equal(null, cancelled.file);
  assert.deepEqual([], cancelled.candidates);
  assert.equal("", cancelled.selectedSectionId);
});

test("all required BCA errors resolve to safe user actions", () => {
  const codes = [
    "invalid_section_selection",
    "unsupported_statement",
    "no_parseable_transactions",
    "provider_mismatch",
    "encrypted_pdf",
    "scan_only_pdf",
    "unreadable_pdf",
    "malformed_transaction_row",
  ];

  for (const code of codes) {
    const error = getBcaImportError(code, "SENSITIVE 1234567890");
    assert.equal(code, error.errorCode);
    assert.ok(error.title.length > 0);
    assert.ok(error.message.length > 0);
    assert.equal(false, error.message.includes("1234567890"));
  }
});

test("pending status covers both discovery and selected parse requests", () => {
  assert.equal(true, isBcaRequestPending(BCA_IMPORT_STATUS.UPLOADING));
  assert.equal(true, isBcaRequestPending(BCA_IMPORT_STATUS.PARSING_SELECTED_SECTION));
  assert.equal(false, isBcaRequestPending(BCA_IMPORT_STATUS.SECTION_SELECTED));
});
