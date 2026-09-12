import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  INFORMATION_CLASSIFICATION_LABELS,
  SAFE_PIN_LABELS,
  downloadAssetsCsv,
  useAssets,
  useAssetTypes,
  useComplianceFrameworks,
  useCreateAsset,
  useImportAssetsCsv,
  type CsvImportSummary,
  type InformationClassification,
  type SafePin,
} from "../../hooks/useAssets";
import { getErrorMessage } from "../../services/api";

const CRITICALITY_LABEL: Record<string, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

function AddAssetForm({ onDone }: { onDone: () => void }) {
  const { data: assetTypes, isLoading: assetTypesLoading, isError: assetTypesIsError } = useAssetTypes();
  const { data: complianceFrameworks } = useComplianceFrameworks();
  const createAsset = useCreateAsset();
  const [name, setName] = useState("");
  const [hostname, setHostname] = useState("");
  const [assetTypeId, setAssetTypeId] = useState("");
  const [managementIp, setManagementIp] = useState("");
  const [criticality, setCriticality] = useState<"low" | "medium" | "high" | "critical">("medium");
  const [safePin, setSafePin] = useState<SafePin | "">("");
  const [informationClassification, setInformationClassification] = useState<InformationClassification>("internal");
  const [complianceCodes, setComplianceCodes] = useState<string[]>([]);
  const [backupRequired, setBackupRequired] = useState(false);

  function toggleComplianceCode(code: string) {
    setComplianceCodes((prev) => (prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]));
  }

  function handleSubmit() {
    if (!name.trim() || !assetTypeId) return;
    createAsset.mutate(
      {
        name: name.trim(),
        hostname: hostname.trim() || undefined,
        asset_type_id: assetTypeId,
        management_ip: managementIp.trim() || undefined,
        criticality,
        safe_pin: safePin || undefined,
        information_classification: informationClassification,
        compliance_framework_codes: complianceCodes.length > 0 ? complianceCodes : undefined,
        backup_required: backupRequired,
      },
      { onSuccess: onDone },
    );
  }

  return (
    <div className="panel" style={{ marginBottom: 20 }}>
      <h2>Add Asset</h2>
      <div style={{ display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
        <input placeholder="Name (required)" value={name} onChange={(e) => setName(e.target.value)} />
        <select value={assetTypeId} onChange={(e) => setAssetTypeId(e.target.value)}>
          <option value="">
            {assetTypesLoading ? "Loading asset types..." : "Asset type (required)..."}
          </option>
          {assetTypes?.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
        <input placeholder="Hostname" value={hostname} onChange={(e) => setHostname(e.target.value)} />
        <input placeholder="Management IP" value={managementIp} onChange={(e) => setManagementIp(e.target.value)} />
        <select value={criticality} onChange={(e) => setCriticality(e.target.value as typeof criticality)}>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
        <select value={safePin} onChange={(e) => setSafePin(e.target.value as SafePin | "")}>
          <option value="">SAFE zone (optional)...</option>
          {Object.entries(SAFE_PIN_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      <div style={{ display: "flex", gap: 16, marginBottom: 8, flexWrap: "wrap", alignItems: "center" }}>
        <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, fontWeight: 500, color: "var(--color-text-secondary)" }}>
          Information classification
          <select
            value={informationClassification}
            onChange={(e) => setInformationClassification(e.target.value as InformationClassification)}
          >
            {Object.entries(INFORMATION_CLASSIFICATION_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>

        {complianceFrameworks && complianceFrameworks.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-secondary)" }}>Compliance scope</span>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              {complianceFrameworks.map((f) => (
                <label key={f.id} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 13 }}>
                  <input
                    type="checkbox"
                    checked={complianceCodes.includes(f.code)}
                    onChange={() => toggleComplianceCode(f.code)}
                  />
                  {f.name}
                </label>
              ))}
            </div>
          </div>
        )}

        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
          <input type="checkbox" checked={backupRequired} onChange={(e) => setBackupRequired(e.target.checked)} />
          Backup required
        </label>
      </div>

      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <button onClick={handleSubmit} disabled={!name.trim() || !assetTypeId || createAsset.isPending}>
          {createAsset.isPending ? "Creating..." : "Create Asset"}
        </button>
        <button className="btn-secondary" onClick={onDone}>
          Cancel
        </button>
        {createAsset.isError && <span className="form-error">{getErrorMessage(createAsset.error, "Could not create asset")}</span>}
        {assetTypesIsError && <span className="form-error">Could not load asset types.</span>}
        {!assetTypesLoading && !assetTypesIsError && assetTypes?.length === 0 && (
          <span className="form-error">No asset types configured yet - ask an administrator to add one.</span>
        )}
      </div>
    </div>
  );
}

