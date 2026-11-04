import { cn } from "@/lib/utils";

type TabsProps = {
  value: string;
  onValueChange: (value: string) => void;
  options: { value: string; label: React.ReactNode }[];
  className?: string;
};

export function SegmentedTabs({ value, onValueChange, options, className }: TabsProps) {
  return (
    <div className={cn("grid rounded-lg bg-muted p-1", className)} style={{ gridTemplateColumns: `repeat(${options.length}, 1fr)` }}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          aria-pressed={value === option.value}
          onClick={() => onValueChange(option.value)}
          className={cn(
            "flex h-10 items-center justify-center gap-2 rounded-md text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            value === option.value ? "bg-card text-primary shadow-sm" : "text-muted-foreground hover:bg-card/50 hover:text-foreground"
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
