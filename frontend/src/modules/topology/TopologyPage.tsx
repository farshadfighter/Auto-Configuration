import {
  Background,
  ConnectionMode,
  Controls,
  ReactFlow,
  type Connection,
  type Edge,
  type Node,
  type ReactFlowInstance,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useEffect, useRef, useState } from "react";
import {
  useCreateTopologyLink,
  useTopology,
  useUpdateTopologyLayout,
  useUpdateTopologyLink,
  useValidateTopology,
  type TopologyFinding,
  type TopologyLink,
} from "../../hooks/useTopology";
import { useAssets, useAssetTypes, SAFE_PIN_LABELS, type SafePin } from "../../hooks/useAssets";
import { useSafePathAnalysis, type PathFinding } from "../../hooks/useArchitectureRecommendation";
import { SAFE_PIN_COLORS, DEFAULT_NODE_COLOR } from "../../constants/safePinColors";
import { DEVICE_NODE_TYPES, type DeviceNodeData } from "../design/DeviceNode";
import { LinkEditPanel, type LinkEditState } from "../../components/LinkEditPanel";
import { downloadDiagramPdf, downloadDiagramPng } from "../../utils/exportDiagram";
import { getErrorMessage } from "../../services/api";

function formatLinkLabel(l: TopologyLink): string {
  const parts: string[] = [];
  if (l.source_interface || l.destination_interface) parts.push(`${l.source_interface ?? "?"} ↔ ${l.destination_interface ?? "?"}`);
  if (l.link_type) parts.push(l.link_type.replace(/_/g, " "));
  if (l.speed_mbps) parts.push(`${l.speed_mbps}Mbps`);
  if (l.vlan) parts.push(`VLAN ${l.vlan}`);
  return parts.join(" · ");
}

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

interface PendingLinkConnection {
  source: string;
  target: string;
  sourceLabel: string;
  targetLabel: string;
}

