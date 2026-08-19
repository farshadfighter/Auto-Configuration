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

export function DesignCanvasPage() {
  const { designId } = useParams<{ designId: string }>();
  const { data: design } = useDesign(designId);
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
      graph.components.map((c, i) => ({
        id: c.id,
        position: c.position ?? { x: (i % 5) * 160, y: Math.floor(i / 5) * 120 },
        data: { label: `${c.name} (${c.component_type})` },
        style: { fontSize: 12 },
      })),
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
              disabled={!componentName.trim()}
            >
              Add Component
            </button>
          </div>
          {addComponent.isError && <p className="form-error">{getErrorMessage(addComponent.error, "Could not add component")}</p>}
        </div>
      )}

      <div style={{ height: 520, border: "1px solid var(--color-border)", borderRadius: 8, background: "#fff" }}>
        <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} fitView>
          <Background />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  );
}
