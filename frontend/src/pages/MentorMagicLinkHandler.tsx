import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { apiRequest, setAccessTokenOnly } from "@/services/apiClient";
import { useAuth } from "@/context/AuthContext";
import type { Role } from "@/types/api";

type WorkspaceAccessResponse = {
  access_token: string;
  expires_in: number;
  role: Role;
  workspace_id: string;
  name: string;
};

export function MentorMagicLinkHandler() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const auth = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function redeemToken() {
      if (!token) {
        setError("Invalid magic link URL.");
        return;
      }

      try {
        const data = await apiRequest<WorkspaceAccessResponse>("/workspace/access", {
          method: "POST",
          body: { token },
          auth: false,
        });

        if (!mounted) return;

        // Store access token
        setAccessTokenOnly(data.access_token);

        // Update user state in context
        auth.loginWithWorkspace(data.workspace_id, data.name, data.role);

        // Redirect router to clean /workspace
        navigate("/workspace", { replace: true });
      } catch (err: any) {
        if (!mounted) return;
        setError(err.message || "Failed to redeem magic link. It may be revoked or expired.");
      }
    }

    redeemToken();

    return () => {
      mounted = false;
    };
  }, [token, navigate, auth]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-muted p-4 dark:bg-background">
        <div className="max-w-md w-full bg-card border border-destructive/30 rounded-xl p-6 text-center shadow-xl">
          <div className="w-12 h-12 rounded-full bg-destructive/10 text-destructive flex items-center justify-center mx-auto mb-4 text-xl">
            ⚠️
          </div>
          <h2 className="text-xl font-bold text-destructive mb-2">Access Denied</h2>
          <p className="text-muted-foreground text-sm mb-6">{error}</p>
          <button
            onClick={() => navigate("/login")}
            className="px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-medium rounded-lg transition"
          >
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted dark:bg-background text-foreground dark:text-foreground">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
        <p className="text-muted-foreground text-sm font-medium">Entering Workspace...</p>
      </div>
    </div>
  );
}
