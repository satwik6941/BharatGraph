import {
  FileInput,
  Scissors,
  Sparkles,
  Network,
  Search,
  MessagesSquare,
} from "lucide-react";

const STEPS = [
  {
    n: "01",
    icon: FileInput,
    devanagari: "ग्रहण",
    title: "Ingest",
    desc: "Parse Hindi/Indic PDFs and text. Detect script, normalize Unicode, preserve structure.",
  },
  {
    n: "02",
    icon: Scissors,
    devanagari: "खंडन",
    title: "Chunk",
    desc: "Sentence-aware chunking tuned for Devanagari and Indic punctuation rules.",
  },
  {
    n: "03",
    icon: Sparkles,
    devanagari: "एम्बेडिंग",
    title: "Embed",
    desc: "Multilingual embeddings stored in pgvector for fast semantic similarity search.",
  },
  {
    n: "04",
    icon: Network,
    devanagari: "ज्ञान-ग्राफ",
    title: "Graph",
    desc: "LLM extracts entities and relationships, persisted as a Neo4j knowledge graph.",
  },
  {
    n: "05",
    icon: Search,
    devanagari: "हाइब्रिड खोज",
    title: "Hybrid Retrieval",
    desc: "Vector search finds similar text; graph traversal surfaces connected concepts and multi-hop paths.",
  },
  {
    n: "06",
    icon: MessagesSquare,
    devanagari: "उत्तर",
    title: "Answer",
    desc: "Context is fused and passed to an LLM that returns a cited, reasoning-grounded response.",
  },
];

export const Pipeline = () => {
  return (
    <section id="pipeline" className="relative py-24 md:py-32 bg-parchment">
      <div className="container">
        <div className="mx-auto max-w-2xl text-center">
          <div className="inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.25em] text-accent">
            <span className="h-px w-6 bg-accent/40" />
            The Pipeline
            <span className="h-px w-6 bg-accent/40" />
          </div>
          <h2 className="mt-4 font-devanagari text-4xl md:text-5xl text-primary">
            कैसे काम करता है
          </h2>
          <p className="mt-2 font-display text-2xl md:text-3xl text-foreground/80">
            From raw PDF to multi-hop answer in six stages.
          </p>
        </div>

        <div className="mt-16 grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          {STEPS.map((s, i) => (
            <div
              key={s.n}
              className="group relative rounded-2xl border border-border bg-card p-6 shadow-soft hover:shadow-elevated hover:-translate-y-1 transition-spring"
              style={{ animationDelay: `${i * 60}ms` }}
            >
              <div className="flex items-start justify-between">
                <div className="h-11 w-11 rounded-xl bg-hero flex items-center justify-center shadow-glow-indigo">
                  <s.icon className="h-5 w-5 text-accent-glow" strokeWidth={2} />
                </div>
                <span className="font-mono text-xs text-muted-foreground/60">
                  {s.n}
                </span>
              </div>
              <h3 className="mt-5 font-devanagari text-2xl text-primary">
                {s.devanagari}
              </h3>
              <p className="mt-1 font-display text-lg text-foreground/80">
                {s.title}
              </p>
              <p className="mt-3 text-sm text-muted-foreground leading-relaxed">
                {s.desc}
              </p>
              <div className="absolute bottom-0 left-6 right-6 h-px bg-gradient-to-r from-transparent via-accent/40 to-transparent opacity-0 group-hover:opacity-100 transition-smooth" />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
