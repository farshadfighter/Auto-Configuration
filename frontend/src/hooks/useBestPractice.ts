import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type ApiSuccess } from "../services/api";

export type FindingSeverity = "info" | "low" | "medium" | "high" | "critical";
export type FindingStatus = "new" | "in_review" | "accepted" | "ignored" | "remediated" | "closed";

export interface ArchitectureFinding {
  id: string;
  finding_code: string;
  rule_code: string;
  title: string;
  technology: string;
  category: string;
  severity: FindingSeverity;
  status: FindingStatus;
  recommendation: string | null;
  ignore_reason: string | null;
  detected_at: string;
  affected_asset_ids: string[];
}

export function useFindings(statusFilter?: string) {
  return useQuery({
    queryKey: ["best-practice", "findings", statusFilter],
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<ArchitectureFinding[]>>("/best-practice/findings", {
        params: statusFilter ? { status_filter: statusFilter } : undefined,
      });
      return data.data;
    },
  });
}

export function useRunAnalysis() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post("/best-practice/analyze");
      return data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["best-practice", "findings"] }),
  });
}

export function useAcceptFinding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/best-practice/findings/${id}/accept`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["best-practice", "findings"] }),
  });
}

export function useIgnoreFinding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, reason }: { id: string; reason: string }) => {
      await api.post(`/best-practice/findings/${id}/ignore`, { reason });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["best-practice", "findings"] }),
  });
}
