export type Traffic = "green" | "yellow" | "red";
export type StageStatus = "locked" | "available" | "in_progress" | "completed";

export type TIPSCScore = {
  status: Traffic;
  explanation: string;
};

export type TIPSCResult = {
  scores: Record<"timely" | "importance" | "profitable" | "solvable", TIPSCScore>;
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
  title: string;
  objectives: {
    id: number;
    objective: string;
    whyItMatters: string;
    assumptionsValidated: string[];
    evidenceRequired: string[];
  }[];
  assumptions: {
    risk: "High Risk" | "Medium Risk" | "Low Risk";
    assumption: string;
    whyItMatters: string;
    evidenceRequired: string[];
    signals: { type: "validation" | "invalidation"; text: string }[];
  }[];
  interviewGuide: {
    section: string;
    subtitle: string;
    questions: string[];
  }[];
  executionGuide: {
    before: { title: string; items: string[] }[];
    during: { title: string; items: string[] }[];
    after: { title: string; items: string[] }[];
  };
  recordingTemplate: {
    profileFields: string[];
    contextFields: string[];
    problemEvidenceFields: { label: string; value?: string }[];
    behaviorFields: string[];
    frustrationFields: string[];
    motivationFields: string[];
    memorableQuotes: string[];
    unexpectedInsights: string;
  };
  evidenceChecklist: string[];
  finalSummary: {
    criticalAssumptions: string[];
    biggestRisks: string[];
    successfulInterviews: string[];
  };
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
  { label: "Legal Compliance", passed: true, explanation: "No copyright or regulatory violations found in the proposed solution structure." },
  { label: "Ethical Review", passed: true, explanation: "Proposed pilot does not pose any data privacy or discriminatory risks." },
  { label: "Institutional Policy", passed: true, explanation: "Aligned with PES campus operator guidelines and student initiative policies." },
  { label: "Regulatory Mapping", passed: true, explanation: "Fits under local municipal food waste guidelines and safety standards." }
];

const campusBite = "CampusBite uses IoT weighing bins and ML demand signals to help campus food courts reduce food waste.";

export const mockTIPSCInitial: TIPSCResult = {
  readyForDFV: false,
  explanation: `${campusBite} The concept is promising but the revenue logic needs sharper evidence.`,
  scores: {
    timely: { status: "green", explanation: "IoT sensors and prediction models are critical to deploy now due to rising campus sustainability mandates." },
    importance: { status: "green", explanation: "Reducing campus food waste is highly important for operators to defend their margins and lower reputation pressure." },
    profitable: { status: "yellow", explanation: "Savings are plausible, but pricing and buyer willingness are not yet quantified." },
    solvable: { status: "green", explanation: "The problem is solvable using available IoT weighing bins and predictive demand telemetry." }
  }
};

export const mockTIPSCAfterRound1: TIPSCResult = {
  ...mockTIPSCInitial,
  explanation: "The buyer and savings story improved, but pilot pricing needs one final validation point."
};

