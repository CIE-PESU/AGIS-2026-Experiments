export type Traffic = "green" | "yellow" | "red";
export type StageStatus = "locked" | "available" | "in_progress" | "completed";

export type TIPSScore = {
  status: Traffic;
  explanation: string;
};

export type TIPSResult = {
  scores: Record<"technical" | "innovative" | "profitable" | "scalable", TIPSScore>;
  readyForDFV: boolean;
  explanation: string;
};

export type DFVResult = {
  decision: "GO" | "NO-GO";
  executiveSummary: string;
  dimensions: Record<"desirability" | "feasibility" | "viability", { status: Traffic; summary: string; details: string[] }>;
  recommendations: string[];
};

export type JTBDResult = {
  jobs: { title: string; context: string; outcome: string }[];
  interviewPlan: { objective: string; targetSegments: string[]; questions: string[]; sampleSize: number };
  recommendations: string[];
};

export const preEvaluationQuestions = [
  { key: "problem", label: "Problem Statement", type: "textarea", prompt: "What problem are you solving?" },
  { key: "customer", label: "Customer Segment", type: "textarea", prompt: "Who experiences this problem most acutely?" },
  { key: "consequence", label: "Consequence", type: "textarea", prompt: "What happens if the problem remains unsolved?" },
  { key: "assumptions", label: "Assumptions", type: "textarea", prompt: "What assumptions are behind your idea?" },
  { key: "solution", label: "Proposed Solution", type: "textarea", prompt: "Describe your proposed solution." },
  { key: "geography", label: "Geography", type: "input", prompt: "Where will you begin?" },
  { key: "sector", label: "Sector", type: "input", prompt: "Which sector best fits this idea?" }
] as const;

export const mockComplianceResult = [
  { label: "Legal Compliance", passed: true },
  { label: "Ethical Review", passed: true },
  { label: "Institutional Policy", passed: true },
  { label: "Regulatory Mapping", passed: true }
];

const campusBite = "CampusBite uses IoT weighing bins and ML demand signals to help campus food courts reduce food waste.";

export const mockTIPSInitial: TIPSResult = {
  readyForDFV: false,
  explanation: `${campusBite} The concept is promising but the revenue logic needs sharper evidence.`,
  scores: {
    technical: { status: "green", explanation: "IoT sensors and prediction models are feasible with available campus infrastructure." },
    innovative: { status: "green", explanation: "Combining live waste telemetry with demand prediction is distinct in the campus context." },
    profitable: { status: "yellow", explanation: "Savings are plausible, but pricing and buyer willingness are not yet quantified." },
    scalable: { status: "green", explanation: "The model can expand from PES food courts to other universities and cafeterias." }
  }
};

export const mockTIPSAfterRound1: TIPSResult = {
  ...mockTIPSInitial,
  explanation: "The buyer and savings story improved, but pilot pricing needs one final validation point."
};

export const mockTIPSFinal: TIPSResult = {
  readyForDFV: true,
  explanation: "CampusBite is ready for DFV because the solution, buyer, pilot economics, and campus expansion path are now coherent.",
  scores: {
    technical: mockTIPSInitial.scores.technical,
    innovative: mockTIPSInitial.scores.innovative,
    profitable: { status: "green", explanation: "The pilot can charge a monthly analytics fee tied to measurable waste reduction." },
    scalable: mockTIPSInitial.scores.scalable
  }
};

export const mockFollowUps = [
  { dimension: "Profitable", question: "Who pays for CampusBite, and what measurable financial value do they receive in the first month?" },
  { dimension: "Profitable", question: "What pilot pricing would feel low-risk for a campus food court while proving your savings claim?" }
];

