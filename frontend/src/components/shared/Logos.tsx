import { Link } from "react-router-dom";
import { CIE_LOGO, PES_LOGO } from "@/constants";
import { cn } from "@/lib/utils";

export function Logos({ to = "/", invert = false, className }: { to?: string; invert?: boolean; className?: string }) {
  return (
    <Link to={to} className={cn("flex items-center gap-3", className)}>
      <img src={PES_LOGO} alt="PES University" className={cn("h-9 w-auto object-contain", invert && "brightness-0 invert")} />
      <span className={cn("h-9 w-px", invert ? "bg-white/40" : "bg-border")} />
      <img src={CIE_LOGO} alt="CIE" className={cn("h-9 w-auto object-contain", invert && "brightness-0 invert")} />
    </Link>
  );
}
