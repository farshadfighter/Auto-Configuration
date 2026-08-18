import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type ApiSuccess } from "../services/api";

export interface DeploymentJob {
  id: string;
  configuration_job_id: string;
  status:
    | "queued"
    | "precheck"
    | "precheck_failed"
    | "backup"
    | "backup_failed"
    | "applying"
    | "apply_failed"
    | "verifying"
    | "verify_failed"
    | "success"
    | "rolling_back"
    | "rolled_back"
    | "rollback_failed";
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

const TERMINAL_STATUSES = new Set(["success", "precheck_failed", "backup_failed", "verify_failed", "rolled_back", "rollback_failed"]);

export function useDeploymentJobs() {
  return useQuery({
    queryKey: ["deployment", "jobs"],
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<DeploymentJob[]>>("/deployment/jobs");
      return data.data;
    },
  });
}

export function useDeploymentJob(deploymentId: string | undefined) {
  return useQuery({
    queryKey: ["deployment", "jobs", deploymentId],
    enabled: Boolean(deploymentId),
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<DeploymentJob>>(`/deployment/jobs/${deploymentId}`);
      return data.data;
    },
    refetchInterval: (query) => (query.state.data && !TERMINAL_STATUSES.has(query.state.data.status) ? 1500 : false),
  });
}

export interface DeploymentEvent {
  id: string;
  event_type: string;
  message: string;
  created_at: string;
}

export function useDeploymentEvents(deploymentId: string | undefined) {
  return useQuery({
    queryKey: ["deployment", "jobs", deploymentId, "events"],
    enabled: Boolean(deploymentId),
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<DeploymentEvent[]>>(`/deployment/jobs/${deploymentId}/events`);
      return data.data;
    },
    refetchInterval: 1500,
  });
}

export interface DeploymentResult {
  id: string;
  configuration_object_id: string;
  asset_id: string;
  success: boolean;
  output: string | null;
  error: string | null;
  verified: boolean | null;
}

export function useDeploymentResults(deploymentId: string | undefined) {
  return useQuery({
    queryKey: ["deployment", "jobs", deploymentId, "results"],
    enabled: Boolean(deploymentId),
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<DeploymentResult[]>>(`/deployment/jobs/${deploymentId}/results`);
      return data.data;
    },
  });
}

export function useCreateDeployment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (configurationJobId: string) => {
      const { data } = await api.post<ApiSuccess<DeploymentJob>>("/deployment/jobs", { configuration_job_id: configurationJobId });
      return data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["deployment", "jobs"] }),
  });
}

export function useStartDeployment(deploymentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<ApiSuccess<DeploymentJob>>(`/deployment/jobs/${deploymentId}/start`);
      return data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["deployment", "jobs", deploymentId] }),
  });
}
