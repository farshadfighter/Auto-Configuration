// EVE-NG-style device pictograms: a flat, device-shaped chassis with a small distinguishing
// glyph and a row of port ticks along the bottom edge, so a device reads as an actual piece of
// network hardware on the canvas rather than an abstract symbolic icon (the old Lucide icons -
// a generic Router/Shield/Server glyph - didn't look device-like and gave no sense of ports).

export interface GlyphProps {
  size: number;
  color: string;
  strokeWidth: number;
}

type Glyph = (props: GlyphProps) => React.JSX.Element;

function Chassis({ size, color, strokeWidth, tall = false, children }: GlyphProps & { tall?: boolean; children?: React.ReactNode }) {
  const w = 20;
  const h = tall ? 22 : 14;
  const x = (24 - w) / 2;
  const y = tall ? 1 : (24 - h) / 2 - 1;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <rect x={x} y={y} width={w} height={h} rx={2.5} stroke={color} strokeWidth={strokeWidth} />
      {children}
    </svg>
  );
}

function PortRow({ count, y, color }: { count: number; y: number; color: string; strokeWidth: number }) {
  const startX = 5;
  const endX = 19;
  const step = count > 1 ? (endX - startX) / (count - 1) : 0;
  return (
    <>
      {Array.from({ length: count }, (_, i) => (
        <rect key={i} x={startX + step * i - 0.7} y={y} width={1.4} height={2} fill={color} stroke="none" />
      ))}
    </>
  );
}

const RouterGlyph: Glyph = ({ size, color, strokeWidth }) => (
  <Chassis size={size} color={color} strokeWidth={strokeWidth}>
    <path d="M7 12a5 5 0 0 1 8-4" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" />
    <path d="M9.5 6.5 7 8l0.5-3" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" />
    <path d="M17 12a5 5 0 0 1-8 4" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" />
    <path d="M14.5 17.5 17 16l-0.5 3" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" />
    <PortRow count={4} y={16.5} color={color} strokeWidth={strokeWidth} />
  </Chassis>
);

const SwitchGlyph: Glyph = ({ size, color, strokeWidth }) => (
  <Chassis size={size} color={color} strokeWidth={strokeWidth}>
    <path d="M6 9h9" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" />
    <path d="M12.5 6.5 15 9l-2.5 2.5" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" />
    <path d="M18 13H9" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" />
    <path d="M11.5 10.5 9 13l2.5 2.5" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" />
    <PortRow count={8} y={16.5} color={color} strokeWidth={strokeWidth} />
  </Chassis>
);

const FirewallGlyph: Glyph = ({ size, color, strokeWidth }) => (
  <Chassis size={size} color={color} strokeWidth={strokeWidth}>
    {[7, 10.3, 13.6].map((y, row) => (
      <g key={y}>
        <path d={row % 2 === 0 ? `M6 ${y}h5.5M13 ${y}h5` : `M6 ${y}h2.5M10 ${y}h8`} stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" />
      </g>
    ))}
    <PortRow count={4} y={16.5} color={color} strokeWidth={strokeWidth} />
  </Chassis>
);

function ServerBody({ size, color, strokeWidth, badge }: GlyphProps & { badge?: React.ReactNode }) {
  return (
    <Chassis size={size} color={color} strokeWidth={strokeWidth} tall>
      <path d="M6 6.5h12" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" />
      <path d="M6 11h12" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" />
      <circle cx={8} cy={4} r={0.6} fill={color} stroke="none" />
      <circle cx={8} cy={8.75} r={0.6} fill={color} stroke="none" />
      {badge}
      <PortRow count={2} y={20} color={color} strokeWidth={strokeWidth} />
    </Chassis>
  );
}

const ServerGlyph: Glyph = (props) => <ServerBody {...props} />;

const DomainControllerGlyph: Glyph = (props) => (
  <ServerBody {...props} badge={<circle cx={16} cy={15} r={2.6} stroke={props.color} strokeWidth={props.strokeWidth} />} />
);

