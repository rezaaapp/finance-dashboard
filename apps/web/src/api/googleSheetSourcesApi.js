import axios from "axios";

import {
  DATA_SOURCES_API_URL,
  SYNC_JOBS_API_URL,
} from "./config";
import { buildWorkspaceHeaders } from "./workspaceContext";

const getAuthHeaders = () => {
  const token = localStorage.getItem("finance-dashboard-token");

  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...buildWorkspaceHeaders(),
  };
};

export const testGoogleSheetSource = async (payload) => {
  const response = await axios.post(
    `${DATA_SOURCES_API_URL}/google-sheet/test`,
    payload,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const createGoogleSheetSource = async (payload) => {
  const response = await axios.post(
    `${DATA_SOURCES_API_URL}/google-sheet`,
    payload,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const getGoogleSheetSources = async () => {
  const response = await axios.get(
    DATA_SOURCES_API_URL,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const getGoogleSheetSourceWorksheets = async (sourceId) => {
  const response = await axios.get(
    `${DATA_SOURCES_API_URL}/${sourceId}/worksheets`,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const syncGoogleSheetSource = async (sourceId) => {
  const response = await axios.post(
    `${DATA_SOURCES_API_URL}/${sourceId}/sync`,
    {},
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const deleteGoogleSheetSource = async (sourceId) => {
  await axios.delete(
    `${DATA_SOURCES_API_URL}/${sourceId}`,
    {
      headers: getAuthHeaders(),
    }
  );
};

export const getSyncJob = async (jobId) => {
  const response = await axios.get(
    `${SYNC_JOBS_API_URL}/${jobId}`,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};
