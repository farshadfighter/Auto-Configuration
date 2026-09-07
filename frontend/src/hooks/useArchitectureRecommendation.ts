import { useMutation, useQueryClient } from "@tanstack/react-query";
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
