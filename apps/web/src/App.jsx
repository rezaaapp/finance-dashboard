import Dashboard from "./pages/Dashboard";
import GoogleAuthCallback from "./pages/GoogleAuthCallback";
import Login from "./pages/Login";
import { useState } from "react";

function App() {
  const [auth, setAuth] = useState(() => {
    const token = localStorage.getItem("finance-dashboard-token");
    const username = localStorage.getItem("finance-dashboard-username");
    const email = localStorage.getItem("finance-dashboard-email");
    const userId = localStorage.getItem("finance-dashboard-user-id");

    return token
      ? { token, username, email, userId }
      : null;
  });

  const handleLogin = (authData) => {
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

    setAuth(authData);
  };

  const handleLogout = () => {
    localStorage.removeItem("finance-dashboard-token");
    localStorage.removeItem("finance-dashboard-username");
    localStorage.removeItem("finance-dashboard-email");
    localStorage.removeItem("finance-dashboard-user-id");
    setAuth(null);
  };

  if (window.location.pathname === "/auth/google/callback") {
    return <GoogleAuthCallback onLogin={handleLogin} />;
  }

  if (!auth) {
    return <Login onLogin={handleLogin} />;
  }

  return <Dashboard onLogout={handleLogout} />;
}

export default App;