const DnsServerGlyph: Glyph = (props) => (
  <ServerBody
    {...props}
    badge={
      <g>
        <circle cx={16} cy={15} r={2.6} stroke={props.color} strokeWidth={props.strokeWidth} />
        <path d="M13.4 15h5.2M16 12.4a4 4 0 0 1 0 5.2M16 12.4a4 4 0 0 0 0 5.2" stroke={props.color} strokeWidth={props.strokeWidth * 0.8} />
      </g>
    }
  />
);

const DhcpServerGlyph: Glyph = (props) => (
  <ServerBody
    {...props}
    badge={<path d="M13.5 13.5h5l-1.2 1.2h1.2l-3 3v-1.9h-1.2z" stroke={props.color} strokeWidth={props.strokeWidth * 0.8} strokeLinejoin="round" />}
  />
);

const LoadBalancerGlyph: Glyph = ({ size, color, strokeWidth }) => (
  <Chassis size={size} color={color} strokeWidth={strokeWidth}>
    <path d="M12 6v8M8 10.5l4-2.5 4 2.5" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" />
    <path d="M6 14h2.5M11 14h2M15.5 14H18" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" />
    <PortRow count={4} y={16.5} color={color} strokeWidth={strokeWidth} />
  </Chassis>
);

const IpsGlyph: Glyph = ({ size, color, strokeWidth }) => (
  <Chassis size={size} color={color} strokeWidth={strokeWidth}>
    <circle cx={12} cy={10.5} r={3.2} stroke={color} strokeWidth={strokeWidth} />
    <path d="M12 10.5V8M12 10.5l1.8 1" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" />
    <PortRow count={4} y={16.5} color={color} strokeWidth={strokeWidth} />
  </Chassis>
);

const VpnGlyph: Glyph = ({ size, color, strokeWidth }) => (
  <Chassis size={size} color={color} strokeWidth={strokeWidth}>
    <rect x={9.7} y={9.5} width={4.6} height={3.6} rx={0.6} stroke={color} strokeWidth={strokeWidth} />
    <path d="M10.5 9.5V8a1.5 1.5 0 0 1 3 0v1.5" stroke={color} strokeWidth={strokeWidth} />
    <PortRow count={4} y={16.5} color={color} strokeWidth={strokeWidth} />
  </Chassis>
);

const CloudGatewayGlyph: Glyph = ({ size, color, strokeWidth }) => (
  <Chassis size={size} color={color} strokeWidth={strokeWidth}>
    <path
      d="M8.2 12.6a2.2 2.2 0 0 1 .2-4.4 2.7 2.7 0 0 1 5.1-1 2 2 0 0 1 2.5 1.9 1.9 1.9 0 0 1-.3 3.5z"
      stroke={color}
      strokeWidth={strokeWidth * 0.85}
      strokeLinejoin="round"
    />
    <PortRow count={4} y={16.5} color={color} strokeWidth={strokeWidth} />
  </Chassis>
);

const NacGlyph: Glyph = ({ size, color, strokeWidth }) => (
  <Chassis size={size} color={color} strokeWidth={strokeWidth}>
    <path d="M12 6.5c2 0 3.2.9 3.2 1.9 0 3-1 5.7-3.2 6.6-2.2-.9-3.2-3.6-3.2-6.6 0-1 1.2-1.9 3.2-1.9Z" stroke={color} strokeWidth={strokeWidth} strokeLinejoin="round" />
    <path d="M10.2 10.8l1.2 1.2 2-2.4" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" />
  </Chassis>
);

const SiemGlyph: Glyph = ({ size, color, strokeWidth }) => (
  <Chassis size={size} color={color} strokeWidth={strokeWidth}>
    <path d="M6.5 10.5s2-3 5.5-3 5.5 3 5.5 3-2 3-5.5 3-5.5-3-5.5-3Z" stroke={color} strokeWidth={strokeWidth} strokeLinejoin="round" />
    <circle cx={12} cy={10.5} r={1.4} stroke={color} strokeWidth={strokeWidth} />
    <PortRow count={4} y={16.5} color={color} strokeWidth={strokeWidth} />
  </Chassis>
);

