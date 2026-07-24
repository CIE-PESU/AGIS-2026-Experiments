import { Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import type { Role } from "@/types/api";

const roleHome: Record<Role, string> = {
  student: "/workspace",
  mentor: "/mentor",
  admin: "/admin"
};

export function RequireRole({ role, children }: { role: Role | Role[]; children: React.ReactNode }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  const allowed = Array.isArray(role) ? role : [role];
  if (!allowed.includes(user.role)) return <Navigate to={roleHome[user.role]} replace />;
  return <>{children}</>;
}

export function getRoleHome(role: Role) {
  return roleHome[role];
}
