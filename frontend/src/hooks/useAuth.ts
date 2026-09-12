import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api, type ApiSuccess } from "../services/api";
import { useAuthStore, type CurrentUser } from "../stores/authStore";

interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export function useLogin() {
  const setTokens = useAuthStore((s) => s.setTokens);
  const setUser = useAuthStore((s) => s.setUser);
  const navigate = useNavigate();

  return useMutation({
    mutationFn: async (credentials: { username: string; password: string }) => {
      const { data } = await api.post<ApiSuccess<TokenPair>>("/auth/login", credentials);
      return data.data;
    },
    onSuccess: async (tokens) => {
      setTokens(tokens.access_token, tokens.refresh_token);
      const { data } = await api.get<ApiSuccess<CurrentUser>>("/auth/me");
      setUser(data.data);
      navigate("/dashboard");
    },
  });
}

export function useCurrentUser() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated());
  const setUser = useAuthStore((s) => s.setUser);

  return useQuery({
    queryKey: ["auth", "me"],
    enabled: isAuthenticated,
    queryFn: async () => {
      const { data } = await api.get<ApiSuccess<CurrentUser>>("/auth/me");
      setUser(data.data);
      return data.data;
    },
  });
}

export function useLogout() {
  const logout = useAuthStore((s) => s.logout);
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  return () => {
    logout();
    queryClient.clear();
    navigate("/login");
  };
}
