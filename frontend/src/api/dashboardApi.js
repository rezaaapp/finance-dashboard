import axios from "axios";

const API_URL = "http://127.0.0.1:8000/api/dashboard";

export const getSummary = async (year = "") => {
  const response = await axios.get(
    `${API_URL}/summary?year=${year}`
  );
  return response.data;
};

export const getMonthlySpending = async (year = "") => {
  const response = await axios.get(
    `${API_URL}/monthly-spending?year=${year}`
  );
  return response.data;
};

export const getMonthlySaving = async (year = "") => {
  const response = await axios.get(
    `${API_URL}/monthly-saving?year=${year}`
  );
  return response.data;
};

export const getMonthlyIncome = async (year = "") => {
  const response = await axios.get(
    `${API_URL}/monthly-income?year=${year}`
  );
  return response.data;
};

export const getTopSpending = async (year = "") => {
  const response = await axios.get(
    `${API_URL}/top-spending?year=${year}`
  );
  return response.data;
};

export const getSpendingByCategory = async (year = "") => {
  const response = await axios.get(
    `${API_URL}/spending-by-category?year=${year}`
  );
  return response.data;
};

export const getAnomalies = async (year = "") => {
  const response = await axios.get(
    `${API_URL}/anomalies?year=${year}`
  );
  return response.data;
};

export const getLatestInsight = async (year = "") => {
  const response = await axios.get(
    `${API_URL}/latest-insight?year=${year}`
  );
  return response.data;
};

export const getAvailableYears = async () => {
  const response = await axios.get(
    `${API_URL}/available-years`
  );
  return response.data;
};