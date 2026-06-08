const DEFAULT_LOCAL_API_URL = "http://127.0.0.1:8000/api/dashboard";
const SAME_ORIGIN_API_URL = "/api/dashboard";

const normalizeDashboardUrl = (value) => {
  if (!value) {
    return "";
  }

  const url = value.replace(/\/+$/, "");

  if (url.endsWith("/api/dashboard")) {
    return url;
  }

  if (url.endsWith("/api")) {
    return `${url}/dashboard`;
  }

  return `${url}/api/dashboard`;
};

export const DASHBOARD_API_URL = (() => {
  if (import.meta.env.VITE_API_MODE === "same-origin") {
    return SAME_ORIGIN_API_URL;
  }

  const apiUrl = normalizeDashboardUrl(
    import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL
  );

  if (apiUrl) {
    return apiUrl;
  }

  if (import.meta.env.PROD) {
    throw new Error("VITE_API_URL must be configured for production builds.");
  }

  return DEFAULT_LOCAL_API_URL;
})();

export const AUTH_API_URL = DASHBOARD_API_URL.replace(
  /\/api\/dashboard$/,
  "/api/auth"
);

export const ADMIN_API_URL = DASHBOARD_API_URL.replace(
  /\/api\/dashboard$/,
  "/api/admin"
);

export const GOOGLE_API_URL = DASHBOARD_API_URL.replace(
  /\/api\/dashboard$/,
  "/api/google"
);

export const DATA_SOURCES_API_URL = DASHBOARD_API_URL.replace(
  /\/api\/dashboard$/,
  "/api/data-sources"
);

export const SYNC_JOBS_API_URL = DASHBOARD_API_URL.replace(
  /\/api\/dashboard$/,
  "/api/sync-jobs"
);

export const SETTINGS_API_URL = DASHBOARD_API_URL.replace(
  /\/api\/dashboard$/,
  "/api/settings"
);

export const WORKSPACES_API_URL = DASHBOARD_API_URL.replace(
  /\/api\/dashboard$/,
  "/api/workspaces"
);

export const WORKSPACE_INVITATIONS_API_URL = DASHBOARD_API_URL.replace(
  /\/api\/dashboard$/,
  "/api/workspace-invitations"
);

export const AUTH_BASE_URL = AUTH_API_URL.replace(/\/api\/auth$/, "/auth");
