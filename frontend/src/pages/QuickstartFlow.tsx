import { FormEvent, useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { ArrowRight, CheckCircle2, Loader2, XCircle, Sparkles, Brain, Scale, Heart, Wrench, DollarSign, Shield, TrendingUp, Target } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { TrafficDot } from "@/components/shared/StatusBadge";
import { evaluateQuickstart } from "@/services/authSessions";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import type { QuickstartInput, QuickstartOutput, QuickstartParameterRating } from "@/types/api";
import type { ReactNode } from "react";
import { ThemeToggle } from "@/components/ui/theme-toggle";

const QUESTIONS: { key: keyof QuickstartInput; label: string; prompt: string; type: "input" | "textarea" }[] = [
  { key: "problem", label: "Core Problem", prompt: "What is the core problem you're solving? Be specific.", type: "textarea" },
  { key: "customer", label: "Target Customer", prompt: "Who specifically experiences this problem? (demographics, role, context)", type: "input" },
  { key: "solution", label: "Proposed Solution", prompt: "What is your proposed solution? How does it work?", type: "textarea" },
  { key: "consequence", label: "Consequence if Unsolved", prompt: "What happens if this problem isn't solved? What's the pain?", type: "textarea" },
  { key: "business_model", label: "Business Model", prompt: "How will this make money? Who pays, how much, and why?", type: "textarea" },
  { key: "urgency", label: "Why Now / Timeline", prompt: "Why is now the right time? What's your timeline to launch?", type: "input" },
  { key: "hurdles", label: "Biggest Hurdles", prompt: "What are the biggest technical, legal, or regulatory hurdles?", type: "textarea" },
];

const PARAMETER_GROUPS = {
  ethics: [
    { key: "harm_vector", icon: <Shield className="h-5 w-5" />, color: "text-accent", label: "Harm Vector" },
    { key: "legal_risk", icon: <Scale className="h-5 w-5" />, color: "text-secondary", label: "Legal Risk" },
    { key: "problem_solution_integrity", icon: <Heart className="h-5 w-5" />, color: "text-primary", label: "Problem-Solution Integrity" },
  ],
  tipsc: [
    { key: "timely", icon: <TrendingUp className="h-5 w-5" />, color: "text-[#2b9eb3]", label: "Timely" },
    { key: "important", icon: <Target className="h-5 w-5" />, color: "text-[#2b9eb3]", label: "Important" },
    { key: "profitable", icon: <DollarSign className="h-5 w-5" />, color: "text-[#2b9eb3]", label: "Profitable" },
    { key: "solvable", icon: <Wrench className="h-5 w-5" />, color: "text-[#2b9eb3]", label: "Solvable" },
  ],
  dfv: [
    { key: "desirability", icon: <Heart className="h-5 w-5" />, color: "text-[#7c6fc4]", label: "Desirability" },
    { key: "feasibility", icon: <Wrench className="h-5 w-5" />, color: "text-[#7c6fc4]", label: "Feasibility" },
    { key: "viability", icon: <DollarSign className="h-5 w-5" />, color: "text-[#7c6fc4]", label: "Viability" },
  ],
} as const;

type GroupKey = "ethics" | "tipsc" | "dfv";

const GROUP_LABELS: Record<GroupKey, string> = {
  ethics: "Ethics Gates",
  tipsc: "TIPSC Dimensions",
  dfv: "DFV Pillars",
};

const GROUP_COLORS: Record<GroupKey, string> = {
  ethics: "bg-accent/10 border-accent/20",
  tipsc: "bg-[#2b9eb3]/10 border-[#2b9eb3]/20",
  dfv: "bg-[#7c6fc4]/10 border-[#7c6fc4]/20",
};

export function QuickstartFlow() {
  const { session, sessionId, addEvent, archiveSession } = useAuth();
  const [local, setLocal] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<QuickstartOutput | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeGroup, setActiveGroup] = useState<GroupKey>("ethics");

  const filled = QUESTIONS.every((q) => local[q.key]?.trim());

  if (session.quickstart === "locked") {
    return <Navigate to="/workspace" replace />;
  }

  async function submitForm(event: FormEvent) {
    event.preventDefault();
    if (!filled) {
      toast.error("Please fill in all fields before submitting.");
      return;
    }

    setSubmitting(true);
    setError(null);
    setResult(null);

    try {
      const inputData: QuickstartInput = {
        problem: local.problem,
        customer: local.customer,
        solution: local.solution,
        consequence: local.consequence,
        business_model: local.business_model,
        urgency: local.urgency,
        hurdles: local.hurdles,
      };

      const output = await evaluateQuickstart(inputData);
      setResult(output);
      addEvent("Quickstart Evaluation Completed");
      toast.success("Quickstart evaluation completed!");
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Failed to run evaluation. Check backend connection.";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setSubmitting(false);
    }
  }

  async function retryEvaluation() {
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const inputData: QuickstartInput = {
        problem: local.problem,
        customer: local.customer,
        solution: local.solution,
        consequence: local.consequence,
        business_model: local.business_model,
        urgency: local.urgency,
        hurdles: local.hurdles,
      };
      const output = await evaluateQuickstart(inputData);
      setResult(output);
      addEvent("Quickstart Evaluation Retried");
      toast.success("Re-evaluation completed!");
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Failed to run evaluation.";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setSubmitting(false);
    }
  }

  function getParameterRating(key: string): QuickstartParameterRating | undefined {
    return result?.parameters.find((p) => p.name === key);
  }

  function getGroupParams(group: GroupKey) {
    return PARAMETER_GROUPS[group].map((p) => ({
      ...p,
      rating: getParameterRating(p.key),
    }));
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-8">
      <Header title="Quickstart Evaluation" subtitle="Rapid AI assessment: Ethics + TIPSC + DFV" />

      {!result && !error && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-accent" />
              Quickstart Evaluation Form
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Answer 7 questions → Get 10 parameter ratings (GREEN/YELLOW/RED) with reasons and advice
            </p>
          </CardHeader>
          <CardContent>
            <form onSubmit={submitForm} className="space-y-5">
              {QUESTIONS.map((q) => (
                <label key={q.key} className="block">
                  <span className="text-sm font-semibold">{q.label}</span>
                  <span className="mt-1 block text-xs text-muted-foreground">{q.prompt}</span>
                  {q.type === "textarea" ? (
                    <Textarea
                      className="mt-2"
                      value={local[q.key] || ""}
                      onChange={(e) => setLocal((prev) => ({ ...prev, [q.key]: e.target.value }))}
                      rows={4}
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
              <Button disabled={!filled || submitting} variant="secondary" className="w-full">
                {submitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                Run Quickstart Evaluation
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {submitting && !result && !error && <Loading text="Running quickstart evaluation..." />}

      {error && (
        <Card className="border-destructive/20 bg-destructive/5">
          <CardHeader>
            <CardTitle className="text-destructive">Evaluation Failed</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-lg bg-destructive/10 p-4 text-sm text-destructive">{error}</div>
            <Button variant="secondary" onClick={retryEvaluation} disabled={submitting}>
              {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Retry Evaluation
            </Button>
          </CardContent>
        </Card>
      )}

      {result && (
        <ResultView
          result={result}
          getGroupParams={getGroupParams}
          activeGroup={activeGroup}
          setActiveGroup={setActiveGroup}
        />
      )}
    </main>
  );
}

function Header({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 className="text-3xl font-bold text-primary">{title}</h1>
        <p className="text-muted-foreground">{subtitle}</p>
      </div>
      <div className="flex items-center gap-3">
        <ThemeToggle />
        <Button asChild variant="outline">
          <Link to="/">Back to Home</Link>
        </Button>
      </div>
    </div>
  );
}

function Loading({ text }: { text: string }) {
  return (
    <Card>
      <CardContent className="flex min-h-64 flex-col items-center justify-center gap-4 p-10 text-center text-secondary">
        <Brain className="h-14 w-14 animate-pulse" />
        <Loader2 className="h-6 w-6 animate-spin" />
        <p className="font-semibold">{text}</p>
      </CardContent>
    </Card>
  );
}

function ResultView({
  result,
  getGroupParams,
  activeGroup,
  setActiveGroup,
}: {
  result: QuickstartOutput;
  getGroupParams: (group: GroupKey) => Array<{ key: string; icon: ReactNode; color: string; label: string; rating?: QuickstartParameterRating }>;
  activeGroup: GroupKey;
  setActiveGroup: (group: GroupKey) => void;
}) {
  const groups: GroupKey[] = ["ethics", "tipsc", "dfv"];

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <SummaryCard count={result.green_count} label="GREEN" color="bg-emerald-500/10 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400 border border-emerald-500/30" icon={<CheckCircle2 className="h-6 w-6" />} />
        <SummaryCard count={result.yellow_count} label="YELLOW" color="bg-amber-500/10 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400 border border-amber-500/30" icon={<Sparkles className="h-6 w-6" />} />
        <SummaryCard count={result.red_count} label="RED" color="bg-red-500/10 text-red-700 dark:bg-red-500/20 dark:text-red-400 border border-red-500/30" icon={<XCircle className="h-6 w-6" />} />
      </div>

      {/* Group Tabs */}
      <div className="flex gap-2">
        {groups.map((group) => (
          <button
            key={group}
            onClick={() => setActiveGroup(group)}
            className={`rounded-full px-4 py-2 text-sm font-semibold transition-colors flex items-center gap-2 ${
              activeGroup === group
                ? "bg-secondary text-secondary-foreground shadow-sm"
                : "bg-background text-muted-foreground hover:bg-muted border border-border"
            }`}
          >
            <span className={`h-2 w-2 rounded-full ${
              group === "ethics" ? "bg-accent" : group === "tipsc" ? "bg-primary" : "bg-secondary"
            }`} />
            {GROUP_LABELS[group]}
          </button>
        ))}
      </div>

      {/* Parameter Cards */}
      <div className={`rounded-xl border p-6 ${GROUP_COLORS[activeGroup]}`}>
        <div className="space-y-4">
          {getGroupParams(activeGroup).map(({ key, icon: Icon, color, label, rating }) => (
            <ParameterCard
              key={key}
              label={label}
              icon={Icon}
              iconColor={color}
              rating={rating}
              advice={result?.parameter_advice[key]}
            />
          ))}
        </div>
      </div>

      {/* Priority Advice */}
      {result.priority_advice.length > 0 && (
        <Card className="border-amber-500/30 bg-amber-500/10 dark:bg-amber-500/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
              <Sparkles className="h-5 w-5" />
              Priority Next Steps
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="space-y-2">
              {result.priority_advice.map((step, i) => (
                <li key={i} className="flex items-start gap-3 text-sm text-amber-900">
                  <span className="flex-shrink-0 w-6 text-center font-bold">{i + 1}.</span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      )}

      {/* Proceed to Full Pipeline */}
      <Card className="border-secondary/20 bg-secondary/5">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold text-primary">Ready for Full Pipeline?</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Run the complete TIPSC → DFV → Discovery evaluation for a detailed GO/NO-GO verdict.
              </p>
            </div>
            <Button asChild variant="secondary" size="lg">
              <Link to="/workspace/tipsc" className="inline-flex items-center gap-2">
                Start Full Pipeline <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function SummaryCard({ count, label, color, icon }: { count: number; label: string; color: string; icon: ReactNode }) {
  return (
    <Card className={`relative overflow-hidden ${color}`}>
      <CardContent className="relative z-10 p-6 flex items-center gap-4">
        <div className="h-12 w-12 flex items-center justify-center rounded-xl bg-white/50">
          {icon}
        </div>
        <div>
          <p className="text-3xl font-extrabold">{count}</p>
          <p className="text-sm font-medium uppercase tracking-wide">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function ParameterCard({
  label,
  icon,
  iconColor,
  rating,
  advice,
}: {
  label: string;
  icon: ReactNode;
  iconColor: string;
  rating?: QuickstartParameterRating;
  advice?: string;
}) {
  const ratingColor = rating?.rating === "GREEN" ? "text-emerald-600" :
    rating?.rating === "YELLOW" ? "text-amber-600" :
    rating?.rating === "RED" ? "text-red-600" : "text-muted-foreground";

  const ratingBg = rating?.rating === "GREEN" ? "bg-emerald-100" :
    rating?.rating === "YELLOW" ? "bg-amber-100" :
    rating?.rating === "RED" ? "bg-red-100" : "bg-muted";

  return (
    <div className="rounded-lg border p-4 bg-white/50">
      <div className="mb-3 flex items-center gap-3">
        <div className={`h-10 w-10 flex items-center justify-center rounded-lg ${iconColor}/10`}>
          <span className={`h-5 w-5 ${iconColor}`}>{icon}</span>
        </div>
        <div>
          <h3 className="font-bold text-primary">{label}</h3>
          {rating && (
            <span className={`inline-flex items-center gap-1.5 mt-1 rounded-full px-2.5 py-0.5 text-xs font-bold ${ratingBg} ${ratingColor}`}>
              <TrafficDot status={rating.rating} />
              {rating.rating}
            </span>
          )}
        </div>
      </div>

      {rating && (
        <p className="text-sm text-muted-foreground pl-12 mb-3">{rating.reason}</p>
      )}

      {advice && (
        <div className="rounded-lg bg-slate-50 p-3 pl-12">
          <p className="text-sm text-slate-700 flex items-start gap-2">
            <span className="flex-shrink-0 mt-0.5">→</span>
            <span>{advice}</span>
          </p>
        </div>
      )}

      {!rating && (
        <p className="text-sm text-muted-foreground pl-12">Waiting for evaluation...</p>
      )}
    </div>
  );
}