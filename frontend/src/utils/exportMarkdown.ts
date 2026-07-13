import { preEvaluationQuestions, type DFVResult, type JTBDResult, type TIPSCResult } from "@/data/mockData";

const light = { green: "🟢", yellow: "🟡", red: "🔴" } as const;

export function generateMarkdown(
  results: { tips: TIPSCResult | null; dfv: DFVResult | null; discovery: JTBDResult | null },
  formData: Record<string, string>
) {
  const lines = [`# Agentic AI Entrepreneurship Report`, `Generated: ${new Date().toLocaleString()}`, ""];
  lines.push("## Pre-Evaluation Responses");
  preEvaluationQuestions.forEach((q) => lines.push(`- **${q.label}:** ${formData[q.key] || "Not provided"}`));
  if (results.tips) {
    lines.push("", "## TIPS Evaluation");
    Object.entries(results.tips.scores).forEach(([key, score]) => {
      lines.push(`- ${light[score.status]} **${key.toUpperCase()}:** ${score.explanation}`);
    });
    lines.push(`- **Ready for DFV:** ${results.tips.readyForDFV ? "Yes" : "No"}`, results.tips.explanation);

    if (results.tips.followUps && results.tips.followUps.length > 0) {
      lines.push("", "### Follow-up Questions & Answers");
      results.tips.followUps.forEach((item, index) => {
        lines.push(
          `**Q${index + 1}:** ${item.question}`,
          `**A${index + 1}:** ${item.answer}`,
          ""
        );
      });
    }
  }
  if (results.dfv) {
    lines.push("", "## DFV Analysis", `**Decision:** ${results.dfv.decision}`, results.dfv.executiveSummary);
    Object.entries(results.dfv.dimensions).forEach(([key, item]) => {
      lines.push(`### ${key}`, `${light[item.status]} ${item.summary}`, ...item.details.map((detail) => `- ${detail}`));
    });
    lines.push("### Recommendations", ...results.dfv.recommendations.map((rec, index) => `${index + 1}. ${rec}`));
  }
  if (results.discovery) {
    const disc = results.discovery;
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
