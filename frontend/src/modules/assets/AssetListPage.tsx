import { useState } from "react";
import { Link } from "react-router-dom";
import { SAFE_PIN_LABELS, useAssets, useAssetTypes, useCreateAsset, type SafePin } from "../../hooks/useAssets";
import { getErrorMessage } from "../../services/api";

const CRITICALITY_LABEL: Record<string, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

function AddAssetForm({ onDone }: { onDone: () => void }) {
  const { data: assetTypes, isLoading: assetTypesLoading, isError: assetTypesIsError } = useAssetTypes();
  const createAsset = useCreateAsset();
  const [name, setName] = useState("");
  const [hostname, setHostname] = useState("");
  const [assetTypeId, setAssetTypeId] = useState("");
  const [managementIp, setManagementIp] = useState("");
  const [criticality, setCriticality] = useState<"low" | "medium" | "high" | "critical">("medium");
  const [safePin, setSafePin] = useState<SafePin | "">("");

  function handleSubmit() {
    if (!name.trim() || !assetTypeId) return;
    createAsset.mutate(
      {
        name: name.trim(),
        hostname: hostname.trim() || undefined,
        asset_type_id: assetTypeId,
        management_ip: managementIp.trim() || undefined,
        criticality,
        safe_pin: safePin || undefined,
      },
      { onSuccess: onDone },
    );
  }

  return (
    <div className="panel" style={{ marginBottom: 20 }}>
      <h2>Add Asset</h2>
      <div style={{ display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
        <input placeholder="Name (required)" value={name} onChange={(e) => setName(e.target.value)} />
        <select value={assetTypeId} onChange={(e) => setAssetTypeId(e.target.value)}>
          <option value="">
            {assetTypesLoading ? "Loading asset types..." : "Asset type (required)..."}
          </option>
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
        <select value={safePin} onChange={(e) => setSafePin(e.target.value as SafePin | "")}>
          <option value="">SAFE zone (optional)...</option>
          {Object.entries(SAFE_PIN_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <button onClick={handleSubmit} disabled={!name.trim() || !assetTypeId || createAsset.isPending}>
          {createAsset.isPending ? "Creating..." : "Create Asset"}
        </button>
        <button className="btn-secondary" onClick={onDone}>
          Cancel
        </button>
        {createAsset.isError && <span className="form-error">{getErrorMessage(createAsset.error, "Could not create asset")}</span>}
        {assetTypesIsError && <span className="form-error">Could not load asset types.</span>}
        {!assetTypesLoading && !assetTypesIsError && assetTypes?.length === 0 && (
          <span className="form-error">No asset types configured yet - ask an administrator to add one.</span>
        )}
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
              <th>SAFE Zone</th>
            </tr>
          </thead>
          <tbody>
            {data.data.length === 0 && (
              <tr>
                <td colSpan={8} className="empty-state">
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
                <td>{asset.safe_pin ? SAFE_PIN_LABELS[asset.safe_pin] : <span className="muted">Unclassified</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
