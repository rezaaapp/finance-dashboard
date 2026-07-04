import axios from "axios";

import { ADMIN_API_URL } from "./config";

const getAuthHeaders = () => {
  const token = localStorage.getItem("finance-dashboard-token");

  return token
    ? { Authorization: `Bearer ${token}` }
    : {};
};

export const getAdminUsers = async () => {
  const response = await axios.get(
    `${ADMIN_API_URL}/users`,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const createAdminUser = async (payload) => {
  const response = await axios.post(
    `${ADMIN_API_URL}/users`,
    payload,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const provisionAdminTestUser = async (payload) => {
  const response = await axios.post(
    `${ADMIN_API_URL}/users/provision-test-user`,
    payload,
    { headers: getAuthHeaders() }
  );
  return response.data;
};

export const updateAdminUser = async (userId, payload) => {
  const response = await axios.put(
    `${ADMIN_API_URL}/users/${userId}`,
    payload,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const updateAdminUserRole = async (userId, role) => {
  const response = await axios.patch(
    `${ADMIN_API_URL}/users/${userId}/role`,
    { role },
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const impersonateAdminUser = async (userId) => {
  const response = await axios.post(
    `${ADMIN_API_URL}/users/${userId}/impersonate`,
    {},
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};

export const deleteAdminUser = async (userId) => {
  const response = await axios.delete(
    `${ADMIN_API_URL}/users/${userId}`,
    {
      headers: getAuthHeaders(),
    }
  );

  return response.data;
};
