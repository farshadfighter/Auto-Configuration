import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type ApiSuccess } from "../services/api";

export interface Asset {
  id: string;
  asset_code: string;
  name: string;
  hostname: string | null;
  asset_type_id: string;
  management_ip: string | null;
  criticality: "low" | "medium" | "high" | "critical";
  status: "provisioning" | "active" | "inactive" | "decommissioned" | "unknown";
  managed: "managed" | "unmanaged" | "pending";
  site_id: string | null;
  environment_id: string | null;
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

export interface CreateAssetInput {
  name: string;
  hostname?: string;
  asset_type_id: string;
  management_ip?: string;
  criticality?: Asset["criticality"];
  status?: Asset["status"];
  managed?: Asset["managed"];
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
