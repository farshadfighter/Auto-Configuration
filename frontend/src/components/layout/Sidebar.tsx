import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

const ICON_PROPS = {
  width: 17,
  height: 17,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

const ICONS: Record<string, ReactNode> = {
  dashboard: (
    <svg {...ICON_PROPS}>
      <rect x="3" y="3" width="7" height="9" rx="1.5" />
      <rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" />
      <rect x="3" y="16" width="7" height="5" rx="1.5" />
    </svg>
  ),
  assets: (
    <svg {...ICON_PROPS}>
      <rect x="3" y="4" width="18" height="6" rx="1.5" />
      <rect x="3" y="14" width="18" height="6" rx="1.5" />
      <circle cx="7" cy="7" r="0.6" fill="currentColor" />
      <circle cx="7" cy="17" r="0.6" fill="currentColor" />
    </svg>
  ),
  discovery: (
    <svg {...ICON_PROPS}>
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.35-4.35" />
    </svg>
  ),
  topology: (
    <svg {...ICON_PROPS}>
      <circle cx="12" cy="4.5" r="2" />
      <circle cx="5" cy="19" r="2" />
      <circle cx="19" cy="19" r="2" />
      <path d="M12 6.5v6M12 12.5L6 17M12 12.5l6 4.5" />
    </svg>
  ),
  validation: (
    <svg {...ICON_PROPS}>
      <path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  ),
  design: (
    <svg {...ICON_PROPS}>
      <path d="M4 6h6M4 12h10M4 18h6" />
      <circle cx="16" cy="6" r="2" />
      <circle cx="20" cy="18" r="2" />
    </svg>
  ),
  deployment: (
    <svg {...ICON_PROPS}>
      <path d="M12 3v12" />
      <path d="M7 10l5 5 5-5" />
      <path d="M4 19h16" />
    </svg>
  ),
  backups: (
    <svg {...ICON_PROPS}>
      <rect x="3" y="4" width="18" height="5" rx="1.2" />
      <path d="M5 9v9a2 2 0 002 2h10a2 2 0 002-2V9" />
      <path d="M10 13h4" />
    </svg>
  ),
  drift: (
    <svg {...ICON_PROPS}>
      <path d="M3 12h5l2-7 4 14 2-7h5" />
    </svg>
  ),
  reports: (
    <svg {...ICON_PROPS}>
      <path d="M5 21V10M12 21V4M19 21v-7" />
    </svg>
  ),
  audit: (
    <svg {...ICON_PROPS}>
      <path d="M6 3h9l4 4v14a1 1 0 01-1 1H6a1 1 0 01-1-1V4a1 1 0 011-1z" />
      <path d="M9 12h6M9 16h6M9 8h3" />
    </svg>
  ),
  settings: (
    <svg {...ICON_PROPS}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09a1.65 1.65 0 00-1-1.51 1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09a1.65 1.65 0 001.51-1 1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
    </svg>
  ),
};

// Main sidebar per spec section 81. "Backups & Configuration" has no standalone top-level page
// yet - backup history lives on each Asset's detail page instead, since there's no
// list-all-backups-across-assets endpoint (add one here if that becomes worth a dedicated
// page). "Settings" (spec section 80) is out of scope for this MVP.
const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: "dashboard", enabled: true },
  { to: "/assets", label: "Assets", icon: "assets", enabled: true },
  { to: "/discovery", label: "Discovery", icon: "discovery", enabled: true },
  { to: "/topology", label: "Topology", icon: "topology", enabled: true },
  { to: "/validation", label: "Architecture Validation", icon: "validation", enabled: true },
  { to: "/design-configuration", label: "Design & Configuration", icon: "design", enabled: true },
  { to: "/deployment", label: "Deployment", icon: "deployment", enabled: true },
  { to: "/backups", label: "Backups & Configuration", icon: "backups", enabled: false },
  { to: "/drift", label: "Configuration Drift", icon: "drift", enabled: true },
  { to: "/reports", label: "Reports", icon: "reports", enabled: true },
  { to: "/audit", label: "Audit & Logs", icon: "audit", enabled: true },
  { to: "/settings", label: "Settings", icon: "settings", enabled: false },
];

export function Sidebar() {
  return (
    <nav className="sidebar">
      <div className="sidebar-brand">
        <span className="sidebar-brand-mark">NF</span>
        NGFabric
      </div>
      <ul className="sidebar-nav">
        {NAV_ITEMS.map((item) =>
          item.enabled ? (
            <li key={item.to}>
              <NavLink to={item.to} className={({ isActive }) => (isActive ? "active" : "")}>
                {ICONS[item.icon]}
                {item.label}
              </NavLink>
            </li>
          ) : (
            <li key={item.to} className="disabled" title="Coming in a later phase">
              {ICONS[item.icon]}
              {item.label}
            </li>
          ),
        )}
      </ul>
    </nav>
  );
}
