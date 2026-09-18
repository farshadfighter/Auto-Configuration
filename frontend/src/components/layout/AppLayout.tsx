import { Outlet } from "react-router-dom";
import { useLogout } from "../../hooks/useAuth";
import { useAuthStore } from "../../stores/authStore";
import { NotificationBell } from "./NotificationBell";
import { Sidebar } from "./Sidebar";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  const chars = parts.length > 1 ? [parts[0][0], parts[parts.length - 1][0]] : [name.slice(0, 2)];
  return chars.join("").toUpperCase();
}

export function AppLayout() {
  const user = useAuthStore((s) => s.user);
  const logout = useLogout();
  const displayName = user?.full_name ?? user?.username ?? "";

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-main">
        <header className="topbar">
          <span />
          <div className="topbar-user">
            <NotificationBell />
            <span className="topbar-avatar">{displayName ? initials(displayName) : ""}</span>
            <span>{displayName}</span>
            <button onClick={logout}>Sign out</button>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
