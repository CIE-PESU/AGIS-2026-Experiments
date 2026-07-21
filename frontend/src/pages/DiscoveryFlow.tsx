import React, { useState, useEffect } from "react";
import { Link, Navigate } from "react-router-dom";
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Users,
  Download,
  Info,
  Compass,
  AlertTriangle,
  FileText,
  ListChecks,
  HelpCircle,
  PlayCircle,
  BookOpen,
  ArrowRight,
  Lightbulb
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { triggerDiscovery } from "@/services/authSessions";
import { useAuth } from "@/context/AuthContext";
import { downloadMarkdown, generateDiscoveryMarkdown } from "@/utils/exportMarkdown";
import { toast } from "sonner";

/* ═══════════════════════════════════════════════════════════════════
   DISCOVERY QUESTIONS FORM — founder's own thinking, captured before
   the agent runs. Questions on the left, learning guide on the right,
   side by side always (not stacked below on small screens).
   ═══════════════════════════════════════════════════════════════════ */
interface FieldConfig {
  id: string;
  label: string;
  placeholder: string;
  required?: boolean;
  guide: { title: string; why: string; goodExample: string; avoidThis: string; jtbdTip: string };
}

const discoveryFormFields: FieldConfig[] = [
  { id: "problem", label: "What problem are you trying to solve?", placeholder: "Be specific about the challenge you have identified", required: true, guide: { title: "What problem are you trying to solve?", why: "We start by understanding what problem you have identified. This helps us ground your customer discovery in a real need.", goodExample: "Students struggle to manage group project deadlines and contributions effectively.", avoidThis: 'Avoid vague statements like "make things better" or "improve efficiency" without specifics.', jtbdTip: "In JTBD terms, this is the circumstance or trigger that makes your customer 'hire' a solution." } },
  { id: "targetCustomer", label: "Who experiences this problem?", placeholder: "Describe your target customer in specific terms", required: true, guide: { title: "Who experiences this problem?", why: "Different people experience problems differently. Knowing who you are focusing on helps us tailor your research.", goodExample: "Software development students in their 2nd–4th year working on capstone projects.", avoidThis: 'Avoid broad audience descriptions like "everyone" or "people." Get specific about demographics, roles, and context.', jtbdTip: "In JTBD terms, your customer is the person in a specific circumstance trying to get a job done." } },
  { id: "importance", label: "Why is solving this problem important?", placeholder: "What are the consequences if this problem is not solved?", required: true, guide: { title: "Why is solving this problem important?", why: "Understanding the impact helps you decide if this is worth investigating deeply.", goodExample: "Poor coordination leads to missed deadlines, failed courses, and weakened team dynamics affecting future collaboration.", avoidThis: 'Avoid claiming it is important for "everyone." Focus on the specific impact for your target customer.', jtbdTip: "In JTBD terms, this is the desired outcome and the emotional satisfaction your customer seeks." } },
  { id: "assumptions", label: "Why do you think this problem happens?", placeholder: "Share your current theories about the root causes", required: true, guide: { title: "Why do you think this problem happens?", why: "These are your current hypotheses. They help you identify what you need to learn through interviews.", goodExample: "I assume the problem happens because students don't have a shared digital workspace and lack clear role assignments.", avoidThis: 'Avoid stating solutions disguised as problems. "They need project management software" is a solution, not a problem understanding.', jtbdTip: "In JTBD terms, these are your assumptions about the customer's context, constraints, and current approach." } },
  { id: "learningObjectives", label: "What are you hoping to learn from customer interviews?", placeholder: "What questions or uncertainties do you have?", required: true, guide: { title: "What are you hoping to learn from customer interviews?", why: "This clarifies what questions to ask in interviews. You can structure interviews around your learning objectives.", goodExample: "I want to learn what students currently use to track deadlines and how they handle unexpected changes in team member availability.", avoidThis: "Avoid open-ended curiosity. Focus on specific gaps in your understanding that will change your approach.", jtbdTip: "In JTBD terms, you're identifying the gaps between your assumptions and the customer's real Job-To-Be-Done." } },
  { id: "additionalNotes", label: "Anything else you would like the AI Coach to know?", placeholder: "Optional: any additional context", guide: { title: "Additional context", why: "Share any background info, constraints, or prior research that might help the AI Coach give you better feedback.", goodExample: "We've already done 3 informal interviews and noticed students rely heavily on WhatsApp groups for coordination.", avoidThis: "Don't feel pressured to fill this in — it's optional.", jtbdTip: "Any extra context helps the coach understand your starting point better." } },
];

