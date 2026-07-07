import {
  createSystemInfoFallback,
  normalizeSystemInfo,
} from "../utils/environment";

const RAW_API_URL = (
  import.meta.env.VITE_API_MODE === "same-origin"
    ? ""
    : (
      import.meta.env.VITE_API_URL
      || import.meta.env.VITE_API_BASE_URL
      || "http://127.0.0.1:8000"
    )
).replace(/\/+$/, "");

export const FRONTEND_VERSION = (
  import.meta.env.VITE_APP_VERSION || "v0.9.2-env-foundation"
);
export const FRONTEND_PORT = Number(window.location.port) || null;

export const SYSTEM_INFO_URL = `${RAW_API_URL}/api/system/info`;

export const getSystemInfoFallback = () => createSystemInfoFallback({
  apiUrl: RAW_API_URL,
  frontendPort: FRONTEND_PORT,
  version: FRONTEND_VERSION,
});

export const fetchSystemInfo = async ({ signal } = {}) => {
  const response = await fetch(SYSTEM_INFO_URL, {
    method: "GET",
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new Error(`System info request failed with HTTP ${response.status}.`);
  }

  const payload = await response.json();
  return normalizeSystemInfo(payload, {
    apiUrl: RAW_API_URL,
    frontendPort: FRONTEND_PORT,
    version: FRONTEND_VERSION,
  });
};
