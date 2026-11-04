import { AlertCircle, CheckCircle2, Circle, Clock, Lock, PlayCircle, RefreshCw, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

const map = {
  green: ["bg-emerald-50 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/30", CheckCircle2, "Green"],
  yellow: ["bg-amber-50 dark:bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-500/30", AlertCircle, "Yellow"],
  red: ["bg-red-50 dark:bg-red-500/15 text-red-700 dark:text-red-300 border-red-200 dark:border-red-500/30", XCircle, "Red"],
  queued: ["bg-muted text-foreground border-border", Clock, "Queued"],
  processing: ["bg-blue-50 dark:bg-blue-500/15 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-500/30", RefreshCw, "Processing"],
  done: ["bg-emerald-50 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/30", CheckCircle2, "Done"],
  failed: ["bg-red-50 dark:bg-red-500/15 text-red-700 dark:text-red-300 border-red-200 dark:border-red-500/30", XCircle, "Failed"],
  retry: ["bg-orange-50 dark:bg-orange-500/15 text-orange-700 dark:text-orange-300 border-orange-200 dark:border-orange-500/30", RefreshCw, "Retry"],
  passed: ["bg-emerald-50 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/30", CheckCircle2, "Passed"],
  warning: ["bg-amber-50 dark:bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-500/30", AlertCircle, "Warning"],
  locked: ["bg-muted text-muted-foreground border-border", Lock, "Locked"],
  available: ["bg-blue-50 dark:bg-blue-500/15 text-secondary border-blue-200 dark:border-blue-500/30", PlayCircle, "Available"],
  completed: ["bg-emerald-50 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/30", CheckCircle2, "Completed"],
  in_progress: ["bg-amber-50 dark:bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-500/30", Circle, "In Progress"]
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

export function TrafficDot({
  status,
}: {
  status: "green" | "yellow" | "red" | "GREEN" | "YELLOW" | "RED";
}) {
  const normalized = status.toLowerCase() as "green" | "yellow" | "red";

  const cls = {
    green: "bg-emerald-500 ring-emerald-200",
    yellow: "bg-amber-400 ring-amber-200",
    red: "bg-red-500 ring-red-200",
  }[normalized];

  return (
    <span
      className={cn(
        "inline-block h-5 w-5 rounded-full ring-2 ring-offset-1",
        cls
      )}
    />
  );
}
