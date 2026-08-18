import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type ApiSuccess } from "../services/api";

export interface ConfigurationJob {
  id: string;
  job_number: string;
  name: string;
  description: string | null;
  source_type: "design" | "manual";
  status: "draft" | "generated" | "validating" | "validated" | "pending_approval" | "approved" | "rejected" | "ready" | "failed";
  risk_level: "low" | "medium" | "high" | "critical" | null;
  justification_ref: string | null;
  created_at: string;
}

export interface ConfigurationObject {
  id: string;
  asset_id: string;
  technology: string;
  object_type: string;
  parameters: Record<string, unknown>;
  current_state: Record<string, unknown> | null;
  change_type: "create" | "update" | "delete" | "no_change" | null;
  validation_status: "pending" | "pass" | "warning" | "high" | "critical";
  validation_issues: { code: string; severity: string; field: string | null; message: string }[] | null;
  rendered_operations: { sequence: number; operation_type: string; rendered_config: string }[] | null;
}

export interface TechnologyCatalogEntry {
  technology: string;
  vendor: string;
  supported_os: string[];
  capabilities: Record<string, boolean>;
}

export function useTechnologyCatalog() {
  return useQuery({
    queryKey: ["technologies"],
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<TechnologyCatalogEntry[]>>("/technologies");
      return data.data;
    },
  });
}

export function useConfigurationJobs() {
  return useQuery({
    queryKey: ["configuration", "jobs"],
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<ConfigurationJob[]>>("/configuration/jobs");
      return data.data;
    },
  });
}

export function useConfigurationJob(jobId: string | undefined) {
  return useQuery({
    queryKey: ["configuration", "jobs", jobId],
    enabled: Boolean(jobId),
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<ConfigurationJob>>(`/configuration/jobs/${jobId}`);
      return data.data;
    },
  });
}

export function useConfigurationObjects(jobId: string | undefined) {
  return useQuery({
    queryKey: ["configuration", "jobs", jobId, "objects"],
    enabled: Boolean(jobId),
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<ConfigurationObject[]>>(`/configuration/jobs/${jobId}/objects`);
      return data.data;
    },
  });
}

export interface DiffEntry {
  object_id: string;
  object_type: string;
  technology: string;
  change_type: string | null;
  current_state: Record<string, unknown> | null;
  desired_state: Record<string, unknown>;
  diff: { field: string; before: unknown; after: unknown }[];
}

export function useConfigurationDiff(jobId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ["configuration", "jobs", jobId, "diff"],
    enabled: Boolean(jobId) && enabled,
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<DiffEntry[]>>(`/configuration/jobs/${jobId}/diff`);
      return data.data;
    },
  });
}

export function useCreateConfigurationJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { name: string; justification_ref: string; target_asset_ids?: string[] }) => {
      const { data } = await api.post<ApiSuccess<ConfigurationJob>>("/configuration/jobs", input);
      return data.data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["configuration", "jobs"] }),
  });
}

function invalidateJob(queryClient: ReturnType<typeof useQueryClient>, jobId: string) {
  queryClient.invalidateQueries({ queryKey: ["configuration", "jobs", jobId] });
  queryClient.invalidateQueries({ queryKey: ["configuration", "jobs", jobId, "objects"] });
}

export function useAddConfigurationObject(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { asset_id: string; technology: string; object_type: string; parameters: Record<string, unknown> }) => {
      const { data } = await api.post<ApiSuccess<ConfigurationObject>>(`/configuration/jobs/${jobId}/objects`, input);
      return data.data;
    },
    onSuccess: () => invalidateJob(queryClient, jobId),
  });
}

export function useGenerateJob(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<ApiSuccess<ConfigurationJob>>(`/configuration/jobs/${jobId}/generate`);
      return data.data;
    },
    onSuccess: () => invalidateJob(queryClient, jobId),
  });
}

export function useValidateJob(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<ApiSuccess<ConfigurationJob>>(`/configuration/jobs/${jobId}/validate`);
      return data.data;
    },
    onSuccess: () => invalidateJob(queryClient, jobId),
  });
}

export function useSubmitForApproval(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<ApiSuccess<ConfigurationJob>>(`/configuration/jobs/${jobId}/submit-approval`);
      return data.data;
    },
    onSuccess: () => invalidateJob(queryClient, jobId),
  });
}
