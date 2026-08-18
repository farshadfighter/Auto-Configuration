import { useAssets } from "../../hooks/useAssets";

// KPI tiles per spec section 5. Only asset-derived KPIs are wired up in Phase 1; the rest
// (findings, jobs, deployments, drift, backup health, compliance) light up as those domains land.
export function DashboardPage() {
  const { data, isLoading } = useAssets({ page_size: 1 });
  const totalAssets = data?.meta?.total as number | undefined;

  return (
    <div>
      <h1>Dashboard</h1>
      <div className="kpi-grid">
        <div className="kpi-tile">
          <span className="kpi-value">{isLoading ? "…" : (totalAssets ?? 0)}</span>
          <span className="kpi-label">Total Assets</span>
        </div>
        <div className="kpi-tile disabled">
          <span className="kpi-value">—</span>
          <span className="kpi-label">Architecture Findings</span>
        </div>
        <div className="kpi-tile disabled">
          <span className="kpi-value">—</span>
          <span className="kpi-label">Pending Approvals</span>
        </div>
        <div className="kpi-tile disabled">
          <span className="kpi-value">—</span>
          <span className="kpi-label">Configuration Drift</span>
        </div>
      </div>
    </div>
  );
}
