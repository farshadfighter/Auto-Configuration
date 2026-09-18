import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useGenerateSafeRecommendation } from "../../hooks/useArchitectureRecommendation";
import { useCreateDesign, useDesigns } from "../../hooks/useDesigns";
import { useCreateDesignFromTemplate, useDesignTemplates } from "../../hooks/useDesignTemplates";
import { getErrorMessage } from "../../services/api";

export function DesignListPage() {
  const navigate = useNavigate();
  const { data: designs, isLoading } = useDesigns();
  const createDesign = useCreateDesign();
  const generateSafe = useGenerateSafeRecommendation();
  const { data: templates } = useDesignTemplates();
  const createFromTemplate = useCreateDesignFromTemplate();
  const [name, setName] = useState("");
  const [safeName, setSafeName] = useState("SAFE Recommendation");
  const [pendingTemplateCode, setPendingTemplateCode] = useState<string | null>(null);
  const [templateDesignName, setTemplateDesignName] = useState("");

  function handleCreate() {
    if (!name.trim()) return;
    createDesign.mutate({ name, mode: "manual" });
    setName("");
  }

  function handleStartFromTemplate(templateCode: string) {
    if (!templateDesignName.trim()) return;
    createFromTemplate.mutate(
      { template_code: templateCode, name: templateDesignName.trim() },
      {
        onSuccess: (design) => {
          setPendingTemplateCode(null);
          setTemplateDesignName("");
          navigate(`/design-configuration/designs/${design.id}`);
        },
      },
    );
  }

  function handleGenerateSafe() {
    if (!safeName.trim()) return;
    generateSafe.mutate(safeName.trim(), {
      onSuccess: (result) =>
        navigate(`/design-configuration/designs/${result.design_id}`, {
          state: {
            scaleGaps: result.scale_gaps,
            locationGaps: result.location_gaps,
            coverageWarnings: result.coverage_warnings,
          },
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

      {templates && templates.length > 0 && (
        <div className="panel" style={{ marginBottom: 20 }}>
          <strong>Start from a Template</strong>
          <p className="muted" style={{ margin: "2px 0 12px" }}>
            Begin with a pre-built blueprint instead of an empty canvas - every component and connection is
            already there for you to adjust.
          </p>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {templates.map((t) => (
              <div
                key={t.code}
                className="panel"
                style={{ width: 220, flexShrink: 0, border: "1px solid var(--color-border)" }}
              >
                <strong style={{ fontSize: 13 }}>{t.name}</strong>
                <p className="muted" style={{ fontSize: 12, margin: "4px 0 8px" }}>
                  {t.description}
                </p>
                <p className="muted" style={{ fontSize: 11, margin: "0 0 8px" }}>
                  {t.component_count} devices · {t.relationship_count} links
                </p>
                {pendingTemplateCode === t.code ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    <input
                      placeholder="Design name"
                      value={templateDesignName}
                      onChange={(e) => setTemplateDesignName(e.target.value)}
                      autoFocus
                    />
                    <div style={{ display: "flex", gap: 6 }}>
                      <button
                        style={{ flex: 1 }}
                        onClick={() => handleStartFromTemplate(t.code)}
                        disabled={!templateDesignName.trim() || createFromTemplate.isPending}
                      >
                        {createFromTemplate.isPending ? "Creating..." : "Create"}
                      </button>
                      <button
                        className="btn-secondary"
                        onClick={() => {
                          setPendingTemplateCode(null);
                          setTemplateDesignName("");
                        }}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    style={{ width: "100%" }}
                    onClick={() => {
                      setPendingTemplateCode(t.code);
                      setTemplateDesignName(t.name);
                    }}
                  >
                    Use this template
                  </button>
                )}
              </div>
            ))}
          </div>
          {createFromTemplate.isError && (
            <p className="form-error">{getErrorMessage(createFromTemplate.error, "Could not create design from template")}</p>
          )}
        </div>
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
