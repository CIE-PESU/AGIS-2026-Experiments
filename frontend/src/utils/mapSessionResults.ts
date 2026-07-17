import type { TIPSCResult, DFVResult, JTBDResult, Traffic } from "@/data/mockData";

export function mapTipscOutput(backend: any): TIPSCResult | null {
  if (!backend) return null;
  const rag = backend.tips_rag_scores || {};
  const toStatus = (v: string): Traffic => {
    const s = (v || "").toLowerCase();
    if (s === "green" || s === "yellow" || s === "red") return s;
    return "yellow";
  };

  return {
    scores: {
      timely:     { status: toStatus(rag.T), explanation: rag.T_reason || "" },
      importance: { status: toStatus(rag.I), explanation: rag.I_reason || "" },
      profitable: { status: toStatus(rag.P), explanation: rag.P_reason || "" },
      solvable:   { status: toStatus(rag.S), explanation: rag.S_reason || "" },
    },
    readyForDFV: backend.ready_for_dfv ?? false,
    explanation: backend.reasoning || "",
    followUps: []
  };
}

export function mapDfvOutput(backend: any): DFVResult | null {
  if (!backend || !backend.output) return null;
  const out = backend.output;

  return {
    decision: out.decision ?? out.final_decision?.status ?? "NO-GO",
    executiveSummary: out.executive_summary ?? out.final_decision?.justification ?? "",
    dimensions: out.dimensions ?? undefined,
    recommendations: out.recommendations ?? []
  } as DFVResult;
}

export function mapDiscoveryOutput(backend: any): JTBDResult | null {
  if (!backend || !backend.output) return null;
  return backend.output as JTBDResult;
}