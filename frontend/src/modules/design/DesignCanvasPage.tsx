import {
  Background,
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
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  useAddComponent,
  useAddRelationship,
  useApproveDesign,
  useCreateNewVersion,
  useDesign,
  useMapComponentToAsset,
  useVersionGraph,
  type DesignComponent,
} from "../../hooks/useDesigns";
import { useAssetTypes, useCreateAsset, useCreateAssetRelationship, SAFE_PIN_LABELS, type SafePin } from "../../hooks/useAssets";
import { getErrorMessage } from "../../services/api";
import { SAFE_PIN_COLORS, DEFAULT_NODE_COLOR } from "../../constants/safePinColors";
import { PALETTE_DEVICE_TYPES, DeviceIcon } from "../../components/DeviceIcon";
import { DEVICE_NODE_TYPES, type DeviceNodeData } from "./DeviceNode";

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

export function DesignCanvasPage() {
  const { designId } = useParams<{ designId: string }>();
  const navigate = useNavigate();
  const { data: design, isError: designIsError } = useDesign(designId);
  const versionId = design?.latest_version.id;
  const { data: graph } = useVersionGraph(versionId);
  const addComponent = useAddComponent(versionId, designId ?? "");
  const addRelationship = useAddRelationship(versionId);
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
  const reactFlowInstance = useRef<ReactFlowInstance | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);

  const componentsById = useMemo(() => {
    const map = new Map<string, DesignComponent>();
    for (const c of graph?.components ?? []) map.set(c.id, c);
    return map;
  }, [graph]);

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
        label: r.relationship_type,
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

  async function handleConnect(connection: Connection) {
    if (!connection.source || !connection.target) return;
    await addRelationship.mutateAsync({
      source_component_id: connection.source,
      target_component_id: connection.target,
      relationship_type: RELATIONSHIP_TYPE,
    });
    const sourceAssetId = componentsById.get(connection.source)?.asset_id;
    const targetAssetId = componentsById.get(connection.target)?.asset_id;
    if (sourceAssetId && targetAssetId) {
      await createAssetRelationship.mutateAsync({
        source_asset_id: sourceAssetId,
        target_asset_id: targetAssetId,
        relationship_type: RELATIONSHIP_TYPE,
      });
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
          <span>color = SAFE zone · click a device for details · drag a link between two devices to connect them</span>
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
            onPaneClick={() => setSelectedComponentId(null)}
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
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
    </div>
  );
}
