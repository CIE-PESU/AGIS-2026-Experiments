import { Link } from "react-router-dom";
import {
  ArrowRight,
  Brain,
  CheckCircle2,
  Cpu,
  GraduationCap,
  Instagram,
  Lightbulb,
  Linkedin,
  Mail,
  Menu,
  Rocket,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
  Users,
  Youtube
} from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Logos } from "@/components/shared/Logos";

function Navbar() {
  const [open, setOpen] = useState(false);
  const links = [
    ["How It Works", "#how-it-works"],
    ["Agents", "#agents"],
    ["Contact", "#connect"]
  ];
  return (
    <header className="sticky top-0 z-40 border-b bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4">
        <Logos />
        <nav className="hidden items-center gap-8 text-sm font-semibold text-muted-foreground md:flex">
          {links.map(([label, href]) => <a key={href} href={href} className="hover:text-primary">{label}</a>)}
        </nav>
        <div className="hidden items-center gap-3 md:flex">
          <Button asChild variant="accent" className="rounded-full"><Link to="/login">Get Started <ArrowRight className="h-4 w-4" /></Link></Button>
        </div>
        <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setOpen((v) => !v)}><Menu /></Button>
      </div>
      {open && (
        <div className="space-y-3 border-t bg-white p-4 md:hidden">
          {links.map(([label, href]) => <a key={href} href={href} className="block font-semibold" onClick={() => setOpen(false)}>{label}</a>)}
          <Button asChild variant="accent" className="w-full rounded-full"><Link to="/login">Get Started <ArrowRight className="h-4 w-4" /></Link></Button>
        </div>
      )}
    </header>
  );
}

const stepData = [
  [Lightbulb, "01", "Submit Your Idea", "Capture problem, customer, assumptions, and first solution shape."],
  [Brain, "02", "AI Evaluation", "Move through compliance, TIPS, DFV, and JTBD in sequence."],
  [TrendingUp, "03", "Get Insights", "Receive traffic-light decisions, recommendations, and follow-up prompts."],
  [Rocket, "04", "Build & Launch", "Turn validated evidence into a mentor-ready startup path."]
] as const;

const agents = [
  [ShieldCheck, "Compliance Agent", "Checks legal, ethical, institutional, and regulatory readiness."],
  [Target, "TIPSC Agent", "Scores technical, innovative, profitable, and scalable strength."],
  [TrendingUp, "DFV Agent", "Evaluates desirability, feasibility, and viability for go/no-go clarity."],
  [Users, "JTBD Agent", "Turns ideas into customer jobs, interviews, and discovery priorities."]
] as const;