function ImportSummaryPanel({ summary, onDismiss }: { summary: CsvImportSummary; onDismiss: () => void }) {
  return (
    <div className="panel" style={{ marginBottom: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
        <strong>
          Import complete: {summary.created} created, {summary.updated} updated
          {summary.errors.length > 0 ? `, ${summary.errors.length} row(s) skipped` : ""}
        </strong>
        <button className="btn-secondary" onClick={onDismiss} style={{ padding: "2px 8px" }}>
          &times;
        </button>
      </div>
      {summary.errors.length > 0 && (
        <ul style={{ marginTop: 8 }}>
          {summary.errors.map((e, i) => (
            <li key={i} className="form-error" style={{ display: "block", marginBottom: 4 }}>
              Row {e.row}: {e.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function AssetListPage() {
  const [search, setSearch] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);
  const [importSummary, setImportSummary] = useState<CsvImportSummary | null>(null);
  const { data, isLoading, isError } = useAssets({ search: search || undefined });
  const importCsv = useImportAssetsCsv();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  function handleImportFileChosen(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    importCsv.mutate(file, { onSuccess: setImportSummary });
    e.target.value = "";
  }

  return (
    <div>
      <div className="page-header">
        <h1>Assets</h1>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            className="search-input"
            placeholder="Search by name, hostname, or code..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button className="btn-secondary" onClick={() => downloadAssetsCsv()}>
            Export CSV
          </button>
          <input ref={fileInputRef} type="file" accept=".csv" onChange={handleImportFileChosen} style={{ display: "none" }} />
          <button className="btn-secondary" onClick={() => fileInputRef.current?.click()} disabled={importCsv.isPending}>
            {importCsv.isPending ? "Importing..." : "Import CSV"}
          </button>
          {!showAddForm && <button onClick={() => setShowAddForm(true)}>Add Asset</button>}
        </div>
      </div>

      {importCsv.isError && <p className="form-error">{getErrorMessage(importCsv.error, "CSV import failed")}</p>}
      {importSummary && <ImportSummaryPanel summary={importSummary} onDismiss={() => setImportSummary(null)} />}
      {showAddForm && <AddAssetForm onDone={() => setShowAddForm(false)} />}

      {isLoading && <p>Loading...</p>}
      {isError && <p className="form-error">Failed to load assets.</p>}

      {data && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Asset Code</th>
              <th>Name</th>
              <th>Hostname</th>
              <th>Management IP</th>
              <th>Criticality</th>
              <th>Classification</th>
              <th>Status</th>
              <th>Managed</th>
              <th>SAFE Zone</th>
            </tr>
          </thead>
          <tbody>
            {data.data.length === 0 && (
              <tr>
                <td colSpan={9} className="empty-state">
                  No assets found.
                </td>
              </tr>
            )}
            {data.data.map((asset) => (
              <tr key={asset.id}>
                <td>
                  <Link to={`/assets/${asset.id}`}>{asset.asset_code}</Link>
                </td>
                <td>{asset.name}</td>
                <td>{asset.hostname ?? "—"}</td>
                <td>{asset.management_ip ?? "—"}</td>
                <td>
                  <span className={`badge badge-${asset.criticality}`}>
                    {CRITICALITY_LABEL[asset.criticality]}
                  </span>
                </td>
                <td>{INFORMATION_CLASSIFICATION_LABELS[asset.information_classification]}</td>
                <td>{asset.status}</td>
                <td>{asset.managed}</td>
                <td>{asset.safe_pin ? SAFE_PIN_LABELS[asset.safe_pin] : <span className="muted">Unclassified</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
