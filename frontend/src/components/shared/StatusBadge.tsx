import { AlertCircle, CheckCircle2, Circle, Clock, Lock, PlayCircle, RefreshCw, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

const map = {
  green: ["bg-emerald-50 text-emerald-700 border-emerald-200", CheckCircle2, "Green"],
  yellow: ["bg-amber-50 text-amber-700 border-amber-200", AlertCircle, "Yellow"],
  red: ["bg-red-50 text-red-700 border-red-200", XCircle, "Red"],
  queued: ["bg-slate-50 text-slate-700 border-slate-200", Clock, "Queued"],
  processing: ["bg-blue-50 text-blue-700 border-blue-200", RefreshCw, "Processing"],
  done: ["bg-emerald-50 text-emerald-700 border-emerald-200", CheckCircle2, "Done"],
  failed: ["bg-red-50 text-red-700 border-red-200", XCircle, "Failed"],
  retry: ["bg-orange-50 text-orange-700 border-orange-200", RefreshCw, "Retry"],
  passed: ["bg-emerald-50 text-emerald-700 border-emerald-200", CheckCircle2, "Passed"],
  warning: ["bg-amber-50 text-amber-700 border-amber-200", AlertCircle, "Warning"],
  locked: ["bg-slate-100 text-slate-600 border-slate-200", Lock, "Locked"],
  available: ["bg-blue-50 text-secondary border-blue-200", PlayCircle, "Available"],
  completed: ["bg-emerald-50 text-emerald-700 border-emerald-200", CheckCircle2, "Completed"],
  in_progress: ["bg-amber-50 text-amber-700 border-amber-200", Circle, "In Progress"]
} as const;

export function StatusBadge({ type, label }: { type: keyof typeof map; label?: string }) {
  const [classes, Icon, defaultLabel] = map[type];
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-semibold", classes)}>
      <Icon className="h-3.5 w-3.5" />
      {label || defaultLabel}
    </span>
  );
}

export function TrafficDot({ status }: { status: "green" | "yellow" | "red" }) {
  const cls = {
    green: "bg-emerald-500 ring-emerald-200",
    yellow: "bg-amber-400 ring-amber-200",
    red: "bg-red-500 ring-red-200"
  }[status];
  return <span className={cn("inline-block h-5 w-5 rounded-full ring-2 ring-offset-1", cls)} />;
}
