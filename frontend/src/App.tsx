import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "@/context/AuthContext";
const AdminDashboard = lazy(() => import("@/pages/AdminDashboard").then(m => ({ default: m.AdminDashboard })));
const LandingPage = lazy(() => import("@/pages/LandingPage").then(m => ({ default: m.LandingPage })));
const Login = lazy(() => import("@/pages/Login").then(m => ({ default: m.Login })));
const WorkspaceLayout = lazy(() => import("@/pages/WorkspaceLayout").then(m => ({ default: m.WorkspaceLayout })));
const StudentWorkspace = lazy(() => import("@/pages/StudentWorkspace").then(m => ({ default: m.StudentWorkspace })));
const TIPSCFlow = lazy(() => import("@/pages/TIPSCFlow").then(m => ({ default: m.TIPSCFlow })));
const DFVFlow = lazy(() => import("@/pages/DFVFlow").then(m => ({ default: m.DFVFlow })));
const DiscoveryFlow = lazy(() => import("@/pages/DiscoveryFlow").then(m => ({ default: m.DiscoveryFlow })));
const MentorDashboard = lazy(() => import("@/pages/MentorDashboard").then(m => ({ default: m.MentorDashboard })));
const MentorMagicLinkHandler = lazy(() => import("@/pages/MentorMagicLinkHandler").then(m => ({ default: m.MentorMagicLinkHandler })));
const QuickstartFlow = lazy(() => import("@/pages/QuickstartFlow").then(m => ({ default: m.QuickstartFlow })));

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Suspense fallback={<div role="status" className="p-8">Loading…</div>}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<Login />} />
          <Route path="/workspace/:token" element={<MentorMagicLinkHandler />} />
          <Route path="/workspace" element={<WorkspaceLayout />}>
            <Route index element={<StudentWorkspace />} />
            <Route path="tipsc" element={<TIPSCFlow />} />
            <Route path="dfv" element={<DFVFlow />} />
            <Route path="discovery" element={<DiscoveryFlow />} />
            <Route path="jtbd" element={<Navigate to="/workspace/discovery" replace />} />
          </Route>
          <Route path="/quickstart" element={<QuickstartFlow />} />
          <Route path="/mentor" element={<MentorDashboard />} />
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        </Suspense>
        <Toaster richColors position="top-right" />
      </AuthProvider>
    </BrowserRouter>
  );
}