export function TopologyPage() {
  const { data: graph, isLoading } = useTopology();
  const validate = useValidateTopology();
  const updateLayout = useUpdateTopologyLayout();
  const createLink = useCreateTopologyLink();
  const updateLink = useUpdateTopologyLink();
  const [findings, setFindings] = useState<TopologyFinding[] | null>(null);
  const [safeView, setSafeView] = useState(false);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [pendingConnection, setPendingConnection] = useState<PendingLinkConnection | null>(null);
  const [sourcePort, setSourcePort] = useState("");
  const [targetPort, setTargetPort] = useState("");
  const [editingLinkId, setEditingLinkId] = useState<string | null>(null);
  const [linkEditState, setLinkEditState] = useState<LinkEditState | null>(null);
  const [linkEditError, setLinkEditError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const reactFlowInstance = useRef<ReactFlowInstance | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);

  const { data: assetsResponse } = useAssets({ page_size: 500 });
  const { data: assetTypes } = useAssetTypes();
  const { data: pathFindings, isLoading: pathAnalysisLoading, isError: pathAnalysisError } = useSafePathAnalysis(safeView);

  const assetTypeCodeById = new Map((assetTypes ?? []).map((t) => [t.id, t.code]));
  const assetById = new Map((assetsResponse?.data ?? []).map((a) => [a.id, a]));
  const nodeById = new Map((graph?.nodes ?? []).map((n) => [n.id, n]));
  const linkById = new Map((graph?.links ?? []).map((l) => [l.id, l]));
  const editingLink = editingLinkId ? linkById.get(editingLinkId) : undefined;

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
        const asset = n.reference_id ? assetById.get(n.reference_id) : undefined;
        const componentType = (asset ? assetTypeCodeById.get(asset.asset_type_id) : undefined) ?? n.node_type;
        const color = safeView && pin ? SAFE_PIN_COLORS[pin] : DEFAULT_NODE_COLOR;
        const data: DeviceNodeData = {
          label: n.label,
          componentType,
          color,
          dashed: false,
          subtitle: safeView && pin ? SAFE_PIN_LABELS[pin] : undefined,
        };
        return {
          id: n.id,
          type: "device",
          position: positions[n.id],
          data,
        };
      }),
    );
    setEdges(
      graph.links.map((l) => {
        const badge = badEdges.get(l.id);
        const linkLabel = formatLinkLabel(l);
        return {
          id: l.id,
          source: l.source_node_id,
          target: l.destination_node_id,
          label: badge ? `⚠ ${linkLabel}`.trim() : linkLabel || undefined,
          style: badge ? { stroke: "#dc2626", strokeWidth: 2, strokeDasharray: "6,4" } : undefined,
          labelStyle: badge ? { fill: "#dc2626", fontWeight: 600 } : undefined,
        };
      }),
    );
  }, [graph, safeView, assetsResponse, assetTypes, pathFindings, setNodes, setEdges]);

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

  function handleConnect(connection: Connection) {
    if (!connection.source || !connection.target) return;

    // Dragged directly from one device's specific port handle to another's (EVE-NG style) -
    // commit the link immediately with those exact ports, no confirmation panel needed.
    if (connection.sourceHandle || connection.targetHandle) {
      createLink.mutate({
        source_node_id: connection.source,
        destination_node_id: connection.target,
        source_interface: connection.sourceHandle ?? undefined,
        destination_interface: connection.targetHandle ?? undefined,
      });
      return;
    }

    // Fallback for portless (cross-cutting capability) device types with only the 4 generic
    // handles - ask for optional free-text port names instead.
    setPendingConnection({
      source: connection.source,
      target: connection.target,
      sourceLabel: nodeById.get(connection.source)?.label ?? "source",
      targetLabel: nodeById.get(connection.target)?.label ?? "target",
    });
    setSourcePort("");
    setTargetPort("");
  }

  function resetConnectionForm() {
    setPendingConnection(null);
    setSourcePort("");
    setTargetPort("");
  }

  function handleEdgeClick(_: unknown, edge: Edge) {
    const link = linkById.get(edge.id);
    if (!link) return;
    setEditingLinkId(link.id);
    setLinkEditState({
      sourcePort: link.source_interface ?? "",
      targetPort: link.destination_interface ?? "",
      linkType: link.link_type ?? "",
      speedMbps: link.speed_mbps ? String(link.speed_mbps) : "",
      vlan: link.vlan ? String(link.vlan) : "",
      subnet: link.subnet ?? "",
    });
    setLinkEditError(null);
  }

  function resetLinkEditForm() {
    setEditingLinkId(null);
    setLinkEditState(null);
    setLinkEditError(null);
  }

  async function handleSaveLinkEdit() {
    if (!editingLinkId || !linkEditState) return;
    try {
      await updateLink.mutateAsync({
        id: editingLinkId,
        source_interface: linkEditState.sourcePort || null,
        destination_interface: linkEditState.targetPort || null,
        link_type: linkEditState.linkType || null,
        speed_mbps: linkEditState.speedMbps ? Number(linkEditState.speedMbps) : null,
        vlan: linkEditState.vlan ? Number(linkEditState.vlan) : null,
        subnet: linkEditState.subnet || null,
      });
      resetLinkEditForm();
    } catch (err) {
      setLinkEditError(getErrorMessage(err, "Could not update link"));
    }
  }

  function handleConfirmConnection() {
    if (!pendingConnection) return;
    createLink.mutate(
      {
        source_node_id: pendingConnection.source,
        destination_node_id: pendingConnection.target,
        source_interface: sourcePort || undefined,
        destination_interface: targetPort || undefined,
      },
      { onSuccess: resetConnectionForm },
    );
  }

  async function handleExport(format: "png" | "pdf") {
    if (!wrapperRef.current) return;
    setExporting(true);
    setExportError(null);
    try {
      reactFlowInstance.current?.fitView();
      await new Promise((resolve) => setTimeout(resolve, 100));
      if (format === "png") await downloadDiagramPng(wrapperRef.current, "topology");
      else await downloadDiagramPdf(wrapperRef.current, "topology");
    } catch (err) {
      setExportError(getErrorMessage(err, "Could not export the diagram"));
    } finally {
      setExporting(false);
    }
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
          <button className="btn-secondary" onClick={() => handleExport("png")} disabled={exporting}>
            {exporting ? "Exporting..." : "Export PNG"}
          </button>
          <button className="btn-secondary" onClick={() => handleExport("pdf")} disabled={exporting}>
            Export PDF
          </button>
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

      {exportError && <p className="form-error">{exportError}</p>}
      {validate.isError && <p className="form-error">{getErrorMessage(validate.error, "Validation failed")}</p>}
      {updateLayout.isError && <p className="form-error">{getErrorMessage(updateLayout.error, "Could not save node position")}</p>}
      {createLink.isError && <p className="form-error">{getErrorMessage(createLink.error, "Could not create connection")}</p>}
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

      <div className="canvas-container" style={{ height: 520 }} ref={wrapperRef}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={DEVICE_NODE_TYPES}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeDragStop={handleNodeDragStop}
          onConnect={handleConnect}
          onEdgeClick={handleEdgeClick}
          onInit={(instance) => {
            reactFlowInstance.current = instance;
          }}
          connectionMode={ConnectionMode.Loose}
          fitView
        >
          <Background />
          <Controls />
        </ReactFlow>
      </div>

      {pendingConnection && (
        <div className="panel" style={{ marginTop: 12, maxWidth: 480 }}>
          <strong style={{ fontSize: 13 }}>
            Connect {pendingConnection.sourceLabel} &rarr; {pendingConnection.targetLabel}
          </strong>
          <div style={{ display: "flex", gap: 12, marginTop: 8, alignItems: "flex-end", flexWrap: "wrap" }}>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, color: "var(--color-text-secondary)" }}>
              {pendingConnection.sourceLabel} port
              <input placeholder="Port (optional)" value={sourcePort} onChange={(e) => setSourcePort(e.target.value)} autoFocus />
            </label>
            <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, color: "var(--color-text-secondary)" }}>
              {pendingConnection.targetLabel} port
              <input placeholder="Port (optional)" value={targetPort} onChange={(e) => setTargetPort(e.target.value)} />
            </label>
            <button onClick={handleConfirmConnection} disabled={createLink.isPending}>
              {createLink.isPending ? "Connecting..." : "Connect"}
            </button>
            <button className="btn-secondary" onClick={resetConnectionForm}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {editingLink && linkEditState && (
        <LinkEditPanel
          sourceLabel={nodeById.get(editingLink.source_node_id)?.label ?? "source"}
          targetLabel={nodeById.get(editingLink.destination_node_id)?.label ?? "target"}
          state={linkEditState}
          onChange={setLinkEditState}
          onSave={handleSaveLinkEdit}
          onCancel={resetLinkEditForm}
          saving={updateLink.isPending}
          error={linkEditError}
        />
      )}
    </div>
  );
}
