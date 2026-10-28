import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  Loader2,
  TrendingUp,
  Target,
  Sparkles,
  Zap,
  ShieldCheck,
  Heart,
  Share2,
  Repeat,
  Smile,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { triggerPmf, getSession } from "@/services/authSessions";
import { useAuth } from "@/context/AuthContext";
import type { PMFResult, PMFMetrics, RiskAssessment, SeanEllisTest, NetPromoterScore, RetentionAnalysis } from "@/types/api";
import { toast } from "sonner";

export function PMFFlow() {
  const { session, sessionId, serverStatus, results, addEvent } = useAuth();
  
  const [phase, setPhase] = useState<"trigger" | "processing" | "results">(
    (serverStatus === "pmf_running" || serverStatus === "pmf_waiting")
      ? "processing"
      : results.pmf
      ? "results"
      : "trigger"
  );
  const [submitting, setSubmitting] = useState(false);
  const [pmfData, setPmfData] = useState<PMFResult | null>(results.pmf || null);

  useEffect(() => {
    if (results.pmf) {
      setPmfData(results.pmf);
      setPhase("results");
    }
  }, [results.pmf]);

  useEffect(() => {
    let interval: any = null;
    if (phase === "processing") {
      if (serverStatus === "pmf_completed" && results.pmf) {
        setPmfData(results.pmf);
        setPhase("results");
        addEvent("PMF Analysis Completed");
      } else if (serverStatus === "pmf_failed") {
        setPhase("trigger");
        toast.error("PMF Analysis failed. Please retry.");
      } else if (sessionId) {
        interval = setInterval(async () => {
          try {
            const updatedDoc = await getSession(sessionId);
            if (updatedDoc.pmf) {
              setPmfData(updatedDoc.pmf);
              setPhase("results");
              addEvent("PMF Analysis Completed");
              clearInterval(interval);
            }
          } catch (e) {
            // silent polling error
          }
        }, 3000);
      }
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [phase, serverStatus, results.pmf, sessionId, addEvent]);

  async function handleRunPMF() {
    if (submitting || !sessionId) return;
    setSubmitting(true);
    setPhase("processing");
    addEvent("PMF Triggered");
    try {
      await triggerPmf(sessionId);
      toast.success("Product-Market Fit evaluation started!");
    } catch (err: any) {
      toast.error(err?.message || "Failed to start PMF analysis.");
      setPhase("trigger");
    } finally {
      setSubmitting(false);
    }
  }

  // Extract nested or root PMF data
  const resultObj = pmfData?.output || pmfData;
  const metrics: PMFMetrics | undefined = resultObj?.pmf_metrics;
  const execSummary = resultObj?.executive_summary || (typeof resultObj?.raw === "string" ? resultObj.raw : "");
  const riskAssessment: RiskAssessment | undefined = resultObj?.risk_assessment;
  const recommendations: string[] = resultObj?.recommendations || [];

  const seanEllis: SeanEllisTest | undefined = resultObj?.sean_ellis_test || metrics?.sean_ellis_test;
  const npsData: NetPromoterScore | undefined = resultObj?.net_promoter_score || metrics?.net_promoter_score;
  const retentionData: RetentionAnalysis | undefined = resultObj?.retention_analysis || metrics?.retention_analysis;

  const score = metrics?.pmf_score ?? 0;
  let scoreColor = "text-amber-500 border-amber-500 bg-amber-500/10";
  if (score >= 70) scoreColor = "text-emerald-500 border-emerald-500 bg-emerald-500/10";
  else if (score < 50) scoreColor = "text-red-500 border-red-500 bg-red-500/10";

  return (
    <main className="mx-auto max-w-5xl px-4 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
              Stage 4 • Final Analysis
            </span>
          </div>
          <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-foreground">
            Product-Market Fit (PMF) Analysis
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Evaluating Sean Ellis Test, NPS Score, Uri Levine Retention dynamics, and strategic market fit.
          </p>
        </div>
        <Button asChild variant="outline">
          <Link to="/workspace">Back to Workspace</Link>
        </Button>
      </div>

      {/* Phase 1: Trigger Card */}
      {phase === "trigger" && (
        <Card className="border-2 border-primary/20 shadow-lg backdrop-blur-sm bg-card">
          <CardHeader className="text-center pb-2">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary mb-4">
              <BarChart3 className="h-8 w-8" />
            </div>
            <CardTitle className="text-2xl font-bold">Ready for PMF Viability Assessment</CardTitle>
            <CardDescription className="max-w-lg mx-auto text-base">
              The PMF agent evaluates your product using the Sean Ellis Test (&ge;40% threshold), Net Promoter Score (&gt;50 threshold), and Uri Levine Retention Curve framework.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 pt-4 text-center">
            {serverStatus === "pmf_failed" && (
              <div className="rounded-lg bg-red-500/10 p-4 border border-red-500/30 text-red-600 font-medium text-sm max-w-md mx-auto">
                Previous evaluation failed. Please click below to retry.
              </div>
            )}
            <div className="grid gap-4 md:grid-cols-3 max-w-3xl mx-auto text-left">
              <div className="p-4 rounded-xl border border-border bg-muted/40 space-y-2">
                <div className="flex items-center gap-2 font-semibold text-foreground text-sm">
                  <Heart className="h-4 w-4 text-rose-500" /> Sean Ellis Test
                </div>
                <p className="text-xs text-muted-foreground">Measures % of users who would be "Very Disappointed" without the product (Target: &ge; 40%).</p>
              </div>
              <div className="p-4 rounded-xl border border-border bg-muted/40 space-y-2">
                <div className="flex items-center gap-2 font-semibold text-foreground text-sm">
                  <Share2 className="h-4 w-4 text-blue-500" /> NPS Metric
                </div>
                <p className="text-xs text-muted-foreground">Assesses likelihood to recommend on a 0-10 scale (Target: NPS &gt; 50 signals strong PMF).</p>
              </div>
              <div className="p-4 rounded-xl border border-border bg-muted/40 space-y-2">
                <div className="flex items-center gap-2 font-semibold text-foreground text-sm">
                  <Repeat className="h-4 w-4 text-emerald-500" /> Retention Curve
                </div>
                <p className="text-xs text-muted-foreground">Uri Levine Framework: Verifies flattening retention curves & "smile curve" engagement signals.</p>
              </div>
            </div>

            <Button
              size="lg"
              className="px-8 py-6 text-base font-semibold shadow-md gap-2"
              disabled={submitting}
              onClick={handleRunPMF}
            >
              {submitting ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" /> Starting PMF Agent...
                </>
              ) : (
                <>
                  <Zap className="h-5 w-5 fill-current" /> Execute PMF Evaluation
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Phase 2: Processing State */}
      {phase === "processing" && (
        <Card className="border-2 border-primary/20 shadow-xl p-8 text-center space-y-6">
          <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-primary/10 text-primary animate-pulse">
            <Loader2 className="h-10 w-10 animate-spin" />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-foreground">PMF Agent Analyzing Viability</h2>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              Evaluating Sean Ellis Test, Net Promoter Score (NPS), Uri Levine Retention dynamics, and market alignment...
            </p>
          </div>
          <div className="max-w-md mx-auto h-2 overflow-hidden rounded-full bg-muted">
            <div className="h-full w-3/4 animate-pulse rounded-full bg-primary" />
          </div>
        </Card>
      )}

      {/* Phase 3: Results Display */}
      {phase === "results" && (
        <div className="space-y-6">
          {/* Top Row: Score + Key Metrics */}
          <div className="grid gap-6 md:grid-cols-3">
            {/* Score Card */}
            <Card className="md:col-span-1 border-2 shadow-md flex flex-col justify-between">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                  Overall PMF Score
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col items-center justify-center py-6 space-y-4">
                <div className={`flex h-32 w-32 items-center justify-center rounded-full border-4 text-4xl font-extrabold ${scoreColor}`}>
                  {metrics?.pmf_score ?? "--"}
                  <span className="text-xl font-normal text-muted-foreground">/100</span>
                </div>
                <div className="text-center space-y-1">
                  <span className="text-xs font-semibold px-3 py-1 rounded-full bg-muted text-foreground">
                    {score >= 70 ? "High Market Viability" : score >= 50 ? "Moderate Viability" : "Low Market Readiness"}
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Metrics Breakdown */}
            <Card className="md:col-span-2 shadow-md">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-primary" /> Key Metric Analysis
                </CardTitle>
              </CardHeader>
              <CardContent className="grid gap-4 sm:grid-cols-2 pt-2">
                <div className="p-3 rounded-lg border border-border bg-card">
                  <span className="text-xs font-medium text-muted-foreground">Product-Market Alignment</span>
                  <p className="mt-1 text-sm font-semibold text-foreground">{metrics?.product_market_alignment || "N/A"}</p>
                </div>
                <div className="p-3 rounded-lg border border-border bg-card">
                  <span className="text-xs font-medium text-muted-foreground">Target Market Demand</span>
                  <p className="mt-1 text-sm font-semibold text-foreground">{metrics?.target_market_demand || "N/A"}</p>
                </div>
                <div className="p-3 rounded-lg border border-border bg-card">
                  <span className="text-xs font-medium text-muted-foreground">Value Proposition Strength</span>
                  <p className="mt-1 text-sm font-semibold text-foreground">{metrics?.value_proposition_strength || "N/A"}</p>
                </div>
                <div className="p-3 rounded-lg border border-border bg-card">
                  <span className="text-xs font-medium text-muted-foreground">Defensibility / Moat</span>
                  <p className="mt-1 text-sm font-semibold text-foreground">{metrics?.defensibility || "N/A"}</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* PMF Framework Cards: Sean Ellis, NPS, and Retention */}
          <div className="grid gap-6 md:grid-cols-3">
            {/* 1. Sean Ellis Test */}
            <Card className="shadow-md border-t-4 border-t-rose-500">
              <CardHeader className="pb-2 flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Heart className="h-4 w-4 text-rose-500" /> Sean Ellis Test
                </CardTitle>
                <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${
                  (seanEllis?.very_disappointed_percentage ?? 0) >= 40
                    ? "bg-emerald-500/10 text-emerald-600 border border-emerald-500/30"
                    : "bg-amber-500/10 text-amber-600 border border-amber-500/30"
                }`}>
                  {(seanEllis?.very_disappointed_percentage ?? 0) >= 40 ? "Target Met" : "Below Target"}
                </span>
              </CardHeader>
              <CardContent className="space-y-3 pt-1">
                <div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-2xl font-bold text-foreground">
                      {seanEllis?.very_disappointed_percentage ?? 0}%
                    </span>
                    <span className="text-xs font-medium text-muted-foreground">Target: &ge; 40%</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">"Very disappointed" if product disappears</p>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className={`h-full rounded-full ${
                      (seanEllis?.very_disappointed_percentage ?? 0) >= 40 ? "bg-rose-500" : "bg-amber-500"
                    }`}
                    style={{ width: `${Math.min(100, seanEllis?.very_disappointed_percentage ?? 0)}%` }}
                  />
                </div>
                {seanEllis?.analysis && (
                  <p className="text-xs text-foreground/80 leading-relaxed pt-1 border-t border-border/50">
                    {seanEllis.analysis}
                  </p>
                )}
              </CardContent>
            </Card>

            {/* 2. Net Promoter Score (NPS) */}
            <Card className="shadow-md border-t-4 border-t-blue-500">
              <CardHeader className="pb-2 flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Share2 className="h-4 w-4 text-blue-500" /> Net Promoter Score
                </CardTitle>
                <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${
                  (npsData?.nps_score ?? 0) > 50
                    ? "bg-emerald-500/10 text-emerald-600 border border-emerald-500/30"
                    : "bg-amber-500/10 text-amber-600 border border-amber-500/30"
                }`}>
                  {(npsData?.nps_score ?? 0) > 50 ? "Strong PMF (>50)" : "Needs Work"}
                </span>
              </CardHeader>
              <CardContent className="space-y-3 pt-1">
                <div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-2xl font-bold text-foreground">
                      {npsData?.nps_score ?? 0}
                    </span>
                    <span className="text-xs font-medium text-muted-foreground">Target: NPS &gt; 50</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">Scale 0-10 Likelihood to Recommend</p>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className={`h-full rounded-full ${
                      (npsData?.nps_score ?? 0) > 50 ? "bg-blue-500" : "bg-amber-500"
                    }`}
                    style={{ width: `${Math.min(100, Math.max(0, npsData?.nps_score ?? 0))}%` }}
                  />
                </div>
                {npsData?.promoters_ratio && (
                  <p className="text-xs text-foreground/80 leading-relaxed pt-1 border-t border-border/50">
                    {npsData.promoters_ratio}
                  </p>
                )}
              </CardContent>
            </Card>

            {/* 3. Retention Analysis (Uri Levine Framework) */}
            <Card className="shadow-md border-t-4 border-t-emerald-500">
              <CardHeader className="pb-2 flex flex-row items-center justify-between">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Repeat className="h-4 w-4 text-emerald-500" /> Retention Curve
                </CardTitle>
                <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${
                  retentionData?.value_creation_signal === "STRONG"
                    ? "bg-emerald-500/10 text-emerald-600 border border-emerald-500/30"
                    : "bg-amber-500/10 text-amber-600 border border-amber-500/30"
                }`}>
                  {retentionData?.value_creation_signal || "MODERATE"} Value Creation
                </span>
              </CardHeader>
              <CardContent className="space-y-3 pt-1">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-base font-bold text-foreground flex items-center gap-1.5">
                      <Smile className="h-4 w-4 text-emerald-500" />
                      {retentionData?.curve_trajectory || "Flattening Curve"}
                    </span>
                    <span className="text-xs font-medium text-emerald-600 bg-emerald-500/10 px-2 py-0.5 rounded">
                      Uri Levine Model
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">Retention flattens over time rather than decaying</p>
                </div>
                {retentionData?.summary && (
                  <p className="text-xs text-foreground/80 leading-relaxed pt-1 border-t border-border/50">
                    {retentionData.summary}
                  </p>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Executive Summary */}
          {execSummary && (
            <Card className="shadow-md border-l-4 border-l-primary">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg font-bold">Executive Summary</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-foreground/90 leading-relaxed whitespace-pre-line">{execSummary}</p>
              </CardContent>
            </Card>
          )}

          {/* Risk Assessment */}
          {riskAssessment && (
            <Card className="shadow-md">
              <CardHeader className="pb-2 flex flex-row items-center justify-between">
                <CardTitle className="text-base font-semibold flex items-center gap-2 text-foreground">
                  <ShieldAlert className="h-5 w-5 text-amber-500" /> Risk Assessment
                </CardTitle>
                <span className={`px-2.5 py-0.5 text-xs font-bold rounded-full ${
                  riskAssessment.risk_level === "LOW"
                    ? "bg-emerald-500/10 text-emerald-600 border border-emerald-500/30"
                    : riskAssessment.risk_level === "MODERATE"
                    ? "bg-amber-500/10 text-amber-600 border border-amber-500/30"
                    : "bg-red-500/10 text-red-600 border border-red-500/30"
                }`}>
                  Risk Level: {riskAssessment.risk_level}
                </span>
              </CardHeader>
              <CardContent className="pt-2">
                {riskAssessment.key_risks && riskAssessment.key_risks.length > 0 ? (
                  <ul className="space-y-2 text-sm">
                    {riskAssessment.key_risks.map((risk, i) => (
                      <li key={i} className="flex items-start gap-2 text-foreground/90">
                        <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
                        <span>{risk}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">No significant risks flagged.</p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Recommendations */}
          {recommendations.length > 0 && (
            <Card className="shadow-md">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-emerald-500" /> Strategic Recommendations
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-2">
                <ol className="space-y-2 text-sm text-foreground/90">
                  {recommendations.map((rec, i) => (
                    <li key={i} className="flex items-start gap-3">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                        {i + 1}
                      </span>
                      <span className="pt-0.5">{rec}</span>
                    </li>
                  ))}
                </ol>
              </CardContent>
            </Card>
          )}

          {/* Bottom Actions */}
          <div className="flex items-center justify-between border-t border-border pt-6">
            <Button variant="outline" onClick={handleRunPMF} disabled={submitting}>
              {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Re-run PMF Analysis
            </Button>
            <Button asChild variant="secondary" className="gap-2">
              <Link to="/workspace">
                Return to Workspace <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      )}
    </main>
  );
}
