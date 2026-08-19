import { useState } from "react";
import { useAcceptFinding, useFindings, useIgnoreFinding, useRunAnalysis } from "../../hooks/useBestPractice";
import { getErrorMessage } from "../../services/api";

const STATUS_BADGE: Record<string, string> = {
  new: "badge-medium",
  in_review: "badge-medium",
  accepted: "badge-low",
  ignored: "badge-low",
  remediated: "badge-low",
  closed: "badge-low",
};

export function FindingsPage() {
  const [statusFilter, setStatusFilter] = useState("new");
  const { data: findings, isLoading } = useFindings(statusFilter || undefined);
  const runAnalysis = useRunAnalysis();
  const acceptFinding = useAcceptFinding();
  const ignoreFinding = useIgnoreFinding();
  const [ignoringId, setIgnoringId] = useState<string | null>(null);
  const [ignoreReason, setIgnoreReason] = useState("");

  function submitIgnore(id: string) {
    if (!ignoreReason.trim()) return;
    ignoreFinding.mutate({ id, reason: ignoreReason });
    setIgnoringId(null);
    setIgnoreReason("");
  }

  return (
    <div>
      <div className="page-header">
        <h1>Architecture Validation</h1>
        <button onClick={() => runAnalysis.mutate()} disabled={runAnalysis.isPending}>
          {runAnalysis.isPending ? "Analyzing..." : "Run Best Practice Analysis"}
        </button>
      </div>
      {runAnalysis.isError && <p className="form-error">{getErrorMessage(runAnalysis.error)}</p>}
      {acceptFinding.isError && <p className="form-error">{getErrorMessage(acceptFinding.error, "Could not accept finding")}</p>}
      {ignoreFinding.isError && <p className="form-error">{getErrorMessage(ignoreFinding.error, "Could not ignore finding")}</p>}

      <div style={{ marginBottom: 12 }}>
        <label>
          Status:{" "}
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All</option>
            <option value="new">New</option>
            <option value="in_review">In Review</option>
            <option value="accepted">Accepted</option>
            <option value="ignored">Ignored</option>
            <option value="remediated">Remediated</option>
            <option value="closed">Closed</option>
          </select>
        </label>
      </div>

      {isLoading && <p>Loading...</p>}
      {findings && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Code</th>
              <th>Title</th>
              <th>Category</th>
              <th>Severity</th>
              <th>Status</th>
              <th>Affected</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {findings.length === 0 && (
              <tr>
                <td colSpan={7} className="empty-state">
                  No findings.
                </td>
              </tr>
            )}
            {findings.map((f) => (
              <tr key={f.id}>
                <td>{f.finding_code}</td>
                <td>
                  {f.title}
                  {f.recommendation && <div className="muted">{f.recommendation}</div>}
                </td>
                <td>{f.category}</td>
                <td>
                  <span className={`badge badge-${f.severity}`}>{f.severity}</span>
                </td>
                <td>
                  <span className={`badge ${STATUS_BADGE[f.status]}`}>{f.status}</span>
                </td>
                <td>{f.affected_asset_ids.length}</td>
                <td>
                  {f.status === "new" && (
                    <div style={{ display: "flex", gap: 6 }}>
                      <button onClick={() => acceptFinding.mutate(f.id)}>Accept</button>
                      <button onClick={() => setIgnoringId(f.id)}>Ignore</button>
                    </div>
                  )}
                  {ignoringId === f.id && (
                    <div style={{ marginTop: 6 }}>
                      <input
                        placeholder="Reason (required)"
                        value={ignoreReason}
                        onChange={(e) => setIgnoreReason(e.target.value)}
                      />
                      <button onClick={() => submitIgnore(f.id)} disabled={!ignoreReason.trim()}>
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
