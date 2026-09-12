import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useAsset, useAssetRelationships } from "../../hooks/useAssets";
import { useAssetBackups, useCreateBackup } from "../../hooks/useBackups";
import { useAssetConfigurationVersions } from "../../hooks/useConfiguration";
import { getErrorMessage } from "../../services/api";

export function AssetDetailPage() {
  const { assetId } = useParams<{ assetId: string }>();
  const navigate = useNavigate();
  const { data: asset, isLoading, isError } = useAsset(assetId);
  const { data: relationships } = useAssetRelationships(assetId);
  const { data: backups } = useAssetBackups(assetId);
  const { data: versions } = useAssetConfigurationVersions(assetId);
  const createBackup = useCreateBackup(assetId ?? "");
  const [technology, setTechnology] = useState("cisco_iosxe");

  if (isLoading) return <p>Loading...</p>;
  if (isError || !asset) return <p className="form-error">Asset not found.</p>;

  return (
    <div>
      <Link to="/assets">&larr; Back to assets</Link>
      <div className="page-header">
        <h1>
          {asset.name} <span className="muted">({asset.asset_code})</span>
        </h1>
        <button onClick={() => navigate(`/design-configuration/jobs?target_asset_id=${asset.id}`)}>Configure</button>
      </div>

      <dl className="detail-grid">
        <dt>Hostname</dt>
        <dd>{asset.hostname ?? "—"}</dd>
        <dt>Management IP</dt>
        <dd>{asset.management_ip ?? "—"}</dd>
        <dt>Criticality</dt>
        <dd>{asset.criticality}</dd>
        <dt>Status</dt>
        <dd>{asset.status}</dd>
        <dt>Managed</dt>
        <dd>{asset.managed}</dd>
      </dl>

      <h2>Relationships</h2>
      {!relationships || relationships.length === 0 ? (
        <p className="empty-state">No relationships recorded.</p>
      ) : (
        <ul>
          {relationships.map((rel) => (
            <li key={rel.id}>
              {rel.relationship_type}: {rel.source_asset_id} &rarr; {rel.target_asset_id}
            </li>
          ))}
        </ul>
      )}

      <h2>Backups</h2>
      <div style={{ display: "flex", gap: 8, marginBottom: 12, alignItems: "center" }}>
        <select value={technology} onChange={(e) => setTechnology(e.target.value)}>
          <option value="cisco_iosxe">cisco_iosxe</option>
          <option value="fortios">fortios</option>
          <option value="windows_dns">windows_dns</option>
          <option value="windows_dhcp">windows_dhcp</option>
        </select>
        <button onClick={() => createBackup.mutate({ technology })} disabled={createBackup.isPending}>
          Pull Live Backup
        </button>
        {createBackup.isError && (
          <span className="form-error">{getErrorMessage(createBackup.error, "Backup failed - is the device reachable?")}</span>
        )}
      </div>
      {!backups || backups.length === 0 ? (
        <p className="empty-state">No backups yet.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Created</th>
              <th>Type</th>
              <th>Technology</th>
              <th>Size</th>
              <th>Checksum</th>
            </tr>
          </thead>
          <tbody>
            {backups.map((b) => (
              <tr key={b.id}>
                <td>{new Date(b.created_at).toLocaleString()}</td>
                <td>{b.backup_type}</td>
                <td>{b.technology}</td>
                <td>{b.size_bytes} B</td>
                <td style={{ fontFamily: "monospace", fontSize: "0.75rem" }}>{b.checksum.slice(0, 12)}…</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2>Configuration Version History</h2>
      {!versions || versions.length === 0 ? (
        <p className="empty-state">No deployed configuration versions yet.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Deployed</th>
              <th>Technology</th>
              <th>Object Type</th>
              <th>Version</th>
              <th>Checksum</th>
            </tr>
          </thead>
          <tbody>
            {versions.map((v) => (
              <tr key={v.id}>
                <td>{new Date(v.created_at).toLocaleString()}</td>
                <td>{v.technology}</td>
                <td>{v.object_type}</td>
                <td>v{v.version_number}</td>
                <td style={{ fontFamily: "monospace", fontSize: "0.75rem" }}>{v.checksum.slice(0, 12)}…</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
