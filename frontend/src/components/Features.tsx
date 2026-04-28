import { Languages, GitBranch, ShieldCheck, Zap, BookOpen, Layers } from "lucide-react";

const FEATURES = [
  {
    icon: Languages,
    title: "Indic-first NLP",
    desc: "Built for Devanagari and Indian language morphology — not retrofitted from English models.",
  },
  {
    icon: GitBranch,
    title: "Multi-hop reasoning",
    desc: "Graph traversal connects facts across documents, surfacing answers a vector search alone would miss.",
  },
  {
    icon: BookOpen,
    title: "Cited & grounded",
    desc: "Every answer ships with source snippets, page numbers, and the entity path used to derive it.",
  },
  {
    icon: Layers,
    title: "Hybrid by default",
    desc: "Use Graph-RAG where it shines, plain RAG where it suffices. The system picks the right strategy per query.",
  },
  {
    icon: Zap,
    title: "Streaming answers",
    desc: "Token-by-token responses with live retrieval traces — built for real-time interaction.",
  },
  {
    icon: ShieldCheck,
    title: "Open & extensible",
    desc: "Pluggable embeddings, swappable graph store (Neo4j today), and LLM-agnostic synthesis layer.",
  },
];

export const Features = () => {
  return (
    <section id="features" className="py-24 md:py-32">
      <div className="container">
        <div className="mx-auto max-w-2xl text-center">
          <div className="inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.25em] text-accent">
            <span className="h-px w-6 bg-accent/40" />
            Why it matters
            <span className="h-px w-6 bg-accent/40" />
          </div>
          <h2 className="mt-4 font-devanagari text-4xl md:text-5xl text-primary">
            विशेषताएँ
          </h2>
          <p className="mt-2 font-display text-2xl md:text-3xl text-foreground/80">
            Document intelligence designed for Bharat.
          </p>
        </div>

        <div className="mt-16 grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="group rounded-2xl border border-border bg-card/60 p-6 hover:border-accent/40 hover:bg-card transition-smooth"
            >
              <div className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10 text-accent group-hover:bg-saffron group-hover:text-accent-foreground group-hover:shadow-glow-saffron transition-spring">
                <f.icon className="h-5 w-5" />
              </div>
              <h3 className="mt-5 font-display text-xl text-foreground">
                {f.title}
              </h3>
              <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                {f.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
