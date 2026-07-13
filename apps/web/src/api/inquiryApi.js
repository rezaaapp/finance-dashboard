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


const buildPeriodPayload = ({ query, year, month, start_date, end_date, period_mode }) => ({
  query,
  ...(year && { year: Number(year) }),
  ...(year && month && { month: Number(month) }),
  ...(start_date && { start_date }),
  ...(end_date && { end_date }),
  ...(period_mode && { period_mode }),
});


export const searchInquiry = async ({ query, year, month, start_date, end_date, period_mode }) => {
  const response = await axios.post(
    INQUIRY_API_URL,
    buildPeriodPayload({ query, year, month, start_date, end_date, period_mode }),
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};


export const getInquiryDetail = async ({
  query,
  year,
  month,
  start_date,
  end_date,
  period_mode,
  limit = 25,
  offset = 0,
}) => {
  const response = await axios.get(
    `${INQUIRY_API_URL}/detail`,
    {
      params: {
        query,
        limit,
        offset,
        ...(year && { year: Number(year) }),
        ...(year && month && { month: Number(month) }),
        ...(start_date && { start_date }),
        ...(end_date && { end_date }),
        ...(period_mode && { period_mode }),
      },
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};
