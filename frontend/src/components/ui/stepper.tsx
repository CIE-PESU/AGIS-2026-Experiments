import { cn } from "@/lib/utils";

interface StepperProps {
  steps: Array<{ label: string; description?: string }>;
  currentStep: number; // 0-indexed
  className?: string;
  orientation?: "horizontal" | "vertical";
  showDescriptions?: boolean;
}

export function Stepper({
  steps,
  currentStep,
  className,
  orientation = "horizontal",
  showDescriptions = true,
}: StepperProps) {
  return (
    <nav
      className={cn(
        "flex",
        orientation === "horizontal" ? "flex-row items-start gap-4" : "flex-col gap-6",
        className
      )}
      aria-label="Progress steps"
    >
      {steps.map((step, index) => {
        const isCompleted = index < currentStep;
        const isCurrent = index === currentStep;

        const circleClass = cn(
          "flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold transition-all duration-200 flex-shrink-0",
          isCompleted
            ? "bg-primary text-white"
            : isCurrent
            ? "bg-primary text-white ring-2 ring-primary ring-offset-2"
            : "bg-muted text-muted-foreground"
        );

        const lineClass = cn(
          "flex-1 h-0.5 transition-colors duration-200",
          index < steps.length - 1 && (isCompleted || isCurrent ? "bg-primary" : "bg-muted")
        );

        return (
          <div
            key={index}
            className={cn(
              "flex",
              orientation === "horizontal" ? "flex-col items-center" : "flex-row items-start gap-4"
            )}
          >
            <div className="flex items-start gap-3">
              <div className="relative">
                <span className={cn("flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold transition-all duration-200 flex-shrink-0",
                  isCompleted ? "bg-primary text-white" :
                  isCurrent ? "bg-primary text-white ring-2 ring-primary ring-offset-2" :
                  "bg-muted text-muted-foreground")}>
                  {isCompleted ? "✓" : index + 1}
                </span>
                {index < steps.length - 1 && (
                  <div
                    className={cn(
                      "absolute left-1/2 top-8 bottom-0 w-0.5",
                      orientation === "horizontal" ? "left-1/2 top-8 bottom-0 w-0.5" : "left-4 top-8 h-full w-0.5"
                    )}
                  >
                    <div className={lineClass} style={{ height: orientation === "horizontal" ? "100%" : "calc(100% - 1.5rem)" }} />
                  </div>
                )}
              </div>
              <div className={cn(
                "min-w-0",
                orientation === "horizontal" ? "text-center" : "flex-1"
              )}>
                <span
                  className={cn(
                    "text-sm font-semibold transition-colors",
                    isCompleted || isCurrent ? "text-primary" : "text-muted-foreground"
                  )}
                >
                  {step.label}
                </span>
                {showDescriptions && step.description && (
                  <p className={cn(
                    "text-xs mt-0.5 truncate",
                    orientation === "horizontal" ? "max-w-[120px] mx-auto" : "",
                    isCompleted || isCurrent ? "text-muted-foreground" : "text-muted-foreground/50"
                  )}>
                    {step.description}
                  </p>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </nav>
  );
}