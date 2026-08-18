import { useState } from "react";
import { Link } from "react-router-dom";
import { useAssets } from "../../hooks/useAssets";

const CRITICALITY_LABEL: Record<string, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

export function AssetListPage() {
  const [search, setSearch] = useState("");
  const { data, isLoading, isError } = useAssets({ search: search || undefined });

  return (
    <div>
      <div className="page-header">
        <h1>Assets</h1>
        <input
          className="search-input"
          placeholder="Search by name, hostname, or code..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

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
