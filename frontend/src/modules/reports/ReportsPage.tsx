import {
  useAssetInventoryReport,
  useBackupsReport,
  useConfigurationJobsReport,
  useDeploymentsReport,
  useDriftReport,
  useFindingsReport,
  useTechnologyCoverageReport,
} from "../../hooks/useReports";

function TileStatus({ isLoading, isError }: { isLoading: boolean; isError: boolean }) {
  if (isError) return <p className="form-error">Failed to load.</p>;
  if (isLoading) return <p>Loading...</p>;
  return null;
}

function CountBreakdown({ counts, exclude = [] }: { counts: Record<string, unknown>; exclude?: string[] }) {
  const hidden = new Set(["total", ...exclude]);
  const entries = Object.entries(counts).filter(([k]) => !hidden.has(k));
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
          <TileStatus isLoading={inventory.isLoading} isError={inventory.isError} />
          {inventory.data && <CountBreakdown counts={inventory.data} />}
        </div>
        <div className="kpi-tile">
          <h2>Architecture Findings</h2>
          <TileStatus isLoading={findings.isLoading} isError={findings.isError} />
          {findings.data && <CountBreakdown counts={findings.data} />}
        </div>
        <div className="kpi-tile">
          <h2>Configuration Jobs</h2>
          <TileStatus isLoading={jobs.isLoading} isError={jobs.isError} />
          {jobs.data && <CountBreakdown counts={jobs.data} />}
        </div>
        <div className="kpi-tile">
          <h2>Deployments</h2>
          <TileStatus isLoading={deployments.isLoading} isError={deployments.isError} />
          {deployments.data && (
            <>
              <p>Success rate: {deployments.data.success_rate !== null ? `${Math.round(deployments.data.success_rate * 100)}%` : "—"}</p>
              <CountBreakdown counts={deployments.data} exclude={["success_rate"]} />
            </>
          )}
        </div>
        <div className="kpi-tile">
          <h2>Backups</h2>
          <TileStatus isLoading={backups.isLoading} isError={backups.isError} />
          {backups.data && <CountBreakdown counts={backups.data} />}
        </div>
        <div className="kpi-tile">
          <h2>Configuration Drift</h2>
          <TileStatus isLoading={drift.isLoading} isError={drift.isError} />
          {drift.data && <CountBreakdown counts={drift.data} />}
        </div>
      </div>

      <h2 style={{ marginTop: 24 }}>Technology Coverage</h2>
      <TileStatus isLoading={coverage.isLoading} isError={coverage.isError} />
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
