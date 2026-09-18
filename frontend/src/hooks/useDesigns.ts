import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type ApiSuccess } from "../services/api";

export interface DesignVersion {
  id: string;
  design_id: string;
  version_number: number;
  version_label: string;
  status: "draft" | "under_review" | "approved" | "superseded" | "archived";
  created_at: string;
}

export interface Design {
  id: string;
  name: string;
  description: string | null;
  mode: "best_practice_assisted" | "manual";
  created_at: string;
}

export interface DesignDetail extends Design {
  latest_version: DesignVersion;
}

export function useDesigns() {
  return useQuery({
    queryKey: ["designs"],
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<Design[]>>("/designs");
      return data.data;
    },
  });
}

export function useDesign(designId: string | undefined) {
  return useQuery({
    queryKey: ["designs", designId],
    enabled: Boolean(designId),
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<DesignDetail>>(`/designs/${designId}`);
      return data.data;
    },
  });
}

export function useCreateDesign() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { name: string; description?: string; mode?: string }) => {
      const { data } = await api.post<ApiSuccess<Design>>("/designs", input);
      return data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["designs"] }),
  });
}

export interface DesignComponent {
  id: string;
  component_type: string;
  technology: string | null;
  name: string;
  properties: Record<string, unknown> | null;
  position: { x: number; y: number } | null;
  asset_id: string | null;
}

export interface DesignRelationship {
  id: string;
  source_component_id: string;
  target_component_id: string;
  relationship_type: string;
  source_interface: string | null;
  target_interface: string | null;
  link_type: string | null;
  speed_mbps: number | null;
  vlan: number | null;
  subnet: string | null;
}

export function useVersionGraph(versionId: string | undefined) {
  return useQuery({
    queryKey: ["designs", "versions", versionId],
    enabled: Boolean(versionId),
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<{ components: DesignComponent[]; relationships: DesignRelationship[] }>>(
        `/designs/versions/${versionId}`,
      );
      return data.data;
    },
  });
}

export function useAddComponent(versionId: string | undefined, designId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      component_type: string;
      name: string;
      properties?: Record<string, unknown>;
      position?: { x: number; y: number };
    }) => {
      const { data } = await api.post<ApiSuccess<DesignComponent>>(`/designs/versions/${versionId}/components`, input);
      return data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["designs", "versions", versionId] });
      queryClient.invalidateQueries({ queryKey: ["designs", designId] });
    },
  });
}

export function useMapComponentToAsset(versionId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { component_id: string; asset_id: string }) => {
      await api.post(`/designs/components/${input.component_id}/map-asset`, { asset_id: input.asset_id });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["designs", "versions", versionId] }),
  });
}

export function useAddRelationship(versionId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      source_component_id: string;
      target_component_id: string;
      relationship_type: string;
      source_interface?: string;
      target_interface?: string;
      link_type?: string;
      speed_mbps?: number;
      vlan?: number;
      subnet?: string;
    }) => {
      const { data } = await api.post<ApiSuccess<DesignRelationship>>(`/designs/versions/${versionId}/relationships`, input);
      return data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["designs", "versions", versionId] }),
  });
}

export function useUpdateRelationship(versionId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      id: string;
      source_interface?: string | null;
      target_interface?: string | null;
      link_type?: string | null;
      speed_mbps?: number | null;
      vlan?: number | null;
      subnet?: string | null;
    }) => {
      const { id, ...rest } = input;
      const { data } = await api.patch<ApiSuccess<DesignRelationship>>(`/designs/relationships/${id}`, rest);
      return data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["designs", "versions", versionId] }),
  });
}

export function useApproveDesign(designId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (comment?: string) => {
      const { data } = await api.post<ApiSuccess<DesignVersion>>(`/designs/${designId}/approve`, { comment });
      return data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["designs", designId] }),
  });
}

export function useCreateNewVersion(designId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<ApiSuccess<DesignVersion>>(`/designs/${designId}/versions`);
      return data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["designs", designId] }),
  });
}
