import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAsset } from "../../hooks/useAssets";
import { useConfigurationJobs, useCreateConfigurationJob } from "../../hooks/useConfiguration";
import { getErrorMessage } from "../../services/api";

const STATUS_BADGE: Record<string, string> = {
  draft: "badge-medium",
  generated: "badge-medium",
  validating: "badge-medium",
  validated: "badge-low",
  pending_approval: "badge-medium",
  approved: "badge-low",
  ready: "badge-low",
  rejected: "badge-critical",
  failed: "badge-critical",
};

export function ConfigurationJobsPage() {
  const { data: jobs, isLoading, isError } = useConfigurationJobs();
  const createJob = useCreateConfigurationJob();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const targetAssetId = searchParams.get("target_asset_id") ?? undefined;
  const { data: targetAsset } = useAsset(targetAssetId);
  const [name, setName] = useState("");
  const [justification, setJustification] = useState("");

  async function handleCreate() {
    if (!name.trim() || !justification.trim()) return;
    const job = await createJob.mutateAsync({
      name,
      justification_ref: justification,
      target_asset_ids: targetAssetId ? [targetAssetId] : undefined,
    });
    setName("");
    setJustification("");
    navigate(`/design-configuration/jobs/${job.id}`);
  }

  return (
    <div>
      <div className="page-header">
        <h1>Configuration Jobs</h1>
      </div>

      {targetAssetId && (
        <p className="muted" style={{ marginBottom: 12 }}>
          Scoped to device: <strong>{targetAsset?.name ?? targetAssetId}</strong>
        </p>
      )}

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <input placeholder="Job name" value={name} onChange={(e) => setName(e.target.value)} />
        <input placeholder="Justification (ticket/reason)" value={justification} onChange={(e) => setJustification(e.target.value)} style={{ width: 260 }} />
        <button onClick={handleCreate} disabled={!name.trim() || !justification.trim() || createJob.isPending}>
          Create Job
        </button>
      </div>
      {createJob.isError && <p className="form-error">{getErrorMessage(createJob.error, "Could not create job")}</p>}

      {isLoading && <p>Loading...</p>}
      {isError && <p className="form-error">Failed to load configuration jobs.</p>}
      {jobs && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Job #</th>
              <th>Name</th>
              <th>Status</th>
              <th>Risk</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {jobs.length === 0 && (
              <tr>
                <td colSpan={5} className="empty-state">
                  No configuration jobs yet.
                </td>
              </tr>
            )}
            {jobs.map((j) => (
              <tr key={j.id}>
                <td>
                  <Link to={`/design-configuration/jobs/${j.id}`}>{j.job_number}</Link>
                </td>
                <td>{j.name}</td>
                <td>
                  <span className={`badge ${STATUS_BADGE[j.status]}`}>{j.status}</span>
                </td>
                <td>{j.risk_level ? <span className={`badge badge-${j.risk_level}`}>{j.risk_level}</span> : "—"}</td>
                <td>{new Date(j.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
