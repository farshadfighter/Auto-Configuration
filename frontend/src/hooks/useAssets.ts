import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type ApiSuccess } from "../services/api";

export type SafePin =
  | "internet_edge"
  | "wan"
  | "campus_core"
  | "campus_distribution"
  | "campus_access"
  | "data_center"
  | "branch"
  | "cloud"
  | "management";

export const SAFE_PIN_LABELS: Record<SafePin, string> = {
  internet_edge: "Internet Edge",
  wan: "WAN",
  campus_core: "Campus Core",
  campus_distribution: "Campus Distribution",
  campus_access: "Campus Access",
  data_center: "Data Center",
  branch: "Branch",
  cloud: "Cloud",
  management: "Management & Security Operations",
};

// ISO/IEC 27001-style ISMS asset-register fields (Annex A.5.9 inventory, A.5.12/A.5.13
// classification) - distinct from `criticality`, which rates operational impact rather than
// information sensitivity.
export type InformationClassification = "public" | "internal" | "confidential" | "restricted";

export const INFORMATION_CLASSIFICATION_LABELS: Record<InformationClassification, string> = {
  public: "Public",
  internal: "Internal",
  confidential: "Confidential",
  restricted: "Restricted",
};

export type BackupFrequency = "none" | "daily" | "weekly" | "monthly";

export const BACKUP_FREQUENCY_LABELS: Record<BackupFrequency, string> = {
  none: "None",
  daily: "Daily",
  weekly: "Weekly",
  monthly: "Monthly",
};

export interface Asset {
  id: string;
  asset_code: string;
  name: string;
  hostname: string | null;
  asset_type_id: string;
  vendor_id: string | null;
  os_id: string | null;
  location_id: string | null;
  zone_id: string | null;
  management_ip: string | null;
  criticality: "low" | "medium" | "high" | "critical";
  status: "provisioning" | "active" | "inactive" | "decommissioned" | "unknown";
  managed: "managed" | "unmanaged" | "pending";
  site_id: string | null;
  environment_id: string | null;
  safe_pin: SafePin | null;
  owner_id: string | null;
  custodian_id: string | null;
  information_classification: InformationClassification;
  compliance_scope: string[];
  acquired_at: string | null;
  warranty_expires_at: string | null;
  planned_retirement_at: string | null;
  decommissioned_at: string | null;
  disposal_method: string | null;
  disposal_notes: string | null;
  risk_assessment_ref: string | null;
  risk_last_reviewed_at: string | null;
  backup_required: boolean;
  backup_frequency: BackupFrequency | null;
}

interface AssetListParams {
  page?: number;
  page_size?: number;
  search?: string;
}

export function useAssets(params: AssetListParams = {}) {
  return useQuery({
    queryKey: ["assets", params],
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<Asset[]>>("/assets", { params });
      return data;
    },
  });
}

export function useAsset(assetId: string | undefined) {
  return useQuery({
    queryKey: ["assets", assetId],
    enabled: Boolean(assetId),
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<Asset>>(`/assets/${assetId}`);
      return data.data;
    },
  });
}

export interface AssetRelationship {
  id: string;
  source_asset_id: string;
  target_asset_id: string;
  relationship_type: string;
}

export function useAssetRelationships(assetId: string | undefined) {
  return useQuery({
    queryKey: ["assets", assetId, "relationships"],
    enabled: Boolean(assetId),
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<AssetRelationship[]>>(`/assets/${assetId}/relationships`);
      return data.data;
    },
  });
}

export function useCreateAssetRelationship() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { source_asset_id: string; target_asset_id: string; relationship_type: string }) => {
      const { data } = await api.post<ApiSuccess<AssetRelationship>>("/assets/relationships", input);
      return data.data;
    },
    onSuccess: (_, input) => {
      queryClient.invalidateQueries({ queryKey: ["assets", input.source_asset_id, "relationships"] });
      queryClient.invalidateQueries({ queryKey: ["assets", input.target_asset_id, "relationships"] });
      queryClient.invalidateQueries({ queryKey: ["topology"] });
    },
  });
}

