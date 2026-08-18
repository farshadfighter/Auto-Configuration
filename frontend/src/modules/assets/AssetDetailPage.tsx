import { Link, useParams } from "react-router-dom";
import { useAsset, useAssetRelationships } from "../../hooks/useAssets";

export function AssetDetailPage() {
  const { assetId } = useParams<{ assetId: string }>();
  const { data: asset, isLoading, isError } = useAsset(assetId);
  const { data: relationships } = useAssetRelationships(assetId);

  if (isLoading) return <p>Loading...</p>;
  if (isError || !asset) return <p className="form-error">Asset not found.</p>;

  return (
    <div>
      <Link to="/assets">&larr; Back to assets</Link>
      <h1>
        {asset.name} <span className="muted">({asset.asset_code})</span>
      </h1>

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
    </div>
  );
}
