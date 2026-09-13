import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type ApiSuccess } from "../services/api";

export interface TopologyNode {
  id: string;
  node_type: string;
  reference_id: string | null;
  label: string;
}

export interface TopologyLink {
  id: string;
  source_node_id: string;
  destination_node_id: string;
  link_type: string | null;
  status: string;
}

export interface TopologyGraph {
  nodes: TopologyNode[];
  links: TopologyLink[];
}

export function useTopology() {
  return useQuery({
    queryKey: ["topology"],
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<TopologyGraph>>("/topology");
      return data.data;
    },
  });
}

export interface TopologyFinding {
  code: string;
  severity: string;
  node_id: string;
  message: string;
}

export function useValidateTopology() {
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<ApiSuccess<TopologyFinding[]>>("/topology/validate");
      return data.data;
    },
  });
}

export function useCreateTopologyLink() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { source_node_id: string; destination_node_id: string; link_type?: string }) => {
      const { data } = await api.post<ApiSuccess<TopologyLink>>("/topology/links", input);
      return data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["topology"] }),
  });
}

export function useUpdateTopologyLayout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (positions: { node_id: string; x: number; y: number }[]) => {
      await api.put("/topology/layout", { positions });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["topology"] }),
  });
}