export const mockTIPSCFinal: TIPSCResult = {
  readyForDFV: true,
  explanation: "CampusBite is ready for DFV because the solution, buyer, pilot economics, and campus expansion path are now coherent.",
  scores: {
    timely: mockTIPSCInitial.scores.timely,
    importance: mockTIPSCInitial.scores.importance,
    profitable: { status: "green", explanation: "The pilot can charge a monthly analytics fee tied to measurable waste reduction." },
    solvable: mockTIPSCInitial.scores.solvable
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
  title: "Pharmaceutical Traceability Platform",
  objectives: [
    {
      id: 1,
      objective: "Validate Problem Severity (Confirm that counterfeit detection is a high-priority operational challenge, not just a compliance checkbox.)",
      whyItMatters: "If the problem isn't painful enough, customers won't pay or change behavior regardless of the solution quality.",
      assumptionsValidated: [
        "Counterfeit medicines are a sufficiently important problem.",
        "Legal liability protection is a stronger motivator than detection itself."
      ],
      evidenceRequired: [
        "Customer describes specific incidents where they felt vulnerable to counterfeit risks.",
        "Customer admits current methods leave them exposed to legal/financial risk.",
        "They express active anxiety about supply chain integrity."
      ]
    },
    {
      id: 2,
      objective: "Map Current Workflow & Alternatives (Understand exactly how verification is done today and what tools are currently in use.)",
      whyItMatters: "You cannot build a solution that fits if you don't know the existing process. Misunderstanding current alternatives leads to building something nobody uses.",
      assumptionsValidated: [
        "Distributors prefer solutions integrated into existing ERP systems.",
        "Current QR-based approaches are perceived as inadequate."
      ],
      evidenceRequired: [
        "Customer describes their step-by-step verification routine.",
        "They name specific tools (e.g., Tally, Excel, manual logs) used for tracking.",
        "They express clear dissatisfaction with current methods' limitations."
      ]
    },
    {
      id: 3,
      objective: "Identify True Decision Drivers (Determine who holds the budget and what motivates their decision to adopt new compliance tech.)",
      whyItMatters: "Building a solution that solves the wrong problem or targets the wrong stakeholder leads to zero adoption.",
      assumptionsValidated: [
        "Manufacturers are willing to invest in improved traceability.",
        "Economic buyers (Manufacturers) vs. Users (Distributors) have aligned incentives."
      ],
      evidenceRequired: [
        "Clear identification of who signs off on software purchases.",
        "Evidence that manufacturers care about distributor verification capabilities.",
        "Understanding if 'trust' is a purchasable metric for them."
      ]
    },
    {
      id: 4,
      objective: "Assess Willingness to Change (Determine the threshold required for customers to adopt new verification processes.)",
      whyItMatters: "High adoption friction kills startups even with good technology. You need to know how much disruption they will tolerate.",
      assumptionsValidated: [
        "Workflow disruption is a major reason existing systems are not adopted.",
        "Would distributors change their existing processes?"
      ],
      evidenceRequired: [
        "Customer admits current workflows are inefficient but 'safe'.",
        "They express openness to new tools if the cost of inaction (liability) outweighs implementation friction.",
        "They describe past instances where they switched vendors due to pain."
      ]
    },
    {
      id: 5,
      objective: "Surface Hidden Anxieties (Uncover fears about data privacy, system reliability, and operational security that might block adoption.)",
      whyItMatters: "Unaddressed anxieties cause customers to reject solutions even if the core problem is solved.",
      assumptionsValidated: [
        "Counterfeit products undermine confidence in pharmaceutical distribution.",
        "Pharmacists/distributors may lose trust within the supply chain."
      ],
      evidenceRequired: [
        "Customer shares stories about past data breaches or verification failures.",
        "They express hesitation regarding sharing sensitive inventory data with third parties.",
        "They mention specific fears about regulatory audits failing due to poor traceability."
      ]
    }
  ],
  assumptions: [
    {
      risk: "High Risk",
      assumption: "Counterfeit detection is a top operational priority for distributors. (Problem Importance)",
      whyItMatters: "If this isn't true, the product has no market fit.",
      evidenceRequired: [
        "Customer describes active efforts to solve this problem today.",
        "They allocate budget or time specifically to this issue."
      ],
      signals: [
        { type: "validation", text: "We spend X hours/month worrying about this." },
        { type: "invalidation", text: "It's a nice-to-have but not urgent." }
      ]
    },
    {
      risk: "High Risk",
      assumption: "Distributors will adopt new verification methods if the cost of inaction is high enough. (Adoption Willingness)",
      whyItMatters: "Determines pricing strategy and sales cycle length.",
      evidenceRequired: [
        "Customer admits they would switch tools to avoid specific risks.",
        "They describe past behavior changes due to compliance needs."
      ],
      signals: [
        { type: "validation", text: "If we could prove this, I'd sign off immediately." },
        { type: "invalidation", text: "We can't change our process right now." }
      ]
    },
    {
      risk: "Medium Risk",
      assumption: "Distributors prefer ERP integration over standalone apps. (Friction & Barriers)",
      whyItMatters: "Impacts technical architecture and sales pitch.",
      evidenceRequired: [
        "Customer explains why they rejected standalone tools in the past.",
        "They describe their current tech stack limitations."
      ],
      signals: [
        { type: "validation", text: "We can't add another app; it needs to live inside Tally." },
        { type: "invalidation", text: "Standalone is fine if it's easy." }
      ]
    },
    {
      risk: "Medium Risk",
      assumption: "Legal liability protection is a stronger motivator than efficiency. (Customer Motivations)",
      whyItMatters: "Determines value proposition messaging.",
      evidenceRequired: [
        "Customer cites legal/audit fears as primary reason for current actions.",
        "They mention fines or lawsuits more often than time-saving."
      ],
      signals: [
        { type: "validation", text: "We need this to pass the audit, not just save time." },
        { type: "invalidation", text: "We want something that makes our life easier." }
      ]
    },
    {
      risk: "Medium Risk",
      assumption: "Manufacturers are willing to invest in distributor traceability. (Business Assumptions)",
      whyItMatters: "Determines who pays for the solution.",
      evidenceRequired: [
        "Manufacturer stakeholders discuss budget allocation for supply chain security.",
        "They express concern about brand damage from distributors' failures."
      ],
      signals: [
        { type: "validation", text: "We need our partners to verify correctly." },
        { type: "invalidation", text: "Manufacturers don't care; they just want cheap goods." }
      ]
    },
    {
      risk: "Low Risk",
      assumption: "Current QR codes are perceived as inadequate by stakeholders. (Alternatives)",
      whyItMatters: "Validates the need for a new technology approach.",
      evidenceRequired: [
        "Customer admits current QR scanning is insufficient or easily faked.",
        "They mention limitations of existing holograms/SMS systems."
      ],
      signals: [
        { type: "validation", text: "The old QR codes don't tell us enough." },
        { type: "invalidation", text: "We are happy with our current verification." }
      ]
    }
  ],
  interviewGuide: [
    {
      section: "A. Warm-Up",
      subtitle: "Build Rapport",
      questions: [
        "Can you walk me through a typical day in the life of someone responsible for verifying medicine inventory at your facility?",
        "What are the top three operational challenges your team faces right now regarding supply chain management?"
      ]
    },
    {
      section: "B. Problem Exploration & Current Behavior",
      subtitle: "Understand the Core Struggles",
      questions: [
        "Tell me about the last time you received a batch of medicines that raised a red flag or required extra verification steps. What happened then?",
        "When you receive a shipment, what specific steps do you take to ensure it is authentic before moving it into your warehouse?"
      ]
    },
    {
      section: "C. Struggling Moments and Triggers",
      subtitle: "Identify Triggers for Change",
      questions: [
        "What was the most stressful situation you've experienced regarding counterfeit risks or supply chain compliance in the last year? What made it difficult at that moment?",
        "Can you describe a time when an existing verification method failed to give you confidence? How did you handle it afterward?"
      ]
    },
    {
      section: "D. Current Alternatives & Workarounds",
      subtitle: "Examine Workarounds and Friction",
      questions: [
        "What tools or systems are currently helping you manage this risk? Why do you think they work (or don't work) for your specific needs?",
        "If you had to describe the biggest limitation of your current verification process, what would it be?"
      ]
    },
    {
      section: "E. Friction and Anxiety & Closing Reflection",
      subtitle: "Uncover Deeper Obstacles",
      questions: [
        "What is the one thing that makes you hesitate before approving a new vendor or software tool for supply chain management?",
        "Looking back at our conversation, if you could change one thing about how your team handles counterfeit risk today, what would it be?"
      ]
    }
  ],
  executionGuide: {
    before: [
      {
        title: "Preparation",
        items: [
          "Review the 'Current Project Understanding' but remember these are hypotheses. Do not memorize answers to avoid leading questions.",
          "Mindset: You are a researcher, not a salesperson. Your goal is to learn, not to convince."
        ]
      },
      {
        title: "Setup",
        items: [
          "Schedule 30-45 minutes.",
          "Ask for a quiet environment (phone or in-person).",
          "Ensure you have recording permission (audio only is usually fine if consented)."
        ]
      }
    ],
    during: [
      {
        title: "Listening Techniques",
        items: [
          "Practice 'Active Listening'. When they pause, wait 3 seconds before speaking. Let them finish their thought completely."
        ]
      },
      {
        title: "Follow-up Probing",
        items: [
          "Use the 'Tell me more' technique. If they say 'It's complicated,' ask 'Can you give me an example of that?' or 'What specifically makes it complicated?'"
        ]
      },
      {
        title: "Avoid Leading Language",
        items: [
          "Do not say, 'You hate standalone apps, right?' Instead say, 'How do you feel about using a separate app versus one inside your current system?'"
        ]
      },
      {
        title: "Common Mistakes to Avoid",
        items: [
          "Interrupting to explain how your solution works.",
          "Asking 'Would you buy this?' (Hypotheticals are unreliable).",
          "Nodding too much or smiling when they mention a problem (this signals agreement rather than curiosity)."
        ]
      }
    ],
    after: [
      {
        title: "Documentation",
        items: [
          "Fill out the Recording Template immediately while memories are fresh.",
          "Tag specific quotes that contradict your assumptions."
        ]
      },
      {
        title: "Reflection",
        items: [
          "Write down one 'Aha!' moment and one 'Red Flag' from the interview.",
          "Did they mention a problem you didn't expect?"
        ]
      }
    ]
  },
  recordingTemplate: {
    profileFields: [
      "Name/Role (Anonymized)",
      "Company Type: [ ] Distributor [ ] Manufacturer [ ] Other"
    ],
    contextFields: [
      "Date & Duration",
      "Location: [ ] In-person [ ] Phone [ ] Video",
      "Interviewer Notes on Vibe (e.g., Skeptical, Enthusiastic, Busy)"
    ],
    problemEvidenceFields: [
      { label: "Specific Incidents Mentioned" },
      { label: "Frequency of Problem (Rare / Occasional / Frequent)" },
      { label: "Impact Description (Financial loss, Time lost, Reputation risk)" }
    ],
    behaviorFields: [
      "Tools Currently Used",
      "Workflow Steps Described",
      "Workarounds Mentioned"
    ],
    frustrationFields: [
      "Top Frustration",
      "Key Anxiety/Fear",
      "Decision Makers Involved"
    ],
    motivationFields: [
      "Primary Driver for Change (Liability / Efficiency / Trust)",
      "Budget/Investment Willingness"
    ],
    memorableQuotes: [
      "Quote 1",
      "Quote 2"
    ],
    unexpectedInsights: "What did you learn that contradicted your initial assumptions?"
  },
  evidenceChecklist: [
    "Evidence of Problem Occurrence: Did the customer describe a specific instance where counterfeit risk or verification failure happened? (e.g., 'Last month we had to reject...')",
    "Evidence of Current Alternatives: Did they name specific tools used today? (e.g., 'We use Tally,' 'We scan QR codes manually.')",
    "Evidence of Consequences: Did they mention the cost or impact of current methods? (e.g., 'It takes 2 hours per batch,' 'We fear audits.')",
    "Evidence of Frustration: Did they express dissatisfaction with existing solutions? (e.g., 'The QR codes are easy to fake.')",
    "Evidence of Willingness to Change: Did they admit current methods are insufficient and would try something better if it solved the pain?",
    "Evidence of Adoption Barriers: Did they mention specific reasons why new tools fail? (e.g., 'We can't install another app,' 'It's too slow.')",
    "Evidence Contradicting Assumptions: Note any statements that directly conflict with your initial hypotheses (e.g., They said efficiency is more important than liability)."
  ],
  finalSummary: {
    criticalAssumptions: [
      "Problem Severity: Is counterfeit detection a top priority, or just a compliance checkbox?",
      "Adoption Willingness: Are distributors willing to change their workflow despite friction?",
      "Motivation Driver: Is legal liability the primary motivator, or is operational efficiency more important?"
    ],
    biggestRisks: [
      "Low Urgency: If distributors view this as a low-priority issue, they will not adopt new tools even if they work well.",
      "Integration Friction: If customers strictly require ERP integration and cannot tolerate standalone apps, technical complexity may block adoption.",
      "Micro-incentives/Misaligned Incentives: If manufacturers (economic buyers) do not care about distributor verification capabilities, the business model of selling to distributors may fail."
    ],
    successfulInterviews: [
      "Specific Pain Points: Concrete stories of where current methods fail or cause anxiety.",
      "Current Workflows: Detailed maps of how they verify inventory today (to identify integration opportunities).",
      "Decision Criteria: Clear understanding of who signs off on purchases and what metrics they use to judge success (e.g., 'We buy based on audit readiness, not just speed').",
      "Validation or Pivot Data: Evidence that either supports the current direction or indicates a need to pivot away from certain features (like standalone apps) before building."
    ]
  }
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
      { srn: "PES1UG21CS001", name: "Aarav Sharma", tips: mockTIPSCFinal.scores, dfv: "GO", jtbd: true, lastActive: "12 min ago" },
      { srn: "PES1UG21CS002", name: "Meera Iyer", tips: mockTIPSCInitial.scores, dfv: "GO", jtbd: false, lastActive: "1 hr ago" },
      { srn: "PES1UG21CS003", name: "Kabir Rao", tips: mockTIPSCInitial.scores, dfv: "Pending", jtbd: false, lastActive: "3 hrs ago" },
      { srn: "PES1UG21CS010", name: "Nisha Verma", tips: mockTIPSCFinal.scores, dfv: "NO-GO", jtbd: false, lastActive: "Yesterday" }
    ]
  },
  {
    name: "Team Beta",
    members: [
      { srn: "PES1UG21CS011", name: "Rohan Das", tips: mockTIPSCFinal.scores, dfv: "GO", jtbd: true, lastActive: "2 days ago" },
      { srn: "PES1UG21CS012", name: "Ishaan Gupta", tips: mockTIPSCInitial.scores, dfv: "Pending", jtbd: false, lastActive: "4 hrs ago" },
      { srn: "PES1UG21CS013", name: "Tara Singh", tips: mockTIPSCAfterRound1.scores, dfv: "GO", jtbd: false, lastActive: "Today" }
    ]
  }
];
