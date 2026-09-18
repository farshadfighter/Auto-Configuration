import { Handle, Position, type NodeProps } from "@xyflow/react";
import { DeviceIcon } from "../../components/DeviceIcon";
import { defaultPortsForType } from "../../constants/devicePorts";

export interface DeviceNodeData extends Record<string, unknown> {
  label: string;
  componentType: string;
  color: string;
  dashed: boolean;
  subtitle?: string;
}

const PORT_HANDLE_STYLE = { width: 7, height: 7, background: "var(--color-border-strong)", border: "1.5px solid var(--color-surface)" };
const GENERIC_HANDLE_STYLE = { width: 8, height: 8, background: "var(--color-border-strong)" };

// Real, per-port connection handles (EVE-NG style: drag from a specific numbered port on one
// device straight to a specific port on another) instead of a fixed 4 generic dots regardless
// of how many actual ports the device type has. Device types with no known port catalog
// (cross-cutting capabilities like SIEM/AAA) keep the old 4 generic handles so they stay
// connectable.
export function DeviceNode({ data, selected }: NodeProps) {
  const { label, componentType, color, dashed, subtitle } = data as unknown as DeviceNodeData;
  const ports = defaultPortsForType(componentType);
  const minWidth = ports.length > 0 ? Math.max(110, ports.length * 9) : 110;

  return (
    <div
      className="device-node"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 4,
        padding: "10px 14px",
        borderRadius: 10,
        border: `2px ${dashed ? "dashed" : "solid"} ${color}`,
        background: dashed ? "var(--color-surface)" : `${color}14`,
        boxShadow: selected ? `0 0 0 3px ${color}33` : "var(--shadow-sm)",
        minWidth,
        cursor: "pointer",
      }}
    >
      {ports.length > 0 ? (
        ports.map((port, i) => (
          <Handle
            key={port}
            id={port}
            type="source"
            position={Position.Bottom}
            style={{ ...PORT_HANDLE_STYLE, left: `${((i + 0.5) / ports.length) * 100}%` }}
            title={port}
          />
        ))
      ) : (
        <>
          <Handle type="target" position={Position.Left} style={GENERIC_HANDLE_STYLE} />
          <Handle type="target" position={Position.Top} style={GENERIC_HANDLE_STYLE} />
          <Handle type="source" position={Position.Right} style={GENERIC_HANDLE_STYLE} />
          <Handle type="source" position={Position.Bottom} style={GENERIC_HANDLE_STYLE} />
        </>
      )}
      <DeviceIcon type={componentType} color={color} size={22} />
      <div style={{ fontSize: 12, fontWeight: 600, textAlign: "center", lineHeight: 1.25, color: "var(--color-text)" }}>{label}</div>
      {subtitle && <div style={{ fontSize: 10, color: "var(--color-muted)" }}>{subtitle}</div>}
      {ports.length > 0 && <div style={{ fontSize: 9, color: "var(--color-muted)" }}>{ports.length} ports</div>}
    </div>
  );
}

export const DEVICE_NODE_TYPES = { device: DeviceNode };
