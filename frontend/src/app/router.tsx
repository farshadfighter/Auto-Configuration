import { Navigate, Outlet, createBrowserRouter } from "react-router-dom";
import { AppLayout } from "../components/layout/AppLayout";
import { useCurrentUser } from "../hooks/useAuth";
import { LoginPage } from "../modules/auth/LoginPage";
import { AuditLogPage } from "../modules/audit/AuditLogPage";
import { AssetDetailPage } from "../modules/assets/AssetDetailPage";
import { AssetListPage } from "../modules/assets/AssetListPage";
import { DashboardPage } from "../modules/dashboard/DashboardPage";
import { DiscoveryJobsPage } from "../modules/discovery/DiscoveryJobsPage";
import { TopologyPage } from "../modules/topology/TopologyPage";
import { useAuthStore } from "../stores/authStore";

function RequireAuth() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated());
  useCurrentUser();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Outlet />;
}

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: "/", element: <Navigate to="/dashboard" replace /> },
          { path: "/dashboard", element: <DashboardPage /> },
          { path: "/assets", element: <AssetListPage /> },
          { path: "/assets/:assetId", element: <AssetDetailPage /> },
          { path: "/discovery", element: <DiscoveryJobsPage /> },
          { path: "/topology", element: <TopologyPage /> },
          { path: "/audit", element: <AuditLogPage /> },
        ],
      },
    ],
  },
]);
