import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type ApiSuccess } from "../services/api";
import type { DesignDetail } from "./useDesigns";

export interface DesignTemplate {
  code: string;
  name: string;
  description: string;
  category: string;
  component_count: number;
  relationship_count: number;
}

export function useDesignTemplates() {
  return useQuery({
    queryKey: ["design-templates"],
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<DesignTemplate[]>>("/design-templates");
      return data.data;
    },
  });
}

export function useCreateDesignFromTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { template_code: string; name: string; description?: string }) => {
      const { data } = await api.post<ApiSuccess<DesignDetail>>("/designs/from-template", input);
      return data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["designs"] }),
  });
}
