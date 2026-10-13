import { cn } from "@/lib/utils";
import { ArrowRight, Sparkles, Lightbulb, Users, Target, CheckCircle2 } from "lucide-react";

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  action?: {
    label: string;
    onClick: () => void;
    href?: string;
    variant?: "primary" | "secondary" | "outline";
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
    href?: string;
  };
  illustration?: "default" | "chat" | "search" | "folder" | "chart" | "settings" | "users";
  className?: string;
}

const illustrations = {
  default: (
    <div className="mx-auto w-24 h-24 rounded-full bg-muted/50 flex items-center justify-center">
      <Sparkles className="h-12 w-12 text-muted-foreground/50" />
    </div>
  ),
  chat: (
    <div className="mx-auto w-24 h-24 rounded-full bg-muted/50 flex items-center justify-center">
      <Users className="h-12 w-12 text-muted-foreground/50" />
    </div>
  ),
  search: (
    <div className="mx-auto w-24 h-24 rounded-full bg-muted/50 flex items-center justify-center">
      <Lightbulb className="h-12 w-12 text-muted-foreground/50" />
    </div>
  ),
  folder: (
    <div className="mx-auto w-24 h-24 rounded-full bg-muted/50 flex items-center justify-center">
      <Users className="h-12 w-12 text-muted-foreground/50" />
    </div>
  ),
  chart: (
    <div className="mx-auto w-24 h-24 rounded-full bg-muted/50 flex items-center justify-center">
      <Target className="h-12 w-12 text-muted-foreground/50" />
    </div>
  ),
  settings: (
    <div className="mx-auto w-24 h-24 rounded-full bg-muted/50 flex items-center justify-center">
      <Lightbulb className="h-12 w-12 text-muted-foreground/50" />
    </div>
  ),
  users: (
    <div className="mx-auto w-24 h-24 rounded-full bg-muted/50 flex items-center justify-center">
      <Users className="h-12 w-12 text-muted-foreground/50" />
    </div>
  ),
};

export function EmptyState({
  title,
  description,
  icon,
  action,
  secondaryAction,
  illustration = "default",
  className,
}: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center text-center py-12 px-4", className)}>
      {icon || illustrations[illustration]}

      <h3 className="mt-6 text-lg font-semibold text-foreground">{title}</h3>

      <p className="mt-2 text-sm text-muted-foreground max-w-sm">
        {description}
      </p>

      {(action || secondaryAction) && (
        <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-3">
{action && (
            <a
              href={action.href}
              onClick={(e) => { e.preventDefault(); action.onClick(); }}
              className={cn(
                "inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                action.variant === "primary"
                  ? "bg-primary text-white hover:bg-primary/90"
                  : action.variant === "secondary"
                  ? "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                  : "border border-border bg-background hover:bg-muted"
              )}
            >
              {action.label}
              <ArrowRight className="h-4 w-4" />
            </a>
          )}

          {secondaryAction && (
            <a
              href={secondaryAction.href}
              onClick={(e) => { e.preventDefault(); secondaryAction.onClick(); }}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              {secondaryAction.label}
            </a>
          )}
        </div>
      )}
    </div>
  );
}

// Pre-built empty state variants for common use cases
export const EmptyStateVariants = {
  noSessions: () => (
    <EmptyState
      title="No active sessions"
      description="Start your first evaluation to see your progress here."
      illustration="folder"
      action={{
        label: "Start Evaluation",
        onClick: () => {},
        href: "/login?redirect=/quickstart",
        variant: "primary",
      }}
    />
  ),
  noComments: () => (
    <EmptyState
      title="No remarks yet"
      description="Your mentor's comments will show up here once they review your work."
      illustration="chat"
    />
  ),
  noTeamProgress: () => (
    <EmptyState
      title="No team data yet"
      description="Team progress will appear here once your teammates start their evaluations."
      illustration="users"
    />
  ),
  noResults: () => (
    <EmptyState
      title="No results yet"
      description="Run an evaluation to see your results and insights."
      illustration="chart"
      action={{
        label: "Run Evaluation",
        onClick: () => {},
        variant: "primary",
      }}
    />
  ),
  noSessionsMentor: () => (
    <EmptyState
      title="No teams assigned"
      description="You don't have any teams assigned to mentor yet."
      illustration="users"
    />
  ),
  generic: (title: string, description: string, action?: EmptyStateProps["action"]) => (
    <EmptyState title={title} description={description} action={action} />
  ),
};