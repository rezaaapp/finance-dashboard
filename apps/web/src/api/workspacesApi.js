import axios from "axios";

import { WORKSPACES_API_URL } from "./config";
import { buildWorkspaceHeaders } from "./workspaceContext";

const getAuthHeaders = () => {
  const token = localStorage.getItem("finance-dashboard-token");

  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...buildWorkspaceHeaders(),
  };
};

export const getWorkspaces = async () => {
  const response = await axios.get(
    WORKSPACES_API_URL,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};
