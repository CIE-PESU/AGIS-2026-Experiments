import { ChevronDown } from "lucide-react";
import { memberConversations, mockTIPSFinal, type StageStatus, type Traffic } from "@/data/mockData";
import { StatusBadge, TrafficDot } from "@/components/shared/StatusBadge";

type StudentDetail = {
  srn: string;
  name?: string;
  lastActive?: string;
  tips?: typeof mockTIPSFinal.scores | Traffic;
  dfv?: string;
  jtbd?: boolean;
};

const fallback = memberConversations.PES1UG21CS001;

function Section({ title, children, open = true }: { title: string; children: React.ReactNode; open?: boolean }) {
  return (
    <details open={open} className="rounded-lg border bg-white p-4">
      <summary className="flex cursor-pointer list-none items-center justify-between text-sm font-semibold">
        {title}
        <ChevronDown className="h-4 w-4" />
      </summary>
      <div className="mt-4">{children}</div>
    </details>
  );
}

export function DetailedProgressView({ student }: { student: StudentDetail }) {
  const conversation = memberConversations[student.srn as keyof typeof memberConversations] || fallback;
  const statuses: { label: string; value: StageStatus }[] = [
    { label: "TIPS", value: "completed" },
    { label: "DFV", value: student.dfv === "Pending" ? "available" : "completed" },
    { label: "JTBD", value: student.jtbd ? "completed" : "locked" }
  ];
  const tips = typeof student.tips === "string" ? mockTIPSFinal.scores : student.tips || mockTIPSFinal.scores;
  return (
    <div className="space-y-4">
      <div className="rounded-lg bg-muted p-4">
        <p className="font-semibold">{student.name || conversation.name}</p>
        <p className="text-sm text-muted-foreground">
          {student.srn} · Last active {student.lastActive || conversation.lastActive}
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {statuses.map((status) => (
          <div key={status.label} className="rounded-lg border p-3">
            <p className="mb-2 text-xs font-semibold text-muted-foreground">{status.label}</p>
            <StatusBadge type={status.value} />
          </div>
        ))}
      </div>
      <Section title="Pre-Evaluation Responses">
        <div className="space-y-3">
          {Object.entries(conversation.preEval).map(([key, value], index) => (
            <div key={key} className="rounded-md bg-muted/70 p-3 text-sm">
              <p className="font-semibold">{index + 1}. {key}</p>
              <p className="mt-1 text-muted-foreground">{value}</p>
            </div>
          ))}
        </div>
      </Section>
      <Section title="TIPS Evaluation Scores" open={false}>
        <div className="grid gap-3 sm:grid-cols-2">
          {Object.entries(tips).map(([key, score]) => (
            <div key={key} className="rounded-md border p-3">
              <div className="mb-2 flex items-center gap-2">
                <TrafficDot status={score.status} />
                <p className="font-semibold capitalize">{key}</p>
              </div>
              <p className="text-sm text-muted-foreground">{score.explanation}</p>
            </div>
          ))}
        </div>
      </Section>
      <Section title="TIPS Follow-up Q&A" open={false}>
        <div className="space-y-3">
          {conversation.followUps.map((item, index) => (
            <div key={item.question} className="grid gap-3 md:grid-cols-2">
              <div className="rounded-md bg-amber-50 p-3 text-sm"><b>AI Question {index + 1}:</b> {item.question}</div>
              <div className="rounded-md bg-emerald-50 p-3 text-sm"><b>Student Response:</b> {item.answer}</div>
            </div>
          ))}
        </div>
      </Section>
      <div className={student.dfv === "NO-GO" ? "rounded-lg bg-red-50 p-4 text-red-700" : "rounded-lg bg-emerald-50 p-4 text-emerald-700"}>
        <b>DFV Decision:</b> {student.dfv || "GO"}
      </div>
      <Section title="DFV Analysis Inputs" open={false}>
        <div className="grid gap-3 md:grid-cols-3">
          {Object.entries(conversation.dfvInputs).map(([key, value]) => (
            <div key={key} className="rounded-md border p-3 text-sm">
              <p className="font-semibold capitalize">{key}</p>
              <p className="mt-1 text-muted-foreground">{value}</p>
            </div>
          ))}
        </div>
      </Section>
      <p className="rounded-lg bg-muted p-3 text-center text-xs font-semibold text-muted-foreground">View only · Mentor comments do not alter student submissions.</p>
    </div>
  );
}
