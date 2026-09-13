import {
  Archive,
  BarChart3,
  GitCompare,
  LayoutDashboard,
  ListChecks,
  PencilRuler,
  Rocket,
  ScrollText,
  Search,
  Server,
  Settings,
  ShieldCheck,
  Waypoints,
  type LucideIcon,
} from "lucide-react";
import { NavLink } from "react-router-dom";

const ICONS: Record<string, LucideIcon> = {
  dashboard: LayoutDashboard,
  assetRequirement: ListChecks,
  assets: Server,
  discovery: Search,
  topology: Waypoints,
  validation: ShieldCheck,
  design: PencilRuler,
  deployment: Rocket,
  backups: Archive,
  drift: GitCompare,
  reports: BarChart3,
  audit: ScrollText,
  settings: Settings,
};

// Main sidebar per spec section 81, grouped like a modern SaaS nav instead of one flat list.
// "Backups & Configuration" has no standalone top-level page yet - backup history lives on
// each Asset's detail page instead, since there's no list-all-backups-across-assets endpoint
// (add one here if that becomes worth a dedicated page). "Settings" (spec section 80) is out
// of scope for this MVP.
const NAV_GROUPS: { label: string; items: { to: string; label: string; icon: string; enabled: boolean }[] }[] = [
  {
    label: "Overview",
    items: [{ to: "/dashboard", label: "Dashboard", icon: "dashboard", enabled: true }],
  },
  {
    label: "Inventory",
    items: [
      { to: "/asset-requirement", label: "Asset Requirement", icon: "assetRequirement", enabled: true },
      { to: "/assets", label: "Assets", icon: "assets", enabled: true },
      { to: "/discovery", label: "Discovery", icon: "discovery", enabled: true },
      { to: "/topology", label: "Topology", icon: "topology", enabled: true },
    ],
  },
  {
    label: "Design & Operations",
    items: [
      { to: "/validation", label: "Architecture Validation", icon: "validation", enabled: true },
      { to: "/design-configuration", label: "Design & Configuration", icon: "design", enabled: true },
      { to: "/deployment", label: "Deployment", icon: "deployment", enabled: true },
      { to: "/backups", label: "Backups & Configuration", icon: "backups", enabled: false },
      { to: "/drift", label: "Configuration Drift", icon: "drift", enabled: true },
    ],
  },
  {
    label: "Insights",
    items: [
      { to: "/reports", label: "Reports", icon: "reports", enabled: true },
      { to: "/audit", label: "Audit & Logs", icon: "audit", enabled: true },
    ],
  },
  {
    label: "Admin",
    items: [{ to: "/settings", label: "Settings", icon: "settings", enabled: false }],
  },
];

export function Sidebar() {
  return (
    <nav className="sidebar">
      <div className="sidebar-brand">
        <span className="sidebar-brand-mark">NF</span>
        NGFabric
      </div>
      <ul className="sidebar-nav">
        {NAV_GROUPS.map((group) => (
          <li key={group.label} style={{ marginBottom: 0 }}>
            <div className="sidebar-group-label">{group.label}</div>
            <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
              {group.items.map((item) => {
                const Icon = ICONS[item.icon];
                return item.enabled ? (
                  <li key={item.to}>
                    <NavLink to={item.to} className={({ isActive }) => (isActive ? "active" : "")}>
                      <Icon size={16} strokeWidth={1.8} />
                      {item.label}
                    </NavLink>
                  </li>
                ) : (
                  <li key={item.to} className="disabled" title="Coming in a later phase">
                    <Icon size={16} strokeWidth={1.8} />
                    {item.label}
                  </li>
                );
              })}
            </ul>
          </li>
        ))}
      </ul>
    </nav>
  );
}
