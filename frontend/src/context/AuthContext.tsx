import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { clearTokens, getRefreshToken } from "@/services/apiClient";
import { login as apiLogin, logout as apiLogout } from "@/services/authSessions";
import { deriveStageAccess } from "@/hooks/useSessionStream";
import type { DFVResult, JTBDResult, StageStatus, TIPSCResult } from "@/data/mockData";
import type { Role, SessionDocument, SessionStatus } from "@/types/api";
import { registerStudentTeam, getStudents, initializeStorage } from "@/utils/adminData";

export type AppUser = { userId: string; srn: string; name: string; role: Role; teamId: string | null };
export type SessionState = { tipsc: StageStatus; dfv: StageStatus; discovery: StageStatus };
export type SessionResults = { tips: TIPSCResult | null; dfv: DFVResult | null; discovery: JTBDResult | null };
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
  sessionDoc: SessionDocument | null;
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
  const [sessionDoc, setSessionDoc] = useState<SessionDocument | null>(null);

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
    setSessionDoc(null);
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
    setSessionIdState(doc.session_id ?? (doc as any)._id ?? null);
    setServerStatus(doc.status);
    setSession(deriveStageAccess(doc.status));
    setSessionDoc(doc);

    // TIPSC result — the `tipsc` field IS the result object directly (no .output wrapper)
    if (doc.tipsc) {
      const tipsOutput = doc.tipsc as any;
      const tipsRag = tipsOutput.tips_rag_scores || {};
      const mappedTips = {
        scores: {
          timely: {
            status: (tipsRag.T || tipsOutput.scores?.timely?.status || "green").toLowerCase() as any,
            explanation: tipsRag.T_reason || tipsOutput.scores?.timely?.explanation || ""
          },
          importance: {
            status: (tipsRag.I || tipsOutput.scores?.importance?.status || "green").toLowerCase() as any,
            explanation: tipsRag.I_reason || tipsOutput.scores?.importance?.explanation || ""
          },
          profitable: {
            status: (tipsRag.P || tipsOutput.scores?.profitable?.status || "green").toLowerCase() as any,
            explanation: tipsRag.P_reason || tipsOutput.scores?.profitable?.explanation || ""
          },
          solvable: {
            status: (tipsRag.S || tipsOutput.scores?.solvable?.status || "green").toLowerCase() as any,
            explanation: tipsRag.S_reason || tipsOutput.scores?.solvable?.explanation || ""
          }
        },
        readyForDFV: tipsOutput.ready_for_dfv ?? tipsOutput.readyForDFV ?? false,
        explanation: tipsOutput.reasoning || tipsOutput.explanation || "",
        followUps: (doc.followup_history || []).map((h: any) => ({
          question: h.question,
          answer: h.answer
        }))
      };
      setResults(prev => ({ ...prev, tips: mappedTips }));
    }

    // DFV result — the `dfv` field may have .output nested or be the result directly
    if (doc.dfv) {
      const dfvResult = (doc.dfv as any).output ?? doc.dfv;
      setResults(prev => ({ ...prev, dfv: dfvResult as any }));
    }

    // Discovery result — same shape as DFV
    if (doc.discovery) {
      const discoveryResult = (doc.discovery as any).output ?? doc.discovery;
      setResults(prev => ({ ...prev, discovery: discoveryResult as any }));
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
    setSessionIdState(null);
    setServerStatus("archived");
    setSession(defaultSession);
    setResults(defaultResults);
    updateFormData({});
    setTimeline([{ label: "Session Archived", timestamp: timestamp() }]);
    setSessionDoc(null);
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
      archiveSession,
      sessionDoc
    }),
    [user, sessionId, serverStatus, session, results, formDataState, timeline, login, logout, setSessionFromServer, unlockNext, saveResults, addEvent, setFormData, setSessionId, archiveSession, sessionDoc]
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
