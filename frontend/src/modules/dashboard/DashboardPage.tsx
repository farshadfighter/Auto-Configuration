import { ClipboardCheck, GitCompare, Server, ShieldAlert, type LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";
import { useApprovalRequests } from "../../hooks/useApproval";
import { useAssets } from "../../hooks/useAssets";
import { useFindings } from "../../hooks/useBestPractice";
import { useDriftFindings } from "../../hooks/useDrift";

interface Tile {
  to: string;
  label: string;
  value: number | undefined;
  isLoading: boolean;
  icon: LucideIcon;
  tint: string;
}

function StatTile({ to, label, value, isLoading, icon: Icon, tint }: Tile) {
  return (
    <Link to={to} className="kpi-tile" style={{ textDecoration: "none" }}>
      <div className="kpi-tile-top">
        <span className="kpi-icon" style={{ background: `${tint}1a`, color: tint }}>
          <Icon size={17} strokeWidth={2} />
        </span>
      </div>
      <div>
        <div className="kpi-value">{isLoading ? "…" : (value ?? 0)}</div>
        <div className="kpi-label">{label}</div>
      </div>
    </Link>
  );
}

export function DashboardPage() {
  const { data: assets, isLoading: assetsLoading } = useAssets({ page_size: 1 });
  const { data: findings, isLoading: findingsLoading } = useFindings("new");
  const { data: approvals, isLoading: approvalsLoading } = useApprovalRequests("pending");
  const { data: drift, isLoading: driftLoading } = useDriftFindings("new");

  return (
    <div>
      <h1>Dashboard</h1>
      <p className="muted" style={{ marginTop: -8, marginBottom: 20 }}>
        A snapshot of what needs attention right now.
      </p>
      <div className="kpi-grid">
        <StatTile
          to="/assets"
          label="Total Assets"
          value={assets?.meta?.total as number | undefined}
          isLoading={assetsLoading}
          icon={Server}
          tint="#2563eb"
        />
        <StatTile
          to="/validation"
          label="Architecture Findings"
          value={findings?.length}
          isLoading={findingsLoading}
          icon={ShieldAlert}
          tint="#d97706"
        />
        <StatTile
          to="/design-configuration/jobs"
          label="Pending Approvals"
          value={approvals?.length}
          isLoading={approvalsLoading}
          icon={ClipboardCheck}
          tint="#5b5bd6"
        />
        <StatTile
          to="/drift"
          label="Configuration Drift"
          value={drift?.length}
          isLoading={driftLoading}
          icon={GitCompare}
          tint="#e5484d"
        />
      </div>
    </div>
  );
}
