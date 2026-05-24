const DEFAULT_LOCAL_API_URL = "http://127.0.0.1:8000/api/dashboard";

export const DASHBOARD_API_URL = (() => {
  const apiUrl = import.meta.env.VITE_API_URL
    || import.meta.env.VITE_API_BASE_URL;

  if (apiUrl) {
    return apiUrl;
  }

  if (import.meta.env.PROD) {
    throw new Error("VITE_API_URL must be configured for production builds.");
  }

  return DEFAULT_LOCAL_API_URL;
})();

export const AUTH_API_URL = DASHBOARD_API_URL.replace(
  "/api/dashboard",
  "/api/auth"
);
