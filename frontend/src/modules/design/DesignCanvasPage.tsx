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
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  useAddComponent,
  useAddRelationship,
  useApproveDesign,
  useCreateNewVersion,
  useDesign,
  useMapComponentToAsset,
  useUpdateRelationship,
  useVersionGraph,
  type DesignComponent,
  type DesignRelationship,
} from "../../hooks/useDesigns";
import { useAssetTypes, useCreateAsset, useCreateAssetRelationship, SAFE_PIN_LABELS, type SafePin } from "../../hooks/useAssets";
import type { CoverageWarnings, LocationGapFinding, ScaleGapFinding } from "../../hooks/useArchitectureRecommendation";
import { getErrorMessage } from "../../services/api";
import { SAFE_PIN_COLORS, DEFAULT_NODE_COLOR } from "../../constants/safePinColors";
import { PALETTE_DEVICE_TYPES, DeviceIcon } from "../../components/DeviceIcon";
import { LinkEditPanel, type LinkEditState } from "../../components/LinkEditPanel";
import { downloadDiagramPdf, downloadDiagramPng } from "../../utils/exportDiagram";
import { useCompareDesignVersions, useDesignVersions } from "../../hooks/useDesignDiff";
import { DEVICE_NODE_TYPES, type DeviceNodeData } from "./DeviceNode";

