import axios from "axios";

const API_URL = "http://127.0.0.1:8000/api/dashboard";

export const getSummary = async (year, month) => {

  const response = await axios.get(
    `${API_URL}/summary`,
    {
      params: { 
      ...(year && { year }),
      ...(month && { month }) 
      }
    }
  );

  return response.data;
};

export const getMonthlySpending = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/monthly-spending`,
    {
      params: {
        ...(year && { year }),
        ...(month && { month }) 
        }
    }
  );
  return response.data;
};

export const getMonthlySaving = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/monthly-saving`,
    {
      params: {
        ...(year && { year }),
        ...(month && { month }) 
        }
    }
  );
  return response.data;
};

export const getMonthlyIncome = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/monthly-income`,
    {
      params: {
        ...(year && { year }),
        ...(month && { month }) 
        }
    }
  );
  return response.data;
};

export const getTopSpending = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/top-spending`,
    {
      params: {
        ...(year && { year }),
        ...(month && { month }) 
        }
    }
  );
  return response.data;
};

export const getSpendingByCategory = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/spending-by-category`,
    {
      params: {
        ...(year && { year }),
        ...(month && { month }) 
        }
    }
  );
  return response.data;
};

export const getAnomalies = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/anomalies`,
    {
      params: {
        ...(year && { year }),
        ...(month && { month }) 
        }
    }
  );
  return response.data;
};

export const getLatestInsight = async (year, month) => {
  const response = await axios.get(
    `${API_URL}/latest-insight`,
    {
      params: {
        ...(year && { year }),
        ...(month && { month }) 
        }
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
    

