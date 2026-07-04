import axios from "axios";

import { DASHBOARD_API_URL } from "./config";
import { buildWorkspaceHeaders } from "./workspaceContext";

export const factoryResetWorkspaceData = async () => {
  const token = localStorage.getItem("finance-dashboard-token");
  const response = await axios.post(
    `${DASHBOARD_API_URL.replace(/\/api\/dashboard$/, "/api")}/workspace/factory-reset-data`,
    {},
    { headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...buildWorkspaceHeaders() } }
  );
  return response.data;
};
