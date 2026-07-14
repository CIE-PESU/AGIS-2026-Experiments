import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, ArrowRight, Brain, CheckCircle2, Loader2, Shield, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { StatusBadge, TrafficDot } from "@/components/shared/StatusBadge";
import { SESSION_FIELD_MIN, USE_MOCK_FLOWS } from "@/constants";
import {
  preEvaluationQuestions,
  mockTIPSCAfterRound1,
  mockTIPSCFinal,
  mockFollowUps,
} from "@/data/mockData";
import type { TIPSCResult, Traffic } from "@/data/mockData";
import { checkCompliance, getInitialTIPSCScores, submitFollowup } from "@/services/api";
import { createSession } from "@/services/authSessions";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

type Phase =
  | "form"
  | "compliance_loading"
  | "compliance_result"
  | "scoring_loading"
  | "scores"
  | "followup"
  | "followup_loading"
  | "final";

export function TIPSCFlow() {
  const { user, sessionId, serverStatus, results, formData, setFormData, saveResults, unlockNext, addEvent, setSessionId } = useAuth();

  // Initialise phase from persisted results (handles page refresh / re-entry)
  const initialTips = results.tips as any;
  const initialReady = initialTips?.readyForDFV ?? initialTips?.ready_for_dfv ?? false;
  const [phase, setPhase] = useState<Phase>(initialReady ? "final" : "form");

  const [local, setLocal] = useState<Record<string, string>>(formData);
  const [compliance, setCompliance] = useState<{ label: string; passed: boolean; explanation?: string }[]>([]);
  const [localTips, setLocalTips] = useState<TIPSCResult | null>(results.tips);
  const [question, setQuestion] = useState<{ dimension: string; question: string } | null>(null);
  const [round, setRound] = useState(0);
  const [answer, setAnswer] = useState("");

  // Combined tips source: SSE-driven (real) takes priority over mock local state
  const tipsData: any = results.tips ?? localTips;
  const readyForDFV: boolean = tipsData?.readyForDFV ?? tipsData?.ready_for_dfv ?? false;
  const filled = preEvaluationQuestions.every((q) => local[q.key]?.trim());

  // ── SSE-driven phase transitions (real backend only) ──────────────────────
  useEffect(() => {
    if (USE_MOCK_FLOWS) return;

    const activePhases: Phase[] = ["scoring_loading", "followup_loading", "compliance_loading"];
    if (!activePhases.includes(phase)) return;
    if (!serverStatus) return;

    if (serverStatus === "tipsc_completed" && results.tips) {
      addEvent("TIPSC Evaluation Completed");
      unlockNext("tipsc");
      setPhase("final");
      return;
    }

    if (serverStatus === "waiting_for_founder") {
      addEvent("Follow-up Question Ready");
      setPhase("followup");
      return;
    }

    if (serverStatus === "tipsc_failed") {
      addEvent("TIPSC Evaluation Failed");
      toast.error("TIPSC evaluation failed. Please check your inputs and retry.");
      setPhase("form");
      return;
    }
  }, [serverStatus, results.tips, phase, unlockNext, addEvent]);

  // ── Auto-start loading when sessionId appears in real mode ────────────────
  useEffect(() => {
    if (USE_MOCK_FLOWS) return;
    if (!sessionId) return;
    if (phase === "form") {
      setPhase("scoring_loading");
    }
  }, [sessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ─────────────────────────────────────────────────────────────────────────
  // Form submission — creates session, then branches on mock vs real
  // ─────────────────────────────────────────────────────────────────────────

  async function submitForm(event: FormEvent) {
    event.preventDefault();
    const problem_statement = [local.problem, local.customer, local.consequence]
      .filter(Boolean)
      .join(" ")
      .trim();
    const idea = [local.solution, local.assumptions, local.geography, local.sector]
      .filter(Boolean)
      .join(" ")
      .trim();

    if (problem_statement.length < SESSION_FIELD_MIN || idea.length < SESSION_FIELD_MIN) {
      toast.error(`Problem statement and idea must each be at least ${SESSION_FIELD_MIN} characters.`);
      return;
    }

    setFormData(local);
    addEvent("Session Created");

    let resolvedSessionId: string;
    try {
      const created = await createSession({ problem_statement, idea }, crypto.randomUUID());
      resolvedSessionId = created.session_id;
      setSessionId(resolvedSessionId);
    } catch {
      resolvedSessionId = `ses_mock_${Date.now()}`;
      setSessionId(resolvedSessionId);
      toast.message("Session saved locally — backend unavailable.");
    }

    if (USE_MOCK_FLOWS) {
      // Mock path: run compliance check then TIPSC scoring via mock API
      setPhase("compliance_loading");
      const complianceResult = await checkCompliance(resolvedSessionId);
      setCompliance(complianceResult);
      addEvent("Compliance Passed");
      setPhase("compliance_result");
    } else {
      // Real backend: TIPSC starts automatically on session creation.
      // The SSE stream (in WorkspaceLayout) will push status updates to AuthContext.
      setPhase("scoring_loading");
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Mock-only: manual scoring trigger after compliance step
  // ─────────────────────────────────────────────────────────────────────────

  async function score() {
    setPhase("scoring_loading");
    const data = await getInitialTIPSCScores(sessionId ?? "");
    setLocalTips(data);
    // Mock: initial result is not ready for DFV, so we queue a followup question
    const followUp = !data.readyForDFV ? mockFollowUps[0] : null;
    setQuestion(followUp);
    saveResults("tips", data);
    addEvent("Initial TIPSC Scores Generated");
    setPhase(followUp ? "scores" : "final");
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Follow-up submission — branches on mock vs real
  // ─────────────────────────────────────────────────────────────────────────

  async function sendFollowUp() {
    if (!answer.trim()) return;
    setPhase("followup_loading");

    if (USE_MOCK_FLOWS) {
      // Mock path: simulate re-evaluation with canned data
      await new Promise((r) => setTimeout(r, 2000));
      const nextTips = round === 0 ? mockTIPSCAfterRound1 : mockTIPSCFinal;
      const nextFollowUp = round === 0 ? mockFollowUps[1] : null;
      const updatedTips: TIPSCResult = {
        ...nextTips,
        followUps: [...(localTips?.followUps || []), { question: question?.question || "", answer }],
      };
      setLocalTips(updatedTips);
      saveResults("tips", updatedTips);
      addEvent(`TIPSC Follow-up Round ${round + 1} Submitted`);
      setRound((r) => r + 1);
      setAnswer("");
      setQuestion(nextFollowUp);
      if (nextTips.readyForDFV) {
        unlockNext("tipsc");
        addEvent("TIPSC Completed");
        setPhase("final");
      } else {
        setPhase(nextFollowUp ? "scores" : "final");
      }
    } else {
      // Real backend: POST the answer, then SSE drives the next phase
      const studentId = user?.srn ?? user?.userId ?? "";
      try {
        await submitFollowup(studentId, answer);
        addEvent("Follow-up Answer Submitted");
        setAnswer("");
        // Stay in followup_loading — the SSE useEffect above will transition
        // to "followup" (another question) or "final" (tipsc_completed)
      } catch {
        toast.error("Failed to submit follow-up. Please try again.");
        setPhase("followup");
      }
    }
  }

  function repeatTIPSC() {
    setCompliance([]);
    setLocalTips(null);
    setQuestion(null);
    setRound(0);
    setAnswer("");
    setLocal({});
    setFormData({});
    addEvent("TIPSC Restarted");
    setPhase("form");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const getStepIndex = (p: Phase): number => {
    switch (p) {
      case "form": return 0;
      case "compliance_loading":
      case "compliance_result": return 1;
      case "scoring_loading":
      case "scores": return 2;
      case "followup":
      case "followup_loading": return 3;
      case "final": return 4;
      default: return 0;
    }
  };

  // ─────────────────────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────────────────────

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-primary">TIPSC Evaluation</h1>
          <p className="text-muted-foreground">Pre-Evaluation → Compliance → TIPSC Scoring → Follow-ups → Results</p>
        </div>
        <Button asChild variant="outline"><Link to="/workspace">Back to Workspace</Link></Button>
      </div>

      {/* Step progress bar */}
      <div className="mb-8 grid grid-cols-5 gap-2">
        {["Pre-Evaluation", "Compliance", "TIPSC Scoring", "Follow-ups", "Results"].map((step, index) => (
          <div
            key={step}
            className={`rounded-full px-2 py-2 text-center text-xs font-semibold ${
              index <= getStepIndex(phase) ? "bg-secondary text-white" : "bg-white text-muted-foreground"
            }`}
          >
            {step}
          </div>
        ))}
      </div>

      {/* ── Pre-Evaluation Form ── */}
      {phase === "form" && (
        <Card>
          <CardHeader><CardTitle>Pre-Evaluation Form</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={submitForm} className="space-y-5">
              {preEvaluationQuestions.map((q) => (
                <label key={q.key} className="block">
                  <span className="text-sm font-semibold">{q.label}</span>
                  <span className="mt-1 block text-xs text-muted-foreground">{q.prompt}</span>
                  {q.type === "textarea" ? (
                    <Textarea
                      className="mt-2"
                      value={local[q.key] || ""}
                      onChange={(e) => setLocal({ ...local, [q.key]: e.target.value })}
                    />
                  ) : (
                    <Input
                      className="mt-2"
                      value={local[q.key] || ""}
                      onChange={(e) => setLocal({ ...local, [q.key]: e.target.value })}
                    />
                  )}
                </label>
              ))}
              <Button disabled={!filled} variant="secondary">Submit for Evaluation</Button>
            </form>
          </CardContent>
        </Card>
      )}

      {/* ── Compliance Loading / Result (mock mode only) ── */}
      {phase === "compliance_loading" && (
        <Loading icon={<Shield />} text="Compliance agent is reviewing your submission..." />
      )}
      {phase === "compliance_result" && (
        <Card>
          <CardHeader><CardTitle>Compliance Result</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {compliance.map((item) => (
              <div key={item.label} className="rounded-lg border p-4 bg-slate-50/30">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-sm">{item.label}</span>
                  <StatusBadge type={item.passed ? "passed" : "failed"} />
                </div>
                {item.explanation && (
                  <p className="mt-2 text-xs text-muted-foreground leading-relaxed">{item.explanation}</p>
                )}
              </div>
            ))}
            <Button onClick={score} variant="secondary">Continue to TIPSC Scoring</Button>
          </CardContent>
        </Card>
      )}

      {/* ── Scoring in progress ── */}
      {phase === "scoring_loading" && (
        <Loading icon={<Brain />} text="TIPSC agent is evaluating your idea — this may take a minute..." />
      )}

      {/* ── Scores display (mock: after score(), real: after SSE tipsc_completed) ── */}
      {(phase === "scores" || phase === "final") && tipsData && (
        <Card>
          <CardHeader><CardTitle>TIPSC Scores</CardTitle></CardHeader>
          <CardContent>
            <ScoreGrid tips={tipsData} />

            {/* Mock: show inline follow-up prompt on the scores view */}
            {phase === "scores" && question && (
              <div className="mt-6 rounded-lg bg-amber-50 p-4 text-amber-800">
                <b>{question.dimension} needs more information.</b>
                <p className="mt-1 text-sm">{question.question}</p>
                <Button className="mt-4" variant="accent" onClick={() => setPhase("followup")}>
                  Answer Follow-up
                </Button>
              </div>
            )}

            {/* Final verdict */}
            {phase === "final" && (
              <div className={`mt-6 rounded-lg p-4 ${readyForDFV ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800"}`}>
                <div className="flex items-center gap-2 font-bold">
                  {readyForDFV ? <CheckCircle2 /> : <XCircle />}
                  {readyForDFV ? "Ready for DFV" : "Not Yet Ready"}
                </div>
                <p className="mt-2 text-sm">
                  {tipsData.explanation ?? tipsData.overall_readiness ?? ""}
                </p>
                <div className="mt-4 flex items-center justify-between gap-3">
                  <Button variant="outline" onClick={repeatTIPSC} className="inline-flex items-center gap-2">
                    <ArrowLeft className="h-4 w-4" /> Repeat
                  </Button>
                  {readyForDFV ? (
                    <Button asChild variant="secondary">
                      <Link to="/workspace/dfv" className="inline-flex items-center gap-2">
                        Proceed to DFV <ArrowRight className="h-4 w-4" />
                      </Link>
                    </Button>
                  ) : (
                    <Button
                      variant="secondary"
                      disabled
                      title="Resolve the weak/red dimensions above before proceeding to DFV"
                      className="inline-flex items-center gap-2 opacity-50 cursor-not-allowed"
                    >
                      Proceed to DFV <ArrowRight className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ── Follow-up question ── */}
      {phase === "followup" && (
        <Card>
          <CardHeader>
            <CardTitle>
              {question ? `${question.dimension} Follow-up` : "Follow-up Question"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {question ? (
              <p className="font-semibold">{question.question}</p>
            ) : (
              <p className="font-semibold text-amber-700">
                The TIPSC evaluator needs more information. Please elaborate on any dimensions
                that may need strengthening.
              </p>
            )}
            <Textarea
              className="mt-4"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Provide additional context to strengthen your evaluation..."
            />
            <Button
              disabled={!answer.trim()}
              className="mt-4"
              variant="secondary"
              onClick={sendFollowUp}
            >
              Submit &amp; Re-evaluate
            </Button>
          </CardContent>
        </Card>
      )}

      {/* ── Re-evaluation in progress ── */}
      {phase === "followup_loading" && (
        <Loading icon={<Brain />} text="Re-evaluating with your answer..." />
      )}
    </main>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Helper components
// ─────────────────────────────────────────────────────────────────────────────

function Loading({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <Card>
      <CardContent className="flex min-h-64 flex-col items-center justify-center gap-4 p-10 text-center text-secondary">
        <div className="animate-pulse [&_svg]:h-14 [&_svg]:w-14">{icon}</div>
        <Loader2 className="h-6 w-6 animate-spin" />
        <p className="font-semibold">{text}</p>
      </CardContent>
    </Card>
  );
}

/**
 * Normalise TIPSC score data from either the real backend or mock shape.
 *
 * Backend shape: tips_rag_scores.T / I / P / S  (+  T_reason etc.)
 * Mock shape:    scores.timely / importance / profitable / solvable  ({ status, explanation })
 */
function normalizeScores(tips: any): { key: string; status: Traffic; explanation: string }[] {
  if (tips?.tips_rag_scores) {
    const rag = tips.tips_rag_scores;
    const LABELS: Record<string, string> = {
      T: "Timing",
      I: "Importance",
      P: "Profitable",
      S: "Solvable",
    };
    return Object.entries(LABELS).map(([k, name]) => ({
      key: name,
      status: ((rag[k] as string)?.toLowerCase() ?? "yellow") as Traffic,
      explanation: rag[`${k}_reason`] ?? "",
    }));
  }

  if (tips?.scores) {
    return Object.entries(tips.scores).map(([key, score]: [string, any]) => ({
      key: key.charAt(0).toUpperCase() + key.slice(1),
      status: score.status as Traffic,
      explanation: score.explanation ?? "",
    }));
  }

  return [];
}

function ScoreGrid({ tips }: { tips: any }) {
  const scores = normalizeScores(tips);
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {scores.map(({ key, status, explanation }) => (
        <div key={key} className="rounded-lg border p-4">
          <div className="mb-3 flex items-center gap-2">
            <TrafficDot status={status} />
            <h3 className="font-bold capitalize">{key}</h3>
          </div>
          <p className="text-sm text-muted-foreground">{explanation}</p>
        </div>
      ))}
    </div>
  );
}