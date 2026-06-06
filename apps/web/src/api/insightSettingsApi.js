import axios from "axios";

import { SETTINGS_API_URL } from "./config";

const getAuthHeaders = () => {
  const token = localStorage.getItem("finance-dashboard-token");

  return token
    ? { Authorization: `Bearer ${token}` }
    : {};
};

export const getInsightThresholds = async () => {
  const response = await axios.get(
    `${SETTINGS_API_URL}/insight-thresholds`,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const updateInsightThresholds = async (payload) => {
  const response = await axios.put(
    `${SETTINGS_API_URL}/insight-thresholds`,
    payload,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};
