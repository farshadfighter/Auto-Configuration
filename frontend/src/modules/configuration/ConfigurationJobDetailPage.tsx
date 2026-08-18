import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useApprovalRequestForJob, useApproveRequest, useRejectRequest } from "../../hooks/useApproval";
import { useAssets } from "../../hooks/useAssets";
import { getErrorMessage } from "../../services/api";
import {
  useAddConfigurationObject,
  useConfigurationDiff,
  useConfigurationJob,
  useConfigurationObjects,
  useGenerateJob,
  useSubmitForApproval,
  useTechnologyCatalog,
  useValidateJob,
} from "../../hooks/useConfiguration";
import { useCreateDeployment } from "../../hooks/useDeployment";

const OBJECT_TYPE_PARAM_HINTS: Record<string, string> = {
  vlan: '{"vlan_id": 120, "name": "Guest"}',
  interface: '{"name": "Gi1/0/1", "mode": "access", "access_vlan": 120}',
  firewall_policy: '{"name": "allow-web", "srcintf": "port1", "dstintf": "port2", "srcaddr": "all", "dstaddr": "all", "action": "accept"}',
  dns_zone: '{"zone_name": "corp.local", "dynamic_update": "secure"}',
  dhcp_scope: '{"scope_id": "10.0.0.0", "name": "Branch", "start_range": "10.0.0.10", "end_range": "10.0.0.200", "subnet_mask": "255.255.255.0"}',
};

const VALIDATION_BADGE: Record<string, string> = {
  pending: "badge-medium",
  pass: "badge-low",
  warning: "badge-medium",
  high: "badge-high",
  critical: "badge-critical",
};