export const mockDFVResult: DFVResult = {
  decision: "GO",
  executiveSummary: "CampusBite has strong student and operator relevance, feasible pilot requirements, and a viable path if pricing is tied to verified waste reduction.",
  dimensions: {
    desirability: {
      status: "green",
      summary: "Food court managers and student sustainability groups have a clear reason to care.",
      details: ["Daily waste creates visible cost and reputation pressure.", "Students can be recruited as champions for adoption."]
    },
    feasibility: {
      status: "green",
      summary: "A constrained pilot can be built with off-the-shelf sensors and simple dashboards.",
      details: ["Hardware complexity is manageable.", "Prediction accuracy can improve iteratively using campus data."]
    },
    viability: {
      status: "yellow",
      summary: "Revenue is credible, but proof depends on a tight pilot contract and savings baseline.",
      details: ["Start with one food court and one subscription tier.", "Tie renewal to documented reduction in discarded food."]
    }
  },
  recommendations: [
    "Run a 30-day pilot with one high-volume vendor.",
    "Baseline current waste before installing sensors.",
    "Price the pilot as a low monthly analytics fee.",
    "Publish a weekly savings and waste dashboard.",
    "Secure a CIE mentor review before expanding."
  ]
};

export const mockJTBDResult: JTBDResult = {
  jobs: [
    { title: "Reduce avoidable food waste", context: "When daily demand fluctuates", outcome: "Managers want accurate prep guidance before peak hours." },
    { title: "Defend operating margins", context: "When ingredients are discarded", outcome: "Vendors want waste translated into financial loss." },
    { title: "Show sustainability progress", context: "When campus leadership asks for impact", outcome: "Administrators want clear reduction metrics." },
    { title: "Coordinate surplus decisions", context: "When excess food remains", outcome: "Teams want timely prompts for discounts or donation workflows." }
  ],
  interviewPlan: {
    objective: "Validate waste cost, buyer urgency, and dashboard adoption for a campus food waste pilot.",
    targetSegments: ["Food court operators", "Hostel mess managers", "Student sustainability leads", "Campus administration"],
    questions: [
      "How do you currently estimate demand before service?",
      "What food categories are wasted most often?",
      "How do you measure the cost of discarded food?",
      "What dashboard signal would change tomorrow's preparation plan?",
      "What would make a paid pilot feel worthwhile?"
    ],
    sampleSize: 15
  },
  recommendations: [
    "Interview operators before refining hardware.",
    "Test whether savings, sustainability, or compliance is the strongest buying trigger.",
    "Prototype the dashboard with manual data first.",
    "Ask each segment to rank the four jobs by urgency."
  ]
};

export const mockMentorMessages = [
  { sender: "Dr. Priya Menon", timestamp: "Today, 10:15 AM", message: "Strong start. Tighten the buyer and revenue assumptions before DFV." },
  { sender: "Dr. Priya Menon", timestamp: "Yesterday, 5:40 PM", message: "Use the follow-up rounds to make the pilot economics concrete." }
];

const responses = (idea: string, segment: string, solution: string) => ({
  problem: `${idea} addresses an urgent campus operations problem with measurable student impact.`,
  customer: segment,
  consequence: "Without intervention, students and operators lose time, money, and trust in campus services.",
  assumptions: "The team assumes early adopters will try a low-risk pilot and share operational data.",
  solution,
  geography: "PES University, Bengaluru",
  sector: "Campus Technology"
});

