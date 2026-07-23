import { useState, useEffect } from "react";
import { ChevronDown, Loader2, AlertCircle } from "lucide-react";
import { type StageStatus, type Traffic } from "@/data/mockData";
import { StatusBadge, TrafficDot } from "@/components/shared/StatusBadge";
import { getSession } from "@/services/authSessions";
import { deriveCanonicalStageAccess } from "@/utils/sessionStatus";
import { PreEvaluationCard } from "@/components/shared/PreEvaluationCard";
import { ValidationCard } from "@/components/shared/ValidationCard";
import { RegulatoryCard } from "@/components/shared/RegulatoryCard";
import { EthicsCard } from "@/components/shared/EthicsCard";

type StudentDetail = {
  srn: string;
  name?: string;
  lastActive?: string;
  tips?: any;
  dfv?: string;
  jtbd?: boolean;
  sessionId?: string | null;
};

type MainTabKey = "tipsc" | "dfv" | "discovery";
type TipscSubTabKey = "preeval" | "validation" | "regulatory" | "ethics" | "tipsc" | "founder";

const MAIN_TABS: { key: MainTabKey; label: string }[] = [
  { key: "tipsc", label: "TIPSC" },
  { key: "dfv", label: "DFV" },
  { key: "discovery", label: "Discovery / JTBD" }
];

const TIPSC_SUBTABS: { key: TipscSubTabKey; label: string }[] = [
  { key: "preeval", label: "Pre Evaluation" },
  { key: "validation", label: "Validation" },
  { key: "regulatory", label: "Regulatory" },
  { key: "ethics", label: "Ethics" },
  { key: "tipsc", label: "TIPSC" },
  { key: "founder", label: "Follow-up" }
];

function Section({ title, children, open = true }: { title: string; children: React.ReactNode; open?: boolean }) {
  return (
    <details open={open} className="rounded-lg border bg-white p-4">
      <summary className="flex cursor-pointer list-none items-center justify-between text-sm font-semibold">
        {title}
        <ChevronDown className="h-4 w-4" />
      </summary>
      <div className="mt-4">{children}</div>
    </details>
  );
}

function EmptyTabState({ label }: { label: string }) {
  return (
    <p className="text-sm text-muted-foreground p-4 text-center rounded-lg bg-muted/40">
      {label} results will appear here once that stage completes.
    </p>
  );
}

/** Renders an arbitrary discovery field: arrays as bullet lists, strings as paragraphs, objects as key/value pairs. */
function DiscoveryField({ label, value }: { label: string; value: any }) {
  if (value === undefined || value === null || value === "") return null;

  return (
    <div className="rounded-md border p-3">
      <p className="font-semibold text-sm capitalize">{label.replace(/_/g, " ")}</p>
      <div className="mt-2 text-sm text-muted-foreground">
        {Array.isArray(value) ? (
          <ul className="list-disc pl-5 space-y-1">
            {value.map((item, i) => (
              <li key={i}>{typeof item === "string" ? item : JSON.stringify(item)}</li>
            ))}
          </ul>
        ) : typeof value === "object" ? (
          <div className="space-y-1">
            {Object.entries(value).map(([k, v]) => (
              <p key={k}>
                <span className="font-medium capitalize">{k.replace(/_/g, " ")}:</span> {typeof v === "string" ? v : JSON.stringify(v)}
              </p>
            ))}
          </div>
        ) : (
          <p className="whitespace-pre-wrap">{String(value)}</p>
        )}
      </div>
    </div>
  );
}

