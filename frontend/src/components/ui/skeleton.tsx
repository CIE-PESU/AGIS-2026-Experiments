import { cn } from "@/lib/utils";

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "text" | "circular" | "rectangular";
  animation?: "pulse" | "wave" | "none";
}

export function Skeleton({
  className,
  variant = "text",
  animation = "pulse",
  ...props
}: SkeletonProps) {
  const baseStyles = "bg-muted animate-pulse rounded";

  const variantStyles = {
    text: "h-4 w-full max-w-[250px]",
    circular: "h-10 w-10 rounded-full",
    rectangular: "h-16 w-full rounded-lg",
  };

  const animationStyles = {
    pulse: "animate-pulse",
    wave: "animate-[shimmer_1.5s_infinite]",
    none: "",
  };

  return (
    <div
      className={cn(baseStyles, variantStyles[variant], animationStyles[animation], className)}
      {...props}
    />
  );
}

export function SkeletonText({ lines = 3, className, ...props }: { lines?: number; className?: string } & Omit<SkeletonProps, "variant">) {
  return (
    <div className={className} {...props}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} variant="text" className={i === lines - 1 ? "max-w-[60%]" : ""} />
      ))}
    </div>
  );
}

export function SkeletonCard({ className, ...props }: { className?: string } & Omit<SkeletonProps, "variant">) {
  return (
    <div className={className} {...props}>
      <Skeleton variant="rectangular" className="mb-4" />
      <SkeletonText lines={3} />
    </div>
  );
}