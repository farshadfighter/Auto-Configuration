import { useMutation, useQuery } from "@tanstack/react-query";
import { api, type ApiSuccess } from "../services/api";
import type { DesignVersion } from "./useDesigns";

export function useDesignVersions(designId: string | undefined) {
  return useQuery({
    queryKey: ["designs", designId, "versions"],
    enabled: Boolean(designId),
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<DesignVersion[]>>(`/designs/${designId}/versions`);
      return data.data;
    },
  });
}

export interface ComponentChange {
  name: string;
  changes: Record<string, [unknown, unknown]>;
}

export interface RelationshipChange {
  key: string;
  changes: Record<string, [unknown, unknown]>;
}

export interface DesignDiff {
  added_components: string[];
  removed_components: string[];
  changed_components: ComponentChange[];
  added_relationships: string[];
  removed_relationships: string[];
  changed_relationships: RelationshipChange[];
}

export function useCompareDesignVersions(designId: string | undefined) {
  return useMutation({
    mutationFn: async (input: { from_version_id: string; to_version_id: string }) => {
      const { data } = await api.get<ApiSuccess<DesignDiff>>(`/designs/${designId}/versions/diff`, { params: input });
      return data.data;
    },
  });
}
