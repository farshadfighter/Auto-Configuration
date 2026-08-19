import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAcceptDriftCurrent, useDriftFindings, useIgnoreDrift, useRestoreDesired, useRunDriftAnalysis } from "../../hooks/useDrift";
import { getErrorMessage } from "../../services/api";

const STATUS_BADGE: Record<string, string> = {
  new: "badge-critical",
  accepted: "badge-low",
  ignored: "badge-low",
  remediated: "badge-low",
};

export function DriftFindingsPage() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState("new");
  const { data: findings, isLoading } = useDriftFindings(statusFilter || undefined);
  const runAnalysis = useRunDriftAnalysis();
  const acceptCurrent = useAcceptDriftCurrent();
  const ignoreDrift = useIgnoreDrift();
  const restoreDesired = useRestoreDesired();
  const [ignoringId, setIgnoringId] = useState<string | null>(null);
  const [reason, setReason] = useState("");

  async function handleRestore(id: string) {
    try {
      const result = await restoreDesired.mutateAsync(id);
      navigate(`/design-configuration/jobs/${result.configuration_job_id}`);
    } catch {
      // surfaced below via restoreDesired.isError
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Configuration Drift</h1>
        <button onClick={() => runAnalysis.mutate()} disabled={runAnalysis.isPending}>
          {runAnalysis.isPending ? "Analyzing..." : "Run Drift Analysis"}
        </button>
      </div>
      {runAnalysis.isError && <p className="form-error">{getErrorMessage(runAnalysis.error)}</p>}
      {acceptCurrent.isError && <p className="form-error">{getErrorMessage(acceptCurrent.error, "Could not accept current state")}</p>}
      {ignoreDrift.isError && <p className="form-error">{getErrorMessage(ignoreDrift.error, "Could not ignore finding")}</p>}
      {restoreDesired.isError && <p className="form-error">{getErrorMessage(restoreDesired.error, "Could not create remediation job")}</p>}

      <div style={{ marginBottom: 12 }}>
        <label>
          Status:{" "}
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All</option>
            <option value="new">New</option>
            <option value="accepted">Accepted</option>
            <option value="ignored">Ignored</option>
            <option value="remediated">Remediated</option>
          </select>
        </label>
      </div>

      {isLoading && <p>Loading...</p>}
      {findings && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Technology</th>
              <th>Object</th>
              <th>Severity</th>
              <th>Status</th>
              <th>Diff</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {findings.length === 0 && (
              <tr>
                <td colSpan={6} className="empty-state">
                  No drift findings.
                </td>
              </tr>
            )}
            {findings.map((f) => (
              <tr key={f.id}>
                <td>{f.technology}</td>
                <td>{f.object_type}</td>
                <td>
                  <span className={`badge badge-${f.severity}`}>{f.severity}</span>
                </td>
                <td>
                  <span className={`badge ${STATUS_BADGE[f.status]}`}>{f.status}</span>
                </td>
                <td>
                  {f.diff.map((d, i) => (
                    <div key={i} style={{ fontSize: "0.75rem" }}>
                      {d.field}: {JSON.stringify(d.before)} &rarr; {JSON.stringify(d.after)}
                    </div>
                  ))}
                </td>
                <td>
                  {f.status === "new" && (
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                      <button onClick={() => acceptCurrent.mutate(f.id)}>Accept Current</button>
                      <button onClick={() => handleRestore(f.id)}>Restore Desired</button>
                      <button onClick={() => setIgnoringId(f.id)}>Ignore</button>
                    </div>
                  )}
                  {ignoringId === f.id && (
                    <div style={{ marginTop: 6 }}>
                      <input placeholder="Reason (required)" value={reason} onChange={(e) => setReason(e.target.value)} />
                      <button
                        onClick={() => {
                          ignoreDrift.mutate({ id: f.id, reason });
                          setIgnoringId(null);
                          setReason("");
                        }}
                        disabled={!reason.trim()}
                      >
                        Confirm
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
