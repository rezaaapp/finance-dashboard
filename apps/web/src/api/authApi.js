import axios from "axios";

import { AUTH_API_URL } from "./config";

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
