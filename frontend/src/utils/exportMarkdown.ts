import { preEvaluationQuestions, type DFVResult, type JTBDResult, type TIPSResult } from "@/data/mockData";

const light = { green: "🟢", yellow: "🟡", red: "🔴" } as const;

export function generateMarkdown(
  results: { tips: TIPSResult | null; dfv: DFVResult | null; discovery: JTBDResult | null },
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
  }
  if (results.dfv) {
    lines.push("", "## DFV Analysis", `**Decision:** ${results.dfv.decision}`, results.dfv.executiveSummary);
    Object.entries(results.dfv.dimensions).forEach(([key, item]) => {
      lines.push(`### ${key}`, `${light[item.status]} ${item.summary}`, ...item.details.map((detail) => `- ${detail}`));
    });
    lines.push("### Recommendations", ...results.dfv.recommendations.map((rec, index) => `${index + 1}. ${rec}`));
  }
  if (results.discovery) {
    lines.push("", "## Customer Discovery", "### Customer Jobs");
    results.discovery.jobs.forEach((job) => lines.push(`- **${job.title}:** ${job.context} Outcome: ${job.outcome}`));
    lines.push("### Interview Plan", results.discovery.interviewPlan.objective);
    lines.push(`Sample size: ${results.discovery.interviewPlan.sampleSize}`);
    lines.push("Questions:", ...results.discovery.interviewPlan.questions.map((q, index) => `${index + 1}. ${q}`));
    lines.push("### Recommendations", ...results.discovery.recommendations.map((rec, index) => `${index + 1}. ${rec}`));
  }
  return lines.join("\n");
}

export function downloadMarkdown(content: string, filename: string) {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
