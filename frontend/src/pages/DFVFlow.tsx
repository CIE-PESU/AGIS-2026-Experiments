import { useState, useEffect } from "react";
import { Link, Navigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, CheckCircle2, DollarSign, Heart, Loader2, ThumbsDown, ThumbsUp, Wrench } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { TrafficDot } from "@/components/shared/StatusBadge";
import { DFV_CONTEXT_MIN } from "@/constants";
import { triggerDfv } from "@/services/authSessions";
import { useAuth } from "@/context/AuthContext";
import type { DFVResult, TIPSCResult } from "@/data/mockData";
import { toast } from "sonner";

export function DFVFlow() {
  const { session, sessionId, serverStatus, results, saveResults, formData, setFormData, unlockNext, addEvent } = useAuth();
  
  const [phase, setPhase] = useState<"form" | "processing" | "results">(
    (serverStatus === "dfv_running" || serverStatus === "dfv_waiting") ? "processing" : results.dfv ? "results" : "form"
  );
  
  const result = results.dfv;
  const [inputs, setInputs] = useState({ desirability_context: "", feasibility_context: "", viability_context: "" });
  
  if (session.dfv === "locked") return <Navigate to="/workspace" replace />;

  const decision = result?.decision ?? (result as any)?.final_decision?.status ?? "NO-GO";
  const execSummary = result?.executiveSummary ?? (result as any)?.final_decision?.justification ?? "";
  const passed = decision === "GO";

  useEffect(() => {
    if (phase === "processing") {
      if (serverStatus === "dfv_completed" && results.dfv) {
        setPhase("results");
        addEvent("DFV Analysis Completed");
        unlockNext("dfv");
      } else if (serverStatus === "dfv_failed") {
        setPhase("form");
        toast.error("DFV Analysis failed. Please try again.");
      }
    }
  }, [phase, serverStatus, results.dfv, addEvent, unlockNext]);

  async function run() {
    const payload = {
      desirability_context: inputs.desirability_context.trim(),
      feasibility_context: inputs.feasibility_context.trim(),
      viability_context: inputs.viability_context.trim()
    };
    if (Object.values(payload).some((value) => value.length < DFV_CONTEXT_MIN)) {
      toast.error(`Each DFV context field must be at least ${DFV_CONTEXT_MIN} characters.`);
      return;
    }
    setPhase("processing");
    addEvent("DFV Triggered");
    try {
      if (sessionId) await triggerDfv(sessionId, payload);
    } catch {
      toast.error("Failed to start DFV analysis. Check backend connection.");
      setPhase("form");
    }
  }

  function repeatDFV() {
    setInputs({ desirability_context: "", feasibility_context: "", viability_context: "" });
    try {
      saveResults("dfv", undefined as unknown as DFVResult);
    } catch {
      // ignore
    }
    addEvent("DFV Restarted");
    setPhase("form");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function repeatTIPSCFromHere() {
    try {
      saveResults("tips", undefined as unknown as TIPSCResult);
    } catch {
      // ignore if saveResults doesn't accept undefined
    }
    setFormData({});
  }

  const sections = [
    ["desirability_context", Heart, "text-accent", "Who wants this, and why now?"],
    ["feasibility_context", Wrench, "text-secondary", "What can your team build and operate?"],
    ["viability_context", DollarSign, "text-primary", "How does this become sustainable?"]
  ] as const;

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <Header title="DFV Analysis" />
      {phase === "form" && (
        <Card>
          <CardContent className="space-y-6 p-6">
            {sections.map(([key, Icon, color, prompt]) => (
              <label key={key} className="block">
                <span className="flex items-center gap-2 font-semibold capitalize">
                  <Icon className={`h-5 w-5 ${color}`} /> {key.replace("_", " ")}
                </span>
                <span className="mt-1 block text-sm text-muted-foreground">{prompt}</span>
                <Textarea
                  className="mt-2"
                  value={inputs[key]}
                  onChange={(e) => setInputs({ ...inputs, [key]: e.target.value })}
                />
              </label>
            ))}
            <Button variant="secondary" disabled={!Object.values(inputs).every(Boolean)} onClick={run}>
              Run DFV Analysis
            </Button>
          </CardContent>
        </Card>
      )}
      {phase === "processing" && (
        <Card>
          <CardContent className="space-y-6 p-10">
            {sections.map(([key]) => (
              <div key={key}>
                <div className="mb-2 flex items-center justify-between text-sm font-semibold capitalize">
                  <span>{key.replace("_", " ")} Agent</span>
                  <Loader2 className="h-4 w-4 animate-spin" />
                </div>
                <div className="h-3 overflow-hidden rounded-full bg-muted">
                  <div className="h-full w-2/3 animate-pulse rounded-full bg-secondary" />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
      {phase === "results" && result && (
        <Card>
          <CardHeader>
            <CardTitle>DFV Results</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`rounded-lg p-5 ${passed ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}`}>
              <div className="flex items-center gap-2 text-xl font-bold">
                {passed ? <ThumbsUp /> : <ThumbsDown />} {decision}
              </div>
              <p className="mt-2 text-sm">{execSummary}</p>
            </div>

            {/* Support both dimensions (mock) and hypotheses/metrics (real backend) */}
            {result.dimensions ? (
              <div className="mt-6 grid gap-4 md:grid-cols-3">
                {Object.entries(result.dimensions).map(([key, val]: [string, any]) => (
                  <div key={key} className="rounded-lg border p-4">
                    <div className="flex items-center gap-2">
                      <TrafficDot status={val.status} />
                      <h3 className="font-bold capitalize">{key}</h3>
                    </div>
                    <p className="mt-3 text-sm text-muted-foreground">{val.summary}</p>
                    <ul className="mt-3 space-y-2 text-sm">
                      {val.details.map((d: string) => (
                        <li key={d} className="flex gap-2">
                          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                          {d}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            ) : (result as any).hypotheses ? (
              <div className="mt-6 grid gap-4 md:grid-cols-3">
                <div className="rounded-lg border p-4 bg-slate-50/50">
                  <h3 className="font-bold text-accent mb-2">Desirability</h3>
                  <p className="text-sm text-muted-foreground">{(result as any).hypotheses.desirability_statement}</p>
                  {(result as any).tips_validated_metrics?.importance_metric && (
                    <div className="mt-3 rounded bg-white p-2 border border-slate-100 text-xs">
                      <b>Validated Metric:</b> {(result as any).tips_validated_metrics.importance_metric}
                    </div>
                  )}
                </div>
                <div className="rounded-lg border p-4 bg-slate-50/50">
                  <h3 className="font-bold text-secondary mb-2">Feasibility</h3>
                  <p className="text-sm text-muted-foreground">{(result as any).hypotheses.feasibility_statement}</p>
                  {(result as any).tips_validated_metrics?.solvability_constraint && (
                    <div className="mt-3 rounded bg-white p-2 border border-slate-100 text-xs">
                      <b>Constraint:</b> {(result as any).tips_validated_metrics.solvability_constraint}
                    </div>
                  )}
                </div>
                <div className="rounded-lg border p-4 bg-slate-50/50">
                  <h3 className="font-bold text-primary mb-2">Viability</h3>
                  <p className="text-sm text-muted-foreground">{(result as any).hypotheses.viability_statement}</p>
                  {(result as any).tips_validated_metrics?.profitability_pivot && (
                    <div className="mt-3 rounded bg-white p-2 border border-slate-100 text-xs">
                      <b>Pivot Indicator:</b> {(result as any).tips_validated_metrics.profitability_pivot}
                    </div>
                  )}
                </div>
              </div>
            ) : null}

            {result.recommendations && result.recommendations.length > 0 && (
              <>
                <h3 className="mt-6 font-bold">Recommendations</h3>
                <ol className="mt-3 space-y-2 text-sm">
                  {result.recommendations.map((rec: string, i: number) => (
                    <li key={rec}>
                      {i + 1}. {rec}
                    </li>
                  ))}
                </ol>
              </>
            )}

            <div className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t pt-6">
              <div className="flex flex-wrap gap-3">
                <Button variant="outline" onClick={repeatDFV} className="inline-flex items-center gap-2">
                  <ArrowLeft className="h-4 w-4" /> Repeat DFV
                </Button>
                <Button asChild variant="outline" onClick={repeatTIPSCFromHere} className="inline-flex items-center gap-2">
                  <Link to="/workspace/tipsc">
                    <ArrowLeft className="h-4 w-4" /> Repeat TIPSC
                  </Link>
                </Button>
              </div>
              {passed ? (
                <Button asChild variant="secondary">
                  <Link to="/workspace/discovery" className="inline-flex items-center gap-2">
                    Proceed to Customer Discovery <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
              ) : (
                <Button
                  variant="secondary"
                  disabled
                  title="Resolve the NO-GO dimensions above before proceeding to Customer Discovery"
                  className="inline-flex items-center gap-2 opacity-50 cursor-not-allowed"
                >
                  Proceed to Customer Discovery <ArrowRight className="h-4 w-4" />
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </main>
  );
}

function Header({ title }: { title: string }) {
  return (
    <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
      <h1 className="text-3xl font-bold text-primary">{title}</h1>
      <Button asChild variant="outline">
        <Link to="/workspace">Back to Workspace</Link>
      </Button>
    </div>
  );
}