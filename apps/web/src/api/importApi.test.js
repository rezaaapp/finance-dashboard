import assert from "node:assert/strict";
import test from "node:test";

import { buildImportUploadFormData } from "./importUploadFormData.js";

const syntheticPdf = new Blob(["%PDF-synthetic"], { type: "application/pdf" });

test("Blu upload form remains backward-compatible", () => {
  const formData = buildImportUploadFormData(syntheticPdf, "Synthetic Owner");

  assert.deepEqual(
    Array.from(formData.keys()),
    ["file", "statement_owner"]
  );
  assert.equal("Synthetic Owner", formData.get("statement_owner"));
  assert.equal(null, formData.get("expected_provider"));
  assert.equal(null, formData.get("expected_section_id"));
});

test("BCA discovery upload sends expected_provider without section", () => {
  const formData = buildImportUploadFormData(
    syntheticPdf,
    "Synthetic Owner",
    { expectedProvider: "bca" }
  );

  assert.equal("bca", formData.get("expected_provider"));
  assert.equal(null, formData.get("expected_section_id"));
});

test("BCA selected parse sends expected section id", () => {
  const formData = buildImportUploadFormData(
    syntheticPdf,
    "Synthetic Owner",
    {
      expectedProvider: "bca",
      expectedSectionId: "bca-section-synthetic",
    }
  );

  assert.equal("bca", formData.get("expected_provider"));
  assert.equal("bca-section-synthetic", formData.get("expected_section_id"));
});
