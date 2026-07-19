import axios from "axios";

import { IMPORT_API_URL } from "./config";
import { buildImportUploadFormData } from "./importUploadFormData";
import { buildWorkspaceHeaders } from "./workspaceContext";

export { buildImportUploadFormData } from "./importUploadFormData";

const getAuthHeaders = () => {
  const token = localStorage.getItem("finance-dashboard-token");

  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...buildWorkspaceHeaders(),
  };
};

export const uploadImportFile = async (
  file,
  statementOwner,
  options = {}
) => {
  const formData = buildImportUploadFormData(file, statementOwner, options);

  const response = await axios.post(
    `${IMPORT_API_URL}/upload`,
    formData,
    {
      headers: getAuthHeaders(),
      signal: options.signal,
    }
  );

  return response.data;
};

export const getImportReview = async (jobId, params = {}) => {
  const response = await axios.get(
    `${IMPORT_API_URL}/review/${jobId}`,
    {
      headers: getAuthHeaders(),
      params,
    }
  );

  return response.data;
};

export const getImportCategoryOptions = async () => {
  const response = await axios.get(
    `${IMPORT_API_URL}/category-options`,
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

export const getImportHistory = async (params = {}) => {
  const response = await axios.get(
    `${IMPORT_API_URL}/history`,
    {
      headers: getAuthHeaders(),
      params,
    }
  );

  return response.data;
};

export const getImportHistoryDetail = async (jobId) => {
  const response = await axios.get(
    `${IMPORT_API_URL}/history/${jobId}`,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const retryImportSync = async (jobId, payload = {}) => {
  const response = await axios.post(
    `${IMPORT_API_URL}/retry-sync/${jobId}`,
    payload,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};
