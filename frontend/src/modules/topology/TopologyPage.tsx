import { Background, Controls, ReactFlow, type Edge, type Node, useEdgesState, useNodesState } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useEffect, useState } from "react";
import { useTopology, useUpdateTopologyLayout, useValidateTopology, type TopologyFinding } from "../../hooks/useTopology";
import { getErrorMessage } from "../../services/api";

function layoutGrid(nodeIds: string[]): Record<string, { x: number; y: number }> {
  const columns = Math.ceil(Math.sqrt(nodeIds.length || 1));
  const positions: Record<string, { x: number; y: number }> = {};
  nodeIds.forEach((id, index) => {
    positions[id] = { x: (index % columns) * 180, y: Math.floor(index / columns) * 120 };
  });
  return positions;
}

export function TopologyPage() {
  const { data: graph, isLoading } = useTopology();
  const validate = useValidateTopology();
  const updateLayout = useUpdateTopologyLayout();
  const [findings, setFindings] = useState<TopologyFinding[] | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  useEffect(() => {
    if (!graph) return;
    const positions = layoutGrid(graph.nodes.map((n) => n.id));
    setNodes(
      graph.nodes.map((n) => ({
        id: n.id,
        position: positions[n.id],
        data: { label: `${n.label} (${n.node_type})` },
        style: { fontSize: 12 },
      })),
    );
    setEdges(
      graph.links.map((l) => ({
        id: l.id,
        source: l.source_node_id,
        target: l.destination_node_id,
        label: l.link_type ?? undefined,
      })),
    );
  }, [graph, setNodes, setEdges]);

  async function handleValidate() {
    try {
      const result = await validate.mutateAsync();
      setFindings(result);
    } catch {
      // surfaced below via validate.isError
    }
  }

  function handleNodeDragStop(_: unknown, node: Node) {
    updateLayout.mutate([{ node_id: node.id, x: node.position.x, y: node.position.y }]);
  }

  return (
    <div>
      <div className="page-header">
        <h1>Topology</h1>
        <button onClick={handleValidate} disabled={validate.isPending}>
          {validate.isPending ? "Validating..." : "Validate Topology"}
        </button>
      </div>

      {validate.isError && <p className="form-error">{getErrorMessage(validate.error, "Validation failed")}</p>}
      {updateLayout.isError && <p className="form-error">{getErrorMessage(updateLayout.error, "Could not save node position")}</p>}

      {isLoading && <p>Loading...</p>}

      {findings && (
        <div style={{ marginBottom: 16 }}>
          {findings.length === 0 ? (
            <p className="empty-state">No structural findings.</p>
          ) : (
            <ul>
              {findings.map((f, i) => (
                <li key={i}>
                  <span className={`badge badge-${f.severity}`}>{f.code}</span> {f.message}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div style={{ height: 520, border: "1px solid var(--color-border)", borderRadius: 8, background: "#fff" }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeDragStop={handleNodeDragStop}
          fitView
        >
          <Background />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  );
}
