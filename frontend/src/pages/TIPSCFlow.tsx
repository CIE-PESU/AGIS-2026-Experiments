import { FormEvent, useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Brain, CheckCircle2, Loader2, XCircle, MessageCircleQuestion } from "lucide-react";
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
import { generateUUID } from "@/lib/utils";

type TabKey = "preeval" | "validation" | "regulatory" | "ethics" | "tipsc" | "founder";

const TABS: { key: TabKey; label: string }[] = [
  { key: "preeval", label: "Pre Evaluation" },
  { key: "validation", label: "Validation" },
  { key: "regulatory", label: "Regulatory" },
  { key: "ethics", label: "Ethics" },
  { key: "tipsc", label: "TIPSC" },
  { key: "founder", label: "Founder" }
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

/** Maps the backend's current step index onto the tab that should be active by default. */
function defaultTabForStep(stepIndex: number): TabKey {
  if (stepIndex <= 1) return "preeval";
  if (stepIndex === 2) return "validation";
  if (stepIndex === 3) return "regulatory";
  if (stepIndex === 4) return "ethics";
  if (stepIndex === 6) return "founder";
  return "tipsc";
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
  const [activeTab, setActiveTab] = useState<TabKey>("preeval");
  const [tabManuallySelected, setTabManuallySelected] = useState(false);

  const tips = sessionDoc?.tipsc ?? null;

  const activeSessionExists = Boolean(sessionId || serverStatus);

  const isProcessing = activeSessionExists && Boolean(serverStatus && PROCESSING_STATUSES.has(serverStatus));
  const isFollowup = serverStatus === "waiting_for_founder";
  const isFinal = activeSessionExists && Boolean(serverStatus && FINAL_STATUSES.has(serverStatus));
  const isFailed = serverStatus === "tipsc_failed";

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

  // Auto-advance the active tab to follow the pipeline's progress, unless the
  // user has manually clicked a different tab (then we respect their choice
  // until they navigate again).
  useEffect(() => {
    if (!tabManuallySelected) {
      setActiveTab(defaultTabForStep(currentStep));
    }
  }, [currentStep, tabManuallySelected]);

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

  function selectTab(key: TabKey) {
    setTabManuallySelected(true);
    setActiveTab(key);
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
        generateUUID()
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
    setTabManuallySelected(false);
    addEvent("TIPSC Restarted");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function retryTIPSC() {
    if (!sessionId) return;

    setSubmitting(true);

    try {
      await triggerTipsc(sessionId);
      addEvent("TIPSC Retry Triggered");
      toast.success("TIPSC restarted.");
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : "Failed to restart TIPSC.";
      toast.error(errorMessage);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      {/* ── Follow-up question — pinned banner, no scrolling required ── */}
      {isFollowup && pendingQuestion && (
  <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-in fade-in duration-200">
    <div className="w-[560px] max-w-[calc(100vw-2rem)] animate-in zoom-in-95 fade-in duration-300">

      {/* Navy tab shape - clean arcs, #2673A6 */}
      <div className="relative z-10 h-24">
        <svg
          className="absolute inset-0 h-full w-full"
          viewBox="0 0 560 100"
          preserveAspectRatio="none"
        >
          <path
            d="M0,20 A20,20 0 0 1 20,0 L320,0 A20,20 0 0 1 340,20 L340,36 A20,20 0 0 0 360,56 L540,56 A20,20 0 0 1 560,76 L560,100 L0,100 Z"
            fill="#2673A6"
          />
        </svg>
        <div className="absolute left-5 top-4 flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-white/10 shrink-0">
            <MessageCircleQuestion className="h-4 w-4 text-white" />
          </div>
          <p className="text-sm font-semibold text-white whitespace-nowrap">TIPSC needs more information</p>
        </div>
      </div>

      {/* White - front, covers most of navy, only the top step peeks */}
      <div className="relative z-20 -mt-8 rounded-[28px] bg-white shadow-2xl px-6 pt-10 pb-8">
        <p className="text-base text-[#34305E]">{pendingQuestion}</p>
        <Textarea
          className="mt-4 bg-slate-50 text-base border-slate-200 rounded-2xl focus-visible:ring-[#34305E]"
          rows={4}
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="Type your answer here..."
          autoFocus
        />
      </div>

      {/* Orange - behind, peeks below the white card */}
      <div className="relative z-10 -mt-6 rounded-[28px] bg-[#E75A2D] pt-6">
        <button
          disabled={!answer.trim() || submitting}
          onClick={sendFollowUp}
          className="w-full h-14 flex items-center justify-center gap-2 text-white font-semibold text-base disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
          Submit & Re-evaluate
        </button>
      </div>

    </div>
  </div>
)}

      <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-primary">TIPSC Evaluation</h1>
          <p className="text-muted-foreground">
            Pre-Evaluation → Validation → Regulatory → Ethics → TIPSC
          </p>
        </div>
        <Button asChild variant="outline">
          <Link to="/workspace">Back to Workspace</Link>
        </Button>
      </div>

      {/* ── Tabs ── */}
      <div className="mb-8 grid grid-cols-2 md:grid-cols-6 gap-2">
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => selectTab(key)}
            className={`rounded-full px-2 py-2 text-center text-xs font-semibold transition-colors ${
              activeTab === key
                ? "bg-secondary text-white"
                : "bg-white text-muted-foreground hover:bg-slate-50"
            }`}
          >
            {label}
          </button>
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

      {/* ── Tab content — only the selected section renders ── */}
      {sessionDoc && (
        <div className="space-y-4">
          {activeTab === "preeval" && sessionDoc.preeval && (
            <PreEvaluationCard data={sessionDoc.preeval} />
          )}
          {activeTab === "preeval" && !sessionDoc.preeval && (
            <EmptyTabState label="Pre-Evaluation" />
          )}

          {activeTab === "validation" && sessionDoc.validation && (
            <ValidationCard data={sessionDoc.validation} />
          )}
          {activeTab === "validation" && !sessionDoc.validation && (
            <EmptyTabState label="Validation" />
          )}

          {activeTab === "regulatory" && sessionDoc.regulatory && (
            <RegulatoryCard data={sessionDoc.regulatory} />
          )}
          {activeTab === "regulatory" && !sessionDoc.regulatory && (
            <EmptyTabState label="Regulatory" />
          )}

          {activeTab === "ethics" && sessionDoc.ethics && (
            <EthicsCard data={sessionDoc.ethics} />
          )}
          {activeTab === "ethics" && !sessionDoc.ethics && (
            <EmptyTabState label="Ethics" />
          )}

          {activeTab === "founder" && (
            <FounderTab
              pendingQuestion={isFollowup ? pendingQuestion : null}
              followupHistory={sessionDoc.followup_history ?? []}
            />
          )}
        </div>
      )}

      {isFailed && (
        <Card className="border-red-200 mt-4">
          <CardHeader>
            <CardTitle className="text-red-600">
              TIPSC Evaluation Failed
            </CardTitle>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">
              {sessionDoc?.error ??
                "The evaluation could not be completed."}
            </div>

            <Button
              variant="secondary"
              onClick={retryTIPSC}
              disabled={submitting}
            >
              {submitting && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Retry TIPSC Evaluation
            </Button>
          </CardContent>
        </Card>
      )}

      {activeTab === "tipsc" && (isFollowup || isFinal) && tips && (
        <Card className="mt-4">
          <CardHeader>
            <CardTitle>TIPSC Scores</CardTitle>
          </CardHeader>
          <CardContent>
            <ScoreGrid tips={tips} />
            {isFinal && (
              <div
                className={`mt-6 rounded-lg p-4 ${readyForDFV ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800"
                  }`}
              >
                <div className="flex items-center gap-2 font-bold">
                  {readyForDFV ? <CheckCircle2 /> : <XCircle />}{" "}
                  {readyForDFV ? "Ready for DFV" : "Not Yet Ready"}
                </div>
                <p className="mt-2 text-sm">
                  {tips.reasoning}
                </p>
                <div className="mt-4 flex items-center justify-end gap-3">
                  {readyForDFV ? (
                    <Button asChild variant="secondary">
                      <Link to="/workspace/dfv" className="inline-flex items-center gap-2">
                        Proceed to DFV <ArrowRight className="h-4 w-4" />
                      </Link>
                    </Button>
                  ) : (
                    <Button
                      variant="secondary"
                      onClick={retryTIPSC}
                      disabled={submitting}
                    >
                      {submitting && (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      )}
                      Retry TIPSC Evaluation
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

function EmptyTabState({ label }: { label: string }) {
  return (
    <Card>
      <CardContent className="py-10 text-center text-sm text-muted-foreground">
        {label} results will appear here once that stage completes.
      </CardContent>
    </Card>
  );
}

function FounderTab({
  pendingQuestion,
  followupHistory
}: {
  pendingQuestion: string | null;
  followupHistory: { question: string; answer: string; turn?: number; answered_at?: string }[];
}) {
  if (!pendingQuestion && followupHistory.length === 0) {
    return <EmptyTabState label="Founder follow-up" />;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Founder Follow-up</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {pendingQuestion && (
          <p className="text-sm text-muted-foreground italic">
            A question is currently pending — see the banner at the top of the page to answer it.
          </p>
        )}
        {[...followupHistory]
          .sort((a, b) => (a.turn ?? 0) - (b.turn ?? 0))
          .map((item, index) => (
            <div key={index} className="rounded-lg border p-4">
              <p className="text-sm font-semibold text-slate-800">Q: {item.question}</p>
              <p className="mt-1 text-sm text-muted-foreground">A: {item.answer}</p>
            </div>
          ))}
      </CardContent>
    </Card>
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