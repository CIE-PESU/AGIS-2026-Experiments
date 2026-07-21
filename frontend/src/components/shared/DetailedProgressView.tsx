import { useState, useEffect } from "react";
import { ChevronDown, Loader2, AlertCircle } from "lucide-react";
import { type StageStatus, type Traffic } from "@/data/mockData";
import { StatusBadge, TrafficDot } from "@/components/shared/StatusBadge";
import { getSession } from "@/services/authSessions";

type StudentDetail = {
  srn: string;
  name?: string;
  lastActive?: string;
  tips?: any;
  dfv?: string;
  jtbd?: boolean;
  sessionId?: string | null;
};

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

export function DetailedProgressView({ student }: { student: StudentDetail }) {
  const [sessionData, setSessionData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

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

  // Parse DFV inputs and decision
  const hasDfv = !!sessionData?.dfv;
  let dfvStatus = "Pending";
  let dfvInputs = null;

  if (hasDfv) {
    const out = sessionData.dfv.output;
    if (out) {
      dfvStatus = out.decision ?? out.final_decision?.status ?? "Pending";
    }
    if (sessionData.dfv_inputs) {
      dfvInputs = {
        desirability: sessionData.dfv_inputs.desirability_context || "No context provided",
        feasibility: sessionData.dfv_inputs.feasibility_context || "No context provided",
        viability: sessionData.dfv_inputs.viability_context || "No context provided"
      };
    }
  }

  const jtbdCompleted = sessionData
    ? !!(sessionData.discovery || sessionData.status === "completed")
    : false;

  const statuses: { label: string; value: StageStatus }[] = [
    { label: "TIPSC", value: hasTips ? "completed" : (sessionData ? "in_progress" : "available") },
    { label: "DFV", value: hasDfv ? "completed" : (hasTips ? "available" : "locked") },
    { label: "JTBD", value: jtbdCompleted ? "completed" : (hasDfv ? "available" : "locked") }
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
      
      <Section title="Pre-Evaluation Responses">
        {preEval ? (
          <div className="space-y-3">
            {Object.entries(preEval).map(([key, value], index) => (
              <div key={key} className="rounded-md bg-muted/70 p-3 text-sm">
                <p className="font-semibold">{index + 1}. {key}</p>
                <p className="mt-1 text-muted-foreground">{value as string}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground p-2">No pre-evaluation answers submitted yet.</p>
        )}
      </Section>

      <Section title="TIPSC Evaluation Scores" open={false}>
        {tips ? (
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
          <p className="text-sm text-muted-foreground p-2">TIPSC evaluation has not been performed yet.</p>
        )}
      </Section>

      <Section title="TIPSC Follow-up Q&A" open={false}>
        <div className="space-y-3">
          {followUps ? (
            followUps.map((item: any, index: number) => (
              <div key={index} className="grid gap-3 md:grid-cols-2">
                <div className="rounded-md bg-amber-50 p-3 text-sm"><b>AI Question {index + 1}:</b> {item.question}</div>
                <div className="rounded-md bg-emerald-50 p-3 text-sm"><b>Student Response:</b> {item.answer}</div>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground p-2">No follow-up exchanges recorded.</p>
          )}
        </div>
      </Section>

      <div className={dfvStatus === "NO-GO" ? "rounded-lg bg-red-50 p-4 text-red-700" : "rounded-lg bg-emerald-50 p-4 text-emerald-700"}>
        <b>DFV Decision:</b> {dfvStatus}
      </div>

      <Section title="DFV Analysis Inputs" open={false}>
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
      <p className="rounded-lg bg-muted p-3 text-center text-xs font-semibold text-muted-foreground">View only · Mentor comments do not alter student submissions.</p>
    </div>
  );
}
