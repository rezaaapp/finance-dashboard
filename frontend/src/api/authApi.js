import axios from "axios";

const DASHBOARD_API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api/dashboard";
const AUTH_API_URL = DASHBOARD_API_URL.replace("/api/dashboard", "/api/auth");

export const login = async (username, password) => {
  const response = await axios.post(
    `${AUTH_API_URL}/login`,
    {
      username,
      password,
    }
  );

  return response.data;
};