export interface CreateAssetInput {
  name: string;
  hostname?: string;
  asset_type_id: string;
  vendor_id?: string;
  os_id?: string;
  location_id?: string;
  zone_id?: string;
  management_ip?: string;
  criticality?: Asset["criticality"];
  status?: Asset["status"];
  managed?: Asset["managed"];
  safe_pin?: SafePin;
  owner_id?: string;
  custodian_id?: string;
  information_classification?: InformationClassification;
  compliance_framework_codes?: string[];
  acquired_at?: string;
  warranty_expires_at?: string;
  planned_retirement_at?: string;
  decommissioned_at?: string;
  disposal_method?: string;
  disposal_notes?: string;
  risk_assessment_ref?: string;
  risk_last_reviewed_at?: string;
  backup_required?: boolean;
  backup_frequency?: BackupFrequency;
}

export function useCreateAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: CreateAssetInput) => {
      const { data } = await api.post<ApiSuccess<Asset>>("/assets", input);
      return data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets"] });
    },
  });
}

export interface AssetType {
  id: string;
  code: string;
  name: string;
  category: string | null;
}

export function useAssetTypes() {
  return useQuery({
    queryKey: ["asset-types"],
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<AssetType[]>>("/asset-types");
      return data.data;
    },
  });
}

export interface ComplianceFramework {
  id: string;
  code: string;
  name: string;
}

export function useComplianceFrameworks() {
  return useQuery({
    queryKey: ["compliance-frameworks"],
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<ComplianceFramework[]>>("/compliance-frameworks");
      return data.data;
    },
  });
}

export interface CsvImportSummary {
  created: number;
  updated: number;
  errors: { row: number; message: string }[];
}

export function useImportAssetsCsv() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post<ApiSuccess<CsvImportSummary>>("/assets/import/csv", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["assets"] }),
  });
}

export interface Vendor {
  id: string;
  name: string;
}

export function useVendors() {
  return useQuery({
    queryKey: ["vendors"],
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<Vendor[]>>("/vendors");
      return data.data;
    },
  });
}

export function useCreateVendor() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { name: string }) => {
      const { data } = await api.post<ApiSuccess<Vendor>>("/vendors", input);
      return data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["vendors"] }),
  });
}

export interface Location {
  id: string;
  name: string;
  address: string | null;
}

export function useLocations() {
  return useQuery({
    queryKey: ["locations"],
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<Location[]>>("/locations");
      return data.data;
    },
  });
}

export function useCreateLocation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { name: string; address?: string }) => {
      const { data } = await api.post<ApiSuccess<Location>>("/locations", input);
      return data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["locations"] }),
  });
}

export interface Zone {
  id: string;
  name: string;
  description: string | null;
}

export function useZones() {
  return useQuery({
    queryKey: ["zones"],
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<Zone[]>>("/zones");
      return data.data;
    },
  });
}

export function useCreateZone() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { name: string; description?: string }) => {
      const { data } = await api.post<ApiSuccess<Zone>>("/zones", input);
      return data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["zones"] }),
  });
}

export interface OperatingSystem {
  id: string;
  name: string;
  vendor_id: string | null;
}

export function useOperatingSystems() {
  return useQuery({
    queryKey: ["operating-systems"],
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<OperatingSystem[]>>("/operating-systems");
      return data.data;
    },
  });
}

export function useCreateOperatingSystem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { name: string; vendor_id?: string }) => {
      const { data } = await api.post<ApiSuccess<OperatingSystem>>("/operating-systems", input);
      return data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["operating-systems"] }),
  });
}

export function useCreateAssetType() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { code: string; name: string; category?: string }) => {
      const { data } = await api.post<ApiSuccess<AssetType>>("/asset-types", input);
      return data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["asset-types"] }),
  });
}

export async function downloadAssetsCsv(): Promise<void> {
  const response = await api.get("/assets/export/csv", { responseType: "blob" });
  const url = URL.createObjectURL(new Blob([response.data], { type: "text/csv" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "assets_export.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
