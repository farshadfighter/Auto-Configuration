import { Navigate, Outlet, createBrowserRouter } from "react-router-dom";
import { AppLayout } from "../components/layout/AppLayout";
import { useCurrentUser } from "../hooks/useAuth";
import { LoginPage } from "../modules/auth/LoginPage";
import { AuditLogPage } from "../modules/audit/AuditLogPage";
import { AssetDetailPage } from "../modules/assets/AssetDetailPage";
import { AssetListPage } from "../modules/assets/AssetListPage";
import { DashboardPage } from "../modules/dashboard/DashboardPage";
import { DiscoveryJobsPage } from "../modules/discovery/DiscoveryJobsPage";
import { ConfigurationJobDetailPage } from "../modules/configuration/ConfigurationJobDetailPage";
import { ConfigurationJobsPage } from "../modules/configuration/ConfigurationJobsPage";
import { DesignCanvasPage } from "../modules/design/DesignCanvasPage";
import { DesignListPage } from "../modules/design/DesignListPage";
import { TopologyPage } from "../modules/topology/TopologyPage";
import { FindingsPage } from "../modules/validation/FindingsPage";
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
          { path: "/validation", element: <FindingsPage /> },
          { path: "/design-configuration", element: <DesignListPage /> },
          { path: "/design-configuration/designs/:designId", element: <DesignCanvasPage /> },
          { path: "/design-configuration/jobs", element: <ConfigurationJobsPage /> },
          { path: "/design-configuration/jobs/:jobId", element: <ConfigurationJobDetailPage /> },
          { path: "/audit", element: <AuditLogPage /> },
        ],
      },
    ],
  },
]);
