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

export async function downloadReportCsv(name: string): Promise<void> {
  const response = await api.get(`/reports/${name}`, { params: { format: "csv" }, responseType: "blob" });
  const url = URL.createObjectURL(new Blob([response.data], { type: "text/csv" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `${name.replace(/-/g, "_")}_report.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
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
