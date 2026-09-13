import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useGenerateSafeRecommendation } from "../../hooks/useArchitectureRecommendation";
import { useCreateDesign, useDesigns } from "../../hooks/useDesigns";
import { getErrorMessage } from "../../services/api";

export function DesignListPage() {
  const navigate = useNavigate();
  const { data: designs, isLoading } = useDesigns();
  const createDesign = useCreateDesign();
  const generateSafe = useGenerateSafeRecommendation();
  const [name, setName] = useState("");
  const [safeName, setSafeName] = useState("SAFE Recommendation");

  function handleCreate() {
    if (!name.trim()) return;
    createDesign.mutate({ name, mode: "manual" });
    setName("");
  }

  function handleGenerateSafe() {
    if (!safeName.trim()) return;
    generateSafe.mutate(safeName.trim(), {
      onSuccess: (result) =>
        navigate(`/design-configuration/designs/${result.design_id}`, {
          state: { scaleGaps: result.scale_gaps, locationGaps: result.location_gaps },
        }),
    });
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

      <div className="panel" style={{ marginBottom: 20, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <div style={{ marginRight: "auto" }}>
          <strong>Generate SAFE Recommendation</strong>
          <p className="muted" style={{ margin: "2px 0 0" }}>
            Builds a reference architecture from assets you've classified by SAFE zone (Assets &rarr; SAFE Zone column).
          </p>
        </div>
        <input placeholder="Design name" value={safeName} onChange={(e) => setSafeName(e.target.value)} />
        <button onClick={handleGenerateSafe} disabled={!safeName.trim() || generateSafe.isPending}>
          {generateSafe.isPending ? "Generating..." : "Generate"}
        </button>
      </div>
      {generateSafe.isError && (
        <p className="form-error">{getErrorMessage(generateSafe.error, "Could not generate recommendation")}</p>
      )}

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
