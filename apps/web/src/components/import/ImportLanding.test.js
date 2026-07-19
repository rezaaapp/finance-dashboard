import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const importLandingSource = readFileSync(
  new URL("./ImportLanding.jsx", import.meta.url),
  "utf8"
);
const bcaImportPanelSource = readFileSync(
  new URL("./BcaImportPanel.jsx", import.meta.url),
  "utf8"
);
const importReviewSource = readFileSync(
  new URL("./ImportReview.jsx", import.meta.url),
  "utf8"
);

test("BCA import is available through a default-on rollback flag", () => {
  assert.match(importLandingSource, /isBcaImportEnabled\(import\.meta\.env\)/);
  assert.match(
    importLandingSource,
    /bcaImportEnabled[\s\S]*<BcaImportPanel/
  );
  assert.match(bcaImportPanelSource, /Didukung/);
  assert.match(
    bcaImportPanelSource,
    /status-badge--success[^>]*>Tersedia/
  );
  assert.doesNotMatch(bcaImportPanelSource, /Uji terbatas|Feature Preview/);
});

test("Blu card remains active and uses the official provider logo", () => {
  assert.match(importLandingSource, /Blu PDF Statement/);
  assert.match(importLandingSource, /\/brands\/blu-logo-white\.png/);
  assert.match(
    importLandingSource,
    /<ProviderBadge variant="success">Tersedia<\/ProviderBadge>/
  );
  assert.doesNotMatch(importLandingSource, />Beta</);
  assert.match(importLandingSource, /Unggah dan periksa PDF/);
  assert.match(importLandingSource, /uploadImportFile\(selectedFile, statementOwner\)/);
});

test("BCA card uses the official provider logo and matches the provider grid", () => {
  assert.match(bcaImportPanelSource, /\/brands\/bca-logo-blue\.png/);
  assert.match(bcaImportPanelSource, /Unggah dan periksa PDF/);
  assert.doesNotMatch(bcaImportPanelSource, /Pilih PDF BCA/);
  assert.doesNotMatch(bcaImportPanelSource, /(?:lg|xl):col-span-2/);
  assert.doesNotMatch(bcaImportPanelSource, /Unggah e-Statement BCA, lalu pilih/);
});

test("BCA selection uses accessible single-choice controls", () => {
  assert.match(bcaImportPanelSource, /<fieldset[\s\S]*aria-describedby="bca-section-help"/);
  assert.match(bcaImportPanelSource, /type="radio"/);
  assert.match(bcaImportPanelSource, /name="bca-section"/);
  assert.match(bcaImportPanelSource, /disabled=\{!candidate\.isSelectable\}/);
  assert.match(bcaImportPanelSource, /disabled=\{!selectedCandidate \|\| requestPending\}/);
  assert.match(bcaImportPanelSource, /Tidak dapat menentukan rekening dari file ini/);
  assert.doesNotMatch(bcaImportPanelSource, /type="checkbox"/);
});

test("BCA loading, cancel, retry, and focus behavior are explicit", () => {
  assert.match(bcaImportPanelSource, /requestInFlightRef/);
  assert.match(bcaImportPanelSource, /AbortController/);
  assert.match(bcaImportPanelSource, /role="status" aria-live="polite"/);
  assert.match(bcaImportPanelSource, /selectionHeadingRef\.current\?\.focus\(\)/);
  assert.match(bcaImportPanelSource, /errorRef\.current\?\.focus\(\)/);
  assert.match(bcaImportPanelSource, /Batalkan pemeriksaan/);
  assert.match(bcaImportPanelSource, /Coba lagi/);
});

test("BCA review shows safe section context and hides adapter midnight", () => {
  assert.match(importReviewSource, /summary\.provider === "bca"/);
  assert.match(importReviewSource, /sectionContext\.display_label/);
  assert.match(importReviewSource, /sectionContext\.masked_identity/);
  assert.match(importReviewSource, /Provider: BCA/);
  assert.match(importReviewSource, /time === "00:00"/);
  assert.match(importReviewSource, /\? "-" : time/);
});
