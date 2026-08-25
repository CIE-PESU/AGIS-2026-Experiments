import { useState, useMemo, useEffect } from "react";
import { Navigate } from "react-router-dom";
import { Plus, Trash2, Edit, Users, UserCheck, BookOpen, Layers, Settings, ShieldAlert, LogOut, Copy, Link2, RefreshCw, Ban, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { SegmentedTabs } from "@/components/ui/tabs";
import { Logos } from "@/components/shared/Logos";
import { RequireRole } from "@/components/shared/RequireRole";
import { useAuth } from "@/context/AuthContext";
import {
  getMentors,
  getTeams,
  getStudents,
  getWorkspaces,
  createWorkspace,
  revokeWorkspace,
  Student,
  Team,
  Mentor,
  AdminWorkspace
} from "@/utils/adminData";

export function AdminDashboard() {
  const { user, logout } = useAuth();
  
  const [mentors, setMentors] = useState<Mentor[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [workspaces, setWorkspaces] = useState<AdminWorkspace[]>([]);
  const [magicTokens, setMagicTokens] = useState<Record<string, string>>({});
  const [activeTab, setActiveTab] = useState("teams");

  // Dialog State: Team
  const [isTeamDialogOpen, setIsTeamDialogOpen] = useState(false);
  const [isAddTeamMode, setIsAddTeamMode] = useState(false);
  const [editingTeam, setEditingTeam] = useState<Team | null>(null);
  const [dialogTeamName, setDialogTeamName] = useState("");
  const [dialogMentorId, setDialogMentorId] = useState("");
  const [dialogTeamMembers, setDialogTeamMembers] = useState<Student[]>([]);
  const [dialogUnassignedPool, setDialogUnassignedPool] = useState<Student[]>([]);
  const [selectedStudentSRN, setSelectedStudentSRN] = useState("");

  // Dialog State: Advisor / Mentor
  const [isMentorDialogOpen, setIsMentorDialogOpen] = useState(false);
  const [isAddMentorMode, setIsAddMentorMode] = useState(false);
  const [advisorModalType, setAdvisorModalType] = useState<"faculty" | "external" | null>(null);
  const [editingMentor, setEditingMentor] = useState<Mentor | null>(null);
  const [dialogMentorName, setDialogMentorName] = useState("");
  const [dialogMentorEmail, setDialogMentorEmail] = useState("");
  const [dialogMentorPassword, setDialogMentorPassword] = useState("");
  const [dialogMentorOrganisation, setDialogMentorOrganisation] = useState("");
  const [dialogMentorRoleTitle, setDialogMentorRoleTitle] = useState("");

  // Load and refresh data
  const refreshData = async () => {
    setMentors(await getMentors());
    setTeams(await getTeams());
    setStudents(await getStudents());
    setWorkspaces(await getWorkspaces());
  };

  useEffect(() => {
    refreshData();
  }, []);

  const saveTokenCache = (wsId: string, rawToken: string) => {
    setMagicTokens(prev => ({ ...prev, [wsId]: rawToken }));
  };

  const getMentorWorkspace = (mentorName: string, mentorId?: string): AdminWorkspace | undefined => {
    return workspaces.find(w => (mentorId && w.mentor_id === mentorId) || w.name === `${mentorName}'s Workspace` || w.name === mentorName);
  };

  const handleGenerateWorkspace = async (mentorName: string, mentorId?: string) => {
    try {
      const { workspace, raw_token } = await createWorkspace(`${mentorName}'s Workspace`, mentorId);
      saveTokenCache(workspace.workspace_id, raw_token);
      await refreshData();

      const magicUrl = `${window.location.origin}/workspace/${raw_token}`;
      navigator.clipboard.writeText(magicUrl);
      toast.success("Workspace created! Magic link copied to clipboard.", {
        description: magicUrl
      });
    } catch (err: any) {
      toast.error(err.message || "Failed to generate workspace.");
    }
  };

  const handleCopyMagicLink = (workspaceId: string) => {
    const rawToken = magicTokens[workspaceId];
    if (!rawToken) {
      toast.error("Magic link token not available in session cache. Please regenerate the link.");
      return;
    }
    const magicUrl = `${window.location.origin}/workspace/${rawToken}`;
    navigator.clipboard.writeText(magicUrl);
    toast.success("Magic link copied to clipboard!");
  };

  const handleRegenerateWorkspace = async (workspaceId: string, mentorName: string, mentorId?: string) => {
    if (confirm(`Regenerate magic link for ${mentorName}? The previous magic link will be revoked immediately.`)) {
      try {
        await revokeWorkspace(workspaceId);
        const { workspace, raw_token } = await createWorkspace(`${mentorName}'s Workspace`, mentorId);
        saveTokenCache(workspace.workspace_id, raw_token);
        await refreshData();

        const magicUrl = `${window.location.origin}/workspace/${raw_token}`;
        navigator.clipboard.writeText(magicUrl);
        toast.success("New magic link generated and copied to clipboard!", {
          description: magicUrl
        });
      } catch (err: any) {
        toast.error(err.message || "Failed to regenerate workspace.");
      }
    }
  };

  const handleRevokeWorkspace = async (workspaceId: string, mentorName: string) => {
    if (confirm(`Revoke workspace access for ${mentorName}? Active mentor sessions will be logged out immediately.`)) {
      try {
        await revokeWorkspace(workspaceId);
        await refreshData();
        toast.success(`Workspace access revoked for ${mentorName}.`);
      } catch (err: any) {
        toast.error(err.message || "Failed to revoke workspace.");
      }
    }
  };

  // Calculate statistics
  const stats = useMemo(() => {
    const totalMentors = mentors.length;
    const totalTeams = teams.length;
    const totalStudents = students.length;
    const tipsComplete = students.filter(s => Object.keys(s.tips).length > 0 && Object.values(s.tips).every(t => t.status === "green")).length;
    const dfvComplete = students.filter(s => s.dfv !== "Pending").length;
    return { totalMentors, totalTeams, totalStudents, tipsComplete, dfvComplete };
  }, [mentors, teams, students]);

  // Map teams with mentor name and list of student members
  const mappedTeams = useMemo(() => {
    return teams.map(team => {
      const mentor = mentors.find(m => m.id === team.mentorId);
      const members = students.filter(s => s.teamId === team.id);
      return {
        ...team,
        mentorName: mentor ? mentor.name : "Unassigned",
        members
      };
    });
  }, [teams, mentors, students]);

  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "admin") return <Navigate to="/workspace" replace />;

  // Handler: Add Team Dialog
  const openAddTeamDialog = () => {
    setIsAddTeamMode(true);
    setEditingTeam(null);
    setDialogTeamName("");
    setDialogMentorId("unassigned");
    setDialogTeamMembers([]);
    setDialogUnassignedPool(students.filter(s => s.teamId === null));
    setSelectedStudentSRN("");
    setIsTeamDialogOpen(true);
  };

  // Handler: Edit Team Dialog
  const openEditTeamDialog = (team: Team) => {
    setIsAddTeamMode(false);
    setEditingTeam(team);
    setDialogTeamName(team.name);
    setDialogMentorId(team.mentorId || "unassigned");
    setDialogTeamMembers(students.filter(s => s.teamId === team.id));
    setDialogUnassignedPool(students.filter(s => s.teamId === null));
    setSelectedStudentSRN("");
    setIsTeamDialogOpen(true);
  };

  // Dialog Action: Remove student from team (moves to unassigned pool)
  const handleRemoveMember = (srn: string) => {
    const student = dialogTeamMembers.find(s => s.srn === srn);
    if (!student) return;
    setDialogTeamMembers(dialogTeamMembers.filter(s => s.srn !== srn));
    setDialogUnassignedPool([...dialogUnassignedPool, { ...student, teamId: null }]);
  };

  // Dialog Action: Add student to team (moves from unassigned pool)
  const handleAddMember = () => {
    if (!selectedStudentSRN) return;
    const student = dialogUnassignedPool.find(s => s.srn === selectedStudentSRN);
    if (!student) return;
    setDialogUnassignedPool(dialogUnassignedPool.filter(s => s.srn !== selectedStudentSRN));
    setDialogTeamMembers([...dialogTeamMembers, { ...student, teamId: editingTeam?.id || "temp" }]);
    setSelectedStudentSRN("");
  };

  // Dialog Save: Team
  const saveTeamChanges = async () => {
    if (!dialogTeamName.trim()) {
      toast.error("Team name is required.");
      return;
    }

    try {
      const url = isAddTeamMode ? "/api/v1/admin/teams" : `/api/v1/admin/teams/${editingTeam?.id}`;
      const method = isAddTeamMode ? "POST" : "PUT";
      
      const res = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("agis_access_token")}`
        },
        body: JSON.stringify({
          name: dialogTeamName,
          mentor_id: dialogMentorId === "unassigned" ? null : dialogMentorId,
          members: dialogTeamMembers.map(m => m.srn)
        })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Failed to save team in backend");
      }

      await refreshData();
      setIsTeamDialogOpen(false);
      toast.success(isAddTeamMode ? "Team created successfully" : "Team updated successfully");
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  // Handler: Delete Team
  const handleDeleteTeam = async (teamId: string) => {
    if (confirm("Are you sure you want to delete this team? Members will be unassigned.")) {
      try {
        const res = await fetch(`/api/v1/admin/teams/${teamId}`, {
          method: "DELETE",
          headers: { "Authorization": `Bearer ${localStorage.getItem("agis_access_token")}` }
        });
        if (!res.ok) throw new Error("Failed to delete team");
        
        await refreshData();
        toast.success("Team deleted successfully");
      } catch (err: any) {
        toast.error(err.message);
      }
    }
  };

  // Handler: Add Faculty Mentor Dialog
  const openAddFacultyMentorDialog = () => {
    setIsAddMentorMode(true);
    setAdvisorModalType("faculty");
    setEditingMentor(null);
    setDialogMentorName("");
    setDialogMentorEmail("");
    setDialogMentorPassword("");
    setDialogMentorOrganisation("PES University");
    setDialogMentorRoleTitle("Faculty Advisor");
    setIsMentorDialogOpen(true);
  };

  // Handler: Add External Reviewer Dialog
  const openAddExternalReviewerDialog = () => {
    setIsAddMentorMode(true);
    setAdvisorModalType("external");
    setEditingMentor(null);
    setDialogMentorName("");
    setDialogMentorEmail("");
    setDialogMentorPassword("");
    setDialogMentorOrganisation("");
    setDialogMentorRoleTitle("External Reviewer");
    setIsMentorDialogOpen(true);
  };

  // Handler: Edit Mentor Dialog
  const openEditMentorDialog = (mentor: Mentor) => {
    setIsAddMentorMode(false);
    const isExternal = mentor.type === "external_reviewer" || mentor.email?.endsWith("@agis.local");
    setAdvisorModalType(isExternal ? "external" : "faculty");
    setEditingMentor(mentor);
    setDialogMentorName(mentor.name);
    setDialogMentorEmail(mentor.email);
    setDialogMentorPassword("");
    setDialogMentorOrganisation(mentor.organisation || (isExternal ? "External Industry / Reviewer" : "PES University"));
    setDialogMentorRoleTitle("");
    setIsMentorDialogOpen(true);
  };

  // Dialog Save: Advisor / Mentor
  const saveMentorChanges = async () => {
    if (!dialogMentorName.trim()) {
      toast.error("Name is required.");
      return;
    }

    if (isAddMentorMode && advisorModalType === "faculty") {
      if (!dialogMentorEmail.trim() || !dialogMentorPassword.trim()) {
        toast.error("Email and Password are required for Faculty Mentors.");
        return;
      }
    }

    try {
      const url = isAddMentorMode ? "/api/v1/admin/mentors" : `/api/v1/admin/mentors/${editingMentor?.id}`;
      const method = isAddMentorMode ? "POST" : "PUT";
      
      const bodyPayload: any = {
        name: dialogMentorName.trim()
      };

      if (advisorModalType === "faculty" && dialogMentorEmail.trim()) {
        bodyPayload.email = dialogMentorEmail.trim();
        if (isAddMentorMode && dialogMentorPassword.trim()) {
          bodyPayload.password = dialogMentorPassword.trim();
        }
      }

      const res = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("agis_access_token")}`
        },
        body: JSON.stringify(bodyPayload)
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Failed to save advisor in backend");
      }

      const responseData = await res.json();

      toast.success(
        isAddMentorMode
          ? advisorModalType === "external"
            ? "External Reviewer created. Click 'Generate Link' when ready to issue an access link."
            : "Faculty Mentor created successfully"
          : "Advisor profile updated successfully"
      );

      await refreshData();
      setIsMentorDialogOpen(false);
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  // Handler: Delete Mentor / Advisor
  const handleDeleteMentor = async (mentorId: string) => {
    if (confirm("Are you sure you want to delete this advisor? Associated access links will be revoked and supervised teams unassigned.")) {
      try {
        // Revoke associated workspace if active
        const ws = workspaces.find(w => w.mentor_id === mentorId);
        if (ws && ws.status === "active") {
          try {
            await revokeWorkspace(ws.workspace_id);
          } catch (e) {
            // Best effort revocation
          }
        }

        const res = await fetch(`/api/v1/admin/mentors/${mentorId}`, {
          method: "DELETE",
          headers: { "Authorization": `Bearer ${localStorage.getItem("agis_access_token")}` }
        });
        if (!res.ok) throw new Error("Failed to delete advisor");
        
        await refreshData();
        toast.success("Advisor deleted successfully");
      } catch (err: any) {
        toast.error(err.message);
      }
    }
  };

  return (
    <RequireRole role="admin">
      <div className="min-h-screen bg-muted/50">
        <header className="border-b bg-white">
          <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between px-4">
            <Logos to="/admin" />
            <div className="flex items-center gap-4">
              <p className="text-sm font-semibold">{user.name}</p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => void logout()}
                className="flex items-center gap-1.5 text-primary border-primary/20 hover:bg-primary/5"
              >
                <LogOut className="h-4 w-4" /> Logout
              </Button>
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-7xl px-4 py-8">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold text-primary">Admin Control Center</h1>
              <p className="mt-2 text-muted-foreground">Manage mentors, teams, and member allocations.</p>
            </div>
          </div>

          {/* Statistics Grid */}
          <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-5 mt-8">
            <Card>
              <CardContent className="p-5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Mentors</p>
                  <p className="mt-2 text-3xl font-bold text-primary">{stats.totalMentors}</p>
                </div>
                <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
                  <UserCheck className="h-6 w-6" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Teams</p>
                  <p className="mt-2 text-3xl font-bold text-primary">{stats.totalTeams}</p>
                </div>
                <div className="p-2 bg-purple-50 rounded-lg text-purple-600">
                  <Layers className="h-6 w-6" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Students</p>
                  <p className="mt-2 text-3xl font-bold text-primary">{stats.totalStudents}</p>
                </div>
                <div className="p-2 bg-green-50 rounded-lg text-green-600">
                  <Users className="h-6 w-6" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">TIPSC Complete</p>
                  <p className="mt-2 text-3xl font-bold text-primary">{stats.tipsComplete}</p>
                </div>
                <div className="p-2 bg-amber-50 rounded-lg text-amber-600">
                  <BookOpen className="h-6 w-6" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">DFV Complete</p>
                  <p className="mt-2 text-3xl font-bold text-primary">{stats.dfvComplete}</p>
                </div>
                <div className="p-2 bg-emerald-50 rounded-lg text-emerald-600">
                  <ShieldAlert className="h-6 w-6" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Segmented Control for Management Area */}
          <div className="mt-8 flex justify-center md:justify-start">
            <SegmentedTabs
              className="max-w-md w-full"
              value={activeTab}
              onValueChange={setActiveTab}
              options={[
                { value: "teams", label: "Teams" },
                { value: "advisors", label: "Advisors" },
                { value: "system", label: "API Endpoints" }
              ]}
            />
          </div>

          {/* TAB: TEAMS */}
          {activeTab === "teams" && (
            <div className="mt-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-primary">Teams List</h2>
                <Button onClick={openAddTeamDialog} variant="secondary" className="flex items-center gap-1">
                  <Plus className="h-4 w-4" /> Add Team
                </Button>
              </div>

              <Card className="overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[800px] text-left text-sm">
                    <thead className="bg-muted text-xs uppercase text-muted-foreground">
                      <tr>
                        <th className="p-4">Team Name</th>
                        <th className="p-4">Mentor Assigned</th>
                        <th className="p-4">Teammates</th>
                        <th className="p-4 text-center">Progress Summary</th>
                        <th className="p-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {mappedTeams.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="p-8 text-center text-muted-foreground italic bg-white">
                            No teams created yet. Click "Add Team" to create one.
                          </td>
                        </tr>
                      ) : (
                        mappedTeams.map(t => {
                          const tipsCount = t.members.filter(s => Object.keys(s.tips).length > 0 && Object.values(s.tips).every(x => x.status === "green")).length;
                          const dfvCount = t.members.filter(s => s.dfv !== "Pending").length;
                          return (
                            <tr key={t.id} className="border-t bg-white hover:bg-slate-50/50">
                              <td className="p-4 font-semibold text-primary">{t.name}</td>
                              <td className="p-4">
                                {t.mentorName === "Unassigned" ? (
                                  <span className="text-muted-foreground italic text-xs bg-slate-100 px-2 py-1 rounded">Unassigned</span>
                                ) : (
                                  <span className="font-medium text-slate-700 bg-blue-50 text-blue-700 px-2 py-1 rounded text-xs">{t.mentorName}</span>
                                )}
                              </td>
                              <td className="p-4">
                                {t.members.length === 0 ? (
                                  <span className="text-muted-foreground italic text-xs">No members</span>
                                ) : (
                                  <div className="flex flex-wrap gap-1 max-w-sm">
                                    {t.members.map(m => (
                                      <span key={m.srn} className="bg-slate-100 border text-slate-700 text-xs px-2 py-0.5 rounded" title={m.srn}>
                                        {m.name}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </td>
                              <td className="p-4 text-center">
                                <span className="inline-flex gap-3 text-xs">
                                  <span>TIPSC: <strong className="text-emerald-700">{tipsCount}/{t.members.length}</strong></span>
                                  <span>DFV: <strong className="text-indigo-700">{dfvCount}/{t.members.length}</strong></span>
                                </span>
                              </td>
                              <td className="p-4 text-right">
                                <div className="inline-flex gap-2">
                                  <Button onClick={() => openEditTeamDialog(t)} variant="outline" size="sm" className="h-8">
                                    <Edit className="h-3.5 w-3.5" /> Edit
                                  </Button>
                                  <Button onClick={() => handleDeleteTeam(t.id)} variant="ghost" size="sm" className="h-8 text-destructive hover:bg-destructive/5 hover:text-destructive">
                                    <Trash2 className="h-3.5 w-3.5" /> Delete
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          )}

          {/* TAB: ADVISORS */}
          {(activeTab === "advisors" || activeTab === "mentors") && (
            <div className="mt-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-primary">Advisors List</h2>
                <div className="flex gap-2">
                  <Button onClick={openAddFacultyMentorDialog} variant="outline" className="flex items-center gap-1 text-indigo-700 border-indigo-200 hover:bg-indigo-50">
                    <UserCheck className="h-4 w-4" /> Add Faculty Mentor
                  </Button>
                  <Button onClick={openAddExternalReviewerDialog} variant="secondary" className="flex items-center gap-1">
                    <Plus className="h-4 w-4" /> Add External Reviewer
                  </Button>
                </div>
              </div>

              <Card className="overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[850px] text-left text-sm">
                    <thead className="bg-muted text-xs uppercase text-muted-foreground">
                      <tr>
                        <th className="p-4">Name</th>
                        <th className="p-4">Type</th>
                        <th className="p-4">Organisation</th>
                        <th className="p-4">Teams</th>
                        <th className="p-4">Access</th>
                        <th className="p-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {mentors.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="p-8 text-center text-muted-foreground italic bg-white">
                            No advisors added yet. Click "Add Faculty Mentor" or "Add External Reviewer" to invite one.
                          </td>
                        </tr>
                      ) : (
                        mentors.map(m => {
                          const isExternal = m.type === "external_reviewer";
                          const supervised = teams.filter(t => t.mentorId === m.id).map(t => t.name);
                          const ws = getMentorWorkspace(m.name, m.id);
                          const hasCachedToken = ws ? !!magicTokens[ws.workspace_id] : false;

                          return (
                            <tr key={m.id} className="border-t bg-white hover:bg-slate-50/50">
                              <td className="p-4 font-semibold text-primary">{m.name}</td>
                              <td className="p-4">
                                {isExternal ? (
                                  <span className="inline-flex items-center gap-1 font-semibold text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded text-xs">
                                    External Reviewer
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1 font-semibold text-indigo-800 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded text-xs">
                                    Faculty Mentor
                                  </span>
                                )}
                              </td>
                              <td className="p-4 text-muted-foreground text-xs">
                                {m.organisation || (isExternal ? "External Industry / Reviewer" : "PES University")}
                              </td>
                              <td className="p-4">
                                {isExternal ? (
                                  <span className="text-muted-foreground italic text-xs">—</span>
                                ) : supervised.length === 0 ? (
                                  <span className="text-muted-foreground italic text-xs">Unassigned</span>
                                ) : (
                                  <div className="flex flex-wrap gap-1 max-w-sm">
                                    {supervised.map(name => (
                                      <span key={name} className="bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs px-2 py-0.5 rounded">
                                        {name}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </td>
                              <td className="p-4">
                                {!ws ? (
                                  <span className="text-muted-foreground italic text-xs bg-slate-100 px-2 py-1 rounded">No Link Issued</span>
                                ) : ws.status === "active" ? (
                                  <span className="inline-flex items-center gap-1 font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-1 rounded text-xs">
                                    <CheckCircle2 className="h-3 w-3" /> Access Ready
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1 font-semibold text-rose-700 bg-rose-50 border border-rose-200 px-2 py-1 rounded text-xs">
                                    <Ban className="h-3 w-3" /> Access Revoked
                                  </span>
                                )}
                              </td>
                              <td className="p-4 text-right">
                                <div className="inline-flex flex-wrap justify-end gap-1.5">
                                  {!ws ? (
                                    <Button
                                      onClick={() => handleGenerateWorkspace(m.name, m.id)}
                                      variant="outline"
                                      size="sm"
                                      className="h-8 text-xs text-indigo-600 border-indigo-200 hover:bg-indigo-50"
                                    >
                                      <Link2 className="h-3.5 w-3.5 mr-1" /> Generate Link
                                    </Button>
                                  ) : ws.status === "active" ? (
                                    <>
                                      <Button
                                        onClick={() => handleCopyMagicLink(ws.workspace_id)}
                                        disabled={!hasCachedToken}
                                        variant="outline"
                                        size="sm"
                                        className="h-8 text-xs text-slate-700"
                                        title={hasCachedToken ? "Copy Magic Link" : "Regenerate link to enable direct copy"}
                                      >
                                        <Copy className="h-3.5 w-3.5 mr-1" /> Copy Link
                                      </Button>
                                      <Button
                                        onClick={() => handleRegenerateWorkspace(ws.workspace_id, m.name, m.id)}
                                        variant="outline"
                                        size="sm"
                                        className="h-8 text-xs text-amber-700 border-amber-200 hover:bg-amber-50"
                                      >
                                        <RefreshCw className="h-3.5 w-3.5 mr-1" /> Regenerate
                                      </Button>
                                      <Button
                                        onClick={() => handleRevokeWorkspace(ws.workspace_id, m.name)}
                                        variant="ghost"
                                        size="sm"
                                        className="h-8 text-xs text-destructive hover:bg-destructive/10"
                                      >
                                        <Ban className="h-3.5 w-3.5 mr-1" /> Revoke
                                      </Button>
                                    </>
                                  ) : (
                                    <Button
                                      onClick={() => handleGenerateWorkspace(m.name, m.id)}
                                      variant="outline"
                                      size="sm"
                                      className="h-8 text-xs text-indigo-600 border-indigo-200 hover:bg-indigo-50"
                                    >
                                      <RefreshCw className="h-3.5 w-3.5 mr-1" /> Regenerate
                                    </Button>
                                  )}
                                  <Button onClick={() => openEditMentorDialog(m)} variant="outline" size="sm" className="h-8">
                                    <Edit className="h-3.5 w-3.5" /> Edit
                                  </Button>
                                  <Button onClick={() => handleDeleteMentor(m.id)} variant="ghost" size="sm" className="h-8 text-destructive hover:bg-destructive/5 hover:text-destructive">
                                    <Trash2 className="h-3.5 w-3.5" /> Delete
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          )}

          {/* TAB: SYSTEM ENDPOINTS */}
          {activeTab === "system" && (
            <div className="mt-6">
              <h2 className="text-xl font-bold text-primary mb-4 font-semibold">Active Backend Endpoints</h2>
              <div className="grid gap-4 md:grid-cols-3">
                {[
                  ["All Sessions", "GET /admin/sessions"],
                  ["Audit Log", "GET /admin/audit"],
                  ["Platform Metrics", "GET /admin/metrics"]
                ].map(([title, endpoint]) => (
                  <Card key={endpoint}>
                    <CardContent className="p-5">
                      <p className="font-bold text-primary">{title}</p>
                      <p className="mt-2 text-sm text-muted-foreground bg-slate-50 border p-2 rounded font-mono select-all">
                        {endpoint}
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </main>

        {/* DIALOG: TEAM ADD / EDIT */}
        <Dialog open={isTeamDialogOpen} onOpenChange={setIsTeamDialogOpen}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle className="text-xl text-primary font-bold">
                {isAddTeamMode ? "Create New Team" : `Edit Team: ${editingTeam?.name}`}
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-4 my-2">
              {/* Field: Team Name */}
              <div>
                <label className="block text-sm font-semibold mb-1 text-slate-700">Team Name</label>
                <Input
                  value={dialogTeamName}
                  onChange={e => setDialogTeamName(e.target.value)}
                  placeholder="Enter team name (e.g. Team Gamma)"
                />
              </div>

              {/* Field: Mentor Allocation */}
              <div>
                <label className="block text-sm font-semibold mb-1 text-slate-700">Allocate Mentor</label>
                <select
                  value={dialogMentorId}
                  onChange={e => setDialogMentorId(e.target.value)}
                  className="flex h-11 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                >
                  <option value="unassigned">-- Unassigned --</option>
                  {mentors
                    .filter(m => m.type === "faculty_mentor")
                    .map(m => (
                      <option key={m.id} value={m.id}>
                        {m.name} ({m.email})
                      </option>
                    ))}
                </select>
              </div>

              {/* Field: Teammates */}
              <div className="border rounded-lg p-4 bg-slate-50/50">
                <h3 className="font-bold text-sm text-primary uppercase tracking-wider mb-2">Team Members</h3>
                
                {/* Current Members */}
                <div className="space-y-2 max-h-36 overflow-y-auto mb-3">
                  {dialogTeamMembers.length === 0 ? (
                    <p className="text-xs text-muted-foreground italic">No members assigned to this team.</p>
                  ) : (
                    dialogTeamMembers.map(m => (
                      <div key={m.srn} className="flex justify-between items-center bg-white p-2 rounded border border-slate-200 text-xs">
                        <div>
                          <span className="font-semibold text-slate-800">{m.name}</span>
                          <span className="text-muted-foreground ml-2">({m.srn})</span>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveMember(m.srn)}
                          className="h-7 text-destructive hover:bg-destructive/5 hover:text-destructive px-2"
                        >
                          Remove
                        </Button>
                      </div>
                    ))
                  )}
                </div>

                {/* Add Member Pool */}
                <div className="flex gap-2 items-end pt-3 border-t">
                  <div className="flex-1">
                    <label className="block text-xs font-semibold mb-1 text-slate-600">Add Available Student</label>
                    <select
                      value={selectedStudentSRN}
                      onChange={e => setSelectedStudentSRN(e.target.value)}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <option value="">-- Select Student --</option>
                      {dialogUnassignedPool.map(s => (
                        <option key={s.srn} value={s.srn}>
                          {s.name} ({s.srn})
                        </option>
                      ))}
                    </select>
                  </div>
                  <Button
                    type="button"
                    onClick={handleAddMember}
                    disabled={!selectedStudentSRN}
                    variant="outline"
                    className="h-10 text-xs font-semibold"
                  >
                    Add Member
                  </Button>
                </div>
              </div>
            </div>

            {/* Footer Buttons */}
            <div className="flex justify-end gap-3 pt-4 border-t mt-4">
              <Button variant="ghost" onClick={() => setIsTeamDialogOpen(false)}>
                Cancel
              </Button>
              <Button variant="secondary" onClick={saveTeamChanges}>
                {isAddTeamMode ? "Create Team" : "Save Changes"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* DIALOG: ADVISOR ADD / EDIT */}
        <Dialog open={isMentorDialogOpen} onOpenChange={setIsMentorDialogOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="text-xl text-primary font-bold">
                {!isAddMentorMode
                  ? "Edit Advisor Profile"
                  : advisorModalType === "faculty"
                  ? "Register Faculty Mentor"
                  : "Invite External Reviewer"}
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-4 my-2">
              <div>
                <label className="block text-sm font-semibold mb-1 text-slate-700">Full Name</label>
                <Input
                  value={dialogMentorName}
                  onChange={e => setDialogMentorName(e.target.value)}
                  placeholder={advisorModalType === "faculty" ? "e.g. Dr. Priya Menon" : "e.g. Alex Vance"}
                />
              </div>

              {advisorModalType === "faculty" && isAddMentorMode && (
                <>
                  <div>
                    <label className="block text-sm font-semibold mb-1 text-slate-700">Email Address</label>
                    <Input
                      type="email"
                      value={dialogMentorEmail}
                      onChange={e => setDialogMentorEmail(e.target.value)}
                      placeholder="e.g. pmenon@pes.edu"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold mb-1 text-slate-700">Password</label>
                    <Input
                      type="password"
                      value={dialogMentorPassword}
                      onChange={e => setDialogMentorPassword(e.target.value)}
                      placeholder="Enter mentor account password"
                    />
                    <p className="text-xs text-muted-foreground mt-1">Faculty mentors use their email and password to log in directly.</p>
                  </div>
                </>
              )}

              {advisorModalType === "external" && isAddMentorMode && (
                <>
                  <div>
                    <label className="block text-sm font-semibold mb-1 text-slate-700">Organisation / Affiliation</label>
                    <Input
                      value={dialogMentorOrganisation}
                      onChange={e => setDialogMentorOrganisation(e.target.value)}
                      placeholder="e.g. Sequoia Capital / Angel Investor"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold mb-1 text-slate-700">Title / Role (Optional)</label>
                    <Input
                      value={dialogMentorRoleTitle}
                      onChange={e => setDialogMentorRoleTitle(e.target.value)}
                      placeholder="e.g. Partner / Startup Coach"
                    />
                  </div>
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-900">
                    <strong>Note:</strong> External reviewers receive an isolated Access Link. No login password or institutional credentials required.
                  </div>
                </>
              )}

              {!isAddMentorMode && editingMentor && (
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-semibold text-slate-500">Advisor Type:</span>
                  {advisorModalType === "external" ? (
                    <span className="inline-flex items-center gap-1 font-semibold text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded text-xs">
                      External Reviewer (Type Locked)
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 font-semibold text-indigo-800 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded text-xs">
                      Faculty Mentor (Type Locked)
                    </span>
                  )}
                </div>
              )}

              {!isAddMentorMode && editingMentor && (() => {
                const ws = getMentorWorkspace(editingMentor.name, editingMentor.id);
                const rawToken = ws ? magicTokens[ws.workspace_id] : null;
                const magicUrl = rawToken ? `${window.location.origin}/workspace/${rawToken}` : null;

                return (
                  <div className="border rounded-lg p-4 bg-slate-50 border-slate-200 mt-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="font-bold text-xs text-primary uppercase tracking-wider">Access Capability</h3>
                      {!ws ? (
                        <span className="text-muted-foreground italic text-xs">No Link Issued</span>
                      ) : ws.status === "active" ? (
                        <span className="inline-flex items-center gap-1 font-semibold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded text-xs">
                          <CheckCircle2 className="h-3 w-3" /> Access Ready
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 font-semibold text-rose-700 bg-rose-100 px-2 py-0.5 rounded text-xs">
                          <Ban className="h-3 w-3" /> Access Revoked
                        </span>
                      )}
                    </div>

                    {!ws ? (
                      <div>
                        <p className="text-xs text-muted-foreground mb-3">No access link issued yet for this advisor.</p>
                        <Button
                          type="button"
                          onClick={() => handleGenerateWorkspace(editingMentor.name, editingMentor.id)}
                          variant="outline"
                          size="sm"
                          className="w-full text-xs text-indigo-600 border-indigo-200 bg-white hover:bg-indigo-50"
                        >
                          <Link2 className="h-3.5 w-3.5 mr-1" /> Generate Access Link
                        </Button>
                      </div>
                    ) : ws.status === "active" ? (
                      <div className="space-y-2">
                        {magicUrl ? (
                          <div>
                            <label className="block text-xs font-semibold mb-1 text-slate-600">Access Magic URL</label>
                            <div className="flex gap-1.5">
                              <Input
                                readOnly
                                value={magicUrl}
                                className="text-xs bg-white font-mono h-8 select-all"
                              />
                              <Button
                                type="button"
                                onClick={() => handleCopyMagicLink(ws.workspace_id)}
                                variant="outline"
                                size="sm"
                                className="h-8 text-xs shrink-0"
                              >
                                <Copy className="h-3.5 w-3.5 mr-1" /> Copy
                              </Button>
                            </div>
                          </div>
                        ) : (
                          <p className="text-xs text-slate-500 italic bg-amber-50 p-2 rounded border border-amber-200">
                            Access Link is Active. Regenerate link to retrieve a copyable URL.
                          </p>
                        )}

                        <div className="flex gap-2 pt-2 border-t border-slate-200">
                          <Button
                            type="button"
                            onClick={() => handleRegenerateWorkspace(ws.workspace_id, editingMentor.name, editingMentor.id)}
                            variant="outline"
                            size="sm"
                            className="flex-1 text-xs text-amber-700 border-amber-200 bg-white hover:bg-amber-50 h-8"
                          >
                            <RefreshCw className="h-3.5 w-3.5 mr-1" /> Regenerate
                          </Button>
                          <Button
                            type="button"
                            onClick={() => handleRevokeWorkspace(ws.workspace_id, editingMentor.name)}
                            variant="outline"
                            size="sm"
                            className="flex-1 text-xs text-destructive border-red-200 bg-white hover:bg-red-50 h-8"
                          >
                            <Ban className="h-3.5 w-3.5 mr-1" /> Revoke
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div>
                        <p className="text-xs text-rose-600 italic mb-2">Access link is revoked. Regenerating will issue a new active link.</p>
                        <Button
                          type="button"
                          onClick={() => handleGenerateWorkspace(editingMentor.name, editingMentor.id)}
                          variant="outline"
                          size="sm"
                          className="w-full text-xs text-indigo-600 border-indigo-200 bg-white hover:bg-indigo-50 h-8"
                        >
                          <RefreshCw className="h-3.5 w-3.5 mr-1" /> Regenerate Active Link
                        </Button>
                      </div>
                    )}
                  </div>
                );
              })()}
            </div>

            {/* Footer Buttons */}
            <div className="flex justify-end gap-3 pt-4 border-t mt-4">
              <Button variant="ghost" onClick={() => setIsMentorDialogOpen(false)}>
                Cancel
              </Button>
              <Button variant="secondary" onClick={saveMentorChanges}>
                {!isAddMentorMode
                  ? "Save Changes"
                  : advisorModalType === "faculty"
                  ? "Create Faculty Mentor"
                  : "Invite & Generate Link"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </RequireRole>
  );
}
