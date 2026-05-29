import { LoaderCircle } from "lucide-react";
import { useEffect, useState } from "react";

const GoogleAuthCallback = ({ onLogin }) => {
  const [error, setError] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const token = params.get("token");
    const name = params.get("name");
    const email = params.get("email");
    const userId = params.get("user_id");
    const role = params.get("role");

    if (!token) {
      setError("Token login Google tidak ditemukan.");
      return;
    }

    onLogin({
      token,
      username: name || email || "Google User",
      email,
      userId,
      role,
      provider: "google",
    });

    window.history.replaceState({}, "", "/");
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
