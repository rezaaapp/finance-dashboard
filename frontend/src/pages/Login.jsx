import { Lock, LogIn, User } from "lucide-react";
import { useState } from "react";

import { login } from "../api/authApi";

const Login = ({ onLogin }) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();

    try {
      setLoading(true);
      setError("");

      const authData = await login(username, password);

      onLogin(authData);
    } catch (err) {
      console.error(err);

      if (err?.response?.status === 401) {
        setError("Username atau password salah.");
        return;
      }

      if (err?.response?.status === 404) {
        setError("Endpoint login tidak ditemukan. Periksa VITE_API_URL.");
        return;
      }

      if (err?.response?.status >= 500) {
        setError("Backend login sedang bermasalah. Periksa environment backend.");
        return;
      }

      setError("Tidak bisa terhubung ke backend login.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dashboard-screen min-h-screen flex items-center justify-center p-6">
      <form
        onSubmit={handleSubmit}
        className="panel w-full max-w-md rounded-2xl p-6 shadow-lg"
      >
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-main">
            Finance AI
          </h1>

          <p className="text-muted mt-2">
            Masuk untuk membuka dashboard.
          </p>
        </div>

        <div className="space-y-4">
          <label className="block">
            <span className="mb-2 block text-sm font-semibold text-soft">
              Username
            </span>

            <div className="form-control flex items-center gap-3 rounded-xl px-4 py-2">
              <User size={18} className="text-muted" />
              <input
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                className="w-full bg-transparent text-main outline-none"
                autoComplete="username"
                required
              />
            </div>
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-semibold text-soft">
              Password
            </span>

            <div className="form-control flex items-center gap-3 rounded-xl px-4 py-2">
              <Lock size={18} className="text-muted" />
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full bg-transparent text-main outline-none"
                autoComplete="current-password"
                required
              />
            </div>
          </label>
        </div>

        {error && (
          <p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="primary-button mt-6 w-full rounded-xl px-4 py-3 font-semibold disabled:cursor-not-allowed disabled:opacity-70"
        >
          <LogIn size={18} />
          {loading ? "Signing in..." : "Login"}
        </button>
      </form>
    </div>
  );
};

export default Login;
