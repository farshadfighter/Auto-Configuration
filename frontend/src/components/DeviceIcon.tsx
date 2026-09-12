import {
  Activity,
  Box,
  Boxes,
  Cloud,
  Fingerprint,
  Gauge,
  KeyRound,
  Lock,
  Network,
  Radar,
  Router as RouterIcon,
  ScrollText,
  Server,
  Shield,
  ShieldAlert,
  Wifi,
  type LucideIcon,
} from "lucide-react";

// Maps a design component_type / asset type code to the icon that best represents it on the
// architecture canvas and topology overlay, so a glance at the diagram reads like a real
// network diagram (device-shaped icons) rather than plain labeled boxes.
const ICON_BY_TYPE: Record<string, LucideIcon> = {
  router: RouterIcon,
  firewall: ShieldAlert,
  switch: Network,
  server: Server,
  domain_controller: Server,
  dns_server: Server,
  dhcp_server: Server,
  load_balancer: Boxes,
  ips: Radar,
  vpn_concentrator: Lock,
  cloud_gateway: Cloud,
  nac: Fingerprint,
  siem: Activity,
  aaa: KeyRound,
  nms: Gauge,
  logging: ScrollText,
  wlc: Wifi,
  zone: Shield,
};

const DEFAULT_ICON: LucideIcon = Box;

export function iconForType(type: string | null | undefined): LucideIcon {
  if (!type) return DEFAULT_ICON;
  return ICON_BY_TYPE[type.toLowerCase()] ?? DEFAULT_ICON;
}

// Palette of device types offered when dragging a new device onto the design canvas -
// deliberately the subset that maps to a real, creatable asset_type (unlike siem/aaa/nms/logging
// which are cross-cutting capabilities represented on the reference diagram but not concrete
// hardware assets in the inventory today).
export const PALETTE_DEVICE_TYPES: { type: string; label: string }[] = [
  { type: "router", label: "Router" },
  { type: "firewall", label: "Firewall" },
  { type: "switch", label: "Switch" },
  { type: "server", label: "Server" },
  { type: "load_balancer", label: "Load Balancer" },
];

export function DeviceIcon({
  type,
  size = 20,
  color,
  strokeWidth = 1.8,
}: {
  type: string | null | undefined;
  size?: number;
  color?: string;
  strokeWidth?: number;
}) {
  const Icon = iconForType(type);
  return <Icon size={size} color={color} strokeWidth={strokeWidth} />;
}
