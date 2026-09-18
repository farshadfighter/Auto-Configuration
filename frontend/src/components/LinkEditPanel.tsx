// Shared "edit connection" panel used by both the Design canvas and the Topology page: lets the
// user attach real link metadata (type, bandwidth, VLAN, subnet) to a connection after it's been
// drawn, since none of that can be captured during the direct port-to-port drag itself.
const LINK_TYPES = ["lan", "wan", "trunk", "point_to_point", "wireless", "vpn"];

export interface LinkEditState {
  sourcePort: string;
  targetPort: string;
  linkType: string;
  speedMbps: string;
  vlan: string;
  subnet: string;
}

export function LinkEditPanel({
  sourceLabel,
  targetLabel,
  state,
  onChange,
  onSave,
  onCancel,
  saving,
  error,
}: {
  sourceLabel: string;
  targetLabel: string;
  state: LinkEditState;
  onChange: (next: LinkEditState) => void;
  onSave: () => void;
  onCancel: () => void;
  saving: boolean;
  error?: string | null;
}) {
  function set<K extends keyof LinkEditState>(key: K, value: string) {
    onChange({ ...state, [key]: value });
  }

  return (
    <div className="panel" style={{ marginTop: 12, maxWidth: 560 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
        <strong style={{ fontSize: 13 }}>
          Edit Link: {sourceLabel} &harr; {targetLabel}
        </strong>
        <button className="btn-secondary" style={{ padding: "2px 8px" }} onClick={onCancel}>
          &times;
        </button>
      </div>
      <div style={{ display: "flex", gap: 12, marginTop: 8, alignItems: "flex-end", flexWrap: "wrap" }}>
        <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, color: "var(--color-text-secondary)" }}>
          {sourceLabel} port
          <input value={state.sourcePort} onChange={(e) => set("sourcePort", e.target.value)} placeholder="Port" autoFocus />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, color: "var(--color-text-secondary)" }}>
          {targetLabel} port
          <input value={state.targetPort} onChange={(e) => set("targetPort", e.target.value)} placeholder="Port" />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, color: "var(--color-text-secondary)" }}>
          Link type
          <select value={state.linkType} onChange={(e) => set("linkType", e.target.value)}>
            <option value="">Unspecified</option>
            {LINK_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, color: "var(--color-text-secondary)" }}>
          Bandwidth (Mbps)
          <input
            type="number"
            min={0}
            value={state.speedMbps}
            onChange={(e) => set("speedMbps", e.target.value)}
            placeholder="e.g. 1000"
            style={{ width: 100 }}
          />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, color: "var(--color-text-secondary)" }}>
          VLAN
          <input
            type="number"
            min={1}
            max={4094}
            value={state.vlan}
            onChange={(e) => set("vlan", e.target.value)}
            placeholder="e.g. 10"
            style={{ width: 80 }}
          />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, color: "var(--color-text-secondary)" }}>
          Subnet
          <input value={state.subnet} onChange={(e) => set("subnet", e.target.value)} placeholder="e.g. 10.0.0.0/30" />
        </label>
        <button onClick={onSave} disabled={saving}>
          {saving ? "Saving..." : "Save"}
        </button>
        <button className="btn-secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
      {error && <p className="form-error">{error}</p>}
    </div>
  );
}
