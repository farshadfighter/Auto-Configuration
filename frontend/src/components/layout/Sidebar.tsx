import { NavLink } from "react-router-dom";

// Main sidebar per spec section 81. Sections beyond Phase 1 (Discovery, Topology, Design &
// Configuration, Deployment, Backups, Drift, Reports) render as disabled placeholders so the
// full information architecture is visible from the start.
const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", enabled: true },
  { to: "/assets", label: "Assets", enabled: true },
  { to: "/discovery", label: "Discovery", enabled: false },
  { to: "/topology", label: "Topology", enabled: false },
  { to: "/validation", label: "Architecture Validation", enabled: false },
  { to: "/design-configuration", label: "Design & Configuration", enabled: false },
  { to: "/deployment", label: "Deployment", enabled: false },
  { to: "/backups", label: "Backups & Configuration", enabled: false },
  { to: "/drift", label: "Configuration Drift", enabled: false },
  { to: "/reports", label: "Reports", enabled: false },
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
