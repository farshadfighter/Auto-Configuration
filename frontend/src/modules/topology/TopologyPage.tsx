import { Background, Controls, ReactFlow, type Edge, type Node, useEdgesState, useNodesState } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useEffect, useState } from "react";
import { useTopology, useUpdateTopologyLayout, useValidateTopology, type TopologyFinding } from "../../hooks/useTopology";
import { useAssets, SAFE_PIN_LABELS, type SafePin } from "../../hooks/useAssets";
import { useSafePathAnalysis, type PathFinding } from "../../hooks/useArchitectureRecommendation";
import { SAFE_PIN_COLORS, DEFAULT_NODE_COLOR } from "../../constants/safePinColors";
import { getErrorMessage } from "../../services/api";

function layoutGrid(nodeIds: string[]): Record<string, { x: number; y: number }> {
  const columns = Math.ceil(Math.sqrt(nodeIds.length || 1));
  const positions: Record<string, { x: number; y: number }> = {};
  nodeIds.forEach((id, index) => {
    positions[id] = { x: (index % columns) * 180, y: Math.floor(index / columns) * 120 };
  });
  return positions;
}

// For a real path (a sequence of asset ids from the topology-driven BFS), the edges that need
// highlighting are the links between each consecutive pair of nodes referencing those assets.
function unprotectedEdgeIds(findings: PathFinding[], nodeIdByAssetId: Map<string, string>, links: { id: string; source_node_id: string; destination_node_id: string }[]): Map<string, PathFinding> {
  const result = new Map<string, PathFinding>();
  for (const finding of findings) {
    if (finding.protected) continue;
    const nodeIds = finding.path_asset_ids.map((assetId) => nodeIdByAssetId.get(assetId)).filter((id): id is string => Boolean(id));
    for (let i = 0; i < nodeIds.length - 1; i++) {
      const a = nodeIds[i];
      const b = nodeIds[i + 1];
      const link = links.find(
        (l) => (l.source_node_id === a && l.destination_node_id === b) || (l.source_node_id === b && l.destination_node_id === a),
      );
      if (link) result.set(link.id, finding);
    }
  }
  return result;
}

export function TopologyPage() {
  const { data: graph, isLoading } = useTopology();
  const validate = useValidateTopology();
  const updateLayout = useUpdateTopologyLayout();
  const [findings, setFindings] = useState<TopologyFinding[] | null>(null);
  const [safeView, setSafeView] = useState(false);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const { data: assetsResponse } = useAssets({ page_size: 500 });
  const { data: pathFindings, isLoading: pathAnalysisLoading, isError: pathAnalysisError } = useSafePathAnalysis(safeView);

  useEffect(() => {
    if (!graph) return;

    const safePinByAssetId = new Map<string, SafePin>();
    const nodeIdByAssetId = new Map<string, string>();
    if (safeView) {
      for (const asset of assetsResponse?.data ?? []) {
        if (asset.safe_pin) safePinByAssetId.set(asset.id, asset.safe_pin);
      }
      for (const node of graph.nodes) {
        if (node.reference_id) nodeIdByAssetId.set(node.reference_id, node.id);
      }
    }
    const badEdges = safeView && pathFindings ? unprotectedEdgeIds(pathFindings, nodeIdByAssetId, graph.links) : new Map<string, PathFinding>();

    const positions = layoutGrid(graph.nodes.map((n) => n.id));
    setNodes(
      graph.nodes.map((n) => {
        const pin = n.reference_id ? safePinByAssetId.get(n.reference_id) : undefined;
        const color = safeView ? (pin ? SAFE_PIN_COLORS[pin] : DEFAULT_NODE_COLOR) : undefined;
        return {
          id: n.id,
          position: positions[n.id],
          data: { label: safeView && pin ? `${n.label} (${n.node_type})\n${SAFE_PIN_LABELS[pin]}` : `${n.label} (${n.node_type})` },
          style: {
            fontSize: 12,
            whiteSpace: "pre-line",
            ...(color ? { border: `2px solid ${color}`, borderRadius: 6 } : {}),
          },
        };
      }),
    );
    setEdges(
      graph.links.map((l) => {
        const badge = badEdges.get(l.id);
        return {
          id: l.id,
          source: l.source_node_id,
          target: l.destination_node_id,
          label: badge ? `⚠ ${l.link_type ?? ""}`.trim() : (l.link_type ?? undefined),
          style: badge ? { stroke: "#dc2626", strokeWidth: 2, strokeDasharray: "6,4" } : undefined,
          labelStyle: badge ? { fill: "#dc2626", fontWeight: 600 } : undefined,
        };
      }),
    );
  }, [graph, safeView, assetsResponse, pathFindings, setNodes, setEdges]);

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

  const unprotected = safeView ? (pathFindings ?? []).filter((f) => !f.protected) : [];
  const usedPins = safeView
    ? Array.from(new Set((assetsResponse?.data ?? []).map((a) => a.safe_pin).filter((p): p is SafePin => Boolean(p))))
    : [];

  return (
    <div>
      <div className="page-header">
        <h1>Topology</h1>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            className={safeView ? "btn-primary" : undefined}
            onClick={() => setSafeView((v) => !v)}
          >
            {safeView ? "Hide SAFE View" : "Show SAFE View"}
          </button>
          <button onClick={handleValidate} disabled={validate.isPending}>
            {validate.isPending ? "Validating..." : "Validate Topology"}
          </button>
        </div>
      </div>

      {validate.isError && <p className="form-error">{getErrorMessage(validate.error, "Validation failed")}</p>}
      {updateLayout.isError && <p className="form-error">{getErrorMessage(updateLayout.error, "Could not save node position")}</p>}
      {safeView && pathAnalysisError && <p className="form-error">Could not analyze real network paths.</p>}

      {isLoading && <p>Loading...</p>}

      {safeView && (
        <div style={{ marginBottom: 16, padding: 12, border: "1px solid var(--border)", borderRadius: 8 }}>
          <strong>SAFE View</strong>
          <p style={{ margin: "4px 0", fontSize: 13, color: "var(--text-muted)" }}>
            Node borders show each device's classified SAFE zone. Red dashed links mark a real path (traced over actual
            topology links) between two zones where SAFE expects a security capability but none sits on that path.
          </p>
          {usedPins.length > 0 && (
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 8 }}>
              {usedPins.map((pin) => (
                <span key={pin} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12 }}>
                  <span
                    style={{ width: 10, height: 10, borderRadius: "50%", background: SAFE_PIN_COLORS[pin], display: "inline-block" }}
                  />
                  {SAFE_PIN_LABELS[pin]}
                </span>
              ))}
            </div>
          )}
          {pathAnalysisLoading && <p>Analyzing real network paths...</p>}
          {!pathAnalysisLoading && unprotected.length === 0 && pathFindings && (
            <p className="empty-state">Every real path SAFE expects protection on is covered.</p>
          )}
          {unprotected.length > 0 && (
            <ul>
              {unprotected.map((f, i) => (
                <li key={i}>
                  <span className={`badge badge-${f.severity}`}>{f.required_capability} missing</span>{" "}
                  {SAFE_PIN_LABELS[f.pin_a as SafePin] ?? f.pin_a} &rarr; {SAFE_PIN_LABELS[f.pin_b as SafePin] ?? f.pin_b}: real path{" "}
                  <em>{f.path_asset_names.join(" → ")}</em> has no {f.required_capability} on it.
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

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

      <div className="canvas-container" style={{ height: 520 }}>
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
