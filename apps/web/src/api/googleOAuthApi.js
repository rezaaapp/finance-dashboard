import axios from "axios";

import { GOOGLE_API_URL } from "./config";

const getAuthHeaders = () => {
  const token = localStorage.getItem("finance-dashboard-token");

  return token
    ? { Authorization: `Bearer ${token}` }
    : {};
};

export const getGoogleOAuthConnectionStatus = async () => {
  const response = await axios.get(
    `${GOOGLE_API_URL}/connection/status`,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const startGoogleOAuth = async () => {
  const response = await axios.get(
    `${GOOGLE_API_URL}/oauth/start`,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const disconnectGoogleOAuth = async () => {
  const response = await axios.post(
    `${GOOGLE_API_URL}/connection/disconnect`,
    {},
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};
