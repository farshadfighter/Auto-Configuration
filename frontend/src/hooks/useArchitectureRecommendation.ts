import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type ApiSuccess } from "../services/api";

export interface ScaleGapFinding {
  pin: string;
  pin_label: string;
  component_type: string;
  component_name: string;
  metric_pin: string;
  metric_asset_count: number;
  existing_count: number;
  required_count: number;
}

export interface LocationGapFinding {
  pin: string;
  pin_label: string;
  location_id: string;
  location_name: string;
  missing_component_type: string;
  missing_component_name: string;
}

export interface CoverageWarnings {
  unclassified_asset_count: number;
  unlocated_counts: Record<string, number>;
}

export interface SafeRecommendationResult {
  design_id: string;
  version_id: string;
  name: string;
  scale_gaps: ScaleGapFinding[];
  location_gaps: LocationGapFinding[];
  coverage_warnings: CoverageWarnings;
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
