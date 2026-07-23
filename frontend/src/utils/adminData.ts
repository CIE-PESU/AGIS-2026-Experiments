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

export interface Mentor {
  id: string;
  srn?: string;
  name: string;
  email: string;
}

const getAuthHeaders = () => ({
  "Content-Type": "application/json",
  "Authorization": `Bearer ${localStorage.getItem("agis_access_token")}`
});

export async function getMentors(): Promise<Mentor[]> {
  const res = await fetch("/api/v1/admin/mentors", { headers: getAuthHeaders() });
  if (!res.ok) return [];
  const data = await res.json();
  return data.data.map((m: any) => ({
    id: m._id || m.id,
    srn: m.srn,
    name: m.name,
    email: m.email
  }));
}

export async function getTeams(): Promise<Team[]> {
  const res = await fetch("/api/v1/admin/teams", { headers: getAuthHeaders() });
  if (!res.ok) return [];
  const data = await res.json();
  return data.data.map((t: any) => ({
    id: t._id || t.id,
    name: t.team_name,
    mentorId: t.mentor_id || null
  }));
}

export async function getStudents(): Promise<Student[]> {
  const res = await fetch("/api/v1/admin/students", { headers: getAuthHeaders() });
  if (!res.ok) return [];
  const data = await res.json();
  const mapTips = (tips: any) => {
    if (!tips || Object.keys(tips).length === 0) return {};
    return {
      timely: { status: tips.T || "yellow", explanation: tips.T_reason || "" },
      importance: { status: tips.I || "yellow", explanation: tips.I_reason || "" },
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
  const res = await fetch(`/api/v1/sessions/${sessionId}/comments`, { headers: getAuthHeaders() });
  if (!res.ok) return [];
  const data = await res.json();
  return data.map((c: any) => ({
    sender: c.mentor_name,
    message: c.comment,
    timestamp: new Date(c.created_at).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" })
  }));
}

export async function addComment(sessionId: string, text: string) {
  const res = await fetch(`/api/v1/sessions/${sessionId}/comments`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ comment: text })
  });
  if (!res.ok) {
    const err = await res.json();
    let msg = "Failed to add comment";
    if (err.error) msg = err.error;
    else if (err.detail && Array.isArray(err.detail)) msg = err.detail[0]?.msg || msg;
    throw new Error(msg);
  }
}

