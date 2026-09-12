import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type ApiSuccess } from "../services/api";

export interface DriftFinding {
  id: string;
  asset_id: string;
  technology: string;
  object_type: string;
  expected_state: Record<string, unknown>;
  actual_state: Record<string, unknown>;
  diff: { field: string; before: unknown; after: unknown }[];
  severity: "low" | "medium" | "high";
  status: "new" | "accepted" | "ignored" | "remediated";
  detected_at: string;
}

export function useDriftFindings(status?: string) {
  return useQuery({
    queryKey: ["drift", "findings", status],
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<DriftFinding[]>>("/drift/findings", {
        params: status ? { status_filter: status } : undefined,
      });
      return data.data;
    },
  });
}

export function useRunDriftAnalysis() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post("/drift/analyze");
      return data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["drift", "findings"] }),
  });
}

export function useAcceptDriftCurrent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/drift/findings/${id}/accept-current`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["drift", "findings"] }),
  });
}

export function useIgnoreDrift() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reason }: { id: string; reason: string }) => {
      await api.post(`/drift/findings/${id}/ignore`, { reason });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["drift", "findings"] }),
  });
}

export function useRestoreDesired() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post<ApiSuccess<{ configuration_job_id: string }>>(`/drift/findings/${id}/restore-desired`);
      return data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["drift", "findings"] }),
  });
}
