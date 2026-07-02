import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { Brain, CheckCircle2, Loader2, Shield, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { StatusBadge, TrafficDot } from "@/components/shared/StatusBadge";
import { SESSION_FIELD_MIN } from "@/constants";
import { preEvaluationQuestions, type TIPSResult } from "@/data/mockData";
import { checkCompliance, getInitialTIPSScores, submitFollowUp } from "@/services/api";
import { createSession } from "@/services/authSessions";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

type Phase = "form" | "compliance_loading" | "compliance_result" | "scoring_loading" | "scores" | "followup" | "followup_loading" | "final";

export function TIPSCFlow() {
  const { results, formData, setFormData, saveResults, unlockNext, addEvent, setSessionId } = useAuth();
  const [phase, setPhase] = useState<Phase>(results.tips?.readyForDFV ? "final" : "form");
  const [local, setLocal] = useState<Record<string, string>>(formData);
  const [compliance, setCompliance] = useState<{ label: string; passed: boolean }[]>([]);
  const [tips, setTips] = useState<TIPSResult | null>(results.tips);
  const [question, setQuestion] = useState<{ dimension: string; question: string } | null>(null);
  const [round, setRound] = useState(0);
  const [answer, setAnswer] = useState("");

  const complete = tips?.readyForDFV;
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
    try {
      const created = await createSession({ problem_statement, idea }, crypto.randomUUID());
      setSessionId(created.session_id);
    } catch {
      setSessionId(`ses_mock_${Date.now()}`);
      toast.message("Session saved locally — backend unavailable.");
    }
    setPhase("compliance_loading");
    const result = await checkCompliance();
    setCompliance(result);
    addEvent("Compliance Passed");
    setPhase("compliance_result");
  }

  async function score() {
    setPhase("scoring_loading");
    const data = await getInitialTIPSScores();
    setTips(data.result);
    setQuestion(data.followUp);
    saveResults("tips", data.result);
    addEvent("Initial TIPS Scores Generated");
    setPhase(data.followUp ? "scores" : "final");
  }

  async function sendFollowUp() {
    setPhase("followup_loading");
    const data = await submitFollowUp(round, answer);
    setTips(data.result);
    saveResults("tips", data.result);
    addEvent(`TIPS Follow-up Round ${round + 1} Submitted`);
    setRound((r) => r + 1);
    setAnswer("");
    setQuestion(data.followUp);
    if (data.result.readyForDFV) {
      unlockNext("tipsc");
      addEvent("TIPS Completed");
      setPhase("final");
    } else {
      setPhase(data.followUp ? "scores" : "final");
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
        <div><h1 className="text-3xl font-bold text-primary">TIPS Evaluation</h1><p className="text-muted-foreground">Pre-Evaluation → Compliance → TIPS Scoring → Follow-ups → Results</p></div>
        <Button asChild variant="outline"><Link to="/workspace">Back to Workspace</Link></Button>
      </div>
      <div className="mb-8 grid grid-cols-5 gap-2">
        {["Pre-Evaluation", "Compliance", "TIPS Scoring", "Follow-ups", "Results"].map((step, index) => (
          <div key={step} className={`rounded-full px-2 py-2 text-center text-xs font-semibold ${index <= ["form","compliance_loading","compliance_result","scoring_loading","scores","followup","followup_loading","final"].indexOf(phase) % 5 ? "bg-secondary text-white" : "bg-white text-muted-foreground"}`}>{step}</div>
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
              <Button disabled={!filled} variant="secondary">Submit for Compliance</Button>
            </form>
          </CardContent>
        </Card>
      )}
      {phase === "compliance_loading" && <Loading icon={<Shield />} text="Compliance agent is reviewing your submission..." />}
      {phase === "compliance_result" && (
        <Card><CardHeader><CardTitle>Compliance Result</CardTitle></CardHeader><CardContent className="space-y-4">
          {compliance.map((item) => <div key={item.label} className="flex items-center justify-between rounded-lg border p-4"><span>{item.label}</span><StatusBadge type={item.passed ? "passed" : "failed"} /></div>)}
          <Button onClick={score} variant="secondary">Continue to TIPS Scoring</Button>
        </CardContent></Card>
      )}
      {phase === "scoring_loading" && <Loading icon={<Brain />} text="TIPS agent is scoring your idea..." />}
      {(phase === "scores" || phase === "final") && tips && (
        <Card><CardHeader><CardTitle>TIPS Scores</CardTitle></CardHeader><CardContent>
          <ScoreGrid tips={tips} />
          {phase === "scores" && question && (
            <div className="mt-6 rounded-lg bg-amber-50 p-4 text-amber-800">
              <b>{question.dimension} needs more information.</b>
              <p className="mt-1 text-sm">{question.question}</p>
              <Button className="mt-4" variant="accent" onClick={() => setPhase("followup")}>Answer Follow-up</Button>
            </div>
          )}
          {phase === "final" && (
            <div className={`mt-6 rounded-lg p-4 ${complete ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800"}`}>
              <div className="flex items-center gap-2 font-bold">{complete ? <CheckCircle2 /> : <XCircle />} {complete ? "Ready for DFV" : "Not Yet Ready"}</div>
              <p className="mt-2 text-sm">{tips.explanation}</p>
            </div>
          )}
        </CardContent></Card>
      )}
      {phase === "followup" && question && (
        <Card><CardHeader><CardTitle>{question.dimension} Follow-up</CardTitle></CardHeader><CardContent>
          <p className="font-semibold">{question.question}</p>
          <Textarea className="mt-4" value={answer} onChange={(e) => setAnswer(e.target.value)} />
          <Button disabled={!answer.trim()} className="mt-4" variant="secondary" onClick={sendFollowUp}>Submit & Re-evaluate</Button>
        </CardContent></Card>
      )}
      {phase === "followup_loading" && <Loading icon={<Brain />} text="Re-evaluating with your answer..." />}
    </main>
  );
}

function Loading({ icon, text }: { icon: React.ReactNode; text: string }) {
  return <Card><CardContent className="flex min-h-64 flex-col items-center justify-center gap-4 p-10 text-center text-secondary"><div className="animate-pulse [&_svg]:h-14 [&_svg]:w-14">{icon}</div><Loader2 className="h-6 w-6 animate-spin" /><p className="font-semibold">{text}</p></CardContent></Card>;
}

function ScoreGrid({ tips }: { tips: TIPSResult }) {
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
