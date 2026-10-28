import { apiFetch } from "@/services/apiClient";

export interface Student {
  srn: string;
  name: string;
  email?: string;
  tips: Record<string, { status: "green" | "yellow" | "red"; explanation: string }>;
  dfv: string; // "GO", "NO-GO", "Pending"
  jtbd: boolean;
  lastActive: string;
  teamId: string | null;
  sessionId?: string | null;
  status?: string;
}

export interface Team {
  id: string;
  name: string;
  mentorId: string | null;
}

/**
 * Phase 1 advisor categories.
 *
 * ARCHITECTURAL GUARDRAIL:
 * Do NOT extend this union with additional participant types
 * (e.g. Judge, Investor, Coach, Alumni, etc.).
 *
 * If AGIS requires more than these two categories,
 * migrate to the planned People → Roles → Capabilities model
 * rather than extending this enum.
 *
 * TODO (Phase 2): Replace AdvisorType with Person + Role assignments
 * once AGIS supports more than two participant categories.
 */
export type AdvisorType = "faculty_mentor" | "external_reviewer";

export interface Mentor {
  id: string;
  srn?: string;
  name: string;
  email: string;
  type: AdvisorType;
  organisation?: string;
}

export interface AdminWorkspace {
  workspace_id: string;
  name: string;
  type: string;
  status: "active" | "revoked";
  mentor_id?: string;
  created_at: string;
  revoked_at?: string | null;
}

export async function getWorkspaces(): Promise<AdminWorkspace[]> {
  const res = await apiFetch("/admin/workspaces", {});
  const data = await res.json();
  return data.data || [];
}

export async function createWorkspace(name: string, mentorId?: string): Promise<{ workspace: AdminWorkspace; raw_token: string }> {
  const res = await apiFetch("/admin/workspaces", {
    method: "POST",
    body: { name, mentor_id: mentorId }
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error?.message || err.detail || "Failed to create workspace");
  }
  const data = await res.json();
  return {
    workspace: data.data,
    raw_token: data.meta?.raw_token
  };
}

export async function revokeWorkspace(workspaceId: string): Promise<AdminWorkspace> {
  const res = await apiFetch(`/admin/workspaces/${workspaceId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error?.message || err.detail || "Failed to revoke workspace");
  }
  const data = await res.json();
  return data.data;
}

export async function getMentors(): Promise<Mentor[]> {
  const res = await apiFetch("/admin/mentors", {});
  const data = await res.json();
  return data.data.map((m: any) => {
    const isExternal = m.type === "external_reviewer" || m.email?.endsWith("@agis.local");
    return {
      id: m._id || m.id,
      srn: m.srn,
      name: m.name,
      email: m.email,
      type: isExternal ? "external_reviewer" : "faculty_mentor",
      organisation: m.organisation || (isExternal ? "External Industry / Reviewer" : "PES University")
    };
  });
}

export async function getTeams(): Promise<Team[]> {
  const res = await apiFetch("/admin/teams", {});
  const data = await res.json();
  return data.data.map((t: any) => ({
    id: t._id || t.id,
    name: t.team_name,
    mentorId: t.mentor_id || null
  }));
}

export async function getStudents(): Promise<Student[]> {
  const res = await apiFetch("/admin/students", {});
  const data = await res.json();
  const mapTips = (tips: any) => {
    if (!tips || Object.keys(tips).length === 0) return {};
    return {
      timely: { status: tips.T || "yellow", explanation: tips.T_reason || "" },
      importance: { status: tips.IMPORTANT || tips.I || "yellow", explanation: tips.IMPORTANT_reason || tips.I_reason || "" },
      profitable: { status: tips.P || "yellow", explanation: tips.P_reason || "" },
      solvable: { status: tips.S || "yellow", explanation: tips.S_reason || "" }
    };
  };

  return data.data.map((s: any) => ({
    srn: s.srn,
    name: s.name,
    email: s.email,
    tips: mapTips(s.tips),
    dfv: s.dfv || "Pending",
    jtbd: false,
    lastActive: "Just now",
    teamId: s.team_id || null,
    sessionId: s.session_id || null,
    status: s.status
  }));
}

export async function getTeamsWithMembers() {
  const teams = await getTeams();
  const students = await getStudents();
  const mentors = await getMentors();

  return teams.map((team) => ({
    ...team,
    mentorName: mentors.find((m) => m.id === team.mentorId)?.name || "Unassigned",
    members: students.filter((student) => student.teamId === team.id)
  }));
}

export interface Comment {
  sender: string;
  message: string;
  timestamp: string;
}

export async function getComments(sessionId: string): Promise<Comment[]> {
  const res = await apiFetch(`/sessions/${sessionId}/comments`, {});
  const data = await res.json();
  return data.map((c: any) => ({
    sender: c.mentor_name,
    message: c.comment,
    timestamp: new Date(c.created_at).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" })
  }));
}

export async function addComment(sessionId: string, text: string) {
  const res = await apiFetch(`/sessions/${sessionId}/comments`, {
    method: "POST",
    body: { comment: text }
  });
  if (!res.ok) {
    const err = await res.json();
    let msg = "Failed to add comment";
    if (err.error) msg = err.error;
    else if (err.detail && Array.isArray(err.detail)) msg = err.detail[0]?.msg || msg;
    throw new Error(msg);
  }
}

