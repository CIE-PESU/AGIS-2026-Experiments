import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "@/context/AuthContext";
import { AdminDashboard } from "@/pages/AdminDashboard";
import { LandingPage } from "@/pages/LandingPage";
import { Login } from "@/pages/Login";
import { WorkspaceLayout } from "@/pages/WorkspaceLayout";
import { StudentWorkspace } from "@/pages/StudentWorkspace";
import { TIPSCFlow } from "@/pages/TIPSCFlow";
import { DFVFlow } from "@/pages/DFVFlow";
import { DiscoveryFlow } from "@/pages/DiscoveryFlow";
import { MentorDashboard } from "@/pages/MentorDashboard";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<Login />} />
          <Route path="/workspace" element={<WorkspaceLayout />}>
            <Route index element={<StudentWorkspace />} />
            <Route path="tipsc" element={<TIPSCFlow />} />
            <Route path="dfv" element={<DFVFlow />} />
            <Route path="discovery" element={<DiscoveryFlow />} />
            <Route path="jtbd" element={<Navigate to="/workspace/discovery" replace />} />
          </Route>
          <Route path="/mentor" element={<MentorDashboard />} />
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <Toaster richColors position="top-right" />
      </AuthProvider>
    </BrowserRouter>
  );
}
