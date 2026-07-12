import { ArrowRight, Lock, LogIn, User } from "lucide-react";
import { useState } from "react";

import { getGoogleLoginUrl, login } from "../api/authApi";
import EnvironmentCard from "../components/environment/EnvironmentCard";

const GoogleMark = () => (
  <svg aria-hidden="true" className="h-5 w-5" viewBox="0 0 24 24">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09Z" />
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23Z" />
    <path fill="#FBBC05" d="M5.84 14.1c-.22-.66-.35-1.36-.35-2.1s.13-1.44.35-2.1V7.06H2.18A10.96 10.96 0 0 0 1 12c0 1.77.42 3.45 1.18 4.94l3.66-2.84Z" />
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06L5.84 9.9C6.71 7.31 9.14 5.38 12 5.38Z" />
  </svg>
);

const Login = ({ onLogin, systemInfoState }) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const landingUrl = import.meta.env.VITE_LANDING_URL || "http://127.0.0.1:5174";

  const handleSubmit = async (event) => {
    event.preventDefault();

    try {
      setLoading(true);
      setError("");

      const authData = await login(username, password);

      onLogin(authData);
    } catch (err) {
      console.error("Login failed.");

      if (err?.response?.status === 401) {
        setError("Username atau password salah.");
        return;
      }

      if (err?.response?.status === 404) {
        setError("Login belum tersedia. Silakan coba lagi beberapa saat lagi.");
        return;
      }

      if (err?.response?.status >= 500) {
        setError("Layanan login sedang bermasalah. Silakan coba lagi beberapa saat lagi.");
        return;
      }

      setError("Omon belum dapat terhubung ke layanan login. Periksa koneksi, lalu coba lagi.");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    window.location.href = getGoogleLoginUrl();
  };

  return (
    <div className="dashboard-screen min-h-screen px-4 py-6 sm:px-6">
      <main className="mx-auto flex min-h-[calc(100vh-3rem)] w-full max-w-md flex-col justify-center gap-4">
        <section className="text-center">
          <a className="inline-flex items-center justify-center gap-3 text-main" href={landingUrl}>
            <span className="grid h-11 w-11 place-items-center rounded-xl bg-[var(--color-accent-bg)] text-sm font-bold text-accent">
              O
            </span>
            <span className="text-lg font-bold">Omon</span>
          </a>
        </section>

        <section>
          <form
            onSubmit={handleSubmit}
            className="panel w-full rounded-lg p-6 shadow-lg sm:p-8"
          >
            <div className="mb-7 text-center">
              <p className="text-xs font-bold uppercase tracking-wider text-muted">
                Calm Financial Companion
              </p>
              <h1 className="mt-2 text-2xl font-bold text-main">
                Masuk ke akun Anda
              </h1>

              <p className="mt-2 text-sm leading-6 text-muted">
                Setelah login berhasil, Anda akan diarahkan ke dashboard utama.
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
              <p role="alert" className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-500">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="primary-button mt-6 w-full rounded-xl px-4 py-3 font-semibold disabled:cursor-not-allowed disabled:opacity-70"
            >
              <LogIn size={18} />
              {loading ? "Memeriksa akun..." : "Masuk dengan akun lokal"}
            </button>

            <div className="my-6 flex items-center gap-3">
              <div className="h-px flex-1 bg-[var(--color-border)]" />
              <span className="text-xs font-semibold uppercase tracking-wide text-muted">
                atau
              </span>
              <div className="h-px flex-1 bg-[var(--color-border)]" />
            </div>

            <button
              type="button"
              onClick={handleGoogleLogin}
              className="secondary-button w-full rounded-xl px-4 py-3 font-semibold"
              aria-label="Lanjutkan dengan Google"
            >
              <GoogleMark />
              Lanjutkan dengan Google
              <ArrowRight size={16} />
            </button>

            <p className="mt-3 text-xs leading-5 text-muted">
              Anda akan diarahkan ke Google. Omon tidak meminta password Google di halaman ini.
            </p>

            <p className="mt-5 text-center text-sm leading-6 text-muted">
              Belum punya akses? Gunakan Google jika tersedia, atau minta admin workspace membuat akses untuk Anda.
            </p>

            <div className="mt-5 text-center">
              <a className="text-sm font-semibold text-accent underline-offset-4 hover:underline" href={landingUrl}>
                Kembali ke landing
              </a>
            </div>
          </form>

          <details className="mt-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-panel)] p-3 text-sm text-muted">
            <summary className="cursor-pointer font-semibold text-soft">
              Informasi environment
            </summary>
            <div className="mt-3">
              <EnvironmentCard systemInfoState={systemInfoState} />
            </div>
          </details>
        </section>
      </main>
    </div>
  );
};

export default Login;
