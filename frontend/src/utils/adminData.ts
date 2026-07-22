import { mockMentorTeams } from "@/data/mockData";

export interface Student {
  srn: string;
  name: string;
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
  name: string;
  email: string;
}

export function initializeStorage() {
  if (!localStorage.getItem("admin_data_initialized")) {
    const initialMentors: Mentor[] = [
      { id: "mentor_1", name: "Dr. Priya Menon", email: "priya.menon@pes.edu" },
      { id: "mentor_2", name: "Prof. Rajesh Kumar", email: "rajesh.kumar@pes.edu" },
      { id: "mentor_3", name: "Dr. Amit Patel", email: "amit.patel@pes.edu" }
    ];

    const initialTeams: Team[] = [
      { id: "team_alpha", name: "Team Alpha", mentorId: "mentor_1" },
      { id: "team_beta", name: "Team Beta", mentorId: "mentor_2" }
    ];

    const initialStudents: Student[] = [
      // Team Alpha members
      {
        srn: "PES1UG21CS001",
        name: "Aarav Sharma",
        tips: {
          timely: { status: "green", explanation: "IoT sensors and prediction models are critical to deploy now due to rising campus sustainability mandates." },
          importance: { status: "green", explanation: "Reducing campus food waste is highly important for operators to defend their margins and lower reputation pressure." },
          profitable: { status: "green", explanation: "The pilot can charge a monthly analytics fee tied to measurable waste reduction." },
          solvable: { status: "green", explanation: "The problem is solvable using available IoT weighing bins and predictive demand telemetry." }
        },
        dfv: "GO",
        jtbd: true,
        lastActive: "12 min ago",
        teamId: "team_alpha"
      },
      {
        srn: "PES1UG21CS002",
        name: "Meera Iyer",
        tips: {
          timely: { status: "green", explanation: "Feasible and compliant." },
          importance: { status: "green", explanation: "Hyperlocal market is unique." },
          profitable: { status: "yellow", explanation: "Pilot margins need validation." },
          solvable: { status: "green", explanation: "Scales to local clusters." }
        },
        dfv: "GO",
        jtbd: false,
        lastActive: "1 hr ago",
        teamId: "team_alpha"
      },
      {
        srn: "PES1UG21CS003",
        name: "Kabir Rao",
        tips: {
          timely: { status: "green", explanation: "Good integration." },
          importance: { status: "green", explanation: "Distinct interface." },
          profitable: { status: "yellow", explanation: "Workflow cost needs detail." },
          solvable: { status: "green", explanation: "Applies to institutional placement teams." }
        },
        dfv: "Pending",
        jtbd: false,
        lastActive: "3 hrs ago",
        teamId: "team_alpha"
      },
      {
        srn: "PES1UG21CS010",
        name: "Nisha Verma",
        tips: {
          timely: { status: "green", explanation: "Simple WhatsApp integration." },
          importance: { status: "green", explanation: "Low friction." },
          profitable: { status: "green", explanation: "Clear SaaS value." },
          solvable: { status: "green", explanation: "Scales to any micro-retailer." }
        },
        dfv: "NO-GO",
        jtbd: false,
        lastActive: "Yesterday",
        teamId: "team_alpha"
      },
      // Team Beta members
      {
        srn: "PES1UG21CS011",
        name: "Rohan Das",
        tips: {
          timely: { status: "green", explanation: "Feasible with standard tech stack." },
          importance: { status: "green", explanation: "Reputation score distinct." },
          profitable: { status: "green", explanation: "Freemium SaaS clear." },
          solvable: { status: "green", explanation: "Partnerships scale well." }
        },
        dfv: "GO",
        jtbd: true,
        lastActive: "2 days ago",
        teamId: "team_beta"
      },
      {
        srn: "PES1UG21CS012",
        name: "Ishaan Gupta",
        tips: {
          timely: { status: "green", explanation: "Standard UI." },
          importance: { status: "yellow", explanation: "Similar to existing." },
          profitable: { status: "yellow", explanation: "Unclear monetize." },
          solvable: { status: "yellow", explanation: "Low lock-in." }
        },
        dfv: "Pending",
        jtbd: false,
        lastActive: "4 hrs ago",
        teamId: "team_beta"
      },
      {
        srn: "PES1UG21CS013",
        name: "Tara Singh",
        tips: {
          timely: { status: "green", explanation: "Workable." },
          importance: { status: "green", explanation: "Distinct features." },
          profitable: { status: "yellow", explanation: "Unproven pricing." },
          solvable: { status: "green", explanation: "Good market fit." }
        },
        dfv: "GO",
        jtbd: false,
        lastActive: "Today",
        teamId: "team_beta"
      },
      // Unassigned
      {
        srn: "PES1UG21CS004",
        name: "Sneha Patel",
        tips: {
          timely: { status: "green", explanation: "Feasible." },
          importance: { status: "green", explanation: "Innovative." },
          profitable: { status: "yellow", explanation: "Pricing model draft." },
          solvable: { status: "green", explanation: "Scales globally." }
        },
        dfv: "Pending",
        jtbd: false,
        lastActive: "1 day ago",
        teamId: null
      },
      {
        srn: "PES1UG21CS005",
        name: "Rahul Kumar",
        tips: {
          timely: { status: "yellow", explanation: "Needs review." },
          importance: { status: "yellow", explanation: "A bit common." },
          profitable: { status: "yellow", explanation: "High upfront cost." },
          solvable: { status: "yellow", explanation: "Slow adoption." }
        },
        dfv: "Pending",
        jtbd: false,
        lastActive: "3 days ago",
        teamId: null
      },
      {
        srn: "PES1UG21CS006",
        name: "Ananya Reddy",
        tips: {
          timely: { status: "green", explanation: "Proven tech stack." },
          importance: { status: "green", explanation: "Good solution." },
          profitable: { status: "green", explanation: "Clear margins." },
          solvable: { status: "green", explanation: "High growth potential." }
        },
        dfv: "Pending",
        jtbd: false,
        lastActive: "Just now",
        teamId: null
      }
    ];

    localStorage.setItem("admin_mentors", JSON.stringify(initialMentors));
    localStorage.setItem("admin_teams", JSON.stringify(initialTeams));
    localStorage.setItem("admin_students", JSON.stringify(initialStudents));
    localStorage.setItem("admin_comments", JSON.stringify({
      "PES1UG21CS001": [
        { sender: "Dr. Priya Menon", message: "Good progress. Ensure you detail the IoT telemetry costs in the profitable tab.", timestamp: "Yesterday" }
      ]
    }));
    localStorage.setItem("admin_data_initialized", "true");
  }
}

