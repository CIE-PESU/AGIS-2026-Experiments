import { Navigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Logos } from "@/components/shared/Logos";
import { RequireRole } from "@/components/shared/RequireRole";
import { useAuth } from "@/context/AuthContext";

export function AdminDashboard() {
  const { user, logout } = useAuth();
  if (!user) return <Navigate to="/login" replace />;

  return (
    <RequireRole role="admin">
      <div className="min-h-screen bg-muted/50">
        <header className="border-b bg-white">
          <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between px-4">
            <Logos to="/admin" />
            <div className="flex items-center gap-3">
              <p className="text-sm font-semibold">{user.name}</p>
              <button className="text-sm text-primary underline" onClick={() => void logout()}>Logout</button>
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-8">
          <h1 className="text-3xl font-bold text-primary">Admin Dashboard</h1>
          <p className="mt-2 text-muted-foreground">Operational oversight via GET /admin/sessions, /admin/audit, and /admin/metrics.</p>
          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {[
              ["All Sessions", "GET /admin/sessions"],
              ["Audit Log", "GET /admin/audit"],
              ["Platform Metrics", "GET /admin/metrics"]
            ].map(([title, endpoint]) => (
              <Card key={endpoint}>
                <CardContent className="p-5">
                  <p className="font-bold">{title}</p>
                  <p className="mt-2 text-sm text-muted-foreground">{endpoint}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </main>
      </div>
    </RequireRole>
  );
}
