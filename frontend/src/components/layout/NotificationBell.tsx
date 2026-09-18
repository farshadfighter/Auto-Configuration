import { Bell } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
  useUnreadCount,
  type Notification,
} from "../../hooks/useNotifications";

function linkForNotification(n: Notification): string | null {
  if (n.object_type === "deployment_job" && n.object_id) return `/deployment/jobs/${n.object_id}`;
  if (n.object_type === "drift_run") return "/drift";
  if (n.object_type === "approval_request") return "/design-configuration/jobs";
  return null;
}

function timeAgo(iso: string): string {
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const { data: unreadCount } = useUnreadCount();
  const { data: notifications } = useNotifications();
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();
  const navigate = useNavigate();

  function handleSelect(n: Notification) {
    if (!n.is_read) markRead.mutate(n.id);
    setOpen(false);
    const link = linkForNotification(n);
    if (link) navigate(link);
  }

  return (
    <div style={{ position: "relative" }}>
      <button
        className="btn-secondary"
        style={{ position: "relative", padding: "6px 10px" }}
        onClick={() => setOpen((v) => !v)}
        aria-label="Notifications"
      >
        <Bell size={16} />
        {Boolean(unreadCount) && (
          <span
            style={{
              position: "absolute",
              top: -4,
              right: -4,
              background: "#dc2626",
              color: "#fff",
              borderRadius: 999,
              fontSize: 10,
              lineHeight: 1,
              padding: "3px 5px",
              fontWeight: 700,
            }}
          >
            {(unreadCount ?? 0) > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div
          className="panel"
          style={{
            position: "absolute",
            top: "calc(100% + 8px)",
            right: 0,
            width: 340,
            maxHeight: 420,
            overflowY: "auto",
            zIndex: 20,
            boxShadow: "var(--shadow-md, 0 8px 24px rgba(0,0,0,0.15))",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <strong style={{ fontSize: 13 }}>Notifications</strong>
            {Boolean(unreadCount) && (
              <button className="btn-secondary" style={{ padding: "2px 8px", fontSize: 11 }} onClick={() => markAllRead.mutate()}>
                Mark all read
              </button>
            )}
          </div>
          {(!notifications || notifications.length === 0) && (
            <p className="empty-state" style={{ marginTop: 8 }}>
              No notifications yet.
            </p>
          )}
          <ul style={{ marginTop: 8, listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: 2 }}>
            {notifications?.map((n) => (
              <li key={n.id}>
                <button
                  onClick={() => handleSelect(n)}
                  style={{
                    width: "100%",
                    textAlign: "left",
                    background: n.is_read ? "transparent" : "var(--color-primary-soft, #eef2ff)",
                    border: "none",
                    borderRadius: 6,
                    padding: 8,
                    cursor: "pointer",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                    <span style={{ fontSize: 12, fontWeight: n.is_read ? 500 : 700 }}>{n.title}</span>
                    <span style={{ fontSize: 10, color: "var(--color-muted)", whiteSpace: "nowrap" }}>{timeAgo(n.created_at)}</span>
                  </div>
                  <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginTop: 2 }}>{n.message}</div>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
