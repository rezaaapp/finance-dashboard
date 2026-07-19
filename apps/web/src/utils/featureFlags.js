export const isBcaImportEnabled = (environment = {}) => {
  const configuredValue = String(
    environment.VITE_BCA_IMPORT_ENABLED ?? "true"
  ).toLowerCase();

  return configuredValue !== "false";
};
