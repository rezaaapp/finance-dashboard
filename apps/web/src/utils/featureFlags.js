export const isBcaImportEnabled = (environment = {}) => (
  String(environment.VITE_BCA_IMPORT_ENABLED || "").toLowerCase() === "true"
);
