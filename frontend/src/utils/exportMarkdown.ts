import { preEvaluationQuestions, type DFVResult, type JTBDResult, type TIPSCResult } from "@/data/mockData";
import type { SessionDocument } from "@/types/api";

const light = { green: "🟢", yellow: "🟡", red: "🔴", GREEN: "🟢", YELLOW: "🟡", RED: "🔴" } as const;

function statusIcon(status?: string | null) {
  if (!status) return "🟢";
  return light[status as keyof typeof light] || "🟢";
}

function fmtDate(value?: string | null) {
  if (!value) return "Unknown";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

export type TimelineEventLike = { label: string; timestamp: string };

export type ExportInput = {
  results: { tips: TIPSCResult | null; dfv: DFVResult | null; discovery: JTBDResult | null };
  formData: Record<string, string>;
  sessionDoc?: SessionDocument | null;
  timeline?: TimelineEventLike[];
};

/**
 * Builds a full markdown transcript of the session: every user input (initial
 * pre-evaluation answers, DFV context answers, discovery questionnaire answers,
 * and every follow-up question/answer exchanged with the founder), plus the
 * complete output of every agent (Pre-Evaluation, Validation, Regulatory,
 * Ethics, TIPSC, DFV, Discovery). Whenever the richer `sessionDoc` from the
 * backend is available it is used as the source of truth (it carries fields
 * the simplified `results` objects drop); `results`/`formData` are used as a
 * fallback so the export still works for locally-mocked sessions.
 */
export function generateMarkdown(input: ExportInput): string;
// Back-compat overload for older call sites passing (results, formData) directly.
export function generateMarkdown(
  results: { tips: TIPSCResult | null; dfv: DFVResult | null; discovery: JTBDResult | null },
  formData: Record<string, string>
): string;
export function generateMarkdown(
  arg1: ExportInput | { tips: TIPSCResult | null; dfv: DFVResult | null; discovery: JTBDResult | null },
  arg2?: Record<string, string>
): string {
  const input: ExportInput =
    arg2 !== undefined ? { results: arg1 as any, formData: arg2 } : (arg1 as ExportInput);
  const { results, formData, sessionDoc, timeline } = input;

  const lines = [
    `# Agentic AI Entrepreneurship Report`,
    `Generated: ${new Date().toLocaleString()}`
  ];
  if (sessionDoc?.session_id) lines.push(`Session ID: ${sessionDoc.session_id}`);
  if (sessionDoc?.created_at) lines.push(`Session Started: ${fmtDate(sessionDoc.created_at)}`);
  if (sessionDoc?.updated_at) lines.push(`Last Updated: ${fmtDate(sessionDoc.updated_at)}`);
  if (sessionDoc?.status) lines.push(`Status: ${sessionDoc.status.replace(/_/g, " ")}`);
  lines.push("");

  // ── Initial idea inputs ────────────────────────────────────────────────
  lines.push("## Initial Idea Inputs (Pre-Evaluation Form)");
  const preeval = sessionDoc?.preeval;
  if (preeval) {
    lines.push(
      `- **Problem Statement:** ${preeval.problem_statement || "Not provided"}`,
      `- **Customer Segment:** ${preeval.customer_segment || "Not provided"}`,
      `- **Consequence:** ${preeval.consequence || "Not provided"}`,
      `- **Proposed Solution:** ${preeval.proposed_solution || "Not provided"}`,
      `- **Target Geography:** ${preeval.target_geography || "Not provided"}`,
      `- **Industry Sector:** ${preeval.industry_sector || "Not provided"}`,
      `- **Assumptions:**`
    );
    (preeval.assumptions || []).forEach((a) => lines.push(`  - ${a}`));
    if (!preeval.assumptions || preeval.assumptions.length === 0) lines.push(`  - Not provided`);
  } else {
    preEvaluationQuestions.forEach((q) => lines.push(`- **${q.label}:** ${formData[q.key] || "Not provided"}`));
  }

  // ── Validation Agent ────────────────────────────────────────────────────
  if (sessionDoc?.validation) {
    const v = sessionDoc.validation;
    lines.push("", "## Validation Agent Output");
    lines.push(`- **Target Geography:** ${v.target_geography || "-"}`, `- **Industry Sector:** ${v.industry_sector || "-"}`);
    lines.push("", "### Checked Assumptions");
    (v.checked_assumptions || []).forEach((c) => {
      lines.push(`- **${c.assumption}** — ${c.verdict}`, `  - Evidence: ${c.evidence}`);
    });
    lines.push(
      "",
      `**Competitor Landscape:** ${v.competitor_landscape || "-"}`,
      `**Market Notes:** ${v.market_notes || "-"}`,
      `**Validation Summary:** ${v.validation_summary}`
    );
  }

  // ── Regulatory Agent ────────────────────────────────────────────────────
  if (sessionDoc?.regulatory) {
    const r = sessionDoc.regulatory;
    lines.push("", "## Regulatory Agent Output");
    lines.push(`- **Target Geography:** ${r.target_geography || "-"}`, `- **Industry Sector:** ${r.industry_sector || "-"}`);
    lines.push("", "### Applicable Regulations");
    (r.applicable_regulations || []).forEach((reg) => {
      lines.push(
        `- **${reg.name}** (${reg.compliance_burden} burden)`,
        `  - Jurisdiction: ${reg.jurisdiction}`,
        `  - Requirement: ${reg.brief_requirement}`
      );
    });
    lines.push(
      "",
      `**Regulatory Summary:** ${r.regulatory_summary || "-"}`,
      `**Requires Specialist Review:** ${r.requires_specialist_review ? "Yes" : "No"}`,
      "",
      "### Key Compliance Risks"
    );
    (r.key_compliance_risks || []).forEach((risk) => lines.push(`- ${risk}`));
  }

  // ── Ethics Agent ────────────────────────────────────────────────────────
  if (sessionDoc?.ethics) {
    const e = sessionDoc.ethics;
    lines.push(
      "",
      "## Ethics Agent Output",
      `- ${statusIcon(e.harm_vector)} **Harm Vector:** ${e.harm_reason}`,
      `- ${statusIcon(e.legal_risk)} **Legal Risk:** ${e.legal_reason}`,
      `- ${statusIcon(e.problem_solution_integrity)} **Problem-Solution Integrity:** ${e.integrity_reason}`,
      `- **Ethics Decision:** ${e.ethics_pass ? "PASSED" : "FAILED"}`,
      `- **Compliance Flag:** ${e.compliance_flag ? "Yes" : "No"}`
    );
    if (e.rejection_reason) lines.push(`- **Rejection Reason:** ${e.rejection_reason}`);
  }

  // ── TIPSC Evaluation ────────────────────────────────────────────────────
  const tipsc = sessionDoc?.tipsc;
  if (tipsc) {
    lines.push("", "## TIPSC Evaluation");
    const rag = tipsc.tips_rag_scores;
    lines.push(
      `- ${statusIcon(rag.T)} **Timely:** ${rag.T_reason}`,
      `- ${statusIcon(rag.I)} **Important:** ${rag.I_reason}`,
      `- ${statusIcon(rag.P)} **Profitable:** ${rag.P_reason}`,
      `- ${statusIcon(rag.S)} **Solvable:** ${rag.S_reason}`,
      `- **Solution Alignment:** ${statusIcon(tipsc.solution_alignment)} ${tipsc.solution_alignment}`,
      `- **Overall Readiness:** ${tipsc.overall_readiness}`,
      `- **Ready for DFV:** ${tipsc.ready_for_dfv ? "Yes" : "No"}`,
      `- **Needs Follow-up:** ${tipsc.needs_followup ? "Yes" : "No"}`,
      `- **Compliance Flag:** ${tipsc.compliance_flag ? "Yes" : "No"}`,
      `- **Follow-ups Asked:** ${tipsc.followups_asked}`
    );
    if (tipsc.missing_criteria?.length) lines.push(`- **Missing Criteria:** ${tipsc.missing_criteria.join(", ")}`);
    lines.push("", "**Reasoning:**", tipsc.reasoning || "-");

    if (tipsc.refined_idea) {
      lines.push(
        "",
        "### Refined Idea (post follow-up)",
        `- **Customer Segment:** ${tipsc.refined_idea.customer_segment}`,
        `- **Qualified Problem:** ${tipsc.refined_idea.qualified_problem}`,
        `- **Consequence:** ${tipsc.refined_idea.consequence}`,
        `- **Proposed Solution:** ${tipsc.refined_idea.proposed_solution}`
      );
    }

    if (tipsc.tips_validated_metrics) {
      const m = tipsc.tips_validated_metrics;
      lines.push(
        "",
        "### Validated Metrics",
        `- **Timely Factor:** ${m.timely_factor}`,
        `- **Importance Metric:** ${m.importance_metric}`,
        `- **Profitability Pivot:** ${m.profitability_pivot}`,
        `- **Solvability Constraint:** ${m.solvability_constraint}`
      );
    }
  } else if (results.tips) {
    lines.push("", "## TIPS Evaluation");
    Object.entries(results.tips.scores).forEach(([key, score]) => {
      lines.push(`- ${light[score.status as keyof typeof light || "green"]} **${key.toUpperCase()}:** ${score.explanation}`);
    });
    lines.push(`- **Ready for DFV:** ${results.tips.readyForDFV ? "Yes" : "No"}`, results.tips.explanation);
  }

  // ── Follow-up Q&A history (founder answers requested mid-evaluation) ────
  if (sessionDoc?.followup_history && sessionDoc.followup_history.length > 0) {
    lines.push("", "## Follow-up Questions & Answers");
    [...sessionDoc.followup_history]
      .sort((a, b) => (a.turn ?? 0) - (b.turn ?? 0))
      .forEach((item, index) => {
        lines.push(
          `**Turn ${item.turn ?? index + 1} — Q:** ${item.question}`,
          `**A:** ${item.answer}`,
          `*Answered: ${fmtDate(item.answered_at)}*`,
          ""
        );
      });
  } else if (results.tips?.followUps && results.tips.followUps.length > 0) {
    lines.push("", "### Follow-up Questions & Answers");
    results.tips.followUps.forEach((item, index) => {
      lines.push(`**Q${index + 1}:** ${item.question}`, `**A${index + 1}:** ${item.answer}`, "");
    });
  }

  // ── DFV Analysis ────────────────────────────────────────────────────────
  if (results.dfv || sessionDoc?.dfv) {
    lines.push("", "## DFV Analysis");

    const dfvInputLabels: [string, string][] = [
      ["dfv_desirability_context", "Desirability Context (founder input)"],
      ["dfv_feasibility_context", "Feasibility Context (founder input)"],
      ["dfv_viability_context", "Viability Context (founder input)"]
    ];
    const hasDfvInputs = dfvInputLabels.some(([key]) => formData[key]);
    if (hasDfvInputs) {
      lines.push("### Founder Inputs to DFV");
      dfvInputLabels.forEach(([key, label]) => lines.push(`- **${label}:** ${formData[key] || "Not provided"}`));
      lines.push("");
    }

    const dfvResult = results.dfv as any;
    const decision = dfvResult?.decision ?? dfvResult?.final_decision?.status ?? "NO-GO";
    const executiveSummary = dfvResult?.executiveSummary ?? dfvResult?.final_decision?.justification ?? "";

    lines.push(`**Decision:** ${decision}`, executiveSummary);

    if (dfvResult?.dimensions) {
      Object.entries(dfvResult.dimensions).forEach(([key, item]: [string, any]) => {
        lines.push(`### ${key}`, `${light[item.status as keyof typeof light || "green"]} ${item.summary}`, ...item.details.map((detail: string) => `- ${detail}`));
      });
    } else if (dfvResult?.hypotheses) {
      const hyps = dfvResult.hypotheses;
      const metrics = dfvResult.tips_validated_metrics || {};
      
      lines.push(
        "### Desirability",
        `🟢 ${hyps.desirability_statement || ""}`,
        metrics.importance_metric ? `- ${metrics.importance_metric}` : "",
        "### Feasibility",
        `🟢 ${hyps.feasibility_statement || ""}`,
        metrics.solvability_constraint ? `- ${metrics.solvability_constraint}` : "",
        "### Viability",
        `🟢 ${hyps.viability_statement || ""}`,
        metrics.profitability_pivot ? `- ${metrics.profitability_pivot}` : ""
      );
    }
    
    if (dfvResult?.recommendations && dfvResult.recommendations.length > 0) {
      lines.push("### Recommendations", ...dfvResult.recommendations.map((rec: string, index: number) => `${index + 1}. ${rec}`));
    }
  }

  // ── Customer Discovery ──────────────────────────────────────────────────
  const discoveryInputLabels: [string, string][] = [
    ["discovery_problem", "Problem"],
    ["discovery_targetCustomer", "Target Customer"],
    ["discovery_importance", "Why It Matters"],
    ["discovery_assumptions", "Assumptions"],
    ["discovery_learningObjectives", "Learning Objectives"],
    ["discovery_additionalNotes", "Additional Notes"]
  ];
  const hasDiscoveryInputs = discoveryInputLabels.some(([key]) => formData[key]);
  if (hasDiscoveryInputs) {
    lines.push("", "## Founder Inputs to Customer Discovery");
    discoveryInputLabels.forEach(([key, label]) => lines.push(`- **${label}:** ${formData[key] || "Not provided"}`));
  }

  if (results.discovery) {
    const disc = results.discovery as any;
    if (disc.report) {
      lines.push("", disc.report);
    } else {
      lines.push(
        "",
        `# Customer Discovery Plan: ${disc.title}`,
        "",
        "## SECTION 1: CUSTOMER DISCOVERY OBJECTIVES",
        "",
        "Before interviewing customers, the team must define what success looks like. These objectives focus on gathering evidence to validate or invalidate critical hypotheses about the market and problem severity.",
        "",
        "| Objective | Why It Matters | Assumptions Validated | Evidence Required for Confidence |",
        "| :--- | :--- | :--- | :--- |"
      );
      disc.objectives.forEach((obj: any) => {
        const assumptionsStr = obj.assumptionsValidated.map((a: string) => `• ${a}`).join("<br>");
        const evidenceStr = obj.evidenceRequired.map((e: string) => `• ${e}`).join("<br>");
        lines.push(`| **${obj.objective}** | ${obj.whyItMatters} | ${assumptionsStr} | ${evidenceStr} |`);
      });

      lines.push(
        "",
        "## SECTION 2: ASSUMPTION VALIDATION MATRIX",
        "",
        "Prioritize assumptions by risk level. Focus discovery on validating High and Medium risk items first.",
        "",
        "| Assumption | Why It Matters | Evidence Required | Signals To Look For (Validation) |",
        "| :--- | :--- | :--- | :--- |"
      );
      disc.assumptions.forEach((ass: any) => {
        const evidenceStr = ass.evidenceRequired.map((e: string) => `• ${e}`).join("<br>");
        const signalsStr = ass.signals
          .map((s: any) => `${s.type === "validation" ? "✅" : "❌"} "${s.text}"`)
          .join("<br>");
        lines.push(`| **${ass.risk}:** ${ass.assumption} | ${ass.whyItMatters} | ${evidenceStr} | ${signalsStr} |`);
      });

      lines.push(
        "",
        "## SECTION 3: CUSTOMER DISCOVERY INTERVIEW GUIDE",
        "",
        "Use this guide to structure your conversations. Focus on past behavior and concrete stories rather than hypothetical opinions."
      );
      let questionIndex = 1;
      disc.interviewGuide.forEach((guide: any) => {
        lines.push("", `### ${guide.section} (${guide.subtitle})`);
        guide.questions.forEach((q: string) => {
          lines.push(`${questionIndex}. "${q}"`);
          questionIndex++;
        });
      });

      lines.push(
        "",
        "## SECTION 4: INTERVIEW EXECUTION GUIDE",
        "",
        "Best practices for conducting productive customer discovery interviews.",
        "",
        "### Before The Interview"
      );
      disc.executionGuide.before.forEach((sec: any) => {
        lines.push(`#### ${sec.title}`, ...sec.items.map((item: string) => `- ${item}`));
      });
      lines.push("", "### During The Interview");
      disc.executionGuide.during.forEach((sec: any) => {
        lines.push(`#### ${sec.title}`, ...sec.items.map((item: string) => `- ${item}`));
      });
      lines.push("", "### After The Interview");
      disc.executionGuide.after.forEach((sec: any) => {
        lines.push(`#### ${sec.title}`, ...sec.items.map((item: string) => `- ${item}`));
      });

      lines.push(
        "",
        "## SECTION 5: INTERVIEW RECORDING TEMPLATE",
        "",
        "Use this template to document notes immediately after each interview. Keep a separate copy for each participant.",
        "",
        "### 1. Interviewee Profile",
        ...disc.recordingTemplate.profileFields.map((f: string) => `- **${f}:** ____________________`),
        "",
        "### 2. Context of Discussion",
        ...disc.recordingTemplate.contextFields.map((f: string) => `- **${f}:** ____________________`),
        "",
        "### 3. Problem Evidence",
        ...disc.recordingTemplate.problemEvidenceFields.map((f: any) => `- **${f.label}:** \n  *Notes:* `),
        "",
        "### 4. Current Behavior & Alternatives",
        ...disc.recordingTemplate.behaviorFields.map((f: string) => `- **${f}:** \n  *Notes:* `),
        "",
        "### 5. Frustrations & Anxieties",
        ...disc.recordingTemplate.frustrationFields.map((f: string) => `- **${f}:** \n  *Notes:* `),
        "",
        "### 6. Motivations",
        ...disc.recordingTemplate.motivationFields.map((f: string) => `- **${f}:** \n  *Notes:* `),
        "",
        "### 7. Memorable Quotes",
        ...disc.recordingTemplate.memorableQuotes.map((q: string, i: number) => `- *Quote ${i+1}:* "${q}"`),
        "",
        "### 8. Unexpected Insights",
        `- **${disc.recordingTemplate.unexpectedInsights}:** \n  *Notes:* `,
        "",
        "## SECTION 6: EVIDENCE COLLECTION CHECKLIST",
        "",
        "Use this checklist to grade the quality of evidence collected after each interview.",
        ""
      );
      disc.evidenceChecklist.forEach((item: string) => {
        const splitVal = item.split(":");
        lines.push(`- [ ] **${splitVal[0]}:** ${splitVal.slice(1).join(":")}`);
      });

      lines.push(
        "",
        "## FINAL SUMMARY",
        "",
        "### 1. The Most Critical Assumptions to Validate",
        ...disc.finalSummary.criticalAssumptions.map((a: string) => `- ${a}`),
        "",
        "### 2. The Biggest Risks Discovered So Far",
        ...disc.finalSummary.biggestRisks.map((r: string) => `- ${r}`),
        "",
        "### 3. What Successful Interviews Should Reveal",
        ...disc.finalSummary.successfulInterviews.map((s: string) => `- ${s}`)
      );
    }
  }

  // ── Activity timeline (session-level audit trail) ───────────────────────
  if (timeline && timeline.length > 0) {
    lines.push("", "## Activity Timeline");
    timeline.forEach((event) => lines.push(`- **${event.timestamp}** — ${event.label}`));
  }

  return lines.join("\n");
}

export function downloadMarkdown(content: string, filename: string) {
  const blob = new Blob([content], { type: "application/octet-stream" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function generateDiscoveryMarkdown(disc: JTBDResult): string {
  const lines = [
    `# Customer Discovery Plan: ${disc.title}`,
    "",
    "## SECTION 1: CUSTOMER DISCOVERY OBJECTIVES",
    "",
    "Before interviewing customers, the team must define what success looks like. These objectives focus on gathering evidence to validate or invalidate critical hypotheses about the market and problem severity.",
    "",
    "| Objective | Why It Matters | Assumptions Validated | Evidence Required for Confidence |",
    "| :--- | :--- | :--- | :--- |"
  ];
  disc.objectives.forEach((obj) => {
    const assumptionsStr = obj.assumptionsValidated.map((a) => `• ${a}`).join("<br>");
    const evidenceStr = obj.evidenceRequired.map((e) => `• ${e}`).join("<br>");
    lines.push(`| **${obj.objective}** | ${obj.whyItMatters} | ${assumptionsStr} | ${evidenceStr} |`);
  });

  lines.push(
    "",
    "## SECTION 2: ASSUMPTION VALIDATION MATRIX",
    "",
    "Prioritize assumptions by risk level. Focus discovery on validating High and Medium risk items first.",
    "",
    "| Assumption | Why It Matters | Evidence Required | Signals To Look For (Validation) |",
    "| :--- | :--- | :--- | :--- |"
  );
  disc.assumptions.forEach((ass) => {
    const evidenceStr = ass.evidenceRequired.map((e) => `• ${e}`).join("<br>");
    const signalsStr = ass.signals
      .map((s) => `${s.type === "validation" ? "✅" : "❌"} "${s.text}"`)
      .join("<br>");
    lines.push(`| **${ass.risk}:** ${ass.assumption} | ${ass.whyItMatters} | ${evidenceStr} | ${signalsStr} |`);
  });

  lines.push(
    "",
    "## SECTION 3: CUSTOMER DISCOVERY INTERVIEW GUIDE",
    "",
    "Use this guide to structure your conversations. Focus on past behavior and concrete stories rather than hypothetical opinions."
  );
  let questionIndex = 1;
  disc.interviewGuide.forEach((guide) => {
    lines.push("", `### ${guide.section} (${guide.subtitle})`);
    guide.questions.forEach((q) => {
      lines.push(`${questionIndex}. "${q}"`);
      questionIndex++;
    });
  });

  lines.push(
    "",
    "## SECTION 4: INTERVIEW EXECUTION GUIDE",
    "",
    "Best practices for conducting productive customer discovery interviews.",
    "",
    "### Before The Interview"
  );
  disc.executionGuide.before.forEach((sec) => {
    lines.push(`#### ${sec.title}`, ...sec.items.map((item) => `- ${item}`));
  });
  lines.push("", "### During The Interview");
  disc.executionGuide.during.forEach((sec) => {
    lines.push(`#### ${sec.title}`, ...sec.items.map((item) => `- ${item}`));
  });
  lines.push("", "### After The Interview");
  disc.executionGuide.after.forEach((sec) => {
    lines.push(`#### ${sec.title}`, ...sec.items.map((item) => `- ${item}`));
  });

  lines.push(
    "",
    "## SECTION 5: INTERVIEW RECORDING TEMPLATE",
    "",
    "Use this template to document notes immediately after each interview. Keep a separate copy for each participant.",
    "",
    "### 1. Interviewee Profile",
    ...disc.recordingTemplate.profileFields.map((f) => `- **${f}:** ____________________`),
    "",
    "### 2. Context of Discussion",
    ...disc.recordingTemplate.contextFields.map((f) => `- **${f}:** ____________________`),
    "",
    "### 3. Problem Evidence",
    ...disc.recordingTemplate.problemEvidenceFields.map((f) => `- **${f.label}:** \n  *Notes:* `),
    "",
    "### 4. Current Behavior & Alternatives",
    ...disc.recordingTemplate.behaviorFields.map((f) => `- **${f}:** \n  *Notes:* `),
    "",
    "### 5. Frustrations & Anxieties",
    ...disc.recordingTemplate.frustrationFields.map((f) => `- **${f}:** \n  *Notes:* `),
    "",
    "### 6. Motivations",
    ...disc.recordingTemplate.motivationFields.map((f) => `- **${f}:** \n  *Notes:* `),
    "",
    "### 7. Memorable Quotes",
    ...disc.recordingTemplate.memorableQuotes.map((q, i) => `- *Quote ${i+1}:* "${q}"`),
    "",
    "### 8. Unexpected Insights",
    `- **${disc.recordingTemplate.unexpectedInsights}:** \n  *Notes:* `,
    "",
    "## SECTION 6: EVIDENCE COLLECTION CHECKLIST",
    "",
    "Use this checklist to grade the quality of evidence collected after each interview.",
    ""
  );
  disc.evidenceChecklist.forEach((item) => {
    const splitVal = item.split(":");
    lines.push(`- [ ] **${splitVal[0]}:** ${splitVal.slice(1).join(":")}`);
  });

  lines.push(
    "",
    "## FINAL SUMMARY",
    "",
    "### 1. The Most Critical Assumptions to Validate",
    ...disc.finalSummary.criticalAssumptions.map((a) => `- ${a}`),
    "",
    "### 2. The Biggest Risks Discovered So Far",
    ...disc.finalSummary.biggestRisks.map((r) => `- ${r}`),
    "",
    "### 3. What Successful Interviews Should Reveal",
    ...disc.finalSummary.successfulInterviews.map((s) => `- ${s}`)
  );
  return lines.join("\n");
}
