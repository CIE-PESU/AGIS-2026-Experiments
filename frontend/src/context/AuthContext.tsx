import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { clearTokens, getRefreshToken } from "@/services/apiClient";
import { login as apiLogin, logout as apiLogout } from "@/services/authSessions";
import { deriveStageAccess } from "@/hooks/useSessionPolling";
import type { DFVResult, JTBDResult, StageStatus, TIPSResult } from "@/data/mockData";
import type { Role, SessionDocument, SessionStatus } from "@/types/api";
import { registerStudentTeam, getStudents, initializeStorage } from "@/utils/adminData";

export type AppUser = { userId: string; srn: string; name: string; role: Role; teamId: string | null };
export type SessionState = { tipsc: StageStatus; dfv: StageStatus; discovery: StageStatus };
export type SessionResults = { tips: TIPSResult | null; dfv: DFVResult | null; discovery: JTBDResult | null };
export type TimelineEvent = { label: string; timestamp: string };
export type FormDataMap = Record<string, string>;

type AuthContextValue = {
  user: AppUser | null;
  sessionId: string | null;
  serverStatus: SessionStatus | null;
  session: SessionState;
  results: SessionResults;
  formData: FormDataMap;
  timeline: TimelineEvent[];
  login: (srn: string, password: string, teamName?: string) => Promise<Role>;
  logout: () => Promise<void>;
  setSessionFromServer: (doc: SessionDocument) => void;
  unlockNext: (completed: keyof SessionState) => void;
  saveResults: <K extends keyof SessionResults>(stage: K, data: SessionResults[K]) => void;
  addEvent: (label: string) => void;
  setFormData: (data: FormDataMap) => void;
  setSessionId: (id: string | null) => void;
  archiveSession: () => void;
};

const defaultSession: SessionState = { tipsc: "available", dfv: "locked", discovery: "locked" };
const defaultResults: SessionResults = { tips: null, dfv: null, discovery: null };
const AuthContext = createContext<AuthContextValue | null>(null);

const timestamp = () =>
  new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date());

function inferMockRole(srn: string): Role {
  const value = srn.trim().toLowerCase();
  if (value.includes("admin")) return "admin";
  if (value.includes("mentor") || value.includes("@")) return "mentor";
  return "student";
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(null);
  const [sessionId, setSessionIdState] = useState<string | null>(null);
  const [serverStatus, setServerStatus] = useState<SessionStatus | null>(null);
  const [session, setSession] = useState<SessionState>(defaultSession);
  const [results, setResults] = useState<SessionResults>(defaultResults);
  const [formDataState, updateFormData] = useState<FormDataMap>({});
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);

  const addEvent = useCallback((label: string) => {
    setTimeline((events) => [...events, { label, timestamp: timestamp() }]);
  }, []);

  const resetWorkspace = useCallback(() => {
    setSessionIdState(null);
    setServerStatus(null);
    setSession(defaultSession);
    setResults(defaultResults);
    updateFormData({});
    setTimeline([]);
  }, []);

  const login = useCallback(async (srn: string, password: string, teamName?: string): Promise<Role> => {
    try {
      const data = await apiLogin(srn, password);
      let resolvedTeamId = data.user.team_id ?? null;
      if (data.role === "student") {
        if (teamName) {
          resolvedTeamId = registerStudentTeam(data.user.srn, teamName);
        } else {
          initializeStorage();
          const existingStudent = getStudents().find(s => s.srn === data.user.srn);
          if (existingStudent) {
            resolvedTeamId = existingStudent.teamId;
          }
        }
      }
      setUser({
        userId: data.user.user_id,
        srn: data.user.srn,
        name: data.user.name,
        role: data.role,
        teamId: resolvedTeamId
      });
      resetWorkspace();
      if (data.role === "student") {
        setTimeline([{ label: "Session Started", timestamp: timestamp() }]);
      }
      return data.role;
    } catch {
      // Dev fallback when backend is unavailable — role is inferred, not user-selected (rbac.md §3)
      await new Promise((resolve) => setTimeout(resolve, 400));
      const role = inferMockRole(srn);
      const cleanId = srn.trim() || "PES2UG22CS001";
      let resolvedTeamId: string | null = null;
      if (role === "student") {
        if (teamName) {
          resolvedTeamId = registerStudentTeam(cleanId, teamName);
        } else {
          initializeStorage();
          const existingStudent = getStudents().find(s => s.srn === cleanId);
          resolvedTeamId = existingStudent ? existingStudent.teamId : `team_${cleanId.slice(-3)}`;
        }
      }
      setUser({
        userId: `usr_mock_${cleanId}`,
        srn: cleanId,
        name: role === "student" ? `Student (${cleanId})` : role === "mentor" ? `Mentor (${cleanId})` : `Admin (${cleanId})`,
        role,
        teamId: resolvedTeamId
      });
      resetWorkspace();
      if (role === "student") {
        setTimeline([{ label: "Session Started", timestamp: timestamp() }]);
      }
      return role;
    }
  }, [resetWorkspace]);

  const logout = useCallback(async () => {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        await apiLogout(refreshToken);
      } catch {
        clearTokens();
      }
    } else {
      clearTokens();
    }
    setUser(null);
    resetWorkspace();
  }, [resetWorkspace]);

  const setSessionFromServer = useCallback((doc: SessionDocument) => {
    setSessionIdState(doc.session_id);
    setServerStatus(doc.status);
    setSession(deriveStageAccess(doc.status));
  }, []);

  const unlockNext = useCallback((completed: keyof SessionState) => {
    setSession((current) => {
      if (completed === "tipsc") return { ...current, tipsc: "completed", dfv: "available" };
      if (completed === "dfv") return { ...current, dfv: "completed", discovery: "available" };
      return { ...current, discovery: "completed" };
    });
  }, []);

  const saveResults = useCallback(<K extends keyof SessionResults>(stage: K, data: SessionResults[K]) => {
    setResults((current) => ({ ...current, [stage]: data }));
  }, []);

  const setFormData = useCallback((data: FormDataMap) => updateFormData(data), []);
  const setSessionId = useCallback((id: string | null) => setSessionIdState(id), []);

  const archiveSession = useCallback(() => {
    setSessionIdState(null);
    setServerStatus("archived");
    setSession(defaultSession);
    setResults(defaultResults);
    updateFormData({});
    setTimeline([{ label: "Session Archived", timestamp: timestamp() }]);
  }, []);

  const value = useMemo(
    () => ({
      user,
      sessionId,
      serverStatus,
      session,
      results,
      formData: formDataState,
      timeline,
      login,
      logout,
      setSessionFromServer,
      unlockNext,
      saveResults,
      addEvent,
      setFormData,
      setSessionId,
      archiveSession
    }),
    [user, sessionId, serverStatus, session, results, formDataState, timeline, login, logout, setSessionFromServer, unlockNext, saveResults, addEvent, setFormData, setSessionId, archiveSession]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}

/** @deprecated Use Role from @/types/api */
export type { Role };
