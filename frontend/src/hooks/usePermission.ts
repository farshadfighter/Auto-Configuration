import { useAuthStore } from "../stores/authStore";

/** Mirrors the backend's require_permission check for conditionally rendering UI. The
 * server remains the source of truth - this only avoids showing actions the user can't use. */
export function useHasPermission(code: string): boolean {
  const user = useAuthStore((s) => s.user);
  if (!user) return false;
  if (user.is_superuser) return true;
  return user.roles.some((role) => role.permissions.some((p) => p.code === code));
}
