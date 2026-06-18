import axios from "axios";

import { INQUIRY_API_URL } from "./config";
import { buildWorkspaceHeaders } from "./workspaceContext";


const getAuthHeaders = () => {
  const token = localStorage.getItem("finance-dashboard-token");

  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...buildWorkspaceHeaders(),
  };
};


const buildPeriodPayload = (query, year, month) => ({
  query,
  ...(year && { year: Number(year) }),
  ...(year && month && { month: Number(month) }),
});


export const searchInquiry = async ({ query, year, month }) => {
  const response = await axios.post(
    INQUIRY_API_URL,
    buildPeriodPayload(query, year, month),
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};


export const getInquiryDetail = async ({ query, year, month, limit = 25, offset = 0 }) => {
  const response = await axios.get(
    `${INQUIRY_API_URL}/detail`,
    {
      params: {
        query,
        limit,
        offset,
        ...(year && { year: Number(year) }),
        ...(year && month && { month: Number(month) }),
      },
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};
