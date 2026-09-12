import { useQuery } from "@tanstack/react-query";
import { api, type ApiSuccess } from "../../services/api";

interface AuditEvent {
  id: string;
  timestamp: string;
  user_id: string | null;
  action: string;
  object_type: string;
  object_id: string | null;
  result: "SUCCESS" | "FAILURE";
}

export function AuditLogPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["audit", "events"],
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<AuditEvent[]>>("/audit/events");
      return data.data;
    },
  });

  return (
    <div>
      <h1>Audit &amp; Logs</h1>
      {isLoading && <p>Loading...</p>}
      {isError && <p className="form-error">Failed to load audit events.</p>}
      {data && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Action</th>
              <th>Object Type</th>
              <th>Object ID</th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody>
            {data.length === 0 && (
              <tr>
                <td colSpan={5} className="empty-state">
                  No audit events yet.
                </td>
              </tr>
            )}
            {data.map((event) => (
              <tr key={event.id}>
                <td>{new Date(event.timestamp).toLocaleString()}</td>
                <td>{event.action}</td>
                <td>{event.object_type}</td>
                <td>{event.object_id ?? "—"}</td>
                <td>
                  <span className={event.result === "SUCCESS" ? "badge badge-low" : "badge badge-critical"}>
                    {event.result}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
