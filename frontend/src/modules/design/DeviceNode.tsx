import { Handle, Position, type NodeProps } from "@xyflow/react";
import { DeviceIcon } from "../../components/DeviceIcon";

export interface DeviceNodeData extends Record<string, unknown> {
  label: string;
  componentType: string;
  color: string;
  dashed: boolean;
  subtitle?: string;
}

const HANDLE_STYLE = { width: 8, height: 8, background: "var(--color-border-strong)" };

export function DeviceNode({ data, selected }: NodeProps) {
  const { label, componentType, color, dashed, subtitle } = data as unknown as DeviceNodeData;

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
        minWidth: 110,
        cursor: "pointer",
      }}
    >
      <Handle type="target" position={Position.Left} style={HANDLE_STYLE} />
      <Handle type="target" position={Position.Top} style={HANDLE_STYLE} />
      <DeviceIcon type={componentType} color={color} size={22} />
      <div style={{ fontSize: 12, fontWeight: 600, textAlign: "center", lineHeight: 1.25, color: "var(--color-text)" }}>{label}</div>
      {subtitle && <div style={{ fontSize: 10, color: "var(--color-muted)" }}>{subtitle}</div>}
      <Handle type="source" position={Position.Right} style={HANDLE_STYLE} />
      <Handle type="source" position={Position.Bottom} style={HANDLE_STYLE} />
    </div>
  );
}

export const DEVICE_NODE_TYPES = { device: DeviceNode };
