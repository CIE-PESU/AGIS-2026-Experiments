import { FormEvent, useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Brain, CheckCircle2, Loader2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { TrafficDot } from "@/components/shared/StatusBadge";
import { preEvaluationQuestions } from "@/data/mockData";
import type { TIPSCResult } from "@/types/api";
import { createSession, triggerTipsc, submitFollowup } from "@/services/authSessions";
import { useAuth } from "@/context/AuthContext";
import { PreEvaluationCard } from "@/components/shared/PreEvaluationCard";
import { ValidationCard } from "@/components/shared/ValidationCard";
import { RegulatoryCard } from "@/components/shared/RegulatoryCard";
import { EthicsCard } from "@/components/shared/EthicsCard";
import { toast } from "sonner";

const STEPS = [
  "Queued",
  "Pre Evaluation",
  "Validation",
  "Regulatory",
  "Ethics",
  "TIPSC",
  "Founder",
  "DFV",
  "Discovery",
  "Completed"
];

const PROCESSING_STATUSES = new Set([
    "created",
    "queued",
    "pre_eval",
    "validation_running",
    "regulatory_running",
    "ethics_running",
    "tipsc_running",
    "tipsc_reevaluation"
]);

const FINAL_STATUSES = new Set([
  "tipsc_completed",
  "dfv_waiting",
  "dfv_running",
  "dfv_completed",
  "discovery_waiting",
  "discovery_running",
  "completed"
]);

function getStepIndex(status?: string | null): number {
  switch (status) {
    case "created":
    case "queued":
      return 0;
    case "pre_eval":
      return 1;
    case "validation_running":
      return 2;
    case "regulatory_running":
      return 3;
    case "ethics_running":
      return 4;
    case "tipsc_running":
    case "tipsc_reevaluation":
      return 5;
    case "waiting_for_founder":
      return 6;
    case "dfv_waiting":
    case "dfv_running":
    case "dfv_completed":
      return 7;
    case "discovery_waiting":
    case "discovery_running":
      return 8;
    case "completed":
      return 9;
    default:
      return 0;
  }
}

function getLoadingText(status?: string | null): string {
  switch (status) {
    case "created":
    case "queued":
      return "Waiting in queue...";
    case "pre_eval":
      return "Running pre-evaluation...";
    case "validation_running":
      return "Running validation...";
    case "regulatory_running":
      return "Checking regulatory compliance...";
    case "ethics_running":
      return "Running ethics analysis...";
    case "tipsc_running":
      return "Running TIPSC evaluation...";
    case "tipsc_reevaluation":
      return "Re-evaluating your submission...";
    default:
      return "Processing...";
  }
}

export function TIPSCFlow() {
  const {
    session,
    formData,
    setFormData,
    addEvent,
    archiveSession,
    sessionId,
    setSessionId,
    serverStatus,
    pendingQuestion,
    unlockNext,
    sessionDoc
  } = useAuth();

  const [local, setLocal] = useState<Record<string, string>>(formData);
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const tips = sessionDoc?.tipsc ?? null;

  const activeSessionExists = Boolean(sessionId || serverStatus);

  const isProcessing = activeSessionExists && Boolean(serverStatus && PROCESSING_STATUSES.has(serverStatus));
  const isFollowup = serverStatus === "waiting_for_founder";
  const isFinal = activeSessionExists && Boolean(serverStatus && FINAL_STATUSES.has(serverStatus));

  const readyForDFV =
    serverStatus === "tipsc_completed" ||
    serverStatus === "dfv_waiting" ||
    serverStatus === "dfv_running" ||
    serverStatus === "dfv_completed" ||
    serverStatus === "discovery_waiting" ||
    serverStatus === "discovery_running" ||
    serverStatus === "completed";

  const currentStep = getStepIndex(serverStatus);
  const loadingText = getLoadingText(serverStatus);

  const filled = preEvaluationQuestions.every((q) => local[q.key]?.trim());

  useEffect(() => {
    if (readyForDFV) {
      unlockNext("tipsc");
    }

    if (serverStatus === "tipsc_failed") {
      toast.error("TIPSC evaluation failed. Please try again.");
    }
  }, [readyForDFV, serverStatus, unlockNext]);

  if (session.tipsc === "locked") {
    return <Navigate to="/workspace" replace />;
  }

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
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Failed to create session. Check backend connection.";
      toast.error(errorMessage);
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
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Failed to submit follow-up answer.";
      toast.error(errorMessage);
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

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-primary">TIPSC Evaluation</h1>
          <p className="text-muted-foreground">
            Pre-Evaluation → Validation → Regulatory → Ethics → TIPSC → DFV → Discovery
          </p>
        </div>
        <Button asChild variant="outline">
          <Link to="/workspace">Back to Workspace</Link>
        </Button>
      </div>

      <div className="mb-8 grid grid-cols-2 md:grid-cols-5 gap-2">
        {STEPS.map((step, index) => (
          <div
            key={step}
            className={`rounded-full px-2 py-2 text-center text-xs font-semibold ${
              index <= currentStep
                ? "bg-secondary text-white"
                : "bg-white text-muted-foreground"
            }`}
          >
            {step}
          </div>
        ))}
      </div>

      {!activeSessionExists && (
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
                      onChange={(e) => setLocal((prev) => ({ ...prev, [q.key]: e.target.value }))}
                    />
                  ) : (
                    <Input
                      className="mt-2"
                      value={local[q.key] || ""}
                      onChange={(e) => setLocal((prev) => ({ ...prev, [q.key]: e.target.value }))}
                    />
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

      {isProcessing && <Loading icon={<Brain />} text={loadingText} />}

      {sessionDoc && (
        <div className="space-y-4">
          {sessionDoc.preeval && <PreEvaluationCard data={sessionDoc.preeval} />}
          {sessionDoc.validation && <ValidationCard data={sessionDoc.validation} />}
          {sessionDoc.regulatory && <RegulatoryCard data={sessionDoc.regulatory} />}
          {sessionDoc.ethics && <EthicsCard data={sessionDoc.ethics} />}
        </div>
      )}

      {(isFollowup || isFinal) && tips && (
        <Card>
          <CardHeader>
            <CardTitle>TIPSC Scores</CardTitle>
          </CardHeader>
          <CardContent>
            <ScoreGrid tips={tips} />
            {isFollowup && pendingQuestion && (
              <div className="mt-6 rounded-lg bg-amber-50 p-4 text-amber-800">
                <b>Additional information needed</b>
                <p className="mt-1 text-sm">{pendingQuestion}</p>
                <Textarea
                  className="mt-4 bg-white"
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                />
                <Button
                  disabled={!answer.trim() || submitting}
                  className="mt-4"
                  variant="secondary"
                  onClick={sendFollowUp}
                >
                  {submitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                  Submit & Re-evaluate
                </Button>
              </div>
            )}
            {isFinal && (
              <div
                className={`mt-6 rounded-lg p-4 ${
                  readyForDFV ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800"
                }`}
              >
                <div className="flex items-center gap-2 font-bold">
                  {readyForDFV ? <CheckCircle2 /> : <XCircle />}{" "}
                  {readyForDFV ? "Ready for DFV" : "Not Yet Ready"}
                </div>
                <p className="mt-2 text-sm">
    {tips.reasoning}
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
                    <Button variant="secondary" disabled className="opacity-50 cursor-not-allowed">
                      Proceed to DFV <ArrowRight className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>
            )}
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
  const scores = [
    {
      key: "Timely",
      status: tips.tips_rag_scores.T,
      reason: tips.tips_rag_scores.T_reason,
    },
    {
      key: "Important",
      status: tips.tips_rag_scores.I,
      reason: tips.tips_rag_scores.I_reason,
    },
    {
      key: "Profitable",
      status: tips.tips_rag_scores.P,
      reason: tips.tips_rag_scores.P_reason,
    },
    {
      key: "Solvable",
      status: tips.tips_rag_scores.S,
      reason: tips.tips_rag_scores.S_reason,
    },
  ];

  return (
    <div className="space-y-6">

      <div className="grid gap-4 md:grid-cols-2">
        {scores.map((score) => (
          <div
            key={score.key}
            className="rounded-lg border p-4"
          >
            <div className="mb-3 flex items-center gap-2">
              <TrafficDot status={score.status} />
              <h3 className="font-bold">
                {score.key}
              </h3>
            </div>

            <p className="text-sm text-muted-foreground">
              {score.reason}
            </p>
          </div>
        ))}
      </div>

      <div className="rounded-lg border p-4">
        <h3 className="font-semibold mb-2">
          Overall Readiness
        </h3>

        <p className="font-medium">
          {tips.overall_readiness}
        </p>
      </div>

      <div className="rounded-lg border p-4">
        <h3 className="font-semibold mb-2">
          Reasoning
        </h3>

        <p className="text-sm whitespace-pre-wrap text-muted-foreground">
          {tips.reasoning}
        </p>
      </div>

    </div>
  );
}