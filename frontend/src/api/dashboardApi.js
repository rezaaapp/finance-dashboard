import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api/dashboard";

const buildParams = (year, month) => ({
  ...(year && { year }),
  ...(month && { month }),
});

export const getSummary = async (year, month) => {

  const response = await axios.get(
    `${API_URL}/summary`,
    {
      params: buildParams(year, month)
    }
  );

  return response.data;
};

export const getMonthlySpending = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/monthly-spending`,
    {
      params: buildParams(year, month)
    }
  );
  return response.data;
};

export const getMonthlySaving = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/monthly-saving`,
    {
      params: buildParams(year, month)
    }
  );
  return response.data;
};

export const getMonthlyIncome = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/monthly-income`,
    {
      params: buildParams(year, month)
    }
  );
  return response.data;
};

export const getTopSpending = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/top-spending`,
    {
      params: buildParams(year, month)
    }
  );
  return response.data;
};

export const getSpendingByCategory = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/spending-by-category`,
    {
      params: buildParams(year, month)
    }
  );
  return response.data;
};

export const getGroceryVsFood = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/grocery-vs-food`,
    {
      params: buildParams(year, month)
    }
  );
  return response.data;
};

export const getCategoryHeatmap = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/category-heatmap`,
    {
      params: buildParams(year, month)
    }
  );
  return response.data;
};

export const getCategoryTrends = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/category-trends`,
    {
      params: buildParams(year, month)
    }
  );
  return response.data;
};

export const getAnomalies = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/anomalies`,
    {
      params: buildParams(year, month)
    }
  );
  return response.data;
};

export const getLatestInsight = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/latest-insight`,
    {
      params: buildParams(year, month)
    }
  );
  return response.data;
};

export const getAvailableYears = async () => {
  const response = await axios.get(
    `${API_URL}/available-years`
  );
  return response.data;
};
    