export function getMentors(): Mentor[] {
  initializeStorage();
  return JSON.parse(localStorage.getItem("admin_mentors") || "[]");
}

export function saveMentors(mentors: Mentor[]) {
  localStorage.setItem("admin_mentors", JSON.stringify(mentors));
}

export function getTeams(): Team[] {
  initializeStorage();
  return JSON.parse(localStorage.getItem("admin_teams") || "[]");
}

export function saveTeams(teams: Team[]) {
  localStorage.setItem("admin_teams", JSON.stringify(teams));
}

export function getStudents(): Student[] {
  initializeStorage();
  return JSON.parse(localStorage.getItem("admin_students") || "[]");
}

export function saveStudents(students: Student[]) {
  localStorage.setItem("admin_students", JSON.stringify(students));
}

export function getTeamsWithMembers() {
  const teams = getTeams();
  const students = getStudents();
  const mentors = getMentors();
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
  initializeStorage();
  const all = JSON.parse(localStorage.getItem("admin_comments") || "{}");
  return all[srn] || [];
}

export function addComment(srn: string, comment: Comment) {
  initializeStorage();
  const all = JSON.parse(localStorage.getItem("admin_comments") || "{}");
  if (!all[srn]) all[srn] = [];
  all[srn].push(comment);
  localStorage.setItem("admin_comments", JSON.stringify(all));
}

export function registerStudentTeam(srn: string, teamName: string): string {
  initializeStorage();
  const students = getStudents();
  const teams = getTeams();
  
  let team = teams.find(t => t.name.toLowerCase() === teamName.trim().toLowerCase());
  if (!team) {
    team = {
      id: "team_" + Date.now(),
      name: teamName.trim(),
      mentorId: null
    };
    teams.push(team);
    saveTeams(teams);
  }
  
  let student = students.find(s => s.srn === srn);
  if (!student) {
    student = {
      srn,
      name: `Student (${srn})`,
      tips: {
        timely: { status: "yellow", explanation: "Draft status" },
        importance: { status: "yellow", explanation: "Draft status" },
        profitable: { status: "yellow", explanation: "Draft status" },
        solvable: { status: "yellow", explanation: "Draft status" }
      },
      dfv: "Pending",
      jtbd: false,
      lastActive: "Just now",
      teamId: team.id
    };
    students.push(student);
  } else {
    student.teamId = team.id;
    student.lastActive = "Just now";
  }
  saveStudents(students);
  return team.id;
}
