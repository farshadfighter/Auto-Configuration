import { useParams } from "react-router-dom";
import { useDeploymentEvents, useDeploymentJob, useDeploymentResults, useStartDeployment } from "../../hooks/useDeployment";

const STATUS_BADGE: Record<string, string> = {
  success: "badge-low",
  rolled_back: "badge-medium",
};

export function DeploymentDetailPage() {
  const { deploymentId } = useParams<{ deploymentId: string }>();
  const { data: deployment } = useDeploymentJob(deploymentId);
  const { data: events } = useDeploymentEvents(deploymentId);
  const { data: results } = useDeploymentResults(deploymentId);
  const startDeployment = useStartDeployment(deploymentId ?? "");

  if (!deployment) return <p>Loading...</p>;

  const isTerminal = !["queued"].includes(deployment.status) || Boolean(deployment.completed_at);

  return (
    <div>
      <div className="page-header">
        <h1>Deployment</h1>
        {deployment.status === "queued" && !deployment.started_at && (
          <button onClick={() => startDeployment.mutate()} disabled={startDeployment.isPending}>
            Start Deployment
          </button>
        )}
      </div>

      <p>
        Status:{" "}
        <span className={`badge ${STATUS_BADGE[deployment.status] ?? (isTerminal && deployment.status !== "success" ? "badge-critical" : "badge-medium")}`}>
          {deployment.status}
        </span>
      </p>

      <h2>Live Progress</h2>
      {events && (
        <ul>
          {events.map((e) => (
            <li key={e.id}>
              <span className="muted">{new Date(e.created_at).toLocaleTimeString()}</span> [{e.event_type}] {e.message}
            </li>
          ))}
        </ul>
      )}

      {results && results.length > 0 && (
        <>
          <h2>Results</h2>
          <table className="data-table">
            <thead>
              <tr>
                <th>Applied</th>
                <th>Verified</th>
                <th>Output / Error</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={r.id}>
                  <td>
                    <span className={`badge ${r.success ? "badge-low" : "badge-critical"}`}>{r.success ? "OK" : "Failed"}</span>
                  </td>
                  <td>
                    {r.verified === null ? "—" : <span className={`badge ${r.verified ? "badge-low" : "badge-critical"}`}>{r.verified ? "Match" : "Mismatch"}</span>}
                  </td>
                  <td style={{ fontFamily: "monospace", fontSize: "0.8rem" }}>{r.error ?? r.output}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
