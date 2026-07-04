import { LoaderCircle } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { ACTIVE_WORKSPACE_STORAGE_KEY } from "../api/workspaceContext";

const getCallbackParams = () => {
  const hashParams = new URLSearchParams(
    window.location.hash.replace(/^#/, "")
  );
  const searchParams = new URLSearchParams(window.location.search);

  return {
    token: hashParams.get("token") || searchParams.get("token"),
    username:
      hashParams.get("name") ||
      hashParams.get("username") ||
      searchParams.get("name") ||
      searchParams.get("username"),
    email: hashParams.get("email") || searchParams.get("email"),
    userId:
      hashParams.get("user_id") ||
      hashParams.get("userId") ||
      searchParams.get("user_id") ||
      searchParams.get("userId"),
    role: hashParams.get("role") || searchParams.get("role"),
    workspaceId:
      hashParams.get("workspace_id") ||
      hashParams.get("workspaceId") ||
      searchParams.get("workspace_id") ||
      searchParams.get("workspaceId"),
  };
};

const GoogleAuthCallback = ({ onLogin }) => {
  const [error, setError] = useState("");
  const processedRef = useRef(false);

  useEffect(() => {
    if (processedRef.current) {
      return;
    }

    processedRef.current = true;

    const {
      token,
      username,
      email,
      userId,
      role,
      workspaceId,
    } = getCallbackParams();

    if (!token) {
      setError("Token login Google tidak ditemukan.");
      return;
    }

    onLogin({
      token,
      username: username || email || "Google User",
      email,
      userId,
      role,
      provider: "google",
    });

    if (workspaceId) {
      localStorage.setItem(ACTIVE_WORKSPACE_STORAGE_KEY, workspaceId);
    }

    window.history.replaceState({}, "", "/dashboard");
    window.location.assign("/dashboard");
  }, [onLogin]);

  return (
    <div className="dashboard-screen min-h-screen flex items-center justify-center p-6">
      <div className="panel w-full max-w-md rounded-lg p-6 text-center shadow-lg">
        {error ? (
          <>
            <h1 className="text-xl font-bold text-main">
              Login Google gagal
            </h1>

            <p className="mt-3 text-sm text-muted">
              {error}
            </p>
            <a href="/" className="primary-button mt-6 inline-flex rounded-xl px-5 py-2.5 font-bold">
              Kembali ke Login
            </a>
          </>
        ) : (
          <>
            <LoaderCircle
              size={28}
              className="mx-auto animate-spin text-accent"
            />

            <h1 className="mt-4 text-xl font-bold text-main">
              Menyelesaikan login
            </h1>

            <p className="mt-3 text-sm text-muted">
              Menghubungkan sesi Google ke dashboard.
            </p>
          </>
        )}
      </div>
    </div>
  );
};

export default GoogleAuthCallback;
