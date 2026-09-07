import { Fragment, useState } from "react";
import { useCreateCsvDiscoveryJob, useDiscoveryErrors, useDiscoveryJobs } from "../../hooks/useDiscovery";
import { getErrorMessage } from "../../services/api";

const STATUS_BADGE: Record<string, string> = {
  success: "badge-low",
  partial: "badge-medium",
  failed: "badge-critical",
  running: "badge-medium",
  queued: "badge-medium",
  cancelled: "badge-medium",
};

const SAMPLE_CSV = "name,asset_type_code,management_ip\nbranch-sw-01,switch,10.20.0.1\n";

export function DiscoveryJobsPage() {
  const { data: jobs, isLoading } = useDiscoveryJobs();
  const [csvContent, setCsvContent] = useState(SAMPLE_CSV);
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
  const createJob = useCreateCsvDiscoveryJob();
  const { data: errors } = useDiscoveryErrors(expandedJobId ?? undefined);

  return (
    <div>
      <h1>Discovery</h1>

      <section style={{ marginBottom: 24 }}>
        <h2>CSV Import</h2>
        <p className="muted">
          Columns: name, asset_type_code (required), hostname, vendor_name, management_ip, serial_number,
          mac_address, criticality.
        </p>
        <textarea
          value={csvContent}
          onChange={(e) => setCsvContent(e.target.value)}
          rows={5}
          style={{ width: "100%", maxWidth: 640, fontFamily: "monospace" }}
        />
        <div style={{ marginTop: 8 }}>
          <button onClick={() => createJob.mutate(csvContent)} disabled={!csvContent.trim() || createJob.isPending}>
            {createJob.isPending ? "Submitting..." : "Run CSV Discovery"}
          </button>
        </div>
        {createJob.isError && (
          <p className="form-error">
            Failed to start discovery job: {getErrorMessage(createJob.error)}
          </p>
        )}
      </section>

      <h2>Jobs</h2>
      {isLoading && <p>Loading...</p>}
      {jobs && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Created</th>
              <th>Method</th>
              <th>Status</th>
              <th>Discovered</th>
              <th>Updated</th>
              <th>Failed</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {jobs.length === 0 && (
              <tr>
                <td colSpan={7} className="empty-state">
                  No discovery jobs yet.
                </td>
              </tr>
            )}
            {jobs.map((job) => (
              <Fragment key={job.id}>
                <tr>
                  <td>{new Date(job.created_at).toLocaleString()}</td>
                  <td>{job.method}</td>
                  <td>
                    <span className={`badge ${STATUS_BADGE[job.status]}`}>{job.status}</span>
                  </td>
                  <td>{job.discovered_count}</td>
                  <td>{job.updated_count}</td>
                  <td>{job.failed_count}</td>
                  <td>
                    {job.failed_count > 0 && (
                      <button className="btn-secondary" onClick={() => setExpandedJobId(expandedJobId === job.id ? null : job.id)}>
                        {expandedJobId === job.id ? "Hide errors" : "Show errors"}
                      </button>
                    )}
                  </td>
                </tr>
                {expandedJobId === job.id && errors && (
                  <tr>
                    <td colSpan={7}>
                      <ul>
                        {errors.map((e) => (
                          <li key={e.id} className="form-error">
                            {e.message}
                          </li>
                        ))}
                      </ul>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
