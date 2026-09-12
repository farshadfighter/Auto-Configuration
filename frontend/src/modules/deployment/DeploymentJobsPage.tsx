import { Link } from "react-router-dom";
import { useDeploymentJobs } from "../../hooks/useDeployment";

const STATUS_BADGE: Record<string, string> = {
  queued: "badge-medium",
  precheck: "badge-medium",
  backup: "badge-medium",
  applying: "badge-medium",
  verifying: "badge-medium",
  success: "badge-low",
  rolled_back: "badge-medium",
  precheck_failed: "badge-critical",
  backup_failed: "badge-critical",
  apply_failed: "badge-critical",
  verify_failed: "badge-critical",
  rollback_failed: "badge-critical",
};

export function DeploymentJobsPage() {
  const { data: deployments, isLoading, isError } = useDeploymentJobs();

  return (
    <div>
      <h1>Deployment</h1>
      <p className="muted">
        Deployments are created from an approved Configuration Job (Design &amp; Configuration &rarr; Configuration Jobs).
      </p>

      {isLoading && <p>Loading...</p>}
      {isError && <p className="form-error">Failed to load deployments.</p>}
      {deployments && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Created</th>
              <th>Status</th>
              <th>Started</th>
              <th>Completed</th>
            </tr>
          </thead>
          <tbody>
            {deployments.length === 0 && (
              <tr>
                <td colSpan={4} className="empty-state">
                  No deployments yet.
                </td>
              </tr>
            )}
            {deployments.map((d) => (
              <tr key={d.id}>
                <td>
                  <Link to={`/deployment/jobs/${d.id}`}>{new Date(d.created_at).toLocaleString()}</Link>
                </td>
                <td>
                  <span className={`badge ${STATUS_BADGE[d.status] ?? "badge-medium"}`}>{d.status}</span>
                </td>
                <td>{d.started_at ? new Date(d.started_at).toLocaleTimeString() : "—"}</td>
                <td>{d.completed_at ? new Date(d.completed_at).toLocaleTimeString() : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
