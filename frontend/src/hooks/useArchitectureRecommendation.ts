import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type ApiSuccess } from "../services/api";

export interface SafeRecommendationResult {
  design_id: string;
  version_id: string;
  name: string;
}

export function useGenerateSafeRecommendation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (name: string) => {
      const { data } = await api.post<ApiSuccess<SafeRecommendationResult>>("/architecture-recommendations/safe", { name });
      return data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["designs"] });
    },
  });
}

export interface PathFinding {
  pin_a: string;
  pin_b: string;
  source_asset_id: string;
  source_asset_name: string;
  target_asset_id: string;
  target_asset_name: string;
  path_asset_ids: string[];
  path_asset_names: string[];
  protected: boolean;
  required_capability: string;
  severity: string;
}

export function useSafePathAnalysis(enabled: boolean) {
  return useQuery({
    queryKey: ["architecture-recommendations", "safe", "path-analysis"],
    enabled,
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<PathFinding[]>>("/architecture-recommendations/safe/path-analysis");
      return data.data;
    },
  });
}