export function ConfigurationJobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { data: job } = useConfigurationJob(jobId);
  const { data: objects } = useConfigurationObjects(jobId);
  const { data: assets } = useAssets({ page_size: 200 });
  const { data: catalog } = useTechnologyCatalog();
  const addObject = useAddConfigurationObject(jobId ?? "");
  const generateJob = useGenerateJob(jobId ?? "");
  const validateJob = useValidateJob(jobId ?? "");
  const submitApproval = useSubmitForApproval(jobId ?? "");
  const { data: approvalRequest } = useApprovalRequestForJob(jobId);
  const approveRequest = useApproveRequest(jobId ?? "");
  const rejectRequest = useRejectRequest(jobId ?? "");
  const createDeployment = useCreateDeployment();
  const [rejectReason, setRejectReason] = useState("");
  const [showDiff, setShowDiff] = useState(false);
  const { data: diff } = useConfigurationDiff(jobId, showDiff);

  const [assetId, setAssetId] = useState("");
  const [technology, setTechnology] = useState("cisco_iosxe");
  const [objectType, setObjectType] = useState("vlan");
  const [paramsText, setParamsText] = useState(OBJECT_TYPE_PARAM_HINTS.vlan);

  if (!job) return <p>Loading...</p>;

  const availableObjectTypes = catalog?.find((c) => c.technology === technology);
  const objectTypeOptions = availableObjectTypes ? Object.keys(availableObjectTypes.capabilities) : [];

  function handleAddObject() {
    try {
      const parameters = JSON.parse(paramsText);
      addObject.mutate({ asset_id: assetId, technology, object_type: objectType, parameters });
    } catch {
      alert("Parameters must be valid JSON");
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>
          {job.job_number} <span className="muted">{job.name}</span>
        </h1>
        <div style={{ display: "flex", gap: 8 }}>
          {job.status === "draft" && (
            <button onClick={() => generateJob.mutate()} disabled={generateJob.isPending}>
              Generate
            </button>
          )}
          {job.status === "generated" && (
            <button onClick={() => validateJob.mutate()} disabled={validateJob.isPending}>
              Validate
            </button>
          )}
          {job.status === "validated" && (
            <button onClick={() => submitApproval.mutate()} disabled={submitApproval.isPending}>
              Submit for Approval
            </button>
          )}
          {job.status === "approved" && (
            <button
              onClick={async () => {
                const deployment = await createDeployment.mutateAsync(job.id);
                navigate(`/deployment/jobs/${deployment.id}`);
              }}
              disabled={createDeployment.isPending}
            >
              Create Deployment
            </button>
          )}
          <button onClick={() => setShowDiff((v) => !v)}>{showDiff ? "Hide Diff" : "Show Diff"}</button>
        </div>
      </div>

      <p>
        Status: <span className="badge badge-medium">{job.status}</span>{" "}
        {job.risk_level && <span className={`badge badge-${job.risk_level}`}>risk: {job.risk_level}</span>}
      </p>

      {job.status === "pending_approval" && approvalRequest && approvalRequest.status === "pending" && (
        <section style={{ marginBottom: 20, border: "1px solid var(--color-border)", borderRadius: 8, padding: 16 }}>
          <h2>Approval Required</h2>
          <p className="muted">
            Requires {approvalRequest.required_approvals} approval(s) at risk level {approvalRequest.risk_level}.
          </p>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button onClick={() => approveRequest.mutate({ requestId: approvalRequest.id })} disabled={approveRequest.isPending}>
              Approve
            </button>
            <input placeholder="Rejection reason" value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} />
            <button
              onClick={() => rejectRequest.mutate({ requestId: approvalRequest.id, comment: rejectReason })}
              disabled={!rejectReason.trim() || rejectRequest.isPending}
            >
              Reject
            </button>
          </div>
          {approveRequest.isError && <p className="form-error">{getErrorMessage(approveRequest.error, "Could not approve")}</p>}
          {rejectRequest.isError && <p className="form-error">{getErrorMessage(rejectRequest.error, "Could not reject")}</p>}
        </section>
      )}

      {job.status === "draft" && (
        <section style={{ marginBottom: 20, border: "1px solid var(--color-border)", borderRadius: 8, padding: 16 }}>
          <h2>Add Configuration Object</h2>
          <div style={{ display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
            <select value={assetId} onChange={(e) => setAssetId(e.target.value)}>
              <option value="">Select asset...</option>
              {assets?.data.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
            <select
              value={technology}
              onChange={(e) => {
                setTechnology(e.target.value);
                const firstType = catalog?.find((c) => c.technology === e.target.value);
                const type = firstType ? Object.keys(firstType.capabilities)[0] : "";
                setObjectType(type);
                setParamsText(OBJECT_TYPE_PARAM_HINTS[type] ?? "{}");
              }}
            >
              {catalog?.map((c) => (
                <option key={c.technology} value={c.technology}>
                  {c.technology}
                </option>
              ))}
            </select>
            <select
              value={objectType}
              onChange={(e) => {
                setObjectType(e.target.value);
                setParamsText(OBJECT_TYPE_PARAM_HINTS[e.target.value] ?? "{}");
              }}
            >
              {objectTypeOptions.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <textarea value={paramsText} onChange={(e) => setParamsText(e.target.value)} rows={3} style={{ width: "100%", maxWidth: 600, fontFamily: "monospace" }} />
          <div style={{ marginTop: 8 }}>
            <button onClick={handleAddObject} disabled={!assetId || addObject.isPending}>
              Add Object
            </button>
          </div>
        </section>
      )}

      <h2>Objects</h2>
      {objects && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Object Type</th>
              <th>Technology</th>
              <th>Change</th>
              <th>Validation</th>
              <th>Rendered Config</th>
            </tr>
          </thead>
          <tbody>
            {objects.length === 0 && (
              <tr>
                <td colSpan={5} className="empty-state">
                  No objects yet.
                </td>
              </tr>
            )}
            {objects.map((o) => (
              <tr key={o.id}>
                <td>{o.object_type}</td>
                <td>{o.technology}</td>
                <td>{o.change_type ?? "—"}</td>
                <td>
                  <span className={`badge ${VALIDATION_BADGE[o.validation_status]}`}>{o.validation_status}</span>
                  {o.validation_issues?.map((issue, i) => (
                    <div key={i} className="form-error" style={{ fontSize: "0.75rem" }}>
                      {issue.message}
                    </div>
                  ))}
                </td>
                <td>
                  <pre style={{ margin: 0, fontSize: "0.75rem", whiteSpace: "pre-wrap" }}>
                    {o.rendered_operations?.map((op) => op.rendered_config).join("\n")}
                  </pre>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {showDiff && diff && (
        <div style={{ marginTop: 20 }}>
          <h2>Diff Preview</h2>
          {diff.map((d) => (
            <div key={d.object_id} style={{ marginBottom: 12, border: "1px solid var(--color-border)", borderRadius: 8, padding: 12 }}>
              <strong>
                {d.object_type} ({d.change_type})
              </strong>
              <ul>
                {d.diff.map((f, i) => (
                  <li key={i}>
                    {f.field}: {JSON.stringify(f.before)} &rarr; {JSON.stringify(f.after)}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
