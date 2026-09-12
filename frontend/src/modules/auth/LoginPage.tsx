import { useState } from "react";
import { useLogin } from "../../hooks/useAuth";
import { getErrorMessage } from "../../services/api";

export function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const login = useLogin();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    login.mutate({ username, password });
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={handleSubmit}>
        <h1>
          <span className="sidebar-brand-mark">NF</span>
          NGFabric
        </h1>
        <p className="login-subtitle">Infrastructure design &amp; change automation</p>
        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus required />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {login.isError && <p className="form-error">{getErrorMessage(login.error, "Invalid username or password.")}</p>}
        <button type="submit" disabled={login.isPending}>
          {login.isPending ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}
