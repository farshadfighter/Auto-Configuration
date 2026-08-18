import { NavLink } from "react-router-dom";

// Main sidebar per spec section 81. "Backups & Configuration" has no standalone top-level page
// yet - backup history lives on each Asset's detail page instead, since there's no
// list-all-backups-across-assets endpoint (add one here if that becomes worth a dedicated
// page). "Settings" (spec section 80) is out of scope for this MVP.
const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", enabled: true },
  { to: "/assets", label: "Assets", enabled: true },
  { to: "/discovery", label: "Discovery", enabled: true },
  { to: "/topology", label: "Topology", enabled: true },
  { to: "/validation", label: "Architecture Validation", enabled: true },
  { to: "/design-configuration", label: "Design & Configuration", enabled: true },
  { to: "/deployment", label: "Deployment", enabled: true },
  { to: "/backups", label: "Backups & Configuration", enabled: false },
  { to: "/drift", label: "Configuration Drift", enabled: true },
  { to: "/reports", label: "Reports", enabled: true },
  { to: "/audit", label: "Audit & Logs", enabled: true },
  { to: "/settings", label: "Settings", enabled: false },
];

export function Sidebar() {
  return (
    <nav className="sidebar">
      <div className="sidebar-brand">NGFabric</div>
      <ul className="sidebar-nav">
        {NAV_ITEMS.map((item) =>
          item.enabled ? (
            <li key={item.to}>
              <NavLink to={item.to} className={({ isActive }) => (isActive ? "active" : "")}>
                {item.label}
              </NavLink>
            </li>
          ) : (
            <li key={item.to} className="disabled" title="Coming in a later phase">
              {item.label}
            </li>
          ),
        )}
      </ul>
    </nav>
  );
}