function DiscoveryQuestionsForm({ onSubmit }: { onSubmit: (data: Record<string, string>) => void }) {
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [activeField, setActiveField] = useState("problem");

  const activeGuide = discoveryFormFields.find((f) => f.id === activeField)?.guide;
  const requiredFields = discoveryFormFields.filter((f) => f.required);
  const filledCount = requiredFields.filter((f) => formData[f.id]?.trim()).length;
  const allFilled = filledCount === requiredFields.length;
  const progress = (filledCount / requiredFields.length) * 100;

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 flex flex-row gap-8 items-start">
      <style>{discoveryFormAnimationStyles}</style>
      <div className="flex-1 min-w-0">
        <div className="bg-card rounded-xl border shadow-md p-6 md:p-8">
          <h2 className="text-2xl font-bold text-foreground mb-1">Describe Your Problem</h2>
          <p className="text-sm text-muted-foreground mb-4">
            Tell us about the problem you are trying to solve. Do not worry about JTBD terminology — just describe your thinking clearly.
          </p>
          <div className="h-1.5 mb-8 w-full rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-secondary transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>

          <div className="space-y-6">
            {discoveryFormFields.map((field, i) => (
              <div
                key={field.id}
                className="discovery-field-fade-in"
                style={{ animationDelay: `${i * 60}ms` }}
              >
                <label className="block text-sm font-semibold text-foreground mb-1.5">
                  {field.label}{field.required && <span className="text-accent ml-0.5">*</span>}
                </label>
                <Textarea
                  value={formData[field.id] || ""}
                  onChange={(e) => setFormData((p) => ({ ...p, [field.id]: e.target.value }))}
                  onFocus={() => setActiveField(field.id)}
                  placeholder={field.placeholder}
                  rows={3}
                  className={`resize-none transition-all duration-200 shadow-sm ${activeField === field.id ? "ring-2 ring-secondary/40 border-secondary" : ""}`}
                />
              </div>
            ))}
          </div>

          <div className="mt-8 flex items-center justify-between">
            <p className="text-xs text-muted-foreground">{filledCount}/{requiredFields.length} required fields completed</p>
            <Button
              onClick={() => onSubmit(formData)}
              disabled={!allFilled}
              className="gap-2 shadow-md text-white"
              style={{ background: allFilled ? "linear-gradient(135deg, hsl(14 78% 53%) 0%, hsl(14 78% 48%) 100%)" : undefined }}
            >
              Review My Thinking <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
      <div className="w-80 shrink-0">
        <div className="sticky top-8">
          {activeGuide && (
            <div
              key={activeGuide.title}
              className="discovery-guide-fade-in bg-card border rounded-xl shadow-md p-5 space-y-4"
            >
              <div>
                <p className="text-[10px] font-bold tracking-widest text-secondary uppercase mb-1">Learning Guide</p>
                <h3 className="text-sm font-bold text-foreground leading-snug">{activeGuide.title}</h3>
              </div>
              <DiscoveryGuideBit icon={<Lightbulb className="w-3.5 h-3.5 text-secondary" />} label="Why are we asking this?" text={activeGuide.why} />
              <DiscoveryGuideBit icon={<CheckCircle2 className="w-3.5 h-3.5 text-secondary" />} label="Good example" text={activeGuide.goodExample} italic />
              <DiscoveryGuideBit icon={<AlertTriangle className="w-3.5 h-3.5 text-accent" />} label="Avoid this" text={activeGuide.avoidThis} italic />
              <div className="rounded-lg p-3 border-l-2 border-secondary" style={{ background: "linear-gradient(135deg, hsl(197 56% 48% / 0.08) 0%, hsl(197 56% 48% / 0.03) 100%)" }}>
                <p className="text-[10px] font-bold tracking-wider text-secondary uppercase mb-1">JTBD Tip</p>
                <p className="text-xs text-muted-foreground leading-relaxed">{activeGuide.jtbdTip}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const discoveryFormAnimationStyles = `
@keyframes discovery-fade-in-up {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}
.discovery-field-fade-in {
  animation: discovery-fade-in-up 0.35s ease-out both;
}
.discovery-guide-fade-in {
  animation: discovery-fade-in-up 0.2s ease-out both;
}
@media (prefers-reduced-motion: reduce) {
  .discovery-field-fade-in, .discovery-guide-fade-in {
    animation: none;
  }
}
`;

function DiscoveryGuideBit({ icon, label, text, italic }: { icon: React.ReactNode; label: string; text: string; italic?: boolean }) {
  return (
    <div className="space-y-0.5">
      <div className="flex items-center gap-1.5">{icon}<span className="text-[10px] font-bold tracking-wider text-muted-foreground uppercase">{label}</span></div>
      <p className={`text-xs text-muted-foreground leading-relaxed ${italic ? "italic" : ""}`}>{text}</p>
    </div>
  );
}

export function DiscoveryFlow() {
  const { session, sessionId, serverStatus, results, unlockNext, addEvent, formData, setFormData } = useAuth();
  
  const [loading, setLoading] = useState(serverStatus === "discovery_running" || serverStatus === "discovery_waiting");
  const result = results.discovery;
  const [discoveryInputs, setDiscoveryInputs] = useState<Record<string, string> | null>(null);
  const [checklistState, setChecklistState] = useState<Record<number, boolean>>({});
  const [activeGuideTab, setActiveGuideTab] = useState<"before" | "during" | "after">("before");

  if (session.discovery === "locked") return <Navigate to="/workspace" replace />;

  useEffect(() => {
    if (loading) {
      if (serverStatus === "completed" && results.discovery) {
        setLoading(false);
        addEvent("Discovery Completed");
        unlockNext("discovery");
      } else if (serverStatus === "discovery_failed") {
        setLoading(false);
        toast.error("Discovery Analysis failed. Please try again.");
      }
    }
  }, [loading, serverStatus, results.discovery, addEvent, unlockNext]);

  async function startDiscovery() {
    if (!discoveryInputs) return;
    setLoading(true);
    addEvent("Discovery Triggered");

    const payload = {
      target_customer_segment: [
        {
          segment: discoveryInputs.targetCustomer || "Target Audience",
          role: "Primary User",
          customer_type: "B2C"
        }
      ],
      problem_statement: discoveryInputs.problem || "",
      problem_consequence: (discoveryInputs.importance || "").split("\n").map((s) => s.trim()).filter(Boolean),
      current_alternatives: ["Manual workarounds", "Legacy solutions"],
      key_assumptions: (discoveryInputs.assumptions || "").split("\n").map((s) => s.trim()).filter(Boolean),
      what_we_already_know: ["Initial problem definition from pre-evaluation"],
      biggest_uncertainty: (discoveryInputs.learningObjectives || "").split("\n").map((s) => s.trim()).filter(Boolean),
      customer_type: ["Primary User"],
      proposed_solution_context: {
        purpose: "Validate early-stage customer hypotheses",
        summary: discoveryInputs.additionalNotes || "Customer discovery and JTBD interview planning"
      }
    };

    try {
      if (sessionId) await triggerDiscovery(sessionId, payload);
    } catch {
      toast.error("Failed to start Discovery analysis. Check backend connection.");
      setLoading(false);
    }
  }

  function handleFormSubmit(data: Record<string, string>) {
    setDiscoveryInputs(data);
    // Persist discovery questionnaire inputs into shared session formData
    // (namespaced) so they are not lost on navigation and can be included
    // in the exported report.
    setFormData({
      ...formData,
      discovery_problem: data.problem || "",
      discovery_targetCustomer: data.targetCustomer || "",
      discovery_importance: data.importance || "",
      discovery_assumptions: data.assumptions || "",
      discovery_learningObjectives: data.learningObjectives || "",
      discovery_additionalNotes: data.additionalNotes || ""
    });
  }

  const exportDiscoveryPlan = () => {
    if (!result) return;
    const markdownContent = generateDiscoveryMarkdown(result);
    downloadMarkdown(markdownContent, `customer-discovery-plan-${Date.now()}.md`);
  };

  const toggleChecklist = (index: number) => {
    setChecklistState((prev) => ({ ...prev, [index]: !prev[index] }));
  };

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      {/* Header and Actions */}
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4 border-b pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-primary">Customer Discovery Planner</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Plan, execute, and record structured jobs-to-be-done validation.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {result && (
            <Button onClick={exportDiscoveryPlan} variant="outline" className="flex items-center gap-2">
              <Download className="h-4 w-4" /> Download Discovery Plan (.md)
            </Button>
          )}
          <Button asChild variant="outline">
            <Link to="/workspace">Back to Workspace</Link>
          </Button>
        </div>
      </div>

      {/* Step 1: Founder's own thinking, captured before the agent runs */}
      {!result && !loading && !discoveryInputs && (
        <DiscoveryQuestionsForm onSubmit={handleFormSubmit} />
      )}

      {/* Step 2: Original trigger area — gated behind the form now */}
      {!result && !loading && discoveryInputs && (
        <Card className="border-primary/20 bg-primary/5">
          <CardContent className="space-y-4 p-8 text-center max-w-2xl mx-auto">
            <Users className="mx-auto h-12 w-12 text-primary/80" />
            <h2 className="text-xl font-bold">Generate Customer Discovery & JTBD Plan</h2>
            <p className="text-muted-foreground text-sm">
              Trigger the discovery planner when DFV is complete. The system will build a comprehensive, step-by-step customer discovery framework tailored to your project.
            </p>
            <Button size="lg" className="w-full sm:w-auto" onClick={() => void startDiscovery()}>
              Trigger Discovery Planner
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Loading State */}
      {loading && (
        <Card className="border-accent/20 bg-accent/5">
          <CardContent className="flex min-h-80 flex-col items-center justify-center gap-4 p-10 text-center text-accent">
            <Users className="h-16 w-16 animate-pulse" />
            <Loader2 className="h-6 w-6 animate-spin text-accent" />
            <div>
              <p className="font-semibold text-lg">Discovery agent is generating customer jobs and interviews...</p>
              <p className="text-xs text-muted-foreground mt-1">This will build guides, matrix plans, and checklists.</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Structured / Markdown Result Output */}
      {result && (
        <>
          {(result as any).report ? (
            <Card className="border-slate-200 shadow-sm p-6 md:p-8 bg-white">
              <MarkdownRenderer content={(result as any).report} />
            </Card>
          ) : (
            <div className="space-y-10">
              {/* Section 1: Customer Discovery Objectives */}
              <Card className="border-slate-200 shadow-sm">
                <CardHeader className="bg-slate-50/50 border-b">
                  <div className="flex items-center gap-2">
                    <Compass className="h-5 w-5 text-primary" />
                    <CardTitle className="text-lg">SECTION 1: CUSTOMER DISCOVERY OBJECTIVES</CardTitle>
                  </div>
                  <CardDescription>
                    Validate or invalidate critical hypotheses about the market and problem severity.
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-6">
                  <div className="space-y-6">
                    {result.objectives?.map((obj) => (
                      <div key={obj.id} className="rounded-lg border bg-white p-5 shadow-sm hover:border-slate-300 transition-colors">
                        <h3 className="font-bold text-slate-800 text-base">{obj.objective}</h3>
                        <div className="mt-4 grid gap-4 md:grid-cols-3">
                          <div className="rounded-md bg-slate-50 p-4">
                            <h4 className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                              <Info className="h-3.5 w-3.5" /> Why It Matters
                            </h4>
                            <p className="text-sm text-slate-600 leading-relaxed">{obj.whyItMatters}</p>
                          </div>
                          <div className="rounded-md bg-slate-50 p-4">
                            <h4 className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                              Assumptions Validated
                            </h4>
                            <ul className="space-y-1.5 text-sm text-slate-600">
                              {obj.assumptionsValidated.map((a) => (
                                <li key={a} className="flex items-start gap-1.5">
                                  <span className="text-primary font-bold mt-0.5">•</span>
                                  <span>{a}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                          <div className="rounded-md bg-emerald-50/40 border border-emerald-100 p-4">
                            <h4 className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-emerald-800 mb-2">
                              Evidence Required
                            </h4>
                            <ul className="space-y-1.5 text-sm text-slate-600">
                              {obj.evidenceRequired.map((e) => (
                                <li key={e} className="flex items-start gap-1.5">
                                  <CheckCircle2 className="h-4.5 w-4.5 text-emerald-600 shrink-0 mt-0.5" />
                                  <span>{e}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Section 2: Assumption Validation Matrix */}
              <Card className="border-slate-200 shadow-sm">
                <CardHeader className="bg-slate-50/50 border-b">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-amber-600" />
                    <CardTitle className="text-lg">SECTION 2: ASSUMPTION VALIDATION MATRIX</CardTitle>
                  </div>
                  <CardDescription>
                    Prioritized hypotheses by risk level. Focus discovery on High and Medium risk items first.
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-6">
                  <div className="grid gap-6 md:grid-cols-2">
                    {result.assumptions?.map((ass, i) => (
                      <div key={i} className="flex flex-col rounded-lg border bg-white p-5 shadow-sm hover:shadow-md transition-shadow">
                        <div className="flex items-center justify-between gap-2 mb-3">
                          <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                            ass.risk === "High Risk"
                              ? "bg-red-100 text-red-800 border border-red-200"
                              : ass.risk === "Medium Risk"
                              ? "bg-amber-100 text-amber-800 border border-amber-200"
                              : "bg-emerald-100 text-emerald-800 border border-emerald-200"
                          }`}>
                            {ass.risk}
                          </span>
                        </div>
                        <h3 className="font-bold text-slate-800 text-base mb-2">{ass.assumption}</h3>
                        <p className="text-sm text-slate-500 mb-4 leading-relaxed"><span className="font-semibold text-slate-700">Impact: </span>{ass.whyItMatters}</p>

                        <div className="mt-auto space-y-3 pt-3 border-t">
                          <div>
                            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Required Evidence</h4>
                            <ul className="space-y-1 text-xs text-slate-600">
                              {ass.evidenceRequired.map((e, idx) => (
                                <li key={idx} className="flex items-start gap-1">
                                  <span className="text-slate-400 font-bold">•</span>
                                  <span>{e}</span>
                                </li>
                              ))}
                            </ul>
                          </div>

                          <div className="rounded-md bg-slate-50 p-2.5 space-y-1.5">
                            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Validation Signals</h4>
                            {ass.signals.map((sig, idx) => (
                              <div key={idx} className="flex items-start gap-1.5 text-xs">
                                {sig.type === "validation" ? (
                                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0 mt-0.5" />
                                ) : (
                                  <XCircle className="h-3.5 w-3.5 text-rose-500 shrink-0 mt-0.5" />
                                )}
                                <span className={sig.type === "validation" ? "text-slate-700 font-medium" : "text-slate-500 italic"}>
                                  {sig.text}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Section 3: Customer Discovery Interview Guide */}
              <Card className="border-slate-200 shadow-sm">
                <CardHeader className="bg-slate-50/50 border-b">
                  <div className="flex items-center gap-2">
                    <HelpCircle className="h-5 w-5 text-indigo-600" />
                    <CardTitle className="text-lg">SECTION 3: CUSTOMER DISCOVERY INTERVIEW GUIDE</CardTitle>
                  </div>
                  <CardDescription>
                    Ask open-ended questions about past behavior and concrete workflows. Avoid hypotheticals.
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-6">
                  <div className="space-y-4">
                    {result.interviewGuide?.map((guide, i) => (
                      <div key={i} className="rounded-lg border bg-white p-5 shadow-sm">
                        <div className="mb-3">
                          <span className="text-xs font-semibold uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded">
                            Section {guide.section}
                          </span>
                          <h3 className="mt-2 text-base font-bold text-slate-800">{guide.subtitle}</h3>
                        </div>
                        <div className="space-y-3 pt-3 border-t">
                          {guide.questions.map((q, idx) => (
                            <div key={idx} className="flex items-start gap-3 rounded-md bg-slate-50 p-3 hover:bg-slate-100 transition-colors">
                              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white">
                                {idx + 1}
                              </span>
                              <p className="text-sm font-semibold text-slate-800 leading-relaxed italic">"{q}"</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Section 4: Interview Execution Guide */}
              {result.executionGuide && (
                <Card className="border-slate-200 shadow-sm">
                  <CardHeader className="bg-slate-50/50 border-b">
                    <div className="flex items-center gap-2">
                      <PlayCircle className="h-5 w-5 text-emerald-600" />
                      <CardTitle className="text-lg">SECTION 4: INTERVIEW EXECUTION GUIDE</CardTitle>
                    </div>
                    <CardDescription>
                      Step-by-step instructions for scheduling, conducting, and analyzing.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-6">
                    <div className="flex justify-center border-b pb-4 mb-6">
                      <div className="flex space-x-1 rounded-lg bg-slate-100 p-1">
                        {(["before", "during", "after"] as const).map((tab) => (
                          <button
                            key={tab}
                            onClick={() => setActiveGuideTab(tab)}
                            className={`rounded-md px-4 py-1.5 text-sm font-medium transition-all ${
                              activeGuideTab === tab
                                ? "bg-white shadow-sm text-slate-800 font-bold"
                                : "text-slate-500 hover:text-slate-800"
                            }`}
                          >
                            {tab.toUpperCase()} THE INTERVIEW
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="grid gap-6 md:grid-cols-3">
                      {result.executionGuide[activeGuideTab]?.map((guideBlock, idx) => (
                        <div key={idx} className="rounded-lg border bg-white p-5 shadow-sm">
                          <h3 className="font-bold text-slate-800 text-sm uppercase tracking-wider mb-3 pb-2 border-b">
                            {guideBlock.title}
                          </h3>
                          <ul className="space-y-2.5">
                            {guideBlock.items.map((item, idy) => (
                              <li key={idy} className="flex items-start gap-2 text-sm text-slate-600 leading-relaxed">
                                <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
                                <span>{item}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Section 5: Interview Recording Template */}
              {result.recordingTemplate && (
                <Card className="border-slate-200 shadow-sm">
                  <CardHeader className="bg-slate-50/50 border-b">
                    <div className="flex items-center gap-2">
                      <FileText className="h-5 w-5 text-blue-600" />
                      <CardTitle className="text-lg">SECTION 5: INTERVIEW RECORDING TEMPLATE</CardTitle>
                    </div>
                    <CardDescription>
                      Preview mockup of the post-interview data record.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-6 bg-slate-50/30">
                    <div className="rounded-lg border bg-white p-6 shadow-md max-w-3xl mx-auto space-y-6">
                      <div className="flex items-center justify-between border-b pb-4">
                        <div>
                          <h3 className="font-bold text-slate-800">INTERVIEW DOCUMENTATION RECORD</h3>
                          <p className="text-xs text-slate-500">Document immediately after interview</p>
                        </div>
                        <span className="text-[10px] uppercase font-bold text-blue-600 bg-blue-50 px-2 py-1 rounded">Mock Template</span>
                      </div>

                      <div className="grid gap-4 sm:grid-cols-2">
                        {result.recordingTemplate.profileFields.map((f, i) => (
                          <div key={i} className="space-y-1">
                            <label className="text-xs font-bold text-slate-500">{f}</label>
                            <input
                              type="text"
                              disabled
                              placeholder="____________________________"
                              className="w-full bg-slate-50 rounded border p-2 text-sm text-slate-400 cursor-not-allowed"
                            />
                          </div>
                        ))}
                        {result.recordingTemplate.contextFields.map((f, i) => (
                          <div key={i} className="space-y-1">
                            <label className="text-xs font-bold text-slate-500">{f}</label>
                            <input
                              type="text"
                              disabled
                              placeholder="____________________________"
                              className="w-full bg-slate-50 rounded border p-2 text-sm text-slate-400 cursor-not-allowed"
                            />
                          </div>
                        ))}
                      </div>

                      <div className="space-y-4 pt-4 border-t">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">Problem & Behavior Records</h4>
                        {result.recordingTemplate.problemEvidenceFields.map((f, i) => (
                          <div key={i} className="space-y-1">
                            <label className="text-xs font-bold text-slate-600">{f.label}</label>
                            <textarea
                              disabled
                              rows={2}
                              placeholder="Write observed answers here..."
                              className="w-full bg-slate-50 rounded border p-2 text-xs text-slate-400 cursor-not-allowed resize-none"
                            />
                          </div>
                        ))}
                        {result.recordingTemplate.behaviorFields.map((f, i) => (
                          <div key={i} className="space-y-1">
                            <label className="text-xs font-bold text-slate-600">{f}</label>
                            <textarea
                              disabled
                              rows={2}
                              placeholder="Write observed answers here..."
                              className="w-full bg-slate-50 rounded border p-2 text-xs text-slate-400 cursor-not-allowed resize-none"
                            />
                          </div>
                        ))}
                      </div>

                      <div className="space-y-4 pt-4 border-t">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">Motivations & Quotes</h4>
                        <div className="grid gap-4 sm:grid-cols-2">
                          {result.recordingTemplate.frustrationFields.map((f, i) => (
                            <div key={i} className="space-y-1">
                              <label className="text-xs font-bold text-slate-600">{f}</label>
                              <input
                                type="text"
                                disabled
                                placeholder="..."
                                className="w-full bg-slate-50 rounded border p-2 text-sm text-slate-400 cursor-not-allowed"
                              />
                            </div>
                          ))}
                          {result.recordingTemplate.motivationFields.map((f, i) => (
                            <div key={i} className="space-y-1">
                              <label className="text-xs font-bold text-slate-600">{f}</label>
                              <input
                                type="text"
                                disabled
                                placeholder="..."
                                className="w-full bg-slate-50 rounded border p-2 text-sm text-slate-400 cursor-not-allowed"
                              />
                            </div>
                          ))}
                        </div>
                        <div className="space-y-2">
                          <label className="text-xs font-bold text-slate-600">Memorable Direct Quotes</label>
                          {result.recordingTemplate.memorableQuotes.map((q, i) => (
                            <div key={i} className="rounded bg-slate-50 border p-2.5 text-xs text-slate-400 italic">
                              "{q}..."
                            </div>
                          ))}
                        </div>
                        <div className="space-y-1">
                          <label className="text-xs font-bold text-slate-600">{result.recordingTemplate.unexpectedInsights}</label>
                          <textarea
                            disabled
                            rows={2}
                            placeholder="..."
                            className="w-full bg-slate-50 rounded border p-2 text-xs text-slate-400 cursor-not-allowed resize-none"
                          />
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Section 6: Evidence Collection Checklist */}
              {result.evidenceChecklist && (
                <Card className="border-slate-200 shadow-sm">
                  <CardHeader className="bg-slate-50/50 border-b">
                    <div className="flex items-center gap-2">
                      <ListChecks className="h-5 w-5 text-primary" />
                      <CardTitle className="text-lg">SECTION 6: EVIDENCE COLLECTION CHECKLIST</CardTitle>
                    </div>
                    <CardDescription>
                      Use this interactive checklist to audit evidence quality after each interview.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-6">
                    <div className="space-y-3">
                      {result.evidenceChecklist.map((item, idx) => {
                        const splitVal = item.split(":");
                        const label = splitVal[0];
                        const detail = splitVal.slice(1).join(":");
                        const isChecked = Boolean(checklistState[idx]);
                        return (
                          <div
                            key={idx}
                            onClick={() => toggleChecklist(idx)}
                            className={`flex items-start gap-3 rounded-lg border p-4 cursor-pointer transition-all ${
                              isChecked
                                ? "border-emerald-500 bg-emerald-50/40"
                                : "border-slate-200 bg-white hover:bg-slate-50"
                            }`}
                          >
                            <input
                              type="checkbox"
                              aria-label={label}
                              checked={isChecked}
                              onChange={() => {}}
                              className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 mt-0.5 cursor-pointer"
                            />
                            <div>
                              <span className={`font-bold text-sm ${isChecked ? "text-emerald-950" : "text-slate-800"}`}>
                                {label}:
                              </span>
                              <p className={`text-sm mt-0.5 ${isChecked ? "text-emerald-900" : "text-slate-500"}`}>
                                {detail}
                              </p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Final Summary Section */}
              {result.finalSummary && (
                <Card className="border-indigo-150 bg-indigo-50/20 shadow-md">
                  <CardHeader className="bg-indigo-50/40 border-b border-indigo-100">
                    <div className="flex items-center gap-2">
                      <BookOpen className="h-5 w-5 text-indigo-700" />
                      <CardTitle className="text-lg text-indigo-950">FINAL SUMMARY</CardTitle>
                    </div>
                    <CardDescription className="text-indigo-800">
                      Key strategic focus areas generated for validation workflows.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-6">
                    <div className="grid gap-6 md:grid-cols-3">
                      <div className="rounded-lg border border-indigo-100 bg-white p-5 shadow-sm">
                        <h3 className="font-bold text-slate-800 text-sm uppercase tracking-wider mb-3 pb-2 border-b">
                          Critical Assumptions
                        </h3>
                        <ul className="space-y-2">
                          {result.finalSummary.criticalAssumptions.map((a, i) => (
                            <li key={i} className="flex items-start gap-2 text-xs text-slate-600 leading-relaxed">
                              <span className="text-indigo-600 font-bold shrink-0 mt-0.5">•</span>
                              <span>{a}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div className="rounded-lg border border-red-100 bg-white p-5 shadow-sm">
                        <h3 className="font-bold text-slate-800 text-sm uppercase tracking-wider mb-3 pb-2 border-b">
                          Biggest Risks
                        </h3>
                        <ul className="space-y-2">
                          {result.finalSummary.biggestRisks.map((r, i) => (
                            <li key={i} className="flex items-start gap-2 text-xs text-slate-600 leading-relaxed">
                              <span className="text-red-500 font-bold shrink-0 mt-0.5">•</span>
                              <span>{r}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div className="rounded-lg border border-emerald-100 bg-white p-5 shadow-sm">
                        <h3 className="font-bold text-slate-800 text-sm uppercase tracking-wider mb-3 pb-2 border-b">
                          Successful Outcomes
                        </h3>
                        <ul className="space-y-2">
                          {result.finalSummary.successfulInterviews.map((s, i) => (
                            <li key={i} className="flex items-start gap-2 text-xs text-slate-600 leading-relaxed">
                              <span className="text-emerald-600 font-bold shrink-0 mt-0.5">•</span>
                              <span>{s}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </>
      )}
    </main>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   SIMPLE PREMIUM MARKDOWN RENDERER
   ═══════════════════════════════════════════════════════════════════ */
function MarkdownRenderer({ content }: { content: string }) {
  const lines = content.split("\n");
  let inTable = false;
  let tableHeaders: string[] = [];
  let tableRows: string[][] = [];

  const renderedElements: React.ReactNode[] = [];

  const parseInline = (text: string) => {
    const parts = text.split(/\*\*(.*?)\*\*/g);
    return parts.map((part, i) => {
      if (i % 2 === 1) {
        return <strong key={i} className="font-bold text-slate-800">{part}</strong>;
      }
      const subParts = part.split(/\*(.*?)\*/g);
      return subParts.map((subPart, j) => {
        if (j % 2 === 1) {
          return <em key={j} className="italic text-slate-700">{subPart}</em>;
        }
        return subPart;
      });
    });
  };

  const flushTable = (key: number) => {
    if (tableHeaders.length === 0 && tableRows.length === 0) return null;
    const element = (
      <div key={`table-${key}`} className="my-6 overflow-x-auto rounded-lg border bg-white shadow-sm">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50/50">
            <tr>
              {tableHeaders.map((h, i) => (
                <th key={i} className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">
                  {parseInline(h)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-slate-200">
            {tableRows.map((row, idx) => (
              <tr key={idx} className="hover:bg-slate-50/30 transition-colors">
                {row.map((cell, i) => (
                  <td key={i} className="px-4 py-3 text-sm text-slate-600 leading-relaxed">
                    {parseInline(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
    tableHeaders = [];
    tableRows = [];
    inTable = false;
    return element;
  };

  for (let idx = 0; idx < lines.length; idx++) {
    const line = lines[idx].trim();

    if (line.startsWith("|")) {
      inTable = true;
      const cells = line.split("|").map(c => c.trim()).filter((_, i, arr) => i > 0 && i < arr.length - 1);
      if (cells.every(c => c.startsWith(":") || c.startsWith("-") || c.endsWith("-"))) {
        continue;
      }
      if (tableHeaders.length === 0) {
        tableHeaders = cells;
      } else {
        tableRows.push(cells);
      }
      continue;
    } else if (inTable) {
      const table = flushTable(idx);
      if (table) renderedElements.push(table);
    }

    if (line === "") {
      continue;
    }

    if (line.startsWith("# ")) {
      renderedElements.push(<h1 key={idx} className="text-2xl md:text-3xl font-extrabold text-primary tracking-tight mt-8 mb-4 border-b pb-2">{parseInline(line.slice(2))}</h1>);
    } else if (line.startsWith("## ")) {
      renderedElements.push(<h2 key={idx} className="text-xl md:text-2xl font-bold text-slate-800 tracking-tight mt-6 mb-3">{parseInline(line.slice(3))}</h2>);
    } else if (line.startsWith("### ")) {
      renderedElements.push(<h3 key={idx} className="text-lg font-bold text-slate-800 mt-4 mb-2">{parseInline(line.slice(4))}</h3>);
    } else if (line.startsWith("#### ")) {
      renderedElements.push(<h4 key={idx} className="text-base font-bold text-slate-700 mt-3 mb-2">{parseInline(line.slice(5))}</h4>);
    } else if (line.startsWith(">")) {
      renderedElements.push(
        <blockquote key={idx} className="border-l-4 border-secondary/50 bg-secondary/5 p-4 my-4 rounded-r-lg italic text-slate-700 leading-relaxed">
          {parseInline(line.slice(1).trim())}
        </blockquote>
      );
    } else if (line.startsWith("- ") || line.startsWith("* ")) {
      renderedElements.push(
        <ul key={idx} className="list-disc pl-6 space-y-1.5 my-2">
          <li className="text-sm text-slate-600 leading-relaxed">{parseInline(line.slice(2))}</li>
        </ul>
      );
    } else if (/^\d+\.\s/.test(line)) {
      const contentStr = line.replace(/^\d+\.\s/, "");
      renderedElements.push(
        <ol key={idx} className="list-decimal pl-6 space-y-1.5 my-2">
          <li className="text-sm text-slate-600 leading-relaxed">{parseInline(contentStr)}</li>
        </ol>
      );
    } else {
      renderedElements.push(<p key={idx} className="text-sm text-slate-600 leading-relaxed my-3">{parseInline(line)}</p>);
    }
  }

  if (inTable) {
    const table = flushTable(lines.length);
    if (table) renderedElements.push(table);
  }

  return <div className="space-y-1">{renderedElements}</div>;
}