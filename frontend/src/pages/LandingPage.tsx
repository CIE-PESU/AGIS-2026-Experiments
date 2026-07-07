import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Menu, Rocket, X, Lightbulb, Cpu, Target, Brain } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Logos } from "@/components/shared/Logos";

/* ═══════════════════════════════════════════════════════════════════
   PETAL FAN DIAGRAM — rounded petals radiating from a central hub,
   each labeled with a title above and sub-label below. Animated to
   read as a live pipeline: a scan arc sweeps the hub, and a light
   particle travels from hub to each petal in sequence, visualizing
   an idea moving through the six evaluation stages.
═══════════════════════════════════════════════════════════════════ */
function ArcDiagram() {
  const W = 520, H = 460;
  const CX = 260, CY = 210;
  const INNER = 34;     // how close the petal's point sits to hub centre
  const OUTER = 168;    // petal tip distance from hub centre
  const PETAL_HALF_DEG = 13.5; // half-width of each petal at its widest (near tip)
  const GAP_DEG = 5;

  const steps = [
    { label: "Idea",       sub: "Submit your idea",       color: "#34305e" },
    { label: "Compliance", sub: "Legal & ethics check",    color: "#e75a2d" },
    { label: "TIPSC",      sub: "5-dimension scoring",     color: "#2b9eb3" },
    { label: "DFV",        sub: "D · F · V analysis",      color: "#7c6fc4" },
    { label: "Discovery",  sub: "JTBD research plan",      color: "#e9a800" },
    { label: "Verdict",    sub: "GO / NO-GO decision",     color: "#059669" },
  ];

  // Fan sweeps through the bottom half, mirroring the reference's arrangement
  const START_DEG = 12;
  const SPAN_DEG  = 156;
  const stepSpan  = (SPAN_DEG - GAP_DEG * (steps.length - 1)) / steps.length;

  function toRad(d: number) { return (d * Math.PI) / 180; }
  function polar(r: number, deg: number) {
    return { x: CX + r * Math.cos(toRad(deg)), y: CY + r * Math.sin(toRad(deg)) };
  }
  function mid(i: number) { return START_DEG + i * (stepSpan + GAP_DEG) + stepSpan / 2; }

  // Petal shape: narrow point near hub, rounded wide cap at the tip —
  // built with two quadratic curves flaring out, joined by an arc across the tip.
  function petalPath(ma: number) {
    const halfDeg = Math.min(PETAL_HALF_DEG, stepSpan / 2);
    const innerPt   = polar(INNER, ma);
    const tipLeft    = polar(OUTER, ma - halfDeg);
    const tipRight   = polar(OUTER, ma + halfDeg);
    const ctrlLeft   = polar(OUTER * 0.62, ma - halfDeg * 1.15);
    const ctrlRight  = polar(OUTER * 0.62, ma + halfDeg * 1.15);
    const tipR = OUTER * 0.24; // rounding radius of the cap

    return `
      M ${innerPt.x} ${innerPt.y}
      Q ${ctrlLeft.x} ${ctrlLeft.y} ${tipLeft.x} ${tipLeft.y}
      A ${tipR} ${tipR} 0 0 1 ${tipRight.x} ${tipRight.y}
      Q ${ctrlRight.x} ${ctrlRight.y} ${innerPt.x} ${innerPt.y}
      Z
    `;
  }

  // radar/scan ring geometry (sweeps around the hub, echoing a slow-turning fan)
  const ringR = INNER + 40;
  const ringCirc = 2 * Math.PI * ringR;
  const arcLen = ringCirc * 0.22;

  return (
    <div className="relative mx-auto w-full max-w-[520px] select-none cie-float">
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="100%"
        aria-label="CIE evaluation pipeline petal diagram" role="img">
        <defs>
          {steps.map((s, i) => (
            <linearGradient key={i} id={`pg${i}`} x1="0" y1="1" x2="1" y2="0">
              <stop offset="0%"   stopColor={s.color} stopOpacity="0.85" />
              <stop offset="100%" stopColor={s.color} stopOpacity="1" />
            </linearGradient>
          ))}
          <filter id="pshadow" x="-30%" y="-30%" width="160%" height="160%">
            <feDropShadow dx="0" dy="3" stdDeviation="4" floodColor="rgba(0,0,0,0.18)" />
          </filter>
          <linearGradient id="hubg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%"   stopColor="#3999c2" />
            <stop offset="100%" stopColor="#34305e" />
          </linearGradient>
          <linearGradient id="radarg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%"   stopColor="#3999c2" stopOpacity="0" />
            <stop offset="100%" stopColor="#3999c2" stopOpacity="0.9" />
          </linearGradient>
        </defs>

        {steps.map((s, i) => {
          const ma = mid(i);
          const path = petalPath(ma);
          const innerPt = polar(INNER, ma);
          const tipMid  = polar(OUTER - 6, ma);
          // label sits just beyond the petal's rounded tip
          const lp = polar(OUTER + 22, ma);
          const sp = polar(OUTER + 22, ma);
          const anchor = lp.x < CX - 8 ? "end" : lp.x > CX + 8 ? "start" : "middle";
          const above = Math.sin(toRad(ma)) < -0.15; // tips pointing upward get label below, and vice versa
          const labelDy = above ? -14 : 24;
          const subDy   = above ? -2  : 38;
          const motionPath = `M ${innerPt.x} ${innerPt.y} L ${tipMid.x} ${tipMid.y}`;
          const delay = i * 0.35; // stagger so stages "light up" in pipeline order

          return (
            <g key={s.label}>
              <path d={path} fill={`url(#pg${i})`} filter="url(#pshadow)" />
              {/* subtle rim highlight */}
              <path d={path} fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth="1" />

              {/* flowing particle: the idea moving out to this stage */}
              <circle r="3.5" fill="white">
                <animateMotion path={motionPath} dur="2.8s" begin={`${delay}s`} repeatCount="indefinite" />
                <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.15;0.8;1"
                  dur="2.8s" begin={`${delay}s`} repeatCount="indefinite" />
              </circle>

              {/* small dot marker at the tip, gently pulsing in sequence */}
              <circle cx={tipMid.x} cy={tipMid.y} r={9} fill="white"
                className="cie-glow" style={{ animationDelay: `${delay}s` }} />
              <circle cx={tipMid.x} cy={tipMid.y} r={9} fill="none" stroke={s.color} strokeWidth="1.5" />

              <text x={lp.x} y={lp.y + labelDy} textAnchor={anchor} dominantBaseline="middle"
                fill={s.color} fontSize="11" fontWeight="800"
                fontFamily="Poppins, sans-serif" letterSpacing="0.3">
                {s.label.toUpperCase()}
              </text>
              <text x={sp.x} y={sp.y + subDy} textAnchor={anchor} dominantBaseline="middle"
                fill="rgba(52,48,94,0.55)" fontSize="8.5" fontWeight="500"
                fontFamily="Inter, sans-serif">
                {s.sub}
              </text>
            </g>
          );
        })}

        {/* ── Hub ── */}
        <circle cx={CX} cy={CY} r={ringR}
          fill="none" stroke="rgba(57,153,194,0.15)" strokeWidth="18" />

        {/* rotating scan arc — sweeps around the hub like a slow-turning fan blade */}
        <g className="cie-spin" style={{ transformOrigin: `${CX}px ${CY}px` }}>
          <circle cx={CX} cy={CY} r={ringR} fill="none" stroke="url(#radarg)" strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={`${arcLen} ${ringCirc - arcLen}`} />
        </g>

        <circle cx={CX} cy={CY} r={INNER + 26}
          fill="url(#hubg)" filter="url(#pshadow)"
          className="cie-pulse" style={{ transformOrigin: `${CX}px ${CY}px` }} />
        <text x={CX} y={CY - 9} textAnchor="middle" dominantBaseline="middle"
          fill="white" fontSize="12" fontWeight="800"
          fontFamily="Poppins, sans-serif" letterSpacing="0.8">AI</text>
        <text x={CX} y={CY + 6} textAnchor="middle" dominantBaseline="middle"
          fill="rgba(255,255,255,0.75)" fontSize="8" fontWeight="600"
          fontFamily="Poppins, sans-serif" letterSpacing="1">ENGINE</text>
        <text x={CX} y={CY + 20} textAnchor="middle" dominantBaseline="middle"
          fill="rgba(255,255,255,0.4)" fontSize="7" fontWeight="500"
          fontFamily="Inter, sans-serif">CIE Platform</text>
      </svg>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   NAV
═══════════════════════════════════════════════════════════════════ */
function Navbar() {
  const [open, setOpen] = useState(false);
  const links: [string, string][] = [
    ["About CIE",  "https://cie.pes.edu/about"],
    ["Programs",   "https://cie.pes.edu/students/programs"],
    ["Events",     "https://cie.pes.edu/students/events"],
    ["Industry",   "https://cie.pes.edu/industry/collaborations"],
    ["Contact",    "https://cie.pes.edu/contact"],
  ];
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-white">
      <div className="mx-auto flex h-[68px] max-w-7xl items-center justify-between gap-6 px-6">
        <Logos />
        <nav className="hidden items-center gap-7 md:flex">
          {links.map(([label, href]) => (
            <a key={href} href={href}
              className="text-[13px] font-medium text-muted-foreground transition-colors hover:text-primary">
              {label}
            </a>
          ))}
          <Link to="/login"
            className="rounded-full bg-accent px-5 py-2 text-[13px] font-semibold text-white transition-opacity hover:opacity-90">
            Sign In
          </Link>
        </nav>
        <button className="rounded-md p-1 text-muted-foreground md:hidden"
          onClick={() => setOpen(v => !v)} aria-label="Toggle menu">
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>
      {open && (
        <div className="border-t border-border bg-white px-6 pb-5 pt-4 md:hidden">
          <div className="flex flex-col gap-4">
            {links.map(([label, href]) => (
              <a key={href} href={href} className="text-sm font-medium text-muted-foreground"
                onClick={() => setOpen(false)}>{label}</a>
            ))}
            <Link to="/login"
              className="mt-1 rounded-full bg-accent px-5 py-2.5 text-center text-sm font-semibold text-white"
              onClick={() => setOpen(false)}>Sign In</Link>
          </div>
        </div>
      )}
    </header>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   DATA
═══════════════════════════════════════════════════════════════════ */
const pipeline = [
  { short: "Idea",  label: "Submit",     bg: "#34305e" },
  { short: "C",     label: "Compliance", bg: "#e75a2d" },
  { short: "TIPS",  label: "TIPSC",      bg: "#2b9eb3" },
  { short: "DFV",   label: "DFV",        bg: "#7c6fc4" },
  { short: "JTBD",  label: "Discovery",  bg: "#e9a800" },
  { short: "GO",    label: "Verdict",    bg: "#059669" },
];

const phases = [
  {
    tag: "Phase 1", color: "#2b9eb3", tagBg: "rgba(43,158,179,0.1)",
    title: "TIPSC Evaluation", subtitle: "Is the idea fundamentally sound?",
    body: "The TIPSC agent scores five dimensions — Timing, Idea, Problem, Solution, and Competition — using a traffic-light system. Each dimension gets a Green, Amber, or Red signal so founders know exactly where their idea is strong and where it needs work before going further.",
    signals: [
      { dim: "Timing",      dot: "#10b981", label: "Strong"   },
      { dim: "Idea",        dot: "#10b981", label: "Strong"   },
      { dim: "Problem",     dot: "#f59e0b", label: "Moderate" },
      { dim: "Solution",    dot: "#10b981", label: "Strong"   },
      { dim: "Competition", dot: "#dc2626", label: "Weak"     },
    ],
  },
  {
    tag: "Phase 2", color: "#7c6fc4", tagBg: "rgba(124,111,196,0.1)",
    title: "DFV Analysis", subtitle: "Does it have real market potential?",
    body: "Three sub-agents run in parallel — Desirability checks user demand and competitor gaps with live web research, Feasibility assesses technical and operational challenges, and Viability evaluates business models, revenue streams, and long-term sustainability. A final DFV decision engine synthesises all three into a GO or NO-GO verdict with positive, actionable guidance.",
    verdict: true,
  },
  {
    tag: "Phase 3", color: "#e9a800", tagBg: "rgba(233,168,0,0.1)",
    title: "Customer Discovery", subtitle: "Who exactly is the customer?",
    body: "The JTBD (Jobs To Be Done) agent turns the validated idea into a concrete customer research plan — generating customer job statements, a structured interview guide, and prioritised discovery questions. Founders leave with a clear plan for their first 10 user conversations.",
    outputs: ["Customer job statements", "Structured interview guide", "Discovery question bank", "Mentor-ready export report"],
  },
];

/* ═══════════════════════════════════════════════════════════════════
   PAGE
═══════════════════════════════════════════════════════════════════ */
export function LandingPage() {
  return (
    <div className="min-h-screen bg-[#fdfdfd] antialiased">

      {/* keyframes — scoped to this page */}
      <style>{`
        @keyframes cie-spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
        @keyframes cie-float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-8px)} }
        @keyframes cie-pulse { 0%,100%{transform:scale(1)} 50%{transform:scale(1.045)} }
        @keyframes cie-glow { 0%,100%{opacity:0.55} 50%{opacity:1} }
        .cie-float { animation: cie-float 6s ease-in-out infinite; }
        .cie-spin  { animation: cie-spin 9s linear infinite; }
        .cie-pulse { animation: cie-pulse 4s ease-in-out infinite; }
        .cie-glow  { animation: cie-glow 3.2s ease-in-out infinite; }
        @media (prefers-reduced-motion: reduce) {
          .cie-float, .cie-spin, .cie-pulse, .cie-glow,
          .cie-float *, .cie-spin *, .cie-pulse *, .cie-glow * {
            animation: none !important;
          }
        }
      `}</style>

      <Navbar />

      {/* ══════════════════════════════════════════════
          HERO
      ══════════════════════════════════════════════ */}
      <section className="relative overflow-hidden border-b border-border bg-gradient-to-br from-white via-[#eaf4fa] to-[#dbeaf6]">
        {/* ambient glow blobs */}
        <div className="pointer-events-none absolute -right-32 -top-32 h-[420px] w-[420px] rounded-full bg-[#3999c2]/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-40 left-1/4 h-[360px] w-[360px] rounded-full bg-[#e75a2d]/10 blur-3xl" />
        {/* subtle dot texture */}
        <div className="pointer-events-none absolute inset-0 opacity-35"
          style={{ backgroundImage: "radial-gradient(rgba(57,153,194,0.18) 1px,transparent 1px)", backgroundSize: "22px 22px" }} />

        <div className="relative mx-auto grid max-w-7xl items-center gap-0 lg:grid-cols-2">

          {/* LEFT — headline */}
          <div className="relative z-10 flex flex-col justify-center px-6 pb-0 pt-20 lg:py-24 lg:pr-12">
            <div className="mb-6 inline-flex w-fit items-center gap-2 rounded-full border border-border bg-white/70 px-4 py-1.5 backdrop-blur-sm">
              <span className="h-1.5 w-1.5 rounded-full bg-[#e75a2d]" />
              <span className="text-[11px] font-bold uppercase tracking-[1.4px] text-muted-foreground">
                CIE · Agentic Evaluation Platform
              </span>
            </div>
            <h1 className="font-poppins text-[clamp(42px,5.5vw,70px)] font-extrabold leading-[1.06] tracking-tight">
              <span style={{ color: "#34305e" }}>Validate</span><br />
              <span style={{ color: "#3999c2" }}>your idea</span><br />
              <span style={{ color: "#e75a2d" }}>before you build.</span>
            </h1>
            <p className="mt-6 max-w-[400px] text-[15px] leading-[1.8] text-muted-foreground">
              A structured AI evaluation system that stress-tests startup and hackathon ideas through compliance, TIPSC, DFV, and customer discovery — before a single line of code is written.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <Link to="/login"
                className="inline-flex items-center gap-2 rounded-full px-7 py-3.5 text-[13px] font-semibold text-white shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-lg"
                style={{ background: "linear-gradient(135deg,#34305e,#3999c2)" }}>
                Start Evaluating <ArrowRight className="h-4 w-4" />
              </Link>
              <a href="#how-it-works"
                className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-muted-foreground transition-colors hover:text-primary">
                See how it works <ArrowRight className="h-3.5 w-3.5" />
              </a>
            </div>
          </div>

          {/* RIGHT — Arc fan diagram */}
          <div className="relative z-10 flex items-center justify-center px-4 py-12 lg:py-20">
            <ArcDiagram />
          </div>
        </div>

        {/* Stats strip */}
        <div className="relative mx-auto flex max-w-7xl divide-x divide-border border-t border-border/70 bg-white/40 px-6 backdrop-blur-sm">
          {([["1000+","Ideas Validated"],["500+","Student Innovators"],["50+","Startups Launched"]] as [string,string][]).map(([num,label]) => (
            <div key={label} className="flex-1 px-6 py-6">
              <p className="font-poppins text-3xl font-extrabold leading-none tracking-tight text-primary">{num}</p>
              <p className="mt-1 text-xs font-medium text-muted-foreground">{label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ══════════════════════════════════════════════
          WHAT IT IS
      ══════════════════════════════════════════════ */}
      <section  id="what-it-is" className="border-b border-border bg-white py-20">
        <div className="mx-auto max-w-7xl px-6">
          <p className="mb-3 flex items-center gap-2 text-[11px] font-bold uppercase tracking-[1.5px] text-accent">
            <span className="block h-0.5 w-5 rounded-full bg-accent" />What it is
          </p>
          <div className="grid gap-12 lg:grid-cols-2 lg:items-start">
            <div>
              <h2 className="font-poppins text-[clamp(26px,3.5vw,40px)] font-extrabold leading-[1.15] tracking-tight text-primary">
                Structured validation,<br />not guesswork.
              </h2>
              <p className="mt-5 text-[15px] leading-[1.85] text-muted-foreground">
                Most student ideas skip straight to building. This platform forces the right questions first — is there a real user need, can it actually be built, and can it sustain itself?
              </p>
              <p className="mt-4 text-[15px] leading-[1.85] text-muted-foreground">
                Multiple AI agents evaluate each dimension in sequence and pass their findings to a final decision engine that issues a clear{" "}
                <strong className="font-semibold text-primary">GO</strong> or{" "}
                <strong className="font-semibold text-primary">NO-GO</strong> with actionable, mentor-style feedback.
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-5 rounded-xl border border-border bg-muted px-5 py-3">
                <span className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">Traffic lights:</span>
                {([["#10b981","Strong"],["#f59e0b","Moderate"],["#dc2626","Weak"]] as [string,string][]).map(([c,l]) => (
                  <span key={l} className="flex items-center gap-1.5 text-[12px] font-medium text-muted-foreground">
                    <span className="h-3 w-3 rounded-full" style={{ background: c }} />{l}
                  </span>
                ))}
              </div>
            </div>
            <div className="rounded-2xl border border-border bg-[#f8f9fb] p-6">
              <div className="mb-4 flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-[#2b9eb3]" />
                <p className="text-[11px] font-bold uppercase tracking-[1.2px] text-[#2b9eb3]">TIPSC — Sample Output</p>
              </div>
              <div className="flex flex-col gap-3">
                {([
                  { dim:"Timely",      dot:"#10b981", label:"Strong",   note:"Market conditions are favourable right now."           },
                  { dim:"Importance",        dot:"#10b981", label:"Strong",   note:"Clear differentiation from existing solutions."        },
                  { dim:"Profitable",     dot:"#f59e0b", label:"Moderate", note:"Pain point is real but severity needs validation."     },
                  { dim:"Solvable",    dot:"#10b981", label:"Strong",   note:"Technically achievable with available tools."          },
                  { dim:"Compliance", dot:"#dc2626", label:"Weak",     note:"Two well-funded competitors occupy the same space."    },
                ] as {dim:string;dot:string;label:string;note:string}[]).map(({dim,dot,label,note}) => (
                  <div key={dim} className="flex items-start gap-3">
                    <div className="mt-1 h-3 w-3 flex-shrink-0 rounded-full" style={{ background: dot }} />
                    <div>
                      <div className="flex items-baseline gap-2">
                        <span className="text-[13px] font-semibold text-primary">{dim}</span>
                        <span className="text-[10px] font-bold uppercase tracking-wide" style={{ color: dot }}>{label}</span>
                      </div>
                      <p className="text-[12px] leading-[1.55] text-muted-foreground">{note}</p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-5 border-t border-border pt-4">
                <p className="mb-3 text-[11px] font-bold uppercase tracking-[1px] text-[#7c6fc4]">DFV Verdict</p>
                <div className="flex gap-2">
                  <div className="flex flex-1 items-center gap-2.5 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
                    <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-emerald-600 font-poppins text-[11px] font-extrabold text-white">GO</div>
                    <div>
                      <p className="text-[12px] font-bold text-emerald-700">Ready to build</p>
                      <p className="text-[11px] text-muted-foreground">Directionally sound across D, F &amp; V.</p>
                    </div>
                  </div>
                  <div className="flex flex-1 items-center gap-2.5 rounded-xl border border-orange-200 bg-orange-50 px-4 py-3">
                    <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-accent font-poppins text-[9px] font-extrabold text-white">NOGO</div>
                    <div>
                      <p className="text-[12px] font-bold text-accent">Strengthen first</p>
                      <p className="text-[11px] text-muted-foreground">Specific next steps, no negative scoring.</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════
          HOW IT WORKS — 3 PHASES
      ══════════════════════════════════════════════ */}
      <section id="how-it-works" className="bg-primary py-20">
        <div className="mx-auto max-w-7xl px-6">
          <div className="mb-14 flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-end">
            <div>
              <p className="mb-3 flex items-center gap-2 text-[11px] font-bold uppercase tracking-[1.4px] text-white/40">
                <span className="block h-0.5 w-5 rounded-full bg-white/30" />How It Works
              </p>
              <h2 className="font-poppins text-[clamp(26px,3.5vw,40px)] font-extrabold leading-[1.15] tracking-tight text-white">
                Three phases.<br />One clear verdict.
              </h2>
            </div>
            <div className="flex items-center gap-1.5">
              {pipeline.map(({short,label,bg},i) => (
                <div key={short} className="flex items-center gap-1.5">
                  <div className="flex flex-col items-center gap-1.5">
                    <div className="flex h-11 w-11 items-center justify-center rounded-full text-[9px] font-bold text-white shadow-md"
                      style={{ background: bg, fontFamily: "'Poppins',sans-serif" }}>{short}</div>
                    <span className="whitespace-nowrap text-[9px] font-medium text-white/40">{label}</span>
                  </div>
                  {i < pipeline.length - 1 && <div className="mb-4 h-px w-4 bg-white/20" />}
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-5 md:grid-cols-3">
            {phases.map((phase, idx) => (
              <div key={phase.tag} className="flex flex-col rounded-2xl border p-7"
                style={{ borderColor:"rgba(255,255,255,0.12)", background:"rgba(255,255,255,0.05)" }}>
                <div className="mb-5 flex items-center justify-between">
                  <span className="rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-[1px]"
                    style={{ background: phase.tagBg, color: phase.color }}>{phase.tag}</span>
                  <span className="font-poppins text-[11px] font-bold text-white/30">0{idx+1}</span>
                </div>
                <h3 className="font-poppins text-[17px] font-bold text-white">{phase.title}</h3>
                <p className="mb-4 mt-1 text-[12px] font-medium" style={{ color: phase.color }}>{phase.subtitle}</p>
                <p className="flex-1 text-[13px] leading-[1.75] text-white/55">{phase.body}</p>

                {"signals" in phase && phase.signals && (
                  <div className="mt-5 flex flex-col gap-2 border-t border-white/10 pt-4">
                    {phase.signals.map(({dim,dot,label}) => (
                      <div key={dim} className="flex items-center gap-2">
                        <div className="h-2.5 w-2.5 flex-shrink-0 rounded-full" style={{ background: dot }} />
                        <span className="text-[12px] font-medium text-white/70">{dim}</span>
                        <span className="ml-auto text-[10px] font-bold uppercase tracking-wide" style={{ color: dot }}>{label}</span>
                      </div>
                    ))}
                  </div>
                )}
                {"verdict" in phase && phase.verdict && (
                  <div className="mt-5 flex gap-2 border-t border-white/10 pt-4">
                    <div className="flex flex-1 items-center gap-2 rounded-lg bg-emerald-900/40 px-3 py-2">
                      <div className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
                      <span className="text-[11px] font-bold text-emerald-400">GO</span>
                    </div>
                    <div className="flex flex-1 items-center gap-2 rounded-lg bg-orange-900/30 px-3 py-2">
                      <div className="h-2.5 w-2.5 rounded-full bg-accent" />
                      <span className="text-[11px] font-bold text-accent">NO-GO</span>
                    </div>
                  </div>
                )}
                {"outputs" in phase && phase.outputs && (
                  <div className="mt-5 flex flex-col gap-2 border-t border-white/10 pt-4">
                    {phase.outputs.map((o:string) => (
                      <div key={o} className="flex items-center gap-2">
                        <span className="text-[11px] font-bold" style={{ color: phase.color }}>→</span>
                        <span className="text-[12px] text-white/60">{o}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════
          WHO IT'S FOR
      ══════════════════════════════════════════════ */}
      <section id="who-its-for" className="bg-white py-20">
        <div className="mx-auto max-w-7xl px-6">
          <p className="mb-3 flex items-center gap-2 text-[11px] font-bold uppercase tracking-[1.5px] text-accent">
            <span className="block h-0.5 w-5 rounded-full bg-accent" />Who it's for
          </p>
          <h2 className="font-poppins text-[clamp(26px,3.5vw,40px)] font-extrabold leading-[1.15] tracking-tight text-primary">
            Built for students.<br />Monitored by mentors.
          </h2>
          <div className="mt-10 grid gap-5 md:grid-cols-2">
            <div className="rounded-2xl border border-[#c4e6f0] bg-[#f0f8fb] p-8">
              <span className="inline-block rounded-full bg-secondary/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[1px] text-secondary">Students</span>
              <h3 className="font-poppins mb-5 mt-4 text-lg font-bold text-primary">Validate before you pitch.</h3>
              <ul className="flex flex-col gap-2.5">
                {["Submit a startup or hackathon idea","Run through TIPSC, DFV, and JTBD in sequence",
                  "Get a GO / NO-GO with specific, positive feedback","Export a mentor-ready validation report",
                ].map(item => (
                  <li key={item} className="flex items-start gap-2.5 text-[13.5px] text-muted-foreground">
                    <span className="mt-0.5 font-bold text-secondary">→</span>{item}
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-2xl border border-[#fad5c4] bg-[#fff7f4] p-8">
              <span className="inline-block rounded-full bg-accent/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[1px] text-accent">Mentors</span>
              <h3 className="font-poppins mb-5 mt-4 text-lg font-bold text-primary">Monitor every team, every step.</h3>
              <ul className="flex flex-col gap-2.5">
                {["Monitor assigned teams in real time","View full AI evaluation transcripts",
                  "Leave remarks on any student session","Spot bottlenecks before they become blockers",
                ].map(item => (
                  <li key={item} className="flex items-start gap-2.5 text-[13.5px] text-muted-foreground">
                    <span className="mt-0.5 font-bold text-accent">→</span>{item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════
          CTA
      ══════════════════════════════════════════════ */}
      <section className="bg-muted py-16">
        <div className="mx-auto max-w-4xl px-6">
          <div className="gradient-cta rounded-2xl px-10 py-12 text-center text-white shadow-xl">
            <Rocket className="mx-auto h-10 w-10" />
            <h2 className="font-poppins mt-4 text-3xl font-bold">Ready to put your idea to the test?</h2>
            <p className="mt-3 text-sm text-white/70">Join 500+ student founders who've validated their ideas through structured AI evaluation.</p>
            <Button asChild variant="accent" size="lg" className="mt-8 rounded-full bg-white text-primary hover:bg-white/90">
              <Link to="/login">Get Started Now <ArrowRight className="h-4 w-4" /></Link>
            </Button>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════
          FOOTER
      ══════════════════════════════════════════════ */}
      <footer id="connect" className="bg-primary py-14 text-white">
        <div className="mx-auto max-w-7xl px-6">
          <div className="grid gap-12 border-b border-white/10 pb-10 md:grid-cols-[2fr_1fr_1fr_1fr]">
            <div>
              <div className="mb-4 flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/10 font-poppins text-[13px] font-bold">CIE</div>
                <div>
                  <p className="font-poppins text-[15px] font-bold leading-tight">CIE</p>
                  <p className="text-[10px] text-white/50">PES University</p>
                </div>
              </div>
              <p className="mb-5 max-w-[220px] text-[13px] leading-[1.7] text-white/50">
                Center for Innovation &amp; Entrepreneurship, PES University. Empowering student founders since 2018.
              </p>
              <div className="flex gap-2">
                {([
                  ["in","https://www.linkedin.com/company/center-for-innovation-and-entrepreneurship-pes-university/"],
                  ["ig","https://www.instagram.com/cie.pesu/"],
                  ["yt","https://www.youtube.com/@CIEPodcast-PESU"],
                  ["sp","https://open.spotify.com/show/2SPdUtKAl4f0CmXrNqhzAc"],
                ] as [string,string][]).map(([label,href]) => (
                  <a key={label} href={href}
                    className="flex h-8 w-8 items-center justify-center rounded-lg text-[11px] font-semibold text-white/60 transition-colors hover:text-white"
                    style={{ background:"rgba(255,255,255,0.08)" }}>{label}</a>
                ))}
              </div>
            </div>
            {([
              ["Platform",[["Sign In","/login"],["What it is","#what-it-is"],["Phases","#how-it-works"],["Who it's for","#who-its-for"]]],
              ["Inside CIE",[["About CIE","https://cie.pes.edu/about"],["Programs","https://cie.pes.edu/students/programs"],["Mentorship","https://cie.pes.edu/students/mentorship"],["Research","https://cie.pes.edu/research"]]],
              ["Contact",[["cie@pes.edu","mailto:cie@pes.edu"],["+91 80 2672 1983","tel:+918026721983"],["Contact Page","https://cie.pes.edu/contact"],["FAQs","https://cie.pes.edu/faqs"]]],
            ] as [string,[string,string][]][]).map(([heading,items]) => (
              <div key={heading}>
                <h4 className="font-poppins mb-4 text-[11px] font-bold uppercase tracking-[0.8px]">{heading}</h4>
                <ul className="flex flex-col gap-2.5">
                  {items.map(([label,href]) => (
                    <li key={label}>
                      <a href={href} className="text-[13px] text-white/50 transition-colors hover:text-white">{label}</a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap items-center justify-between gap-4 pt-6">
            <p className="text-[11.5px] text-white/35">© 2026 Center for Innovation &amp; Entrepreneurship, PES University. All rights reserved.</p>
            <div className="flex gap-4">
              {["Privacy Policy","Terms of Service","Accessibility"].map(label => (
                <a key={label} href="#" className="text-[11.5px] text-white/35 transition-colors hover:text-white/70">{label}</a>
              ))}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}