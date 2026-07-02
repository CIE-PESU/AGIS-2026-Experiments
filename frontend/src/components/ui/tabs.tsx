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
          onClick={() => onValueChange(option.value)}
          className={cn(
            "btn-glossy flex h-10 items-center justify-center gap-2 rounded-md text-sm font-semibold text-muted-foreground",
            value === option.value && "bg-white text-primary shadow-sm"
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
