import { useState, useMemo, useEffect } from "react";
import { Navigate } from "react-router-dom";
import { Plus, Trash2, Edit, Users, UserCheck, BookOpen, Layers, Settings, ShieldAlert, LogOut } from "lucide-react";
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
  saveMentors,
  getTeams,
  saveTeams,
  getStudents,
  saveStudents,
  Student,
  Team,
  Mentor
} from "@/utils/adminData";

export function AdminDashboard() {
  const { user, logout } = useAuth();
  
  const [mentors, setMentors] = useState<Mentor[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
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

  // Dialog State: Mentor
  const [isMentorDialogOpen, setIsMentorDialogOpen] = useState(false);
  const [isAddMentorMode, setIsAddMentorMode] = useState(false);
  const [editingMentor, setEditingMentor] = useState<Mentor | null>(null);
  const [dialogMentorName, setDialogMentorName] = useState("");
  const [dialogMentorEmail, setDialogMentorEmail] = useState("");

  // Load and refresh data
  const refreshData = () => {
    setMentors(getMentors());
    setTeams(getTeams());
    setStudents(getStudents());
  };

  useEffect(() => {
    refreshData();
  }, []);

  // Calculate statistics
  const stats = useMemo(() => {
    const totalMentors = mentors.length;
    const totalTeams = teams.length;
    const totalStudents = students.length;
    const tipsComplete = students.filter(s => Object.values(s.tips).every(t => t.status === "green")).length;
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
  const saveTeamChanges = () => {
    if (!dialogTeamName.trim()) {
      toast.error("Team name is required.");
      return;
    }

    let teamId = editingTeam?.id;
    let updatedTeams = [...teams];

    if (isAddTeamMode) {
      teamId = "team_" + Date.now();
      updatedTeams.push({
        id: teamId,
        name: dialogTeamName,
        mentorId: dialogMentorId === "unassigned" ? null : dialogMentorId
      });
    } else if (teamId) {
      updatedTeams = updatedTeams.map(t => t.id === teamId ? {
        ...t,
        name: dialogTeamName,
        mentorId: dialogMentorId === "unassigned" ? null : dialogMentorId
      } : t);
    }

    // Assign teamId to members, clear teamId for unassigned
    const updatedStudents = students.map(s => {
      if (dialogTeamMembers.some(m => m.srn === s.srn)) {
        return { ...s, teamId: teamId || null };
      }
      if (s.teamId === teamId && !dialogTeamMembers.some(m => m.srn === s.srn)) {
        return { ...s, teamId: null };
      }
      return s;
    });

    saveTeams(updatedTeams);
    saveStudents(updatedStudents);
    refreshData();
    setIsTeamDialogOpen(false);
    toast.success(isAddTeamMode ? "Team created successfully" : "Team updated successfully");
  };

  // Handler: Delete Team
  const handleDeleteTeam = (teamId: string) => {
    if (confirm("Are you sure you want to delete this team? Members will be unassigned.")) {
      const updatedTeams = teams.filter(t => t.id !== teamId);
      const updatedStudents = students.map(s => s.teamId === teamId ? { ...s, teamId: null } : s);
      saveTeams(updatedTeams);
      saveStudents(updatedStudents);
      refreshData();
      toast.success("Team deleted successfully");
    }
  };

  // Handler: Add Mentor Dialog
  const openAddMentorDialog = () => {
    setIsAddMentorMode(true);
    setEditingMentor(null);
    setDialogMentorName("");
    setDialogMentorEmail("");
    setIsMentorDialogOpen(true);
  };

  // Handler: Edit Mentor Dialog
  const openEditMentorDialog = (mentor: Mentor) => {
    setIsAddMentorMode(false);
    setEditingMentor(mentor);
    setDialogMentorName(mentor.name);
    setDialogMentorEmail(mentor.email);
    setIsMentorDialogOpen(true);
  };

  // Dialog Save: Mentor
  const saveMentorChanges = () => {
    if (!dialogMentorName.trim() || !dialogMentorEmail.trim()) {
      toast.error("Name and Email are required.");
      return;
    }

    let updatedMentors = [...mentors];
    if (isAddMentorMode) {
      const mentorId = "mentor_" + Date.now();
      updatedMentors.push({ id: mentorId, name: dialogMentorName, email: dialogMentorEmail });
    } else if (editingMentor) {
      updatedMentors = updatedMentors.map(m => m.id === editingMentor.id ? {
        ...m,
        name: dialogMentorName,
        email: dialogMentorEmail
      } : m);
    }

    saveMentors(updatedMentors);
    refreshData();
    setIsMentorDialogOpen(false);
    toast.success(isAddMentorMode ? "Mentor added successfully" : "Mentor updated successfully");
  };

  // Handler: Delete Mentor
  const handleDeleteMentor = (mentorId: string) => {
    if (confirm("Are you sure you want to delete this mentor? Supervised teams will be unassigned.")) {
      const updatedMentors = mentors.filter(m => m.id !== mentorId);
      const updatedTeams = teams.map(t => t.mentorId === mentorId ? { ...t, mentorId: null } : t);
      saveMentors(updatedMentors);
      saveTeams(updatedTeams);
      refreshData();
      toast.success("Mentor deleted successfully");
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
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">TIPS Complete</p>
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
                { value: "mentors", label: "Mentors" },
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
                          const tipsCount = t.members.filter(s => Object.values(s.tips).every(x => x.status === "green")).length;
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
                                  <span>TIPS: <strong className="text-emerald-700">{tipsCount}/{t.members.length}</strong></span>
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

          {/* TAB: MENTORS */}
          {activeTab === "mentors" && (
            <div className="mt-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-primary">Mentors List</h2>
                <Button onClick={openAddMentorDialog} variant="secondary" className="flex items-center gap-1">
                  <Plus className="h-4 w-4" /> Add Mentor
                </Button>
              </div>

              <Card className="overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[700px] text-left text-sm">
                    <thead className="bg-muted text-xs uppercase text-muted-foreground">
                      <tr>
                        <th className="p-4">Mentor Name</th>
                        <th className="p-4">Email</th>
                        <th className="p-4">Assigned Teams</th>
                        <th className="p-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {mentors.length === 0 ? (
                        <tr>
                          <td colSpan={4} className="p-8 text-center text-muted-foreground italic bg-white">
                            No mentors added yet. Click "Add Mentor" to register one.
                          </td>
                        </tr>
                      ) : (
                        mentors.map(m => {
                          const supervised = teams.filter(t => t.mentorId === m.id).map(t => t.name);
                          return (
                            <tr key={m.id} className="border-t bg-white hover:bg-slate-50/50">
                              <td className="p-4 font-semibold text-primary">{m.name}</td>
                              <td className="p-4 text-muted-foreground">{m.email}</td>
                              <td className="p-4">
                                {supervised.length === 0 ? (
                                  <span className="text-muted-foreground italic text-xs">No active assignments</span>
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
                              <td className="p-4 text-right">
                                <div className="inline-flex gap-2">
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
                  {mentors.map(m => (
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

        {/* DIALOG: MENTOR ADD / EDIT */}
        <Dialog open={isMentorDialogOpen} onOpenChange={setIsMentorDialogOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="text-xl text-primary font-bold">
                {isAddMentorMode ? "Register New Mentor" : "Edit Mentor Profile"}
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-4 my-2">
              <div>
                <label className="block text-sm font-semibold mb-1 text-slate-700">Full Name</label>
                <Input
                  value={dialogMentorName}
                  onChange={e => setDialogMentorName(e.target.value)}
                  placeholder="e.g. Dr. Priya Menon"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold mb-1 text-slate-700">Email Address</label>
                <Input
                  type="email"
                  value={dialogMentorEmail}
                  onChange={e => setDialogMentorEmail(e.target.value)}
                  placeholder="e.g. mentor@pes.edu"
                />
              </div>
            </div>

            {/* Footer Buttons */}
            <div className="flex justify-end gap-3 pt-4 border-t mt-4">
              <Button variant="ghost" onClick={() => setIsMentorDialogOpen(false)}>
                Cancel
              </Button>
              <Button variant="secondary" onClick={saveMentorChanges}>
                {isAddMentorMode ? "Add Mentor" : "Save Changes"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </RequireRole>
  );
}
