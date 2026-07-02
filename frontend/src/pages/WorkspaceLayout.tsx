import { Link, Navigate, Outlet, useLocation } from "react-router-dom";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Logos } from "@/components/shared/Logos";
import { getRoleHome } from "@/components/shared/RequireRole";
import { useAuth } from "@/context/AuthContext";

const names: Record<string, string> = {
  "/workspace": "Workspace",
  "/workspace/tipsc": "TIPS Evaluation",
  "/workspace/dfv": "DFV Analysis",
  "/workspace/discovery": "Customer Discovery"
};

export function WorkspaceLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "student") return <Navigate to={getRoleHome(user.role)} replace />;
  return (
    <div className="min-h-screen bg-muted/50">
      <header className="sticky top-0 z-30 border-b bg-white">
        <div className="mx-auto flex min-h-16 max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-6">
            <Logos to="/workspace" />
            <p className="hidden text-sm font-semibold text-muted-foreground md:block">
              <Link to="/workspace" className="text-primary">Workspace</Link> &gt; {names[location.pathname] || "Current Page"}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden text-right text-xs sm:block">
              <p className="font-semibold">{user.name}</p>
              <p className="text-muted-foreground">{user.srn}{user.teamId ? ` · ${user.teamId}` : ""}</p>
            </div>
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-secondary font-bold text-white">{user.name.charAt(0)}</div>
            <Button variant="ghost" size="icon" onClick={() => void logout()} title="Logout"><LogOut className="h-4 w-4" /></Button>
          </div>
        </div>
      </header>
      <Outlet />
    </div>
  );
}
