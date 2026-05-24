import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api/dashboard";

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
    `${API_URL}/summary`,
    buildConfig(year, month)
  );

  return response.data;
};

export const getMonthlySpending = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/monthly-spending`,
    buildConfig(year, month)
  );
  return response.data;
};

export const getMonthlySaving = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/monthly-saving`,
    buildConfig(year, month)
  );
  return response.data;
};

export const getMonthlyIncome = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/monthly-income`,
    buildConfig(year, month)
  );
  return response.data;
};

export const getTopSpending = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/top-spending`,
    buildConfig(year, month)
  );
  return response.data;
};

export const getSpendingByCategory = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/spending-by-category`,
    buildConfig(year, month)
  );
  return response.data;
};

export const getGroceryVsFood = async (year, month, name) => {
  const response = await axios.get(
    `${API_URL}/grocery-vs-food`,
    buildConfig(year, month, name)
  );
  return response.data;
};

export const getCategoryHeatmap = async (year, month, name) => {
  const response = await axios.get(
    `${API_URL}/category-heatmap`,
    buildConfig(year, month, name)
  );
  return response.data;
};

export const getCategoryTrends = async (year, month, name) => {
  const response = await axios.get(
    `${API_URL}/category-trends`,
    buildConfig(year, month, name)
  );
  return response.data;
};

export const getPersonalAnalytics = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/personal-analytics`,
    buildConfig(year, month)
  );
  return response.data;
};

export const getAnomalies = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/anomalies`,
    buildConfig(year, month)
  );
  return response.data;
};

export const getLatestInsight = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/latest-insight`,
    buildConfig(year, month)
  );
  return response.data;
};

export const getAvailableYears = async () => {
  const response = await axios.get(
    `${API_URL}/available-years`,
    {
      headers: getAuthHeaders()
    }
  );
  return response.data;
};
    

