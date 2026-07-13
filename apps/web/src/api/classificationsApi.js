import axios from "axios";

import { CLASSIFICATIONS_API_URL } from "./config";
import { buildWorkspaceHeaders } from "./workspaceContext";

const getAuthHeaders = () => {
  const token = localStorage.getItem("finance-dashboard-token");

  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...buildWorkspaceHeaders(),
  };
};

export const getUncategorizedGroups = async ({ limit = 100 } = {}) => {
  const response = await axios.get(
    `${CLASSIFICATIONS_API_URL}/uncategorized/groups`,
    {
      params: { limit },
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const applyClassificationSuggestion = async (payload) => {
  const response = await axios.post(
    `${CLASSIFICATIONS_API_URL}/suggestions/apply`,
    payload,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const runClassification = async ({ limit = 500 } = {}) => {
  const response = await axios.post(
    `${CLASSIFICATIONS_API_URL}/run`,
    { limit },
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};
