import { useState } from "react";
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
  BookOpen
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { generateJTBD } from "@/services/api";
import { triggerDiscovery } from "@/services/authSessions";
import { USE_MOCK_FLOWS } from "@/constants";
import { useAuth } from "@/context/AuthContext";
import type { JTBDResult } from "@/data/mockData";
import { downloadMarkdown, generateDiscoveryMarkdown } from "@/utils/exportMarkdown";

export function DiscoveryFlow() {
  const { session, sessionId, results, saveResults, unlockNext, addEvent } = useAuth();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<JTBDResult | null>(results.discovery);
  const [checklistState, setChecklistState] = useState<Record<number, boolean>>({});
  const [activeGuideTab, setActiveGuideTab] = useState<"before" | "during" | "after">("before");

  if (session.discovery === "locked") return <Navigate to="/workspace" replace />;

  async function startDiscovery() {
    setLoading(true);
    addEvent("Discovery Triggered");
    try {
      if (sessionId) await triggerDiscovery(sessionId);
    } catch {
      if (!USE_MOCK_FLOWS) {
        setLoading(false);
        return;
      }
    }
    const data = await generateJTBD();
    setResult(data);
    saveResults("discovery", data);
    unlockNext("discovery");
    addEvent("Discovery Completed");
    setLoading(false);
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

      {/* Trigger Area */}
      {!result && !loading && (
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

      {/* Structured Result Output */}
      {result && (
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
                {result.objectives.map((obj) => (
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
                {result.assumptions.map((ass, i) => (
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
                {result.interviewGuide.map((guide, i) => (
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
                {result.executionGuide[activeGuideTab].map((guideBlock, idx) => (
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

          {/* Section 5: Interview Recording Template */}
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

          {/* Section 6: Evidence Collection Checklist */}
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

          {/* Final Summary Section */}
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
        </div>
      )}
    </main>
  );
}
