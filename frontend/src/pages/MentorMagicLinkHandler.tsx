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
      <div className="min-h-screen flex items-center justify-center bg-gray-900 text-white p-4">
        <div className="max-w-md w-full bg-gray-800 border border-red-500/30 rounded-xl p-6 text-center shadow-xl">
          <div className="w-12 h-12 rounded-full bg-red-500/10 text-red-400 flex items-center justify-center mx-auto mb-4 text-xl">
            ⚠️
          </div>
          <h2 className="text-xl font-bold text-red-400 mb-2">Access Denied</h2>
          <p className="text-gray-300 text-sm mb-6">{error}</p>
          <button
            onClick={() => navigate("/login")}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition"
          >
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900 text-white">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-gray-400 text-sm font-medium">Entering Workspace...</p>
      </div>
    </div>
  );
}
