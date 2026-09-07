import { useState } from "react";
import { Link } from "react-router-dom";
import { useCreateDesign, useDesigns } from "../../hooks/useDesigns";

export function DesignListPage() {
  const { data: designs, isLoading } = useDesigns();
  const createDesign = useCreateDesign();
  const [name, setName] = useState("");

  function handleCreate() {
    if (!name.trim()) return;
    createDesign.mutate({ name, mode: "manual" });
    setName("");
  }

  return (
    <div>
      <div className="page-header">
        <h1>Architecture Designs</h1>
        <div style={{ display: "flex", gap: 8 }}>
          <Link to="/design-configuration/jobs">
            <button type="button" className="btn-secondary">
              Configuration Jobs &rarr;
            </button>
          </Link>
          <input placeholder="New design name" value={name} onChange={(e) => setName(e.target.value)} />
          <button onClick={handleCreate} disabled={!name.trim() || createDesign.isPending}>
            Create Design
          </button>
        </div>
      </div>

      {isLoading && <p>Loading...</p>}
      {designs && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Mode</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {designs.length === 0 && (
              <tr>
                <td colSpan={3} className="empty-state">
                  No designs yet.
                </td>
              </tr>
            )}
            {designs.map((d) => (
              <tr key={d.id}>
                <td>
                  <Link to={`/design-configuration/designs/${d.id}`}>{d.name}</Link>
                </td>
                <td>{d.mode}</td>
                <td>{new Date(d.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
