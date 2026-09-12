import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type ApiSuccess } from "../services/api";

export interface Backup {
  id: string;
  asset_id: string;
  technology: string;
  backup_type: "manual" | "scheduled" | "pre_deployment" | "post_deployment";
  checksum: string;
  size_bytes: number;
  created_at: string;
}

export function useAssetBackups(assetId: string | undefined) {
  return useQuery({
    queryKey: ["backups", "asset", assetId],
    enabled: Boolean(assetId),
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<Backup[]>>(`/assets/${assetId}/backups`);
      return data.data;
    },
  });
}

export function useCreateBackup(assetId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { technology: string; content?: string }) => {
      const { data } = await api.post<ApiSuccess<Backup>>(`/assets/${assetId}/backups`, input);
      return data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["backups", "asset", assetId] }),
  });
}
