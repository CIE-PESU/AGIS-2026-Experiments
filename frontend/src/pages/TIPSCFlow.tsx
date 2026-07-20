import { FormEvent, useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Brain, CheckCircle2, Loader2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { TrafficDot } from "@/components/shared/StatusBadge";
import { preEvaluationQuestions, type TIPSCResult } from "@/data/mockData";
import { createSession, triggerTipsc, submitFollowup } from "@/services/authSessions";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

type Phase = "form" | "processing" | "followup" | "final";

export function TIPSCFlow() {
  const {
    session, results, formData, setFormData, addEvent,
    sessionId, setSessionId, serverStatus, pendingQuestion, unlockNext, archiveSession
  } = useAuth();

  const [local, setLocal] = useState<Record<string, string>>(formData);
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const tips = results.tips;
  const complete = tips?.readyForDFV;
  const filled = preEvaluationQuestions.every((q) => local[q.key]?.trim());

  if (session.tipsc === "locked") return <Navigate to="/workspace" replace />;

  let phase: Phase = "form";
  if (sessionId) {
    if (complete) {
      phase = "final";
    } else if (pendingQuestion) {
      phase = "followup";
    } else if (serverStatus === "queued" || serverStatus === "tipsc_running") {
      phase = "processing";
    } else if (tips) {
      phase = "final";
    } else {
      phase = "processing";
    }
  }

  useEffect(() => {
    if (phase === "final" && complete) {
      unlockNext("tipsc");
    }
    if (serverStatus === "tipsc_failed") {
      toast.error("TIPSC evaluation failed. Please try again.");
    }
  }, [phase, complete, serverStatus, unlockNext]);

  async function submitForm(event: FormEvent) {
    event.preventDefault();
    if (!filled) {
      toast.error("Please fill in all fields before submitting.");
      return;
    }

    setFormData(local);
    setSubmitting(true);

    const assumptionsList = (local.assumptions || "")
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);

    try {
      const created = await createSession(
        {
          problem_statement: local.problem,
          customer_segment: local.customer,
          consequence: local.consequence,
          assumptions: assumptionsList,
          proposed_solution: local.solution,
          target_geography: local.geography,
          industry_sector: local.sector
        },
        crypto.randomUUID()
      );
      setSessionId(created.session_id);
      addEvent("Session Created");

      await triggerTipsc(created.session_id);
      addEvent("TIPSC Triggered");
    } catch (err: any) {
      toast.error(err?.message || "Failed to create session. Check backend connection.");
    } finally {
      setSubmitting(false);
    }
  }

  async function sendFollowUp() {
    if (!sessionId || !answer.trim()) return;
    setSubmitting(true);
    try {
      await submitFollowup(sessionId, answer.trim());
      addEvent("TIPSC Follow-up Submitted");
      setAnswer("");
    } catch (err: any) {
      toast.error(err?.message || "Failed to submit follow-up answer.");
    } finally {
      setSubmitting(false);
    }
  }

  async function repeatTIPSC() {
    if (sessionId) {
      setSubmitting(true);
      try {
        const { archiveSession: archiveSessionApi } = await import("@/services/authSessions");
        await archiveSessionApi(sessionId);
      } catch (err) {
        toast.error("Failed to archive the old session on the server.");
        setSubmitting(false);
        return;
      }
      setSubmitting(false);
    }
    archiveSession();
    setLocal({});
    setFormData({});
    setAnswer("");
    addEvent("TIPSC Restarted");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const getStepIndex = (p: Phase): number => {
    switch (p) {
      case "form": return 0;
      case "processing": return 2;
      case "followup": return 3;
      case "final": return 4;
      default: return 0;
    }
  };

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-primary">TIPSC Evaluation</h1>
          <p className="text-muted-foreground">Pre-Evaluation → TIPSC Scoring → Follow-ups → Results</p>
        </div>
        <Button asChild variant="outline"><Link to="/workspace">Back to Workspace</Link></Button>
      </div>

      <div className="mb-8 grid grid-cols-4 gap-2">
        {["Pre-Evaluation", "TIPSC Scoring", "Follow-ups", "Results"].map((step, index) => (
          <div key={step} className={`rounded-full px-2 py-2 text-center text-xs font-semibold ${index <= getStepIndex(phase) ? "bg-secondary text-white" : "bg-white text-muted-foreground"}`}>{step}</div>
        ))}
      </div>

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
                    <Textarea className="mt-2" value={local[q.key] || ""} onChange={(e) => setLocal({ ...local, [q.key]: e.target.value })} />
                  ) : (
                    <Input className="mt-2" value={local[q.key] || ""} onChange={(e) => setLocal({ ...local, [q.key]: e.target.value })} />
                  )}
                </label>
              ))}
              <Button disabled={!filled || submitting} variant="secondary">
                {submitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                Submit for TIPSC Evaluation
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {phase === "processing" && <Loading icon={<Brain />} text="TIPSC agent is scoring your idea..." />}

      {(phase === "followup" || phase === "final") && tips && (
        <Card><CardHeader><CardTitle>TIPSC Scores</CardTitle></CardHeader><CardContent>
          <ScoreGrid tips={tips} />
          {phase === "followup" && pendingQuestion && (
            <div className="mt-6 rounded-lg bg-amber-50 p-4 text-amber-800">
              <b>Additional information needed</b>
              <p className="mt-1 text-sm">{pendingQuestion}</p>
              <Textarea className="mt-4 bg-white" value={answer} onChange={(e) => setAnswer(e.target.value)} />
              <Button disabled={!answer.trim() || submitting} className="mt-4" variant="secondary" onClick={sendFollowUp}>
                {submitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                Submit & Re-evaluate
              </Button>
            </div>
          )}
          {phase === "final" && (
            <div className={`mt-6 rounded-lg p-4 ${complete ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800"}`}>
              <div className="flex items-center gap-2 font-bold">{complete ? <CheckCircle2 /> : <XCircle />} {complete ? "Ready for DFV" : "Not Yet Ready"}</div>
              <p className="mt-2 text-sm">{tips.explanation}</p>
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
                  <Button variant="secondary" disabled className="opacity-50 cursor-not-allowed">
                    Proceed to DFV <ArrowRight className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>
          )}
        </CardContent></Card>
      )}
    </main>
  );
}

function Loading({ icon, text }: { icon: React.ReactNode; text: string }) {
  return <Card><CardContent className="flex min-h-64 flex-col items-center justify-center gap-4 p-10 text-center text-secondary"><div className="animate-pulse [&_svg]:h-14 [&_svg]:w-14">{icon}</div><Loader2 className="h-6 w-6 animate-spin" /><p className="font-semibold">{text}</p></CardContent></Card>;
}

function ScoreGrid({ tips }: { tips: TIPSCResult }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {Object.entries(tips.scores).map(([key, score]) => (
        <div key={key} className="rounded-lg border p-4">
          <div className="mb-3 flex items-center gap-2"><TrafficDot status={score.status} /><h3 className="font-bold capitalize">{key}</h3></div>
          <p className="text-sm text-muted-foreground">{score.explanation}</p>
        </div>
      ))}
    </div>
  );
}