export function LandingPage() {
  return (
    <div>
      <Navbar />
      <section className="gradient-hero relative overflow-hidden">
        <div className="dot-pattern absolute inset-0 opacity-60" />
        <div className="relative mx-auto grid min-h-[calc(100vh-4rem)] max-w-7xl items-center gap-10 px-4 py-16 lg:grid-cols-2">
          <div>
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border bg-white/75 px-4 py-2 text-sm font-semibold text-primary shadow-sm">
              <Sparkles className="h-4 w-4 text-accent" /> Empowering Innovation Since 2018
            </div>
            <h1 className="text-5xl font-extrabold leading-tight tracking-normal md:text-7xl">
              <span className="text-primary">Ideate.</span><br />
              <span className="text-secondary">Innovate.</span><br />
              <span className="text-gradient">Inspire.</span>
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-muted-foreground">
              PES CIE's agentic evaluation platform helps student founders validate ideas through guided AI frameworks and mentor oversight.
            </p>
            <Button asChild variant="secondary" size="lg" className="mt-8 rounded-full">
              <Link to="/login">Explore Platform <ArrowRight className="h-5 w-5" /></Link>
            </Button>
            <div className="mt-10 grid max-w-2xl grid-cols-3 gap-4">
              {["1000+ Ideas Validated", "500+ Student Innovators", "50+ Startups Launched"].map((stat) => (
                <div key={stat} className="rounded-lg bg-white/65 p-4 text-center shadow-sm">
                  <p className="text-lg font-bold text-primary">{stat.split(" ")[0]}</p>
                  <p className="text-xs text-muted-foreground">{stat.replace(stat.split(" ")[0], "").trim()}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="relative mx-auto aspect-square w-full max-w-[520px]">
            <div className="absolute inset-10 rounded-full border-2 border-dashed border-primary/30" />
            <div className="gradient-primary absolute left-1/2 top-1/2 flex h-28 w-28 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full text-white shadow-xl">
              <Brain className="h-12 w-12" />
            </div>
            {([
              [Lightbulb, "Idea", "left-6 top-20"],
              [Cpu, "AI Analysis", "right-0 top-1/3"],
              [Rocket, "Impact", "bottom-16 left-16"],
              [Target, "Insights", "bottom-8 right-24"]
            ] as const).map(([Icon, label, pos]) => (
              <div key={label} className={`absolute ${pos} rounded-lg bg-white p-4 text-center shadow-lg`}>
                <Icon className="mx-auto h-7 w-7 text-accent" />
                <p className="mt-2 text-xs font-semibold">{label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
      <section id="how-it-works" className="bg-white py-20">
        <div className="mx-auto max-w-7xl px-4">
          <h2 className="text-center text-3xl font-bold text-primary md:text-4xl">How It Works</h2>
          <div className="mt-12 grid gap-6 md:grid-cols-4">
            {stepData.map(([Icon, number, title, description], index) => (
              <Card key={title} className="relative">
                {index < 3 && <ArrowRight className="absolute -right-5 top-1/2 hidden h-6 w-6 text-border md:block" />}
                <CardContent className="p-6">
                  <Icon className="h-9 w-9 text-secondary" />
                  <p className="mt-5 text-xs font-bold text-accent">{number}</p>
                  <h3 className="mt-2 font-bold">{title}</h3>
                  <p className="mt-3 text-sm text-muted-foreground">{description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>
      <section className="bg-muted py-20">
        <div className="mx-auto grid max-w-6xl gap-6 px-4 md:grid-cols-2">
          {[
            ["For Students", "bg-secondary/10", ["Validate startup ideas step by step", "Understand weak assumptions early", "Export mentor-ready reports", "Track team progress", "Build with confidence"]],
            ["For Mentors", "bg-accent/10", ["Monitor assigned teams", "Review full student conversations", "Leave remarks", "Spot bottlenecks quickly", "Guide evidence-based launches"]]
          ].map(([title, bg, benefits]) => (
            <div key={String(title)} className={`rounded-lg ${bg} p-8`}>
              <h2 className="text-2xl font-bold text-primary">{title}</h2>
              <div className="mt-6 space-y-3">
                {(benefits as string[]).map((benefit) => <p key={benefit} className="flex items-center gap-2 text-sm"><CheckCircle2 className="h-5 w-5 text-emerald-600" />{benefit}</p>)}
              </div>
            </div>
          ))}
        </div>
      </section>
      <section id="agents" className="bg-white py-20">
        <div className="mx-auto max-w-7xl px-4">
          <h2 className="text-center text-3xl font-bold text-primary md:text-4xl">AI Agents</h2>
          <div className="mt-12 grid gap-6 md:grid-cols-4">
            {agents.map(([Icon, title, description]) => (
              <Card key={title}>
                <CardContent className="p-6">
                  <Icon className="h-9 w-9 text-accent" />
                  <h3 className="mt-5 font-bold">{title}</h3>
                  <p className="mt-3 text-sm text-muted-foreground">{description}</p>
                  <a href="#how-it-works" className="mt-5 inline-flex items-center gap-1 text-sm font-semibold text-secondary">Learn More <ArrowRight className="h-4 w-4" /></a>
                </CardContent>
              </Card>
            ))}
          </div>
          <div className="mt-16 overflow-x-auto">
            <div className="mx-auto flex min-w-[900px] max-w-6xl items-center justify-between">
              {["Idea Submission", "Compliance Check", "TIPSC Evaluation", "DFV Analysis", "JTBD Discovery", "Final Report"].map((label, index) => (
                <div key={label} className="flex items-center">
                  <div className="flex h-24 w-24 items-center justify-center rounded-full border-2 border-dashed border-secondary bg-muted text-center text-xs font-bold">{label}</div>
                  {index < 5 && <div className="h-px w-16 border-t-2 border-dashed border-border" />}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
      <section className="bg-muted py-20">
        <div className="mx-auto max-w-5xl px-4">
          <div className="gradient-cta rounded-lg p-10 text-center text-white shadow-xl">
            <Rocket className="mx-auto h-12 w-12" />
            <h2 className="mt-5 text-3xl font-bold">Ready to turn your idea into impact?</h2>
            <Button asChild variant="accent" size="lg" className="mt-8 rounded-full bg-white text-primary hover:bg-white/90">
              <Link to="/login">Get Started Now <ArrowRight className="h-5 w-5" /></Link>
            </Button>
          </div>
        </div>
      </section>
      <footer id="connect" className="bg-primary py-12 text-primary-foreground">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 md:grid-cols-3">
          <div><h3 className="text-xl font-bold">PES CIE</h3><p className="mt-3 text-sm text-white/75">Building the next generation of student entrepreneurs.</p></div>
          <div><h3 className="font-bold">Quick Links</h3><a href="#how-it-works" className="mt-3 block text-sm text-white/75">How It Works</a><a href="#agents" className="mt-2 block text-sm text-white/75">Agents</a></div>
          <div><h3 className="font-bold">Connect With Us</h3><div className="mt-3 flex gap-3"><Linkedin /><Instagram /><Youtube /><Mail /></div><p className="mt-3 text-sm text-white/75">cie@pes.edu · +91 80 2672 1983</p></div>
        </div>
        <p className="mt-10 text-center text-xs text-white/60">© 2024 PES University - CIE</p>
      </footer>
    </div>
  );
}
