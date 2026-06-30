import { useEffect, useState } from "react";

import {
  fetchSystemInfo,
  getSystemInfoFallback,
} from "../api/systemInfo";

const useSystemInfo = () => {
  const [state, setState] = useState(() => ({
    status: "loading",
    data: getSystemInfoFallback(),
  }));

  useEffect(() => {
    const controller = new AbortController();

    fetchSystemInfo({ signal: controller.signal })
      .then((data) => {
        setState({ status: "connected", data });
      })
      .catch((error) => {
        if (error?.name === "AbortError") {
          return;
        }

        setState({
          status: "offline",
          data: getSystemInfoFallback(),
        });
      });

    return () => controller.abort();
  }, []);

  return state;
};

export default useSystemInfo;