export function DetailedProgressView({ student }: { student: StudentDetail }) {
  const [sessionData, setSessionData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [mainTab, setMainTab] = useState<MainTabKey>("tipsc");
  const [tipscSubTab, setTipscSubTab] = useState<TipscSubTabKey>("preeval");

  useEffect(() => {
    if (!student.sessionId) {
      setSessionData(null);
      return;
    }
    let active = true;
    async function loadDetail() {
      setLoading(true);
      try {
        const data = await getSession(student.sessionId!);
        if (active) {
          setSessionData(data);
        }
      } catch (err) {
        console.error("Failed to load teammate session detail:", err);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }
    void loadDetail();
    return () => {
      active = false;
    };
  }, [student.sessionId]);

  if (!student.sessionId) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4 text-center bg-muted/40 rounded-lg">
        <AlertCircle className="h-10 w-10 text-muted-foreground/60 mb-3" />
        <p className="font-semibold text-base text-foreground">No Workspace Activity</p>
        <p className="mt-2 text-sm text-muted-foreground max-w-sm">
          This teammate has not started or created a session yet. Their progress will appear once they begin their workspace.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  // Parse Pre-Eval inputs from live DB data
  const hasPreEval = !!(sessionData?.preeval_input || sessionData?.problem_statement);
  const preEval = hasPreEval
    ? {
        "Problem Statement": sessionData?.preeval_input?.problem_statement || sessionData?.problem_statement || "",
        "Customer Segment": sessionData?.preeval_input?.customer_segment || "",
        "Consequence": sessionData?.preeval_input?.consequence || "",
        "Assumptions": Array.isArray(sessionData?.preeval_input?.assumptions)
          ? sessionData.preeval_input.assumptions.join(", ")
          : sessionData?.preeval_input?.assumptions || "",
        "Proposed Solution": sessionData?.preeval_input?.proposed_solution || sessionData?.idea || "",
        "Geography": sessionData?.preeval_input?.target_geography || "",
        "Sector": sessionData?.preeval_input?.industry_sector || ""
      }
    : null;

  // Parse TIPSC scores from live DB data
  const hasTips = !!sessionData?.tipsc?.tips_rag_scores;
  let tips = null;
  if (hasTips) {
    const rag = sessionData.tipsc.tips_rag_scores;
    const toStatus = (v: string): Traffic => {
      const s = (v || "").toLowerCase();
      if (s === "green" || s === "yellow" || s === "red") return s;
      return "yellow";
    };
    tips = {
      timely: { status: toStatus(rag.T), explanation: rag.T_reason || "No explanation provided" },
      importance: { status: toStatus(rag.I), explanation: rag.I_reason || "No explanation provided" },
      profitable: { status: toStatus(rag.P), explanation: rag.P_reason || "No explanation provided" },
      solvable: { status: toStatus(rag.S), explanation: rag.S_reason || "No explanation provided" }
    };
  }

  // Parse follow-up history
  const followUps = sessionData?.followup_history && sessionData.followup_history.length > 0
    ? sessionData.followup_history.map((item: any) => ({
        question: item.question,
        answer: item.answer
      }))
    : null;

  const access = deriveCanonicalStageAccess(sessionData || student);

  // Parse DFV inputs and decision
  const hasDfv = !!sessionData?.dfv || access.dfv === "completed" || access.dfv === "GO" || access.dfv === "NO-GO";
  let dfvStatus = "Pending";
  let dfvInputs = null;

  if (sessionData?.dfv) {
    const out = sessionData.dfv.output || sessionData.dfv;
    if (out) {
      dfvStatus = out.decision ?? out.final_decision?.status ?? out.overall_recommendation ?? out.recommendation ?? "Completed";
    }
    if (sessionData.dfv_inputs) {
      dfvInputs = {
        desirability: sessionData.dfv_inputs.desirability_context || "No context provided",
        feasibility: sessionData.dfv_inputs.feasibility_context || "No context provided",
        viability: sessionData.dfv_inputs.viability_context || "No context provided"
      };
    }
  }

  // Parse Discovery / JTBD data
  const discoveryRaw = sessionData?.discovery ?? null;
  const discoveryOutput = discoveryRaw?.output ?? discoveryRaw ?? null;
  const hasDiscovery = !!discoveryOutput;
  const knownDiscoveryKeys = [
    "customer_jobs",
    "jobs",
    "interview_plan",
    "interview_questions",
    "recommendations",
    "discovery_recommendations",
    "summary"
  ];
  const otherDiscoveryEntries = discoveryOutput
    ? Object.entries(discoveryOutput).filter(([k]) => !knownDiscoveryKeys.includes(k))
    : [];

  const statuses: { label: string; value: any }[] = [
    { label: "TIPSC", value: access.tipsc },
    { label: "DFV", value: (access.dfv === "GO" || access.dfv === "NO-GO") ? "completed" : access.dfv },
    { label: "JTBD", value: access.discovery }
  ];

  return (
    <div className="space-y-4">
      <div className="rounded-lg bg-muted p-4">
        <p className="font-semibold">{student.name || "Teammate"}</p>
        <p className="text-sm text-muted-foreground">
          {student.srn} · Last active {student.lastActive || "Never"}
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {statuses.map((status) => (
          <div key={status.label} className="rounded-lg border p-3">
            <p className="mb-2 text-xs font-semibold text-muted-foreground">{status.label}</p>
            <StatusBadge type={status.value} />
          </div>
        ))}
      </div>

      {/* ── Main tabs: TIPSC / DFV / Discovery ── */}
      <div className="grid grid-cols-3 gap-2">
        {MAIN_TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setMainTab(key)}
            className={`rounded-full px-2 py-2 text-center text-xs font-semibold transition-colors ${
              mainTab === key
                ? "bg-secondary text-white"
                : "bg-white text-muted-foreground hover:bg-slate-50 border"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {mainTab === "tipsc" && (
        <div className="space-y-4">
          {/* ── TIPSC sub-tabs: Pre Eval / Validation / Regulatory / Ethics / TIPSC / Follow-up ── */}
          <div className="flex flex-wrap gap-2">
            {TIPSC_SUBTABS.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setTipscSubTab(key)}
                className={`rounded-full px-3 py-1.5 text-center text-xs font-semibold transition-colors ${
                  tipscSubTab === key
                    ? "bg-primary text-white"
                    : "bg-white text-muted-foreground hover:bg-slate-50 border"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {tipscSubTab === "preeval" && (
            sessionData?.preeval ? (
              <PreEvaluationCard data={sessionData.preeval} />
            ) : preEval ? (
              <div className="space-y-3">
                {Object.entries(preEval).map(([key, value], index) => (
                  <div key={key} className="rounded-md bg-muted/70 p-3 text-sm">
                    <p className="font-semibold">{index + 1}. {key}</p>
                    <p className="mt-1 text-muted-foreground">{value as string}</p>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyTabState label="Pre-Evaluation" />
            )
          )}

          {tipscSubTab === "validation" && (
            sessionData?.validation ? (
              <ValidationCard data={sessionData.validation} />
            ) : (
              <EmptyTabState label="Validation" />
            )
          )}

          {tipscSubTab === "regulatory" && (
            sessionData?.regulatory ? (
              <RegulatoryCard data={sessionData.regulatory} />
            ) : (
              <EmptyTabState label="Regulatory" />
            )
          )}

          {tipscSubTab === "ethics" && (
            sessionData?.ethics ? (
              <EthicsCard data={sessionData.ethics} />
            ) : (
              <EmptyTabState label="Ethics" />
            )
          )}

          {tipscSubTab === "tipsc" && (
            tips ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {Object.entries(tips).map(([key, score]) => (
                  <div key={key} className="rounded-md border p-3">
                    <div className="mb-2 flex items-center gap-2">
                      <TrafficDot status={score.status as Traffic} />
                      <p className="font-semibold capitalize">{key}</p>
                    </div>
                    <p className="text-sm text-muted-foreground">{score.explanation}</p>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyTabState label="TIPSC" />
            )
          )}

          {tipscSubTab === "founder" && (
            followUps ? (
              <div className="space-y-3">
                {followUps.map((item: any, index: number) => (
                  <div key={index} className="grid gap-3 md:grid-cols-2">
                    <div className="rounded-md bg-amber-50 p-3 text-sm"><b>AI Question {index + 1}:</b> {item.question}</div>
                    <div className="rounded-md bg-emerald-50 p-3 text-sm"><b>Student Response:</b> {item.answer}</div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyTabState label="Follow-up" />
            )
          )}
        </div>
      )}

      {mainTab === "dfv" && (
        <div className="space-y-4">
          <div className={dfvStatus === "NO-GO" ? "rounded-lg bg-red-50 p-4 text-red-700" : "rounded-lg bg-emerald-50 p-4 text-emerald-700"}>
            <b>DFV Decision:</b> {dfvStatus}
          </div>

          <Section title="DFV Analysis Inputs">
            {dfvInputs ? (
              <div className="grid gap-3 md:grid-cols-3">
                {Object.entries(dfvInputs).map(([key, value]) => (
                  <div key={key} className="rounded-md border p-3 text-sm">
                    <p className="font-semibold capitalize">{key}</p>
                    <p className="mt-1 text-muted-foreground">{value as string}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground p-2">DFV analysis has not been performed yet.</p>
            )}
          </Section>
        </div>
      )}

      {mainTab === "discovery" && (
        <div className="space-y-4">
          {hasDiscovery ? (
            <div className="space-y-3">
              <DiscoveryField label="Customer Jobs" value={discoveryOutput.customer_jobs ?? discoveryOutput.jobs} />
              <DiscoveryField label="Interview Plan" value={discoveryOutput.interview_plan ?? discoveryOutput.interview_questions} />
              <DiscoveryField label="Recommendations" value={discoveryOutput.recommendations ?? discoveryOutput.discovery_recommendations} />
              <DiscoveryField label="Summary" value={discoveryOutput.summary} />
              {otherDiscoveryEntries.map(([key, value]) => (
                <DiscoveryField key={key} label={key} value={value} />
              ))}
            </div>
          ) : (
            <EmptyTabState label="Customer Discovery" />
          )}
        </div>
      )}

      <p className="rounded-lg bg-muted p-3 text-center text-xs font-semibold text-muted-foreground">View only · Mentor comments do not alter student submissions.</p>
    </div>
  );
}