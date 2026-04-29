import heroGraph from "@/assets/hero-graph.jpg";
import { ArrowRight, Sparkles } from "lucide-react";

export const Hero = () => {
  return (
    <section className="relative overflow-hidden">
      {/* Background graph image */}
      <div className="absolute inset-0 -z-10">
        <img
          src={heroGraph}
          alt=""
          width={1536}
          height={1024}
          className="absolute inset-0 h-full w-full object-cover opacity-[0.18]"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-background via-background/85 to-background" />
      </div>

      <div className="container relative pt-20 pb-28 md:pt-28 md:pb-36">
        <div className="mx-auto max-w-4xl text-center">
          {/* Eyebrow */}
          <div className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/5 px-3.5 py-1.5 text-xs font-medium text-accent animate-fade-in">
            <Sparkles className="h-3 w-3" />
            <span className="font-mono uppercase tracking-widest">Hybrid Graph-RAG · Hindi-first</span>
          </div>

          {/* Devanagari headline */}
          <h1 className="mt-8 font-devanagari text-5xl md:text-7xl lg:text-8xl text-primary leading-[1.05] animate-fade-up">
            Bharat<span className="gradient-text">Graph</span>
          </h1>

          {/* English subhead */}
          <p
            className="mt-6 text-2xl md:text-3xl font-display text-foreground/80 leading-snug animate-fade-up"
            style={{ animationDelay: "0.1s" }}
          >
            A bridge between Indian languages and machine reasoning.
          </p>

          <p
            className="mx-auto mt-6 max-w-2xl text-base md:text-lg text-muted-foreground leading-relaxed animate-fade-up"
            style={{ animationDelay: "0.2s" }}
          >
            Upload Hindi PDFs. Watch them become searchable knowledge graphs.
            Ask complex, multi-hop questions and get answers grounded in
            citations and entity relationships — powered by hybrid vector and
            graph retrieval.
          </p>

          {/* CTAs */}
          <div
            className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3 animate-fade-up"
            style={{ animationDelay: "0.3s" }}
          >
            <a
              href="#demo"
              className="group inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground shadow-elevated hover:shadow-glow-indigo hover:-translate-y-0.5 transition-spring"
            >
              Try the live demo
              <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition-smooth" />
            </a>
            <a
              href="#pipeline"
              className="inline-flex items-center gap-2 rounded-lg border border-border bg-card/60 backdrop-blur px-6 py-3 text-sm font-medium text-foreground hover:bg-card hover:border-primary/30 transition-smooth"
            >
              How it works
            </a>
          </div>

          {/* Stats / language chips */}
          <div
            className="mt-14 flex flex-wrap items-center justify-center gap-x-6 gap-y-3 text-xs animate-fade-up"
            style={{ animationDelay: "0.4s" }}
          >
            <span className="font-mono uppercase tracking-widest text-muted-foreground">
              Currently supported
            </span>
            <div className="flex flex-wrap items-center gap-2">
              <LangChip label="हिन्दी" sublabel="Hindi" active />
              <LangChip label="తెలుగు" sublabel="Telugu" active />
              <LangChip label="मराठी" sublabel="Marathi" active />

            </div>
          </div>
        </div>
      </div>

      <div className="container">
        <div className="divider-ornament" />
      </div>
    </section>
  );
};

const LangChip = ({
  label,
  sublabel,
  active,
}: {
  label: string;
  sublabel: string;
  active?: boolean;
}) => (
  <div
    className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs transition-smooth ${
      active
        ? "border-accent/40 bg-accent/10 text-foreground shadow-soft"
        : "border-border bg-card/40 text-muted-foreground"
    }`}
  >
    <span className="font-devanagari">{label}</span>
    <span className="font-mono text-[10px] uppercase tracking-wider opacity-70">
      {sublabel}
    </span>
    {active && (
      <span className="ml-0.5 h-1.5 w-1.5 rounded-full bg-accent animate-pulse-glow" />
    )}
    {!active && (
      <span className="ml-0.5 font-mono text-[9px] uppercase tracking-wider text-muted-foreground/70">
        soon
      </span>
    )}
  </div>
);
