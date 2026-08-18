import {
  useAssetInventoryReport,
  useBackupsReport,
  useConfigurationJobsReport,
  useDeploymentsReport,
  useDriftReport,
  useFindingsReport,
  useTechnologyCoverageReport,
} from "../../hooks/useReports";

function CountBreakdown({ counts }: { counts: Record<string, unknown> }) {
  const entries = Object.entries(counts).filter(([k]) => k !== "total");
  if (entries.length === 0) return <p className="empty-state">No data.</p>;
  return (
    <ul>
      {entries.map(([key, value]) =>
        typeof value === "object" && value !== null ? (
          <li key={key}>
            {key}:
            <ul>
              {Object.entries(value as Record<string, number>).map(([k, v]) => (
                <li key={k}>
                  {k || "(none)"}: {v}
                </li>
              ))}
            </ul>
          </li>
        ) : (
          <li key={key}>
            {key}: {String(value)}
          </li>
        ),
      )}
    </ul>
  );
}

export function ReportsPage() {
  const inventory = useAssetInventoryReport();
  const findings = useFindingsReport();
  const jobs = useConfigurationJobsReport();
  const deployments = useDeploymentsReport();
  const backups = useBackupsReport();
  const drift = useDriftReport();
  const coverage = useTechnologyCoverageReport();

  return (
    <div>
      <h1>Reports</h1>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16 }}>
        <div className="kpi-tile">
          <h2>Asset Inventory</h2>
          {inventory.data && <CountBreakdown counts={inventory.data} />}
        </div>
        <div className="kpi-tile">
          <h2>Architecture Findings</h2>
          {findings.data && <CountBreakdown counts={findings.data} />}
        </div>
        <div className="kpi-tile">
          <h2>Configuration Jobs</h2>
          {jobs.data && <CountBreakdown counts={jobs.data} />}
        </div>
        <div className="kpi-tile">
          <h2>Deployments</h2>
          {deployments.data && (
            <>
              <p>Success rate: {deployments.data.success_rate !== null ? `${Math.round(deployments.data.success_rate * 100)}%` : "—"}</p>
              <CountBreakdown counts={deployments.data} />
            </>
          )}
        </div>
        <div className="kpi-tile">
          <h2>Backups</h2>
          {backups.data && <CountBreakdown counts={backups.data} />}
        </div>
        <div className="kpi-tile">
          <h2>Configuration Drift</h2>
          {drift.data && <CountBreakdown counts={drift.data} />}
        </div>
      </div>

      <h2 style={{ marginTop: 24 }}>Technology Coverage</h2>
      {coverage.data && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Technology</th>
              <th>Vendor</th>
              <th>Object Types</th>
              <th>Assets Deployed</th>
            </tr>
          </thead>
          <tbody>
            {coverage.data.map((c) => (
              <tr key={c.technology}>
                <td>{c.technology}</td>
                <td>{c.vendor}</td>
                <td>{c.object_types.join(", ")}</td>
                <td>{c.deployed_asset_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
