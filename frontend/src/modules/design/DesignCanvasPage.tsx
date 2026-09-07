import { Background, Controls, ReactFlow, type Edge, type Node, useEdgesState, useNodesState } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  useAddComponent,
  useApproveDesign,
  useCreateNewVersion,
  useDesign,
  useVersionGraph,
} from "../../hooks/useDesigns";
import { getErrorMessage } from "../../services/api";

const STATUS_BADGE: Record<string, string> = {
  draft: "badge-medium",
  under_review: "badge-medium",
  approved: "badge-low",
  superseded: "badge-medium",
  archived: "badge-medium",
};

// Colors for the SAFE-zone-classified components an architecture recommendation generates
// (see useArchitectureRecommendation / backend app/domains/architecture_recommendation).
// Manually-added components have no safe_pin and fall back to the default color below.
const SAFE_PIN_COLORS: Record<string, string> = {
  cloud: "#0ea5e9",
  internet_edge: "#dc2626",
  wan: "#d97706",
  branch: "#65a30d",
  campus_core: "#4f46e5",
  campus_distribution: "#7c3aed",
  campus_access: "#a855f7",
  data_center: "#0891b2",
  management: "#64748b",
};
const DEFAULT_NODE_COLOR = "#334155";

export function DesignCanvasPage() {
  const { designId } = useParams<{ designId: string }>();
  const { data: design, isError: designIsError } = useDesign(designId);
  const versionId = design?.latest_version.id;
  const { data: graph } = useVersionGraph(versionId);
  const addComponent = useAddComponent(versionId, designId ?? "");
  const approveDesign = useApproveDesign(designId ?? "");
  const createNewVersion = useCreateNewVersion(designId ?? "");
  const [componentName, setComponentName] = useState("");
  const [componentType, setComponentType] = useState("router");

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => {
    if (!graph) return;
    setNodes(
      graph.components.map((c, i) => {
        const safePin = typeof c.properties?.safe_pin === "string" ? c.properties.safe_pin : null;
        const isRecommended = c.properties?.recommended === true;
        const color = (safePin && SAFE_PIN_COLORS[safePin]) || DEFAULT_NODE_COLOR;
        return {
          id: c.id,
          position: c.position ?? { x: (i % 5) * 160, y: Math.floor(i / 5) * 120 },
          data: { label: `${c.name} (${c.component_type})` },
          style: {
            fontSize: 12,
            border: `2px ${isRecommended ? "dashed" : "solid"} ${color}`,
            background: isRecommended ? "#ffffff" : `${color}14`,
            opacity: isRecommended ? 0.85 : 1,
          },
        };
      }),
    );
    setEdges(
      graph.relationships.map((r) => ({
        id: r.id,
        source: r.source_component_id,
        target: r.target_component_id,
        label: r.relationship_type,
      })),
    );
  }, [graph, setNodes, setEdges]);

  if (designIsError) return <p className="form-error">Design not found.</p>;
  if (!design) return <p>Loading...</p>;

  const isDraft = design.latest_version.status === "draft";

  return (
    <div>
      <div className="page-header">
        <h1>
          {design.name} <span className={`badge ${STATUS_BADGE[design.latest_version.status]}`}>{design.latest_version.version_label} · {design.latest_version.status}</span>
        </h1>
        <div style={{ display: "flex", gap: 8 }}>
          {isDraft && (
            <button onClick={() => approveDesign.mutate(undefined)} disabled={approveDesign.isPending}>
              Approve
            </button>
          )}
          {!isDraft && (
            <button onClick={() => createNewVersion.mutate()} disabled={createNewVersion.isPending}>
              Create New Version
            </button>
          )}
        </div>
      </div>

      {approveDesign.isError && <p className="form-error">{getErrorMessage(approveDesign.error, "Could not approve design")}</p>}
      {createNewVersion.isError && (
        <p className="form-error">{getErrorMessage(createNewVersion.error, "Could not create new version")}</p>
      )}

      {isDraft && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <select value={componentType} onChange={(e) => setComponentType(e.target.value)}>
              <option value="router">Router</option>
              <option value="switch">Switch</option>
              <option value="firewall">Firewall</option>
              <option value="server">Server</option>
              <option value="domain_controller">Domain Controller</option>
              <option value="zone">Zone</option>
            </select>
            <input placeholder="Component name" value={componentName} onChange={(e) => setComponentName(e.target.value)} />
            <button
              onClick={() => {
                if (!componentName.trim()) return;
                addComponent.mutate({ component_type: componentType, name: componentName });
                setComponentName("");
              }}
              disabled={!componentName.trim() || addComponent.isPending}
            >
              Add Component
            </button>
          </div>
          {addComponent.isError && <p className="form-error">{getErrorMessage(addComponent.error, "Could not add component")}</p>}
        </div>
      )}

      {graph?.components.some((c) => c.properties?.safe_pin) && (
        <div className="muted" style={{ marginBottom: 8, display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center" }}>
          <span>
            <strong style={{ border: "2px solid #334155", padding: "1px 6px", borderRadius: 4, marginRight: 4 }}>solid</strong>
            existing asset
          </span>
          <span>
            <strong style={{ border: "2px dashed #334155", padding: "1px 6px", borderRadius: 4, marginRight: 4 }}>dashed</strong>
            recommended, not yet in inventory
          </span>
          <span>color = SAFE zone</span>
        </div>
      )}

      <div className="canvas-container" style={{ height: 520 }}>
        <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} fitView>
          <Background />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  );
}