const AaaGlyph: Glyph = ({ size, color, strokeWidth }) => (
  <Chassis size={size} color={color} strokeWidth={strokeWidth}>
    <circle cx={9.3} cy={10} r={1.6} stroke={color} strokeWidth={strokeWidth} />
    <path d="M10.6 10h6.4M14.5 10v1.6M16.5 10v1.2" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" />
    <PortRow count={4} y={16.5} color={color} strokeWidth={strokeWidth} />
  </Chassis>
);

const NmsGlyph: Glyph = ({ size, color, strokeWidth }) => (
  <Chassis size={size} color={color} strokeWidth={strokeWidth}>
    <path d="M7.5 12.5a4.5 4.5 0 0 1 9 0" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" />
    <path d="M12 12.5 14.3 9.3" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" />
    <circle cx={12} cy={12.5} r={0.7} fill={color} stroke="none" />
    <PortRow count={4} y={16.5} color={color} strokeWidth={strokeWidth} />
  </Chassis>
);

const LoggingGlyph: Glyph = ({ size, color, strokeWidth }) => (
  <Chassis size={size} color={color} strokeWidth={strokeWidth}>
    <path d="M8 7.5h8M8 10h8M8 12.5h5.5" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" />
    <PortRow count={4} y={16.5} color={color} strokeWidth={strokeWidth} />
  </Chassis>
);

const WlcGlyph: Glyph = ({ size, color, strokeWidth }) => (
  <Chassis size={size} color={color} strokeWidth={strokeWidth}>
    <path d="M8.5 11a5 5 0 0 1 7 0" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" />
    <path d="M10 13a2.7 2.7 0 0 1 4 0" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" />
    <circle cx={12} cy={15} r={0.7} fill={color} stroke="none" />
    <PortRow count={4} y={17.2} color={color} strokeWidth={strokeWidth} />
  </Chassis>
);

const ZoneGlyph: Glyph = ({ size, color, strokeWidth }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <path d="M12 3.5 19 6.5v5c0 5-3 8-7 9-4-1-7-4-7-9v-5Z" stroke={color} strokeWidth={strokeWidth} strokeLinejoin="round" />
  </svg>
);

const GenericGlyph: Glyph = ({ size, color, strokeWidth }) => (
  <Chassis size={size} color={color} strokeWidth={strokeWidth}>
    <rect x={9.5} y={8.5} width={5} height={5} rx={0.6} stroke={color} strokeWidth={strokeWidth} />
    <PortRow count={4} y={16.5} color={color} strokeWidth={strokeWidth} />
  </Chassis>
);

const ICON_BY_TYPE: Record<string, Glyph> = {
  router: RouterGlyph,
  firewall: FirewallGlyph,
  switch: SwitchGlyph,
  server: ServerGlyph,
  domain_controller: DomainControllerGlyph,
  dns_server: DnsServerGlyph,
  dhcp_server: DhcpServerGlyph,
  load_balancer: LoadBalancerGlyph,
  ips: IpsGlyph,
  vpn_concentrator: VpnGlyph,
  cloud_gateway: CloudGatewayGlyph,
  nac: NacGlyph,
  siem: SiemGlyph,
  aaa: AaaGlyph,
  nms: NmsGlyph,
  logging: LoggingGlyph,
  wlc: WlcGlyph,
  zone: ZoneGlyph,
};

const DEFAULT_GLYPH: Glyph = GenericGlyph;

export function iconForType(type: string | null | undefined): Glyph {
  if (!type) return DEFAULT_GLYPH;
  return ICON_BY_TYPE[type.toLowerCase()] ?? DEFAULT_GLYPH;
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
  color = "#334155",
  strokeWidth = 1.6,
}: {
  type: string | null | undefined;
  size?: number;
  color?: string;
  strokeWidth?: number;
}) {
  const Glyph = iconForType(type);
  return <Glyph size={size} color={color} strokeWidth={strokeWidth} />;
}
