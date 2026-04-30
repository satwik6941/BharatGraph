import { Github, Mail, Network } from "lucide-react";

export const Footer = () => {
  return (
    <footer id="about" className="relative border-t border-border bg-hero text-primary-foreground overflow-hidden">
      <div className="absolute inset-0 opacity-30 pointer-events-none">
        <div className="absolute top-1/2 left-1/4 h-64 w-64 rounded-full bg-accent/30 blur-3xl" />
        <div className="absolute bottom-0 right-1/4 h-64 w-64 rounded-full bg-primary-glow/40 blur-3xl" />
      </div>

      <div className="container relative py-20">
        <div className="grid md:grid-cols-3 gap-12">
          <div className="md:col-span-2">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-saffron flex items-center justify-center shadow-glow-saffron">
                <Network className="h-4 w-4 text-accent-foreground" strokeWidth={2.5} />
              </div>
              <div>
                <div className="font-devanagari text-2xl">BharatGraph</div>
                <div className="font-mono text-[10px] uppercase tracking-widest text-primary-foreground/60">
                  Gyaansetu · Knowledge Bridge
                </div>
              </div>
            </div>
            <p className="mt-6 max-w-lg text-primary-foreground/75 leading-relaxed">
              An academic research project on automatic knowledge graph
              construction for Indian languages. Currently optimized for Hindi,
              Marathi and Telugu on the roadmap.
            </p>
            <div className="mt-8 flex items-center gap-3">
              <a
                href="#"
                className="inline-flex items-center gap-2 rounded-lg border border-primary-foreground/20 bg-primary-foreground/5 px-4 py-2 text-xs font-mono uppercase tracking-widest hover:bg-primary-foreground/10 transition-smooth"
              >
                <Github className="h-3.5 w-3.5" /> Source
              </a>
              <a
                href="#"
                className="inline-flex items-center gap-2 rounded-lg border border-primary-foreground/20 bg-primary-foreground/5 px-4 py-2 text-xs font-mono uppercase tracking-widest hover:bg-primary-foreground/10 transition-smooth"
              >
                <Mail className="h-3.5 w-3.5" /> Contact
              </a>
            </div>
          </div>

          <div className="space-y-6 text-sm">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-widest text-accent-glow">
                Stack
              </div>
              <ul className="mt-3 space-y-1.5 text-primary-foreground/75">
                <li>Neo4j · Knowledge graph</li>
                <li>Vyakyarth · Embeddings</li>
                <li>OpenAI · Multi-hop synthesis</li>
                <li>FastAPI · Python backend</li>
              </ul>
            </div>
            <div>
              <div className="font-mono text-[10px] uppercase tracking-widest text-accent-glow">
                Roadmap
              </div>
              <ul className="mt-3 space-y-1.5 text-primary-foreground/75 font-devanagari">
                <li>தமிழ் — Tamil support</li>
                <li>मराठी — Marathi support</li>
                <li>తెలుగు — Telugu support</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="mt-16 pt-6 border-t border-primary-foreground/10 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-primary-foreground/50 font-mono uppercase tracking-widest">
          <span>© {new Date().getFullYear()} BharatGraph Research</span>
          <span className="font-devanagari normal-case tracking-normal text-sm text-primary-foreground/70 italic">
            "विद्या ददाति विनयम्"
          </span>
        </div>
      </div>
    </footer>
  );
};
