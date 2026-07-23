import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { clearTokens, getRefreshToken } from "@/services/apiClient";
import { login as apiLogin, logout as apiLogout, getActiveSession } from "@/services/authSessions";
import { deriveStageAccess } from "@/hooks/useSessionPolling";
import type { DFVResult, JTBDResult, StageStatus, TIPSCResult } from "@/data/mockData";
import type { Role, SessionDocument, SessionStatus } from "@/types/api";
import { getStudents } from "@/utils/adminData";
import { mapTipscOutput, mapDfvOutput, mapDiscoveryOutput } from "@/utils/mapSessionResults";

export type AppUser = { userId: string; srn: string; name: string; role: Role; teamId: string | null };
export type SessionState = { tipsc: StageStatus; dfv: StageStatus; discovery: StageStatus };
export type SessionResults = { tips: TIPSCResult | null; dfv: DFVResult | null; discovery: JTBDResult | null };
export type TimelineEvent = { label: string; timestamp: string };
export type FormDataMap = Record<string, string>;

type AuthContextValue = {
  user: AppUser | null;
  sessionId: string | null;
  serverStatus: SessionStatus | null;
  pendingQuestion: string | null;
  
  session: SessionState;
  results: SessionResults;
  formData: FormDataMap;
  timeline: TimelineEvent[];
  sessionDoc: SessionDocument | null;
  login: (srn: string, password: string) => Promise<Role>;
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
  const [user, setUser] = useState<AppUser | null>(() => {
    const saved = localStorage.getItem("appUser");
    return saved ? JSON.parse(saved) : null;
  });
  const [sessionId, setSessionIdState] = useState<string | null>(() => localStorage.getItem("appSessionId"));

  useEffect(() => {
    if (user) localStorage.setItem("appUser", JSON.stringify(user));
    else localStorage.removeItem("appUser");
  }, [user]);

  useEffect(() => {
    if (sessionId) localStorage.setItem("appSessionId", sessionId);
    else localStorage.removeItem("appSessionId");
  }, [sessionId]);

  const [serverStatus, setServerStatus] = useState<SessionStatus | null>(null);
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [session, setSession] = useState<SessionState>(defaultSession);
  const [results, setResults] = useState<SessionResults>(defaultResults);
  const [formDataState, updateFormData] = useState<FormDataMap>({});
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [sessionDoc, setSessionDoc] = useState<SessionDocument | null>(null);

  const addEvent = useCallback((label: string) => {
    setTimeline((events) => [...events, { label, timestamp: timestamp() }]);
  }, []);

  const resetWorkspace = useCallback(() => {
    setSessionIdState(null);
    setServerStatus(null);
    setPendingQuestion(null);
    setSession(defaultSession);
    setResults(defaultResults);
    updateFormData({});
    setTimeline([]);
    setSessionDoc(null);
  }, []);

  const login = useCallback(async (srn: string, password: string): Promise<Role> => {
    try {
      const data = await apiLogin(srn, password, undefined);
      let resolvedTeamId = data.user.team_id ?? null;
      if (data.role === "student") {
        if (!resolvedTeamId) {
          const allStudents = await getStudents();
          const existingStudent = allStudents.find((s: any) => s.srn === data.user.srn);
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
        try {
          const activeSession = await getActiveSession(data.user.user_id);
          if (activeSession) {
            setSessionFromServer(activeSession);
          }
        } catch {
          // Ignore, no active session or network error
        }
        setTimeline([{ label: "Session Started", timestamp: timestamp() }]);
      }
      return data.role;
    } catch (error) {
      throw error;
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
    console.log("Incoming session update:", doc.status);
    setSessionIdState(doc.session_id ?? (doc as any)._id ?? null);
    setServerStatus(doc.status);
    setPendingQuestion(doc.pending_question ?? null);
    setSession(deriveStageAccess(doc));
    setSessionDoc(doc);

    if (doc.tipsc) {
      const tipscData = doc.tipsc;
      setResults(prev => ({ ...prev, tips: mapTipscOutput(tipscData) }));
    }
    if (doc.dfv) {
      const dfvData = doc.dfv;
      setResults(prev => ({ ...prev, dfv: mapDfvOutput(dfvData) }));
    }
    if (doc.discovery) {
      const discoveryData = doc.discovery;
      setResults(prev => ({ ...prev, discovery: mapDiscoveryOutput(discoveryData) }));
    }
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
  localStorage.removeItem("appSessionId");

  setSessionIdState(null);
  setServerStatus(null);
  setPendingQuestion(null);
  setSession(defaultSession);
  setResults(defaultResults);
  updateFormData({});
  setTimeline([]);
  setSessionDoc(null);
}, []);

  const value = useMemo(
    () => ({
      user, sessionId, serverStatus, pendingQuestion, session, results,
      formData: formDataState, timeline, sessionDoc,
      login, logout, setSessionFromServer, unlockNext, saveResults,
      addEvent, setFormData, setSessionId, archiveSession
    }),
    [user, sessionId, serverStatus, pendingQuestion, session, results, formDataState, timeline, sessionDoc, login, logout, setSessionFromServer, unlockNext, saveResults, addEvent, setFormData, setSessionId, archiveSession]
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