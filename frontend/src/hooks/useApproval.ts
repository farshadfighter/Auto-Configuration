import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type ApiSuccess } from "../services/api";

export interface ApprovalRequest {
  id: string;
  configuration_job_id: string;
  status: "pending" | "approved" | "rejected";
  risk_level: string;
  required_approvals: number;
  created_at: string;
}

export function useApprovalRequests(statusFilter?: string) {
  return useQuery({
    queryKey: ["approval", "requests", statusFilter],
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<ApprovalRequest[]>>("/approval/requests", {
        params: statusFilter ? { status_filter: statusFilter } : undefined,
      });
      return data.data;
    },
  });
}

export function useApprovalRequestForJob(jobId: string | undefined) {
  return useQuery({
    queryKey: ["approval", "requests", "job", jobId],
    enabled: Boolean(jobId),
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<ApprovalRequest[]>>("/approval/requests");
      return data.data.find((r) => r.configuration_job_id === jobId) ?? null;
    },
  });
}

export function useApproveRequest(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ requestId, comment }: { requestId: string; comment?: string }) => {
      await api.post(`/approval/requests/${requestId}/approve`, { comment });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approval", "requests", "job", jobId] });
      queryClient.invalidateQueries({ queryKey: ["configuration", "jobs", jobId] });
      queryClient.invalidateQueries({ queryKey: ["configuration", "jobs"] });
    },
  });
}

export function useRejectRequest(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ requestId, comment }: { requestId: string; comment: string }) => {
      await api.post(`/approval/requests/${requestId}/reject`, { comment });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approval", "requests", "job", jobId] });
      queryClient.invalidateQueries({ queryKey: ["configuration", "jobs", jobId] });
      queryClient.invalidateQueries({ queryKey: ["configuration", "jobs"] });
    },
  });
}