export const memberConversations = {
  PES1UG21CS001: {
    name: "Aarav Sharma",
    lastActive: "12 min ago",
    preEval: responses("CampusBite", "Food court operators and sustainability clubs", "IoT bins plus ML demand prediction to cut food waste."),
    followUps: [
      { question: mockFollowUps[0].question, answer: "Food court managers pay because lower waste improves margins within weeks." },
      { question: mockFollowUps[1].question, answer: "A Rs. 2,000 pilot fee with renewal after verified savings feels low-risk." }
    ],
    dfvInputs: {
      desirability: "Vendors want lower waste and students want visible sustainability action.",
      feasibility: "The team can pilot with load sensors, spreadsheet baselines, and a simple dashboard.",
      viability: "A subscription can be linked to savings and later bundled for multi-campus deployments."
    }
  },
  PES1UG21CS002: {
    name: "Meera Iyer",
    lastActive: "1 hr ago",
    preEval: responses("MealMate", "Students in hostels and nearby home chefs", "A verified hyperlocal food marketplace for affordable fresh meals."),
    followUps: [{ question: "How will trust be established?", answer: "Verified kitchens, student reviews, and limited delivery radius." }],
    dfvInputs: { desirability: "Students need affordable meals.", feasibility: "Supply onboarding is manual but workable.", viability: "Commission per order plus featured sellers." }
  },
  PES1UG21CS003: {
    name: "Kabir Rao",
    lastActive: "3 hrs ago",
    preEval: responses("PlaceRight", "Placement teams and final-year students", "AI placement management to match roles, resumes, and preparation paths."),
    followUps: [{ question: "Who owns the workflow?", answer: "Placement coordinators own dashboards while students get guided tasks." }],
    dfvInputs: { desirability: "Placement teams face repetitive coordination.", feasibility: "Integrates first via CSV imports.", viability: "Department license model." }
  },
  PES1UG21CS010: {
    name: "Nisha Verma",
    lastActive: "Yesterday",
    preEval: responses("StockSmart", "Small retailers managing stock through WhatsApp", "WhatsApp-based inventory reminders and low-stock alerts."),
    followUps: [{ question: "What is the wedge?", answer: "Retailers already use WhatsApp, so onboarding friction is minimal." }],
    dfvInputs: { desirability: "Retailers miss stockouts.", feasibility: "WhatsApp bot and simple catalog.", viability: "Monthly SaaS for shops." }
  },
  PES1UG21CS011: {
    name: "Rohan Das",
    lastActive: "2 days ago",
    preEval: responses("StudyHub", "Students looking for peer-curated notes", "A campus knowledge sharing hub with reputation scoring."),
    followUps: [{ question: "How will quality stay high?", answer: "Mentor moderation and upvotes from verified course cohorts." }],
    dfvInputs: { desirability: "Students need reliable notes.", feasibility: "Web app and course tagging.", viability: "Freemium plus college partnerships." }
  }
} as const;

export const mockMyTeammates = [
  { name: "Sneha Patel", srn: "PES1UG21CS002", tips: "green" as Traffic, dfv: "GO", jtbd: true },
  { name: "Rahul Kumar", srn: "PES1UG21CS003", tips: "yellow" as Traffic, dfv: "GO", jtbd: false },
  { name: "Ananya Reddy", srn: "PES1UG21CS010", tips: "green" as Traffic, dfv: "Pending", jtbd: false }
];

export const mockMentorTeams = [
  {
    name: "Team Alpha",
    members: [
      { srn: "PES1UG21CS001", name: "Aarav Sharma", tips: mockTIPSFinal.scores, dfv: "GO", jtbd: true, lastActive: "12 min ago" },
      { srn: "PES1UG21CS002", name: "Meera Iyer", tips: mockTIPSInitial.scores, dfv: "GO", jtbd: false, lastActive: "1 hr ago" },
      { srn: "PES1UG21CS003", name: "Kabir Rao", tips: mockTIPSInitial.scores, dfv: "Pending", jtbd: false, lastActive: "3 hrs ago" },
      { srn: "PES1UG21CS010", name: "Nisha Verma", tips: mockTIPSFinal.scores, dfv: "NO-GO", jtbd: false, lastActive: "Yesterday" }
    ]
  },
  {
    name: "Team Beta",
    members: [
      { srn: "PES1UG21CS011", name: "Rohan Das", tips: mockTIPSFinal.scores, dfv: "GO", jtbd: true, lastActive: "2 days ago" },
      { srn: "PES1UG21CS012", name: "Ishaan Gupta", tips: mockTIPSInitial.scores, dfv: "Pending", jtbd: false, lastActive: "4 hrs ago" },
      { srn: "PES1UG21CS013", name: "Tara Singh", tips: mockTIPSAfterRound1.scores, dfv: "GO", jtbd: false, lastActive: "Today" }
    ]
  }
];
