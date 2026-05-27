import axios from "axios";

import { DASHBOARD_API_URL } from "./config";

const getAuthHeaders = () => {
  const token = localStorage.getItem("finance-dashboard-token");

  return token
    ? { Authorization: `Bearer ${token}` }
    : {};
};

const buildParams = (year, month, name) => ({
  ...(year && { year }),
  ...(month && { month }),
  ...(name && { name }),
});

const buildConfig = (year, month, name) => ({
  params: buildParams(year, month, name),
  headers: getAuthHeaders(),
});

export const getSummary = async (year, month) => {

  const response = await axios.get(
    `${DASHBOARD_API_URL}/summary`,
    buildConfig(year, month)
  );

  return response.data;
};

export const getMonthlySpending = async (year, month) => {
  const response = await axios.get(
    `${DASHBOARD_API_URL}/monthly-spending`,
    buildConfig(year, month)
  );
  return response.data;
};

export const getMonthlySaving = async (year, month) => {
  const response = await axios.get(
    `${DASHBOARD_API_URL}/monthly-saving`,
    buildConfig(year, month)
  );
  return response.data;
};

export const getMonthlyIncome = async (year, month) => {
  const response = await axios.get(
    `${DASHBOARD_API_URL}/monthly-income`,
    buildConfig(year, month)
  );
  return response.data;
};

export const getTopSpending = async (year, month) => {
  const response = await axios.get(
    `${DASHBOARD_API_URL}/top-spending`,
    buildConfig(year, month)
  );
  return response.data;
};

export const getSpendingByCategory = async (year, month) => {
  const response = await axios.get(
    `${DASHBOARD_API_URL}/spending-by-category`,
    buildConfig(year, month)
  );
  return response.data;
};

export const refreshDashboardData = async (year) => {
  const response = await axios.post(
    `${DASHBOARD_API_URL}/refresh`,
    {},
    {
      params: buildParams(year),
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const getGroceryVsFood = async (year, month, name) => {
  const response = await axios.get(
    `${DASHBOARD_API_URL}/grocery-vs-food`,
    buildConfig(year, month, name)
  );
  return response.data;
};

export const getCategoryHeatmap = async (year, month, name) => {
  const response = await axios.get(
    `${DASHBOARD_API_URL}/category-heatmap`,
    buildConfig(year, month, name)
  );
  return response.data;
};

export const getTransactions = async (year, month, name) => {
  const response = await axios.get(
    `${DASHBOARD_API_URL}/transactions`,
    buildConfig(year, month, name)
  );
  return response.data;
};

export const getCategoryTrends = async (year, month, name) => {
  const response = await axios.get(
    `${DASHBOARD_API_URL}/category-trends`,
    buildConfig(year, month, name)
  );
  return response.data;
};

export const getSourceDanaAnalytics = async (year, month, name) => {
  const response = await axios.get(
    `${DASHBOARD_API_URL}/source-dana-analytics`,
    buildConfig(year, month, name)
  );
  return response.data;
};

export const getPersonalAnalytics = async (year, month) => {
  const response = await axios.get(
    `${DASHBOARD_API_URL}/personal-analytics`,
    buildConfig(year, month)
  );
  return response.data;
};

export const getAnomalies = async (year, month) => {
  const response = await axios.get(
    `${DASHBOARD_API_URL}/anomalies`,
    buildConfig(year, month)
  );
  return response.data;
};

export const getLatestInsight = async (year, month) => {
  const response = await axios.get(
    `${DASHBOARD_API_URL}/latest-insight`,
    buildConfig(year, month)
  );
  return response.data;
};

export const getAvailableYears = async () => {
  const response = await axios.get(
    `${DASHBOARD_API_URL}/available-years`,
    {
      headers: getAuthHeaders()
    }
  );
  return response.data;
};

export const getBudgetForecast = async (year, month) => {
  const response = await axios.get(
    `${DASHBOARD_API_URL}/budget-forecast`,
    buildConfig(year, month)
  );

  return response.data;
};
    

