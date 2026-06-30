import Dashboard from "./pages/Dashboard";
import GoogleAuthCallback from "./pages/GoogleAuthCallback";
import Login from "./pages/Login";
import { useState } from "react";
import useSystemInfo from "./hooks/useSystemInfo";

function App() {
  const systemInfoState = useSystemInfo();
  const [auth, setAuth] = useState(() => {
    const token = localStorage.getItem("finance-dashboard-token");
    const username = localStorage.getItem("finance-dashboard-username");
    const email = localStorage.getItem("finance-dashboard-email");
    const userId = localStorage.getItem("finance-dashboard-user-id");
    const role = localStorage.getItem("finance-dashboard-role");
    const provider = localStorage.getItem("finance-dashboard-provider");

    return token
      ? { token, username, email, userId, role, provider }
      : null;
  });

  const handleLogin = (authData) => {
    if (authData.provider === "impersonation" && auth?.provider !== "impersonation") {
      localStorage.setItem(
        "finance-dashboard-impersonator-auth",
        JSON.stringify(auth)
      );
    }

    localStorage.setItem("finance-dashboard-token", authData.token);
    localStorage.setItem(
      "finance-dashboard-username",
      authData.username || authData.email || "User"
    );

    if (authData.email) {
      localStorage.setItem("finance-dashboard-email", authData.email);
    }

    if (authData.userId) {
      localStorage.setItem("finance-dashboard-user-id", authData.userId);
    }

    if (authData.role) {
      localStorage.setItem("finance-dashboard-role", authData.role);
    }

    if (authData.provider) {
      localStorage.setItem("finance-dashboard-provider", authData.provider);
    } else {
      localStorage.removeItem("finance-dashboard-provider");
    }

    setAuth({
      ...authData,
      username: authData.username || authData.email || "User",
    });
  };

  const restoreAuth = (nextAuth) => {
    localStorage.setItem("finance-dashboard-token", nextAuth.token);
    localStorage.setItem(
      "finance-dashboard-username",
      nextAuth.username || nextAuth.email || "User"
    );

    if (nextAuth.email) {
      localStorage.setItem("finance-dashboard-email", nextAuth.email);
    } else {
      localStorage.removeItem("finance-dashboard-email");
    }

    if (nextAuth.userId) {
      localStorage.setItem("finance-dashboard-user-id", nextAuth.userId);
    } else {
      localStorage.removeItem("finance-dashboard-user-id");
    }

    if (nextAuth.role) {
      localStorage.setItem("finance-dashboard-role", nextAuth.role);
    } else {
      localStorage.removeItem("finance-dashboard-role");
    }

    if (nextAuth.provider) {
      localStorage.setItem("finance-dashboard-provider", nextAuth.provider);
    } else {
      localStorage.removeItem("finance-dashboard-provider");
    }

    setAuth({
      ...nextAuth,
      username: nextAuth.username || nextAuth.email || "User",
    });
  };

  const handleExitImpersonation = () => {
    const storedAdminAuth = localStorage.getItem("finance-dashboard-impersonator-auth");

    if (!storedAdminAuth) {
      handleLogout();
      return;
    }

    try {
      const adminAuth = JSON.parse(storedAdminAuth);

      localStorage.removeItem("finance-dashboard-impersonator-auth");
      restoreAuth(adminAuth);
    } catch (error) {
      console.error(error);
      handleLogout();
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("finance-dashboard-token");
    localStorage.removeItem("finance-dashboard-username");
    localStorage.removeItem("finance-dashboard-email");
    localStorage.removeItem("finance-dashboard-user-id");
    localStorage.removeItem("finance-dashboard-role");
    localStorage.removeItem("finance-dashboard-provider");
    localStorage.removeItem("finance-dashboard-impersonator-auth");
    setAuth(null);
  };

  const isGoogleAuthCallback =
    window.location.pathname === "/auth/callback" ||
    window.location.pathname === "/auth/google/callback";

  if (isGoogleAuthCallback) {
    return <GoogleAuthCallback onLogin={handleLogin} />;
  }

  if (!auth) {
    return <Login onLogin={handleLogin} systemInfoState={systemInfoState} />;
  }

  return (
    <Dashboard
      auth={auth}
      onExitImpersonation={handleExitImpersonation}
      onImpersonate={handleLogin}
      onLogout={handleLogout}
      systemInfoState={systemInfoState}
    />
  );
}

export default App;
