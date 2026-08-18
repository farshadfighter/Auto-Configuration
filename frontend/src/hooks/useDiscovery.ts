import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type ApiSuccess } from "../services/api";

export type DiscoveryMethod = "manual" | "csv_import" | "api_import" | "network_scan" | "snmp" | "ssh" | "winrm";

export interface DiscoveryJob {
  id: string;
  method: DiscoveryMethod;
  status: "queued" | "running" | "partial" | "success" | "failed" | "cancelled";
  discovered_count: number;
  updated_count: number;
  failed_count: number;
  created_at: string;
}

export function useDiscoveryJobs() {
  return useQuery({
    queryKey: ["discovery", "jobs"],
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<DiscoveryJob[]>>("/discovery/jobs");
      return data.data;
    },
    refetchInterval: (query) =>
      query.state.data?.some((j) => j.status === "running" || j.status === "queued") ? 1500 : false,
  });
}

export interface DiscoveryError {
  id: string;
  message: string;
}

export function useDiscoveryErrors(jobId: string | undefined) {
  return useQuery({
    queryKey: ["discovery", "jobs", jobId, "errors"],
    enabled: Boolean(jobId),
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<DiscoveryError[]>>(`/discovery/jobs/${jobId}/errors`);
      return data.data;
    },
  });
}

export function useCreateCsvDiscoveryJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (csvContent: string) => {
      const { data } = await api.post<ApiSuccess<DiscoveryJob>>("/discovery/jobs", {
        method: "csv_import",
        scope: { csv_content: csvContent },
      });
      return data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["discovery", "jobs"] }),
  });
}
