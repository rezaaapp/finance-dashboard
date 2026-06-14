import axios from "axios";

import { BUDGETS_API_URL } from "./config";
import { buildWorkspaceHeaders } from "./workspaceContext";

const getAuthHeaders = () => {
  const token = localStorage.getItem("finance-dashboard-token");

  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...buildWorkspaceHeaders(),
  };
};

export const getBudgets = async (year, month) => {
  const response = await axios.get(
    BUDGETS_API_URL,
    {
      params: { year, month },
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const createBudget = async ({ year, month, category, amount }) => {
  const response = await axios.post(
    BUDGETS_API_URL,
    { year, month, category, amount },
    { headers: getAuthHeaders() }
  );

  return response.data;
};

export const updateBudget = async (budgetId, { category, amount }) => {
  const response = await axios.put(
    `${BUDGETS_API_URL}/${budgetId}`,
    { category, amount },
    { headers: getAuthHeaders() }
  );

  return response.data;
};

export const deleteBudget = async (budgetId) => {
  await axios.delete(
    `${BUDGETS_API_URL}/${budgetId}`,
    { headers: getAuthHeaders() }
  );
};

export const deleteBudgetsByPeriod = async (year, month) => {
  const response = await axios.delete(
    BUDGETS_API_URL,
    {
      params: { year, month },
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const getIgnoredBudgetCategories = async (year, month) => {
  const response = await axios.get(
    `${BUDGETS_API_URL}/ignored`,
    {
      params: { year, month },
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const ignoreBudgetCategory = async ({ year, month, category }) => {
  const response = await axios.post(
    `${BUDGETS_API_URL}/ignored`,
    { year, month, category },
    { headers: getAuthHeaders() }
  );

  return response.data;
};

export const unignoreBudgetCategory = async (ignoredId) => {
  await axios.delete(
    `${BUDGETS_API_URL}/ignored/${ignoredId}`,
    { headers: getAuthHeaders() }
  );
};
