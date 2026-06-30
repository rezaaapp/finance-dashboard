const ENVIRONMENT_PRESENTATION = {
  "local-dev": {
    badgeLabel: "LOCAL-DEV",
    title: "Development Environment",
    databaseLabel: "PostgreSQL Local",
    tone: "dev",
  },
  "local-prod": {
    badgeLabel: "LOCAL-PROD",
    title: "Production Simulation",
    databaseLabel: "Supabase",
    tone: "prod",
  },
  unknown: {
    badgeLabel: "UNKNOWN",
    title: "Environment Unavailable",
    databaseLabel: "Unknown",
    tone: "unknown",
  },
};

export const getEnvironmentPresentation = (appEnv) => (
  ENVIRONMENT_PRESENTATION[appEnv] || ENVIRONMENT_PRESENTATION.unknown
);

export const sanitizeApiUrl = (value) => {
  const rawValue = String(value || "").trim();

  if (!rawValue) {
    return "Not configured";
  }

  try {
    const url = new URL(rawValue);
    return `${url.protocol}//${url.host}`;
  } catch {
    return rawValue.startsWith("/") ? "Same origin" : "Invalid API URL";
  }
};

export const createSystemInfoFallback = ({ apiUrl, frontendPort = null, version }) => ({
  appEnv: "unknown",
  envProfile: "unknown",
  dbTarget: "unknown",
  backendPort: null,
  databaseHost: "Unavailable",
  databaseName: "Unavailable",
  importTempDir: "Unavailable",
  latestMigration: "Unavailable",
  migrationCount: null,
  apiUrl: sanitizeApiUrl(apiUrl),
  frontendPort,
  version,
  connected: false,
});

export const normalizeSystemInfo = (
  rawInfo,
  { apiUrl, frontendPort = null, version },
) => {
  const appEnv = ["local-dev", "local-prod"].includes(rawInfo?.app_env)
    ? rawInfo.app_env
    : "unknown";
  const safeApiUrl = sanitizeApiUrl(apiUrl);
  return {
    appEnv,
    envProfile: String(rawInfo?.env_profile || appEnv || "unknown"),
    dbTarget: String(rawInfo?.db_target || "unknown"),
    backendPort: Number(rawInfo?.backend_port) || null,
    databaseHost: String(rawInfo?.database_host || "Unavailable"),
    databaseName: String(rawInfo?.database_name || "Unavailable"),
    importTempDir: String(rawInfo?.import_temp_dir || "Unavailable"),
    latestMigration: String(rawInfo?.latest_migration || "Unavailable"),
    migrationCount: Number.isFinite(Number(rawInfo?.migration_count))
      ? Number(rawInfo.migration_count)
      : null,
    apiUrl: safeApiUrl,
    frontendPort,
    version,
    connected: true,
  };
};