function VersionComparePanel({ designId, onClose }: { designId: string; onClose: () => void }) {
  const { data: versions } = useDesignVersions(designId);
  const compare = useCompareDesignVersions(designId);
  const [fromVersionId, setFromVersionId] = useState("");
  const [toVersionId, setToVersionId] = useState("");

  function handleCompare() {
    if (!fromVersionId || !toVersionId) return;
    compare.mutate({ from_version_id: fromVersionId, to_version_id: toVersionId });
  }

  const diff = compare.data;
  const hasChanges =
    diff &&
    (diff.added_components.length > 0 ||
      diff.removed_components.length > 0 ||
      diff.changed_components.length > 0 ||
      diff.added_relationships.length > 0 ||
      diff.removed_relationships.length > 0 ||
      diff.changed_relationships.length > 0);

  return (
    <div className="panel" style={{ marginBottom: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
        <strong>Compare Versions</strong>
        <button className="btn-secondary" onClick={onClose} style={{ padding: "2px 8px" }}>
          &times;
        </button>
      </div>
      <div style={{ display: "flex", gap: 12, marginTop: 8, alignItems: "flex-end", flexWrap: "wrap" }}>
        <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, color: "var(--color-text-secondary)" }}>
          From
          <select value={fromVersionId} onChange={(e) => setFromVersionId(e.target.value)} autoFocus>
            <option value="">Select version</option>
            {versions?.map((v) => (
              <option key={v.id} value={v.id}>
                {v.version_label} ({v.status})
              </option>
            ))}
          </select>
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, color: "var(--color-text-secondary)" }}>
          To
          <select value={toVersionId} onChange={(e) => setToVersionId(e.target.value)}>
            <option value="">Select version</option>
            {versions?.map((v) => (
              <option key={v.id} value={v.id}>
                {v.version_label} ({v.status})
              </option>
            ))}
          </select>
        </label>
        <button onClick={handleCompare} disabled={!fromVersionId || !toVersionId || compare.isPending}>
          {compare.isPending ? "Comparing..." : "Compare"}
        </button>
      </div>
      {compare.isError && <p className="form-error">{getErrorMessage(compare.error, "Could not compare versions")}</p>}
      {diff && !hasChanges && (
        <p className="empty-state" style={{ marginTop: 8 }}>
          No differences between these versions.
        </p>
      )}
      {diff && hasChanges && (
        <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 10 }}>
          {diff.added_components.length > 0 && (
            <div>
              <span style={{ fontSize: 12, fontWeight: 600, color: "#16a34a" }}>+ Added devices</span>
              <ul>
                {diff.added_components.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            </div>
          )}
          {diff.removed_components.length > 0 && (
            <div>
              <span style={{ fontSize: 12, fontWeight: 600, color: "#dc2626" }}>- Removed devices</span>
              <ul>
                {diff.removed_components.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            </div>
          )}
          {diff.changed_components.length > 0 && (
            <div>
              <span style={{ fontSize: 12, fontWeight: 600, color: "var(--color-text-secondary)" }}>Changed devices</span>
              <ul>
                {diff.changed_components.map((c) => (
                  <li key={c.name}>
                    {c.name}:{" "}
                    {Object.entries(c.changes)
                      .map(([field, [oldV, newV]]) => `${field} ${String(oldV ?? "—")} → ${String(newV ?? "—")}`)
                      .join(", ")}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {diff.added_relationships.length > 0 && (
            <div>
              <span style={{ fontSize: 12, fontWeight: 600, color: "#16a34a" }}>+ Added connections</span>
              <ul>
                {diff.added_relationships.map((k) => (
                  <li key={k}>{k}</li>
                ))}
              </ul>
            </div>
          )}
          {diff.removed_relationships.length > 0 && (
            <div>
              <span style={{ fontSize: 12, fontWeight: 600, color: "#dc2626" }}>- Removed connections</span>
              <ul>
                {diff.removed_relationships.map((k) => (
                  <li key={k}>{k}</li>
                ))}
              </ul>
            </div>
          )}
          {diff.changed_relationships.length > 0 && (
            <div>
              <span style={{ fontSize: 12, fontWeight: 600, color: "var(--color-text-secondary)" }}>Changed connections</span>
              <ul>
                {diff.changed_relationships.map((r) => (
                  <li key={r.key}>
                    {r.key}:{" "}
                    {Object.entries(r.changes)
                      .map(([field, [oldV, newV]]) => `${field} ${String(oldV ?? "—")} → ${String(newV ?? "—")}`)
                      .join(", ")}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function formatLinkLabel(r: DesignRelationship): string {
  const parts: string[] = [];
  if (r.source_interface || r.target_interface) parts.push(`${r.source_interface ?? "?"} ↔ ${r.target_interface ?? "?"}`);
  if (r.link_type) parts.push(r.link_type.replace(/_/g, " "));
  if (r.speed_mbps) parts.push(`${r.speed_mbps}Mbps`);
  if (r.vlan) parts.push(`VLAN ${r.vlan}`);
  return parts.length > 0 ? parts.join(" · ") : r.relationship_type;
}

function GapReportPanel({
  scaleGaps,
  locationGaps,
  coverageWarnings,
  onDismiss,
}: {
  scaleGaps: ScaleGapFinding[];
  locationGaps: LocationGapFinding[];
  coverageWarnings: CoverageWarnings;
  onDismiss: () => void;
}) {
  const locationGapsByLocation = new Map<string, { name: string; missing: string[] }>();
  for (const g of locationGaps) {
    const entry = locationGapsByLocation.get(g.location_id) ?? { name: g.location_name, missing: [] };
    entry.missing.push(g.missing_component_name);
    locationGapsByLocation.set(g.location_id, entry);
  }

  const unlocatedEntries = Object.entries(coverageWarnings.unlocated_counts).filter(([, count]) => count > 0);
  const hasWarnings = coverageWarnings.unclassified_asset_count > 0 || unlocatedEntries.length > 0;

  return (
    <div className="panel" style={{ marginBottom: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
        <strong>SAFE Scale &amp; Coverage Gap Report</strong>
        <button className="btn-secondary" onClick={onDismiss} style={{ padding: "2px 8px" }}>
          &times;
        </button>
      </div>

      {scaleGaps.length === 0 && locationGaps.length === 0 && (
        <p className="empty-state" style={{ marginTop: 8 }}>
          No capacity or per-site coverage gaps found for the current network size.
        </p>
      )}

      {scaleGaps.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: "var(--color-text-secondary)" }}>Capacity / redundancy</span>
          <ul style={{ marginTop: 4 }}>
            {scaleGaps.map((g, i) => (
              <li key={i}>
                <strong>{g.pin_label}</strong>: needs {g.required_count}&times; {g.component_name} (have {g.existing_count}
                {g.metric_pin === g.pin ? "" : `, based on ${g.metric_asset_count} asset(s) classified in ${g.metric_pin}`})
              </li>
            ))}
          </ul>
        </div>
      )}

      {locationGaps.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: "var(--color-text-secondary)" }}>Per-site coverage</span>
          <ul style={{ marginTop: 4 }}>
            {Array.from(locationGapsByLocation.entries()).map(([locationId, entry]) => (
              <li key={locationId}>
                <strong>{entry.name}</strong>: missing {entry.missing.join(", ")}
              </li>
            ))}
          </ul>
        </div>
      )}

      {hasWarnings && (
        <div style={{ marginTop: 12, paddingTop: 8, borderTop: "1px dashed var(--color-border)" }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: "var(--color-text-secondary)" }}>
            Not included in this analysis
          </span>
          <ul style={{ marginTop: 4 }}>
            {coverageWarnings.unclassified_asset_count > 0 && (
              <li>
                {coverageWarnings.unclassified_asset_count} asset(s) have no SAFE Zone set and were skipped entirely -
                classify them (Assets &rarr; SAFE Zone column) to include them in this analysis.
              </li>
            )}
            {unlocatedEntries.map(([pin, count]) => (
              <li key={pin}>
                {count} {SAFE_PIN_LABELS[pin as SafePin] ?? pin} asset(s) have no Location set and were excluded from
                the per-site coverage check above.
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

const STATUS_BADGE: Record<string, string> = {
  draft: "badge-medium",
  under_review: "badge-medium",
  approved: "badge-low",
  superseded: "badge-medium",
  archived: "badge-medium",
};

const RELATIONSHIP_TYPE = "connected_to";
const DRAG_DATA_TYPE = "application/ngfabric-device-type";

interface PendingDevice {
  type: string;
  position: { x: number; y: number };
  existingComponentId?: string;
}

interface PendingConnection {
  source: string;
  target: string;
  sourceLabel: string;
  targetLabel: string;
}

export function DesignCanvasPage() {
  const { designId } = useParams<{ designId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const [gapReport, setGapReport] = useState<{
    scaleGaps: ScaleGapFinding[];
    locationGaps: LocationGapFinding[];
    coverageWarnings: CoverageWarnings;
  } | null>(null);

  useEffect(() => {
    const navState = location.state as {
      scaleGaps?: ScaleGapFinding[];
      locationGaps?: LocationGapFinding[];
      coverageWarnings?: CoverageWarnings;
    } | null;
    if (!navState) return;
    setGapReport({
      scaleGaps: navState.scaleGaps ?? [],
      locationGaps: navState.locationGaps ?? [],
      coverageWarnings: navState.coverageWarnings ?? { unclassified_asset_count: 0, unlocated_counts: {} },
    });
    // history.state (and so location.state) survives a reload, unlike component state - clear it
    // from the history entry so the report is scoped to this visit only, not every reload.
    navigate(location.pathname, { replace: true, state: null });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const { data: design, isError: designIsError } = useDesign(designId);
  const versionId = design?.latest_version.id;
  const { data: graph } = useVersionGraph(versionId);
  const addComponent = useAddComponent(versionId, designId ?? "");
  const addRelationship = useAddRelationship(versionId);
  const updateRelationship = useUpdateRelationship(versionId);
  const mapComponentToAsset = useMapComponentToAsset(versionId);
  const createAsset = useCreateAsset();
  const createAssetRelationship = useCreateAssetRelationship();
  const approveDesign = useApproveDesign(designId ?? "");
  const createNewVersion = useCreateNewVersion(designId ?? "");
  const { data: assetTypes } = useAssetTypes();

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedComponentId, setSelectedComponentId] = useState<string | null>(null);
  const [pendingDevice, setPendingDevice] = useState<PendingDevice | null>(null);
  const [deviceName, setDeviceName] = useState("");
  const [devicePin, setDevicePin] = useState<SafePin | "">("");
  const [addDeviceError, setAddDeviceError] = useState<string | null>(null);
  const [pendingConnection, setPendingConnection] = useState<PendingConnection | null>(null);
  const [sourcePort, setSourcePort] = useState("");
  const [targetPort, setTargetPort] = useState("");
  const [connectError, setConnectError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [editingRelationshipId, setEditingRelationshipId] = useState<string | null>(null);
  const [linkEditState, setLinkEditState] = useState<LinkEditState | null>(null);
  const [linkEditError, setLinkEditError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [showVersionCompare, setShowVersionCompare] = useState(false);
  const reactFlowInstance = useRef<ReactFlowInstance | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);

  const componentsById = useMemo(() => {
    const map = new Map<string, DesignComponent>();
    for (const c of graph?.components ?? []) map.set(c.id, c);
    return map;
  }, [graph]);

  const relationshipsById = useMemo(() => {
    const map = new Map<string, DesignRelationship>();
    for (const r of graph?.relationships ?? []) map.set(r.id, r);
    return map;
  }, [graph]);
  const editingRelationship = editingRelationshipId ? relationshipsById.get(editingRelationshipId) : undefined;

  useEffect(() => {
    if (!graph) return;
    setNodes(
      graph.components.map((c, i) => {
        const safePin = typeof c.properties?.safe_pin === "string" ? (c.properties.safe_pin as SafePin) : null;
        const dashed = !c.asset_id;
        const color = (safePin && SAFE_PIN_COLORS[safePin]) || DEFAULT_NODE_COLOR;
        const data: DeviceNodeData = {
          label: c.name,
          componentType: c.component_type,
          color,
          dashed,
          subtitle: safePin ? SAFE_PIN_LABELS[safePin] : undefined,
        };
        return {
          id: c.id,
          type: "device",
          position: c.position ?? { x: (i % 5) * 160, y: Math.floor(i / 5) * 120 },
          data,
        };
      }),
    );
    setEdges(
      graph.relationships.map((r) => ({
        id: r.id,
        source: r.source_component_id,
        target: r.target_component_id,
        label: formatLinkLabel(r),
      })),
    );
  }, [graph, setNodes, setEdges]);

  if (designIsError) return <p className="form-error">Design not found.</p>;
  if (!design) return <p>Loading...</p>;

  const isDraft = design.latest_version.status === "draft";
  const selectedComponent = selectedComponentId ? componentsById.get(selectedComponentId) : undefined;

  function resetDeviceForm() {
    setPendingDevice(null);
    setDeviceName("");
    setDevicePin("");
    setAddDeviceError(null);
  }

  async function handleCreateDevice() {
    if (!pendingDevice || !deviceName.trim() || !assetTypes) return;
    const assetType = assetTypes.find((t) => t.code === pendingDevice.type);
    if (!assetType) {
      setAddDeviceError(`No asset type registered for "${pendingDevice.type}" yet.`);
      return;
    }
    setAddDeviceError(null);
    try {
      const asset = await createAsset.mutateAsync({
        name: deviceName,
        asset_type_id: assetType.id,
        safe_pin: devicePin || undefined,
      });
      const componentId =
        pendingDevice.existingComponentId ??
        (
          await addComponent.mutateAsync({
            component_type: pendingDevice.type,
            name: deviceName,
            properties: devicePin ? { safe_pin: devicePin } : undefined,
            position: pendingDevice.position,
          })
        ).id;
      await mapComponentToAsset.mutateAsync({ component_id: componentId, asset_id: asset.id });
      resetDeviceForm();
    } catch (err) {
      setAddDeviceError(getErrorMessage(err, "Could not add device"));
    }
  }

  function handleAddExistingComponentToInventory(component: DesignComponent) {
    setPendingDevice({
      type: component.component_type,
      position: component.position ?? { x: 0, y: 0 },
      existingComponentId: component.id,
    });
    setDeviceName(component.name);
    const safePin = typeof component.properties?.safe_pin === "string" ? (component.properties.safe_pin as SafePin) : "";
    setDevicePin(safePin);
  }

  function handleConnect(connection: Connection) {
    if (!connection.source || !connection.target) return;
    const sourceComponent = componentsById.get(connection.source);
    const targetComponent = componentsById.get(connection.target);

    // The drag started/ended on a specific named port handle (EVE-NG style: dragging directly
    // from one device's port dot to another's) - commit the connection immediately with those
    // exact ports, no confirmation panel needed.
    if (connection.sourceHandle || connection.targetHandle) {
      void commitConnection(
        connection.source,
        connection.target,
        connection.sourceHandle ?? undefined,
        connection.targetHandle ?? undefined,
      );
      return;
    }

    // Fallback for portless (cross-cutting capability) device types with only the 4 generic
    // handles - ask for optional free-text port names instead.
    setPendingConnection({
      source: connection.source,
      target: connection.target,
      sourceLabel: sourceComponent?.name ?? "source",
      targetLabel: targetComponent?.name ?? "target",
    });
    setSourcePort("");
    setTargetPort("");
    setConnectError(null);
  }

  async function commitConnection(
    sourceComponentId: string,
    targetComponentId: string,
    sourceInterface?: string,
    targetInterface?: string,
  ) {
    await addRelationship.mutateAsync({
      source_component_id: sourceComponentId,
      target_component_id: targetComponentId,
      relationship_type: RELATIONSHIP_TYPE,
      source_interface: sourceInterface || undefined,
      target_interface: targetInterface || undefined,
    });
    const sourceAssetId = componentsById.get(sourceComponentId)?.asset_id;
    const targetAssetId = componentsById.get(targetComponentId)?.asset_id;
    if (sourceAssetId && targetAssetId) {
      await createAssetRelationship.mutateAsync({
        source_asset_id: sourceAssetId,
        target_asset_id: targetAssetId,
        relationship_type: RELATIONSHIP_TYPE,
        relationship_metadata:
          sourceInterface || targetInterface
            ? { source_interface: sourceInterface || undefined, target_interface: targetInterface || undefined }
            : undefined,
      });
    }
  }

  function resetConnectionForm() {
    setPendingConnection(null);
    setSourcePort("");
    setTargetPort("");
    setConnectError(null);
  }

  async function handleConfirmConnection() {
    if (!pendingConnection) return;
    setConnecting(true);
    setConnectError(null);
    try {
      await commitConnection(pendingConnection.source, pendingConnection.target, sourcePort, targetPort);
      resetConnectionForm();
    } catch (err) {
      setConnectError(getErrorMessage(err, "Could not connect devices"));
    } finally {
      setConnecting(false);
    }
  }

  function handleEdgeClick(_: unknown, edge: Edge) {
    const relationship = relationshipsById.get(edge.id);
    if (!relationship) return;
    setEditingRelationshipId(relationship.id);
    setLinkEditState({
      sourcePort: relationship.source_interface ?? "",
      targetPort: relationship.target_interface ?? "",
      linkType: relationship.link_type ?? "",
      speedMbps: relationship.speed_mbps ? String(relationship.speed_mbps) : "",
      vlan: relationship.vlan ? String(relationship.vlan) : "",
      subnet: relationship.subnet ?? "",
    });
    setLinkEditError(null);
  }

  function resetLinkEditForm() {
    setEditingRelationshipId(null);
    setLinkEditState(null);
    setLinkEditError(null);
  }

  async function handleSaveLinkEdit() {
    if (!editingRelationshipId || !linkEditState) return;
    try {
      await updateRelationship.mutateAsync({
        id: editingRelationshipId,
        source_interface: linkEditState.sourcePort || null,
        target_interface: linkEditState.targetPort || null,
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

  async function handleExport(format: "png" | "pdf") {
    if (!wrapperRef.current) return;
    setExporting(true);
    setExportError(null);
    try {
      reactFlowInstance.current?.fitView();
      await new Promise((resolve) => setTimeout(resolve, 100));
      const baseName = design?.name.replace(/[^\w.-]+/g, "_") || "design";
      if (format === "png") await downloadDiagramPng(wrapperRef.current, baseName);
      else await downloadDiagramPdf(wrapperRef.current, baseName);
    } catch (err) {
      setExportError(getErrorMessage(err, "Could not export the diagram"));
    } finally {
      setExporting(false);
    }
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    const type = event.dataTransfer.getData(DRAG_DATA_TYPE);
    if (!type || !reactFlowInstance.current) return;
    const position = reactFlowInstance.current.screenToFlowPosition({ x: event.clientX, y: event.clientY });
    setPendingDevice({ type, position });
    setDeviceName("");
    setDevicePin("");
  }

  return (
    <div>
      <div className="page-header">
        <h1>
          {design.name} <span className={`badge ${STATUS_BADGE[design.latest_version.status]}`}>{design.latest_version.version_label} · {design.latest_version.status}</span>
        </h1>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn-secondary" onClick={() => handleExport("png")} disabled={exporting}>
            {exporting ? "Exporting..." : "Export PNG"}
          </button>
          <button className="btn-secondary" onClick={() => handleExport("pdf")} disabled={exporting}>
            Export PDF
          </button>
          <button className="btn-secondary" onClick={() => setShowVersionCompare((v) => !v)}>
            {showVersionCompare ? "Hide Compare" : "Compare Versions"}
          </button>
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

      {exportError && <p className="form-error">{exportError}</p>}

      {showVersionCompare && <VersionComparePanel designId={design.id} onClose={() => setShowVersionCompare(false)} />}

      {gapReport && (
        <GapReportPanel
          scaleGaps={gapReport.scaleGaps}
          locationGaps={gapReport.locationGaps}
          coverageWarnings={gapReport.coverageWarnings}
          onDismiss={() => setGapReport(null)}
        />
      )}

      {approveDesign.isError && <p className="form-error">{getErrorMessage(approveDesign.error, "Could not approve design")}</p>}
      {createNewVersion.isError && (
        <p className="form-error">{getErrorMessage(createNewVersion.error, "Could not create new version")}</p>
      )}
      {addRelationship.isError && <p className="form-error">{getErrorMessage(addRelationship.error, "Could not connect devices")}</p>}

      {graph?.components.length ? (
        <div className="muted" style={{ marginBottom: 8, display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center" }}>
          <span>
            <strong style={{ border: "2px solid #334155", padding: "1px 6px", borderRadius: 4, marginRight: 4 }}>solid</strong>
            in inventory
          </span>
          <span>
            <strong style={{ border: "2px dashed #334155", padding: "1px 6px", borderRadius: 4, marginRight: 4 }}>dashed</strong>
            not yet in inventory
          </span>
          <span>
            color = SAFE zone · click a device for details · drag a link between two devices to connect them · click a
            connection to edit its bandwidth/VLAN
          </span>
        </div>
      ) : null}

      <div style={{ display: "flex", gap: 12 }}>
        {isDraft && (
          <div className="panel" style={{ width: 150, flexShrink: 0, alignSelf: "flex-start" }}>
            <strong style={{ fontSize: 13 }}>Add Device</strong>
            <p className="muted" style={{ fontSize: 12, marginTop: 4 }}>Drag onto the canvas</p>
            {PALETTE_DEVICE_TYPES.map((d) => (
              <div
                key={d.type}
                draggable
                onDragStart={(e) => e.dataTransfer.setData(DRAG_DATA_TYPE, d.type)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "6px 8px",
                  marginTop: 6,
                  border: "1px solid var(--color-border)",
                  borderRadius: 6,
                  cursor: "grab",
                  fontSize: 13,
                }}
              >
                <DeviceIcon type={d.type} size={16} color="var(--color-text-secondary)" />
                {d.label}
              </div>
            ))}
          </div>
        )}

        <div className="canvas-container" style={{ height: 520, flex: 1 }} ref={wrapperRef}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={DEVICE_NODE_TYPES}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={handleConnect}
            onInit={(instance) => {
              reactFlowInstance.current = instance;
            }}
            onNodeClick={(_, node) => setSelectedComponentId(node.id)}
            onEdgeClick={handleEdgeClick}
            onPaneClick={() => setSelectedComponentId(null)}
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            connectionMode={ConnectionMode.Loose}
            fitView
          >
            <Background />
            <Controls />
          </ReactFlow>
        </div>

        {selectedComponent && (
          <div className="panel" style={{ width: 220, flexShrink: 0, alignSelf: "flex-start" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
              <strong style={{ fontSize: 13 }}>{selectedComponent.name}</strong>
              <button className="btn-secondary" style={{ padding: "2px 8px" }} onClick={() => setSelectedComponentId(null)}>
                &times;
              </button>
            </div>
            <p className="muted" style={{ fontSize: 12, margin: "4px 0" }}>{selectedComponent.component_type}</p>
            {typeof selectedComponent.properties?.safe_pin === "string" && (
              <p className="muted" style={{ fontSize: 12, margin: "4px 0" }}>
                Zone: {SAFE_PIN_LABELS[selectedComponent.properties.safe_pin as SafePin] ?? selectedComponent.properties.safe_pin}
              </p>
            )}
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 10 }}>
              {selectedComponent.asset_id ? (
                <>
                  <Link to={`/assets/${selectedComponent.asset_id}`}>
                    <button style={{ width: "100%" }}>View Asset</button>
                  </Link>
                  <button
                    className="btn-secondary"
                    style={{ width: "100%" }}
                    onClick={() => navigate(`/design-configuration/jobs?target_asset_id=${selectedComponent.asset_id}`)}
                  >
                    Configure
                  </button>
                </>
              ) : (
                isDraft && (
                  <button style={{ width: "100%" }} onClick={() => handleAddExistingComponentToInventory(selectedComponent)}>
                    Add to Inventory
                  </button>
                )
              )}
            </div>
          </div>
        )}
      </div>

      {pendingDevice && (
        <div className="panel" style={{ marginTop: 12, maxWidth: 420 }}>
          <strong style={{ fontSize: 13 }}>
            Add {PALETTE_DEVICE_TYPES.find((d) => d.type === pendingDevice.type)?.label ?? pendingDevice.type} to inventory
          </strong>
          <div style={{ display: "flex", gap: 8, marginTop: 8, alignItems: "center", flexWrap: "wrap" }}>
            <input placeholder="Device name" value={deviceName} onChange={(e) => setDeviceName(e.target.value)} autoFocus />
            <select value={devicePin} onChange={(e) => setDevicePin(e.target.value as SafePin | "")}>
              <option value="">No SAFE zone</option>
              {Object.entries(SAFE_PIN_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <button onClick={handleCreateDevice} disabled={!deviceName.trim() || createAsset.isPending || addComponent.isPending}>
              Add Device
            </button>
            <button className="btn-secondary" onClick={resetDeviceForm}>
              Cancel
            </button>
          </div>
          {addDeviceError && <p className="form-error">{addDeviceError}</p>}
        </div>
      )}

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
            <button onClick={handleConfirmConnection} disabled={connecting}>
              {connecting ? "Connecting..." : "Connect"}
            </button>
            <button className="btn-secondary" onClick={resetConnectionForm}>
              Cancel
            </button>
          </div>
          {connectError && <p className="form-error">{connectError}</p>}
        </div>
      )}

      {editingRelationship && linkEditState && (
        <LinkEditPanel
          sourceLabel={componentsById.get(editingRelationship.source_component_id)?.name ?? "source"}
          targetLabel={componentsById.get(editingRelationship.target_component_id)?.name ?? "target"}
          state={linkEditState}
          onChange={setLinkEditState}
          onSave={handleSaveLinkEdit}
          onCancel={resetLinkEditForm}
          saving={updateRelationship.isPending}
          error={linkEditError}
        />
      )}
    </div>
  );
}
