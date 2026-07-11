import { ArrowRight, KeyRound, Lock, LogIn, User } from "lucide-react";
import { useState } from "react";

import { getGoogleLoginUrl, login } from "../api/authApi";
import EnvironmentCard from "../components/environment/EnvironmentCard";

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
    <div className="dashboard-screen min-h-screen p-5 sm:p-6">
      <main className="mx-auto grid min-h-[calc(100vh-2.5rem)] w-full max-w-6xl items-center gap-6 lg:grid-cols-[0.95fr_1.05fr]">
        <section className="panel rounded-lg p-6 sm:p-8">
          <a className="inline-flex items-center gap-3 text-main" href={landingUrl}>
            <span className="grid h-11 w-11 place-items-center rounded-xl bg-[var(--color-accent-bg)] text-sm font-bold text-accent">
              O
            </span>
            <span className="font-bold">Omon</span>
          </a>

          <p className="mt-8 text-xs font-bold uppercase tracking-wider text-muted">
            Calm Financial Companion
          </p>
          <h1 className="mt-3 max-w-xl text-3xl font-bold leading-tight text-main sm:text-4xl">
            Masuk untuk melanjutkan mengelola uang dengan tenang.
          </h1>
          <p className="mt-4 max-w-xl text-sm leading-7 text-muted sm:text-base">
            Omon membantu membaca pemasukan, pengeluaran, budget, dan pola keuangan dari workspace yang sudah tersedia.
          </p>

          <div className="mt-6 grid gap-3 text-sm leading-6 text-muted">
            <p className="rounded-xl border border-[var(--color-border)] bg-[var(--color-panel-hover)] px-4 py-3">
              Gunakan Google untuk melanjutkan jika akunmu terhubung melalui Google.
            </p>
            <p className="rounded-xl border border-[var(--color-border)] bg-[var(--color-panel-hover)] px-4 py-3">
              Gunakan username dan password hanya untuk akun Omon yang sudah tersedia di environment ini.
            </p>
          </div>

          <a className="secondary-button mt-6 rounded-xl px-4 py-2.5 text-sm font-semibold" href={landingUrl}>
            Kembali ke landing
          </a>
        </section>

        <section className="space-y-3">
          <EnvironmentCard systemInfoState={systemInfoState} />

          <form
            onSubmit={handleSubmit}
            className="panel w-full rounded-lg p-6 shadow-lg sm:p-8"
          >
            <div className="mb-7">
              <p className="text-xs font-bold uppercase tracking-wider text-muted">
                Login Omon
              </p>
              <h2 className="mt-2 text-2xl font-bold text-main">
                Masuk ke akun Anda
              </h2>

              <p className="mt-2 text-sm leading-6 text-muted">
                Setelah login berhasil, Anda akan diarahkan ke dashboard utama.
              </p>
            </div>

            <button
              type="button"
              onClick={handleGoogleLogin}
              className="primary-button w-full rounded-xl px-4 py-3 font-semibold"
            >
              <KeyRound size={18} />
              Lanjutkan dengan Google
              <ArrowRight size={16} />
            </button>

            <p className="mt-3 text-xs leading-5 text-muted">
              Anda akan diarahkan ke Google. Omon tidak meminta password Google di halaman ini.
            </p>

            <div className="my-6 flex items-center gap-3">
              <div className="h-px flex-1 bg-[var(--color-border)]" />
              <span className="text-xs font-semibold uppercase tracking-wide text-muted">
                atau login lokal
              </span>
              <div className="h-px flex-1 bg-[var(--color-border)]" />
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
              className="secondary-button mt-6 w-full rounded-xl px-4 py-3 font-semibold disabled:cursor-not-allowed disabled:opacity-70"
            >
              <LogIn size={18} />
              {loading ? "Memeriksa akun..." : "Masuk dengan akun lokal"}
            </button>

            <p className="mt-5 text-center text-sm leading-6 text-muted">
              Belum punya akses? Gunakan Google jika tersedia, atau minta admin workspace membuat akses untuk Anda.
            </p>
          </form>
        </section>
      </main>
    </div>
  );
};

export default Login;
