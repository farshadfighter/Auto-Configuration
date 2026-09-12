import { useQuery } from "@tanstack/react-query";
import { api, type ApiSuccess } from "../services/api";

export interface UserSummary {
  id: string;
  username: string;
  full_name: string | null;
}

export function useUsers() {
  return useQuery({
    queryKey: ["users"],
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<UserSummary[]>>("/users");
      return data.data;
    },
    // Listing users requires user.view, which not every role holds (e.g. a pure asset
    // operator) - fail quietly so owner/custodian pickers just don't render instead of
    // surfacing a scary error on an unrelated page.
    retry: false,
  });
}
