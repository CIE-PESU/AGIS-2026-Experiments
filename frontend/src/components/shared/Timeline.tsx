import { CheckCircle2, Circle, Clock } from "lucide-react";
import type { TimelineEvent } from "@/context/AuthContext";

export function Timeline({ events }: { events: TimelineEvent[] }) {
  return (
    <div className="space-y-0">
      {events.map((event, index) => {
        const isLast = index === events.length - 1;
        const Icon = isLast ? Circle : CheckCircle2;
        return (
          <div key={`${event.label}-${index}`} className="relative flex gap-3 pb-5">
            {!isLast && <span className="absolute left-[9px] top-5 h-full w-px bg-border" />}
            <Icon className={isLast ? "z-10 mt-0.5 h-5 w-5 fill-secondary text-secondary" : "z-10 mt-0.5 h-5 w-5 text-emerald-600"} />
            <div>
              <p className="text-sm font-semibold">{event.label}</p>
              <p className="flex items-center gap-1 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                {event.timestamp}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
