export const buildImportUploadFormData = (
  file,
  statementOwner,
  { expectedProvider, expectedSectionId } = {}
) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("statement_owner", statementOwner);

  if (expectedProvider) {
    formData.append("expected_provider", expectedProvider);
  }

  if (expectedSectionId) {
    formData.append("expected_section_id", expectedSectionId);
  }

  return formData;
};
