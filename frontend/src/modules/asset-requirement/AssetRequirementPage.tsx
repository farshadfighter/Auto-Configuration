import { useState } from "react";
import {
  useAssetTypes,
  useCreateAssetType,
  useCreateLocation,
  useCreateOperatingSystem,
  useCreateVendor,
  useCreateZone,
  useLocations,
  useOperatingSystems,
  useVendors,
  useZones,
} from "../../hooks/useAssets";
import { getErrorMessage } from "../../services/api";

type TabKey = "asset-type" | "location" | "network-zone" | "os-catalog" | "vendors";

const TABS: { key: TabKey; label: string }[] = [
  { key: "asset-type", label: "Asset Type" },
  { key: "location", label: "Location" },
  { key: "network-zone", label: "Network Zone" },
  { key: "os-catalog", label: "OS Catalog" },
  { key: "vendors", label: "Vendors" },
];

function AssetTypeTab() {
  const { data, isLoading, isError } = useAssetTypes();
  const createAssetType = useCreateAssetType();
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");

  function handleSubmit() {
    if (!code.trim() || !name.trim()) return;
    createAssetType.mutate(
      { code: code.trim(), name: name.trim(), category: category.trim() || undefined },
      { onSuccess: () => { setCode(""); setName(""); setCategory(""); } },
    );
  }

  return (
    <div>
      <div className="panel" style={{ marginBottom: 20 }}>
        <h2>Add Asset Type</h2>
        <div style={{ display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
          <input placeholder="Code (required)" value={code} onChange={(e) => setCode(e.target.value)} />
          <input placeholder="Name (required)" value={name} onChange={(e) => setName(e.target.value)} />
          <input placeholder="Category" value={category} onChange={(e) => setCategory(e.target.value)} />
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button onClick={handleSubmit} disabled={!code.trim() || !name.trim() || createAssetType.isPending}>
            {createAssetType.isPending ? "Adding..." : "Add Asset Type"}
          </button>
          {createAssetType.isError && (
            <span className="form-error">{getErrorMessage(createAssetType.error, "Could not add asset type")}</span>
          )}
        </div>
      </div>

      {isLoading && <p>Loading...</p>}
      {isError && <p className="form-error">Failed to load asset types.</p>}
      {data && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Category</th>
            </tr>
          </thead>
          <tbody>
            {data.length === 0 && (
              <tr>
                <td colSpan={3} className="empty-state">
                  No asset types yet.
                </td>
              </tr>
            )}
            {data.map((t) => (
              <tr key={t.id}>
                <td>{t.code}</td>
                <td>{t.name}</td>
                <td>{t.category ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function LocationTab() {
  const { data, isLoading, isError } = useLocations();
  const createLocation = useCreateLocation();
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");

  function handleSubmit() {
    if (!name.trim()) return;
    createLocation.mutate(
      { name: name.trim(), address: address.trim() || undefined },
      { onSuccess: () => { setName(""); setAddress(""); } },
    );
  }

  return (
    <div>
      <div className="panel" style={{ marginBottom: 20 }}>
        <h2>Add Location</h2>
        <div style={{ display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
          <input placeholder="Name (required)" value={name} onChange={(e) => setName(e.target.value)} />
          <input placeholder="Address" value={address} onChange={(e) => setAddress(e.target.value)} />
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button onClick={handleSubmit} disabled={!name.trim() || createLocation.isPending}>
            {createLocation.isPending ? "Adding..." : "Add Location"}
          </button>
          {createLocation.isError && (
            <span className="form-error">{getErrorMessage(createLocation.error, "Could not add location")}</span>
          )}
        </div>
      </div>

      {isLoading && <p>Loading...</p>}
      {isError && <p className="form-error">Failed to load locations.</p>}
      {data && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Address</th>
            </tr>
          </thead>
          <tbody>
            {data.length === 0 && (
              <tr>
                <td colSpan={2} className="empty-state">
                  No locations yet.
                </td>
              </tr>
            )}
            {data.map((l) => (
              <tr key={l.id}>
                <td>{l.name}</td>
                <td>{l.address ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function NetworkZoneTab() {
  const { data, isLoading, isError } = useZones();
  const createZone = useCreateZone();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  function handleSubmit() {
    if (!name.trim()) return;
    createZone.mutate(
      { name: name.trim(), description: description.trim() || undefined },
      { onSuccess: () => { setName(""); setDescription(""); } },
    );
  }

  return (
    <div>
      <div className="panel" style={{ marginBottom: 20 }}>
        <h2>Add Network Zone</h2>
        <div style={{ display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
          <input placeholder="Name (required)" value={name} onChange={(e) => setName(e.target.value)} />
          <input placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button onClick={handleSubmit} disabled={!name.trim() || createZone.isPending}>
            {createZone.isPending ? "Adding..." : "Add Network Zone"}
          </button>
          {createZone.isError && (
            <span className="form-error">{getErrorMessage(createZone.error, "Could not add network zone")}</span>
          )}
        </div>
      </div>

      {isLoading && <p>Loading...</p>}
      {isError && <p className="form-error">Failed to load network zones.</p>}
      {data && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {data.length === 0 && (
              <tr>
                <td colSpan={2} className="empty-state">
                  No network zones yet.
                </td>
              </tr>
            )}
            {data.map((z) => (
              <tr key={z.id}>
                <td>{z.name}</td>
                <td>{z.description ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function OsCatalogTab() {
  const { data, isLoading, isError } = useOperatingSystems();
  const { data: vendors } = useVendors();
  const createOperatingSystem = useCreateOperatingSystem();
  const [name, setName] = useState("");
  const [vendorId, setVendorId] = useState("");

  function handleSubmit() {
    if (!name.trim()) return;
    createOperatingSystem.mutate(
      { name: name.trim(), vendor_id: vendorId || undefined },
      { onSuccess: () => { setName(""); setVendorId(""); } },
    );
  }

  const vendorNameById = new Map((vendors ?? []).map((v) => [v.id, v.name]));

  return (
    <div>
      <div className="panel" style={{ marginBottom: 20 }}>
        <h2>Add Operating System</h2>
        <div style={{ display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
          <input placeholder="Name (required)" value={name} onChange={(e) => setName(e.target.value)} />
          <select value={vendorId} onChange={(e) => setVendorId(e.target.value)}>
            <option value="">Vendor (optional)...</option>
            {vendors?.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
          </select>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button onClick={handleSubmit} disabled={!name.trim() || createOperatingSystem.isPending}>
            {createOperatingSystem.isPending ? "Adding..." : "Add Operating System"}
          </button>
          {createOperatingSystem.isError && (
            <span className="form-error">{getErrorMessage(createOperatingSystem.error, "Could not add operating system")}</span>
          )}
        </div>
      </div>

      {isLoading && <p>Loading...</p>}
      {isError && <p className="form-error">Failed to load operating systems.</p>}
      {data && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Vendor</th>
            </tr>
          </thead>
          <tbody>
            {data.length === 0 && (
              <tr>
                <td colSpan={2} className="empty-state">
                  No operating systems yet.
                </td>
              </tr>
            )}
            {data.map((o) => (
              <tr key={o.id}>
                <td>{o.name}</td>
                <td>{o.vendor_id ? vendorNameById.get(o.vendor_id) ?? "—" : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function VendorsTab() {
  const { data, isLoading, isError } = useVendors();
  const createVendor = useCreateVendor();
  const [name, setName] = useState("");

  function handleSubmit() {
    if (!name.trim()) return;
    createVendor.mutate({ name: name.trim() }, { onSuccess: () => setName("") });
  }

  return (
    <div>
      <div className="panel" style={{ marginBottom: 20 }}>
        <h2>Add Vendor</h2>
        <div style={{ display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
          <input placeholder="Name (required)" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button onClick={handleSubmit} disabled={!name.trim() || createVendor.isPending}>
            {createVendor.isPending ? "Adding..." : "Add Vendor"}
          </button>
          {createVendor.isError && (
            <span className="form-error">{getErrorMessage(createVendor.error, "Could not add vendor")}</span>
          )}
        </div>
      </div>

      {isLoading && <p>Loading...</p>}
      {isError && <p className="form-error">Failed to load vendors.</p>}
      {data && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
            </tr>
          </thead>
          <tbody>
            {data.length === 0 && (
              <tr>
                <td colSpan={1} className="empty-state">
                  No vendors yet.
                </td>
              </tr>
            )}
            {data.map((v) => (
              <tr key={v.id}>
                <td>{v.name}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export function AssetRequirementPage() {
  const [activeTab, setActiveTab] = useState<TabKey>("asset-type");

  return (
    <div>
      <div className="page-header">
        <h1>Asset Requirement</h1>
      </div>
      <p style={{ marginTop: -12, marginBottom: 20, color: "var(--color-text-secondary)", fontSize: 13 }}>
        Define the reference data (asset types, locations, network zones, operating systems, and vendors) used to
        fill in the Assets form.
      </p>

      <div className="tab-bar">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            className={activeTab === tab.key ? "tab-button active" : "tab-button"}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "asset-type" && <AssetTypeTab />}
      {activeTab === "location" && <LocationTab />}
      {activeTab === "network-zone" && <NetworkZoneTab />}
      {activeTab === "os-catalog" && <OsCatalogTab />}
      {activeTab === "vendors" && <VendorsTab />}
    </div>
  );
}
