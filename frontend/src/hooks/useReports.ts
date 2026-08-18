import { useQuery } from "@tanstack/react-query";
import { api, type ApiSuccess } from "../services/api";

function useReport<T>(name: string) {
  return useQuery({
    queryKey: ["reports", name],
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<T>>(`/reports/${name}`);
      return data.data;
    },
  });
}

export interface CountReport {
  total: number;
  [key: string]: unknown;
}

export const useAssetInventoryReport = () => useReport<CountReport>("asset-inventory");
export const useFindingsReport = () => useReport<CountReport>("architecture-findings");
export const useConfigurationJobsReport = () => useReport<CountReport>("configuration-jobs");
export const useDeploymentsReport = () => useReport<CountReport & { success_rate: number | null }>("deployments");
export const useBackupsReport = () => useReport<CountReport>("backups");
export const useDriftReport = () => useReport<CountReport>("drift");

export interface TechnologyCoverageEntry {
  technology: string;
  vendor: string;
  object_types: string[];
  deployed_asset_count: number;
}

export const useTechnologyCoverageReport = () => useReport<TechnologyCoverageEntry[]>("technology-coverage");
