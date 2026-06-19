import axios from "axios";

import { DASHBOARD_API_URL } from "./config";
import { buildWorkspaceHeaders } from "./workspaceContext";

const getAuthHeaders = () => {
  const token = localStorage.getItem("finance-dashboard-token");

  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...buildWorkspaceHeaders(),
  };
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

const normalizePeriodParams = (params = {}) => (
  params && typeof params === "object"
    ? params
    : { year: params }
);

export const getSummary = async (year, month) => {

  const response = await axios.get(
    `${DASHBOARD_API_URL}/summary`,
    buildConfig(year, month)
  );

  return response.data;
};

export const getDashboardViewModel = async (year, month, name) => {
  const response = await axios.get(
    `${DASHBOARD_API_URL}/view-model`,
    buildConfig(year, month, name)
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

export const getFinancialTypes = async (params = {}) => {
  const { year, month } = normalizePeriodParams(params);
  const response = await axios.get(
    `${DASHBOARD_API_URL}/financial-types`,
    buildConfig(year, month)
  );

  return response.data;
};

export const getMonthlyFinancialTypes = async (params = {}) => {
  const { year } = normalizePeriodParams(params);
  const response = await axios.get(
    `${DASHBOARD_API_URL}/monthly-financial-types`,
    buildConfig(year)
  );

  return response.data;
};

export const getRuleBasedInsights = async (params = {}) => {
  const { year, month } = normalizePeriodParams(params);
  const response = await axios.get(
    `${DASHBOARD_API_URL}/rule-based-insights`,
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

export const getMonthlyAllocation = async (year, month, name) => {
  const response = await axios.get(
    `${DASHBOARD_API_URL}/monthly-allocation`,
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

export const saveConfiguration = async (configuration) => {
  const response = await axios.post(
    `${DASHBOARD_API_URL}/configuration`,
    configuration,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const getWorkspaceConfiguration = async () => {
  const response = await axios.get(
    `${DASHBOARD_API_URL}/workspace/configuration`,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const updateWorkspaceConfiguration = async (configuration) => {
  const response = await axios.put(
    `${DASHBOARD_API_URL}/workspace/configuration`,
    configuration,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const getWorkspaceMembers = async () => {
  const response = await axios.get(
    `${DASHBOARD_API_URL}/workspace/members`,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const inviteWorkspaceMember = async (member) => {
  const response = await axios.post(
    `${DASHBOARD_API_URL}/workspace/members`,
    member,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};
    

