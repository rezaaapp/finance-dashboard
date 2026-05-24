import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import { useState } from "react";

function App() {
  const [auth, setAuth] = useState(() => {
    const token = localStorage.getItem("finance-dashboard-token");
    const username = localStorage.getItem("finance-dashboard-username");

    return token
      ? { token, username }
      : null;
  });

  const handleLogin = (authData) => {
    localStorage.setItem("finance-dashboard-token", authData.token);
    localStorage.setItem("finance-dashboard-username", authData.username);
    setAuth(authData);
  };

  const handleLogout = () => {
    localStorage.removeItem("finance-dashboard-token");
    localStorage.removeItem("finance-dashboard-username");
    setAuth(null);
  };

  if (!auth) {
    return <Login onLogin={handleLogin} />;
  }

  return <Dashboard onLogout={handleLogout} />;
}

export default App;
