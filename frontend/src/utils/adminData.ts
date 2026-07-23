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
  return data.data.map((s: any) => ({
    srn: s.srn,
    name: s.name,
    email: s.email,
    tips: {}, // Need real session logic
    dfv: "Pending", // Need real session logic
    jtbd: false,
    lastActive: "Just now",
    teamId: s.team_id || null
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

export function getComments(srn: string): Comment[] {
  const all = JSON.parse(localStorage.getItem("admin_comments") || "{}");
  return all[srn] || [];
}

export function addComment(srn: string, comment: Comment) {
  const all = JSON.parse(localStorage.getItem("admin_comments") || "{}");
  if (!all[srn]) all[srn] = [];
  all[srn].push(comment);
  localStorage.setItem("admin_comments", JSON.stringify(all));
}

