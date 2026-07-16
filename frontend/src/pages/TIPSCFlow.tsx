import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, ArrowRight, Brain, CheckCircle2, Loader2, Shield, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { StatusBadge, TrafficDot } from "@/components/shared/StatusBadge";
import { SESSION_FIELD_MIN } from "@/constants";
import { preEvaluationQuestions, type TIPSCResult } from "@/data/mockData";
import { checkCompliance, getInitialTIPSCScores, submitFollowUp } from "@/services/api";
import { createSession, submitFollowup } from "@/services/authSessions";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

type Phase = "form" | "compliance_loading" | "compliance_result" | "scoring_loading" | "scores" | "followup" | "followup_loading" | "final";

export function TIPSCFlow() {
  const { results, formData, setFormData, saveResults, unlockNext, addEvent, setSessionId, sessionId, serverStatus, sessionDoc, user } = useAuth();
  const [phase, setPhase] = useState<Phase>(results.tips?.readyForDFV ? "final" : "form");
  const [local, setLocal] = useState<Record<string, string>>(formData);
  const [compliance, setCompliance] = useState<{ label: string; passed: boolean; explanation?: string }[]>([]);
  const [tips, setTips] = useState<TIPSCResult | null>(results.tips);
  const [question, setQuestion] = useState<{ dimension: string; question: string } | null>(null);
  const [round, setRound] = useState(0);
  const [answer, setAnswer] = useState("");

  const isMock = !sessionId || sessionId.startsWith("ses_mock_");

  // Derive phase and loading message reactively from the backend status
  let currentPhase = phase;
  if (!isMock && serverStatus) {
    if (serverStatus === "created" || serverStatus === "archived") {
      currentPhase = "form";
    } else if (["queued", "pre_eval", "validation_running", "ethics_running"].includes(serverStatus)) {
      currentPhase = "compliance_loading";
    } else if (serverStatus === "tipsc_running") {
      currentPhase = "scoring_loading";
    } else if (serverStatus === "tipsc_reevaluation") {
      currentPhase = "followup_loading";
    } else if (serverStatus === "waiting_for_founder") {
      currentPhase = phase === "followup" ? "followup" : "scores";
    } else if (["tipsc_completed", "dfv_waiting", "dfv_running", "dfv_completed", "dfv_failed", "discovery_waiting", "discovery_running", "discovery_failed", "completed"].includes(serverStatus)) {
      currentPhase = "final";
    }
  }

  const complete = results.tips?.readyForDFV ?? false;
  const filled = preEvaluationQuestions.every((q) => local[q.key]?.trim());

  async function submitForm(event: FormEvent) {
    event.preventDefault();
    const problem_statement = [local.problem, local.customer, local.consequence].filter(Boolean).join(" ").trim();
    const idea = [local.solution, local.assumptions, local.geography, local.sector].filter(Boolean).join(" ").trim();
    if (problem_statement.length < SESSION_FIELD_MIN || idea.length < SESSION_FIELD_MIN) {
      toast.error(`Problem statement and idea must each be at least ${SESSION_FIELD_MIN} characters.`);
      return;
    }
    setFormData(local);
    addEvent("Session Created");

    const payload = {
      problem_statement: local.problem || "",
      customer_segment: local.customer || "",
      consequence: local.consequence || "",
      assumptions: (local.assumptions || "").split("\n").map((s) => s.trim()).filter(Boolean),
      proposed_solution: local.solution || "",
      target_geography: local.geography || "",
      industry_sector: local.sector || "",
      team_id: user?.teamId || null
    };

    try {
      const created = await createSession(payload, crypto.randomUUID());
      setSessionId(created.session_id);
    } catch {
      setSessionId(`ses_mock_${Date.now()}`);
      toast.message("Session saved locally — backend unavailable.");
      setPhase("compliance_loading");
      const result = await checkCompliance();
      setCompliance(result);
      addEvent("Compliance Passed");
      setPhase("compliance_result");
    }
  }

  async function score() {
    setPhase("scoring_loading");
    const data = await getInitialTIPSCScores();
    setTips(data.result);
    setQuestion(data.followUp);
    saveResults("tips", data.result);
    addEvent("Initial TIPSC Scores Generated");
    setPhase(data.followUp ? "scores" : "final");
  }

  async function sendFollowUp() {
    if (isMock) {
      if (!question) return;
      const newFollowUp = { question: question.question, answer: answer };

      setPhase("followup_loading");
      const data = await submitFollowUp(round, answer);
      const updatedTips = {
        ...data.result,
        followUps: [...(tips?.followUps || []), newFollowUp]
      };

      setTips(updatedTips);
      saveResults("tips", updatedTips);
      addEvent(`TIPSC Follow-up Round ${round + 1} Submitted`);
      setRound((r) => r + 1);
      setAnswer("");
      setQuestion(data.followUp);
      if (data.result.readyForDFV) {
        unlockNext("tipsc");
        addEvent("TIPSC Completed");
        setPhase("final");
      } else {
        setPhase(data.followUp ? "scores" : "final");
      }
    } else {
      if (!sessionId) return;
      try {
        setPhase("followup_loading");
        await submitFollowup(sessionId, answer);
        addEvent(`TIPSC Follow-up Submitted`);
        setAnswer("");
        setPhase("scores");
      } catch {
        toast.error("Failed to submit follow-up answer.");
      }
    }
  }

  function repeatTIPSC() {
    setCompliance([]);
    setTips(null);
    setQuestion(null);
    setRound(0);
    setAnswer("");
    setLocal({});
    setFormData({});
    setSessionId(null);
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

  let loadingText = "Loading...";
  if (!isMock && serverStatus) {
    if (serverStatus === "queued") loadingText = "Session queued in Kafka...";
    if (serverStatus === "pre_eval") loadingText = "Pre-evaluation analysis running...";
    if (serverStatus === "validation_running") loadingText = "Verifying solution parameters...";
    if (serverStatus === "ethics_running") loadingText = "Performing regulatory & ethical evaluation...";
    if (serverStatus === "tipsc_running") loadingText = "AI Coaching Agent is scoring your concept...";
    if (serverStatus === "tipsc_reevaluation") loadingText = "Re-evaluating model with your answer...";
  } else {
    if (phase === "compliance_loading") loadingText = "Compliance agent is reviewing your submission...";
    if (phase === "scoring_loading") loadingText = "TIPSC agent is scoring your idea...";
    if (phase === "followup_loading") loadingText = "Re-evaluating with your answer...";
  }

  const liveQuestion = sessionDoc?.pending_question
    ? { dimension: "Founder Input Required", question: sessionDoc.pending_question }
    : null;
  const currentQuestion = isMock ? question : liveQuestion;

  const currentTips = isMock ? tips : results.tips;

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-primary">TIPSC Evaluation</h1>
          <p className="text-muted-foreground">Pre-Evaluation → Compliance → TIPSC Scoring → Follow-ups → Results</p>
        </div>
        <Button asChild variant="outline">
          <Link to="/workspace">Back to Workspace</Link>
        </Button>
      </div>
      <div className="mb-8 grid grid-cols-5 gap-2">
        {["Pre-Evaluation", "Compliance", "TIPSC Scoring", "Follow-ups", "Results"].map((step, index) => (
          <div
            key={step}
            className={`rounded-full px-2 py-2 text-center text-xs font-semibold ${
              index <= getStepIndex(currentPhase) ? "bg-secondary text-white" : "bg-white text-muted-foreground"
            }`}
          >
            {step}
          </div>
        ))}
      </div>

      {currentPhase === "form" && (
        <Card>
          <CardHeader>
            <CardTitle>Pre-Evaluation Form</CardTitle>
          </CardHeader>
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
              <Button disabled={!filled} variant="secondary">
                Submit for Compliance
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {currentPhase === "compliance_loading" && <Loading icon={<Shield />} text={loadingText} />}

      {currentPhase === "compliance_result" && (
        <Card>
          <CardHeader>
            <CardTitle>Compliance Result</CardTitle>
          </CardHeader>
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
            <Button onClick={score} variant="secondary">
              Continue to TIPSC Scoring
            </Button>
          </CardContent>
        </Card>
      )}

      {currentPhase === "scoring_loading" && <Loading icon={<Brain />} text={loadingText} />}
      {currentPhase === "followup_loading" && <Loading icon={<Brain />} text={loadingText} />}

      {(currentPhase === "scores" || currentPhase === "final") && currentTips && (
        <Card>
          <CardHeader>
            <CardTitle>TIPSC Scores</CardTitle>
          </CardHeader>
          <CardContent>
            <ScoreGrid tips={currentTips} />

            {/* Compliance Review (FastAPI live metadata) */}
            {!isMock && (sessionDoc?.validation || sessionDoc?.regulatory || sessionDoc?.ethics) && (
              <div className="mt-6 space-y-4">
                <h3 className="text-lg font-bold text-primary border-t pt-6">Compliance & Feasibility Review</h3>
                <div className="grid gap-4 md:grid-cols-3">
                  {sessionDoc.validation && (
                    <div className="rounded-lg border p-4 bg-slate-50/30">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold text-sm">Feasibility Check</span>
                        <StatusBadge type={(sessionDoc.validation as any).status === "FAILED" ? "failed" : "passed"} />
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {(sessionDoc.validation as any).reasoning || (sessionDoc.validation as any).explanation || "Passed validation checks."}
                      </p>
                    </div>
                  )}
                  {sessionDoc.regulatory && (
                    <div className="rounded-lg border p-4 bg-slate-50/30">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold text-sm">Regulatory Assessment</span>
                        <StatusBadge type={(sessionDoc.regulatory as any).status === "FAILED" ? "failed" : "passed"} />
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {(sessionDoc.regulatory as any).reasoning || (sessionDoc.regulatory as any).explanation || "No regulatory compliance issues."}
                      </p>
                    </div>
                  )}
                  {sessionDoc.ethics && (
                    <div className="rounded-lg border p-4 bg-slate-50/30">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold text-sm">Ethical Review</span>
                        <StatusBadge type={(sessionDoc.ethics as any).status === "FAILED" ? "failed" : "passed"} />
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {(sessionDoc.ethics as any).reasoning || (sessionDoc.ethics as any).explanation || "Passed ethical guidelines."}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {currentPhase === "scores" && currentQuestion && (
              <div className="mt-6 rounded-lg bg-amber-50 p-4 text-amber-800 border border-amber-200">
                <b>{currentQuestion.dimension} needs more information.</b>
                <p className="mt-1 text-sm">{currentQuestion.question}</p>
                <Button className="mt-4" variant="accent" onClick={() => setPhase("followup")}>
                  Answer Follow-up
                </Button>
              </div>
            )}

            {currentPhase === "final" && (
              <div
                className={`mt-6 rounded-lg p-4 ${
                  complete ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800"
                }`}
              >
                <div className="flex items-center gap-2 font-bold">
                  {complete ? <CheckCircle2 /> : <XCircle />} {complete ? "Ready for DFV" : "Not Yet Ready"}
                </div>
                <p className="mt-2 text-sm">{currentTips.explanation}</p>
                <div className="mt-4 flex items-center justify-between gap-3">
                  <Button variant="outline" onClick={repeatTIPSC} className="inline-flex items-center gap-2">
                    <ArrowLeft className="h-4 w-4" /> Repeat
                  </Button>
                  {complete ? (
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

      {currentPhase === "followup" && currentQuestion && (
        <Card>
          <CardHeader>
            <CardTitle>{currentQuestion.dimension} Follow-up</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="font-semibold">{currentQuestion.question}</p>
            <Textarea className="mt-4" value={answer} onChange={(e) => setAnswer(e.target.value)} />
            <Button disabled={!answer.trim()} className="mt-4" variant="secondary" onClick={sendFollowUp}>
              Submit & Re-evaluate
            </Button>
          </CardContent>
        </Card>
      )}
    </main>
  );
}

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

function ScoreGrid({ tips }: { tips: TIPSCResult }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {Object.entries(tips.scores).map(([key, score]) => (
        <div key={key} className="rounded-lg border p-4">
          <div className="mb-3 flex items-center gap-2">
            <TrafficDot status={score.status} />
            <h3 className="font-bold capitalize">{key}</h3>
          </div>
          <p className="text-sm text-muted-foreground">{score.explanation}</p>
        </div>
      ))}
    </div>
  );
}