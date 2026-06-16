import axios from "axios";

import { IMPORT_API_URL } from "./config";
import { buildWorkspaceHeaders } from "./workspaceContext";

const getAuthHeaders = () => {
  const token = localStorage.getItem("finance-dashboard-token");

  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...buildWorkspaceHeaders(),
  };
};

export const uploadImportFile = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await axios.post(
    `${IMPORT_API_URL}/upload`,
    formData,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const getImportReview = async (jobId) => {
  const response = await axios.get(
    `${IMPORT_API_URL}/review/${jobId}`,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const approveImportReview = async (jobId, payload) => {
  const response = await axios.post(
    `${IMPORT_API_URL}/review/${jobId}/approve`,
    payload,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const rejectImportReview = async (jobId, payload) => {
  const response = await axios.post(
    `${IMPORT_API_URL}/review/${jobId}/reject`,
    payload,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};
