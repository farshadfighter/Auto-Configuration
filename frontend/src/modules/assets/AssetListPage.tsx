import { useState } from "react";
import { Link } from "react-router-dom";
import { useAssets, useAssetTypes, useCreateAsset } from "../../hooks/useAssets";
import { getErrorMessage } from "../../services/api";

const CRITICALITY_LABEL: Record<string, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

function AddAssetForm({ onDone }: { onDone: () => void }) {
  const { data: assetTypes } = useAssetTypes();
  const createAsset = useCreateAsset();
  const [name, setName] = useState("");
  const [hostname, setHostname] = useState("");
  const [assetTypeId, setAssetTypeId] = useState("");
  const [managementIp, setManagementIp] = useState("");
  const [criticality, setCriticality] = useState<"low" | "medium" | "high" | "critical">("medium");

  function handleSubmit() {
    if (!name.trim() || !assetTypeId) return;
    createAsset.mutate(
      {
        name: name.trim(),
        hostname: hostname.trim() || undefined,
        asset_type_id: assetTypeId,
        management_ip: managementIp.trim() || undefined,
        criticality,
      },
      { onSuccess: onDone },
    );
  }

  return (
    <div style={{ marginBottom: 20, border: "1px solid var(--color-border)", borderRadius: 8, padding: 16 }}>
      <h2>Add Asset</h2>
      <div style={{ display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
        <input placeholder="Name (required)" value={name} onChange={(e) => setName(e.target.value)} />
        <select value={assetTypeId} onChange={(e) => setAssetTypeId(e.target.value)}>
          <option value="">Asset type (required)...</option>
          {assetTypes?.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
        <input placeholder="Hostname" value={hostname} onChange={(e) => setHostname(e.target.value)} />
        <input placeholder="Management IP" value={managementIp} onChange={(e) => setManagementIp(e.target.value)} />
        <select value={criticality} onChange={(e) => setCriticality(e.target.value as typeof criticality)}>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
      </div>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <button onClick={handleSubmit} disabled={!name.trim() || !assetTypeId || createAsset.isPending}>
          {createAsset.isPending ? "Creating..." : "Create Asset"}
        </button>
        <button onClick={onDone}>Cancel</button>
        {createAsset.isError && <span className="form-error">{getErrorMessage(createAsset.error, "Could not create asset")}</span>}
      </div>
    </div>
  );
}

export function AssetListPage() {
  const [search, setSearch] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);
  const { data, isLoading, isError } = useAssets({ search: search || undefined });

  return (
    <div>
      <div className="page-header">
        <h1>Assets</h1>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            className="search-input"
            placeholder="Search by name, hostname, or code..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {!showAddForm && <button onClick={() => setShowAddForm(true)}>Add Asset</button>}
        </div>
      </div>

      {showAddForm && <AddAssetForm onDone={() => setShowAddForm(false)} />}

      {isLoading && <p>Loading...</p>}
      {isError && <p className="form-error">Failed to load assets.</p>}

      {data && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Asset Code</th>
              <th>Name</th>
              <th>Hostname</th>
              <th>Management IP</th>
              <th>Criticality</th>
              <th>Status</th>
              <th>Managed</th>
            </tr>
          </thead>
          <tbody>
            {data.data.length === 0 && (
              <tr>
                <td colSpan={7} className="empty-state">
                  No assets found.
                </td>
              </tr>
            )}
            {data.data.map((asset) => (
              <tr key={asset.id}>
                <td>
                  <Link to={`/assets/${asset.id}`}>{asset.asset_code}</Link>
                </td>
                <td>{asset.name}</td>
                <td>{asset.hostname ?? "—"}</td>
                <td>{asset.management_ip ?? "—"}</td>
                <td>
                  <span className={`badge badge-${asset.criticality}`}>
                    {CRITICALITY_LABEL[asset.criticality]}
                  </span>
                </td>
                <td>{asset.status}</td>
                <td>{asset.managed}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
