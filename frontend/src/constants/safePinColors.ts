// Shared between DesignCanvasPage (generated reference diagrams) and TopologyPage (the real
// topology overlay) so a zone reads as the same color in both places.
export const SAFE_PIN_COLORS: Record<string, string> = {
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

export const DEFAULT_NODE_COLOR = "#334155";
