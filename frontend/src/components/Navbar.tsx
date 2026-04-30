import { Network } from "lucide-react";

export const Navbar = () => {
  return (
    <header className="sticky top-0 z-40 w-full">
      <div className="absolute inset-0 bg-background/70 backdrop-blur-xl border-b border-border/50" />
      <nav className="container relative flex h-16 items-center justify-between">
        <a href="#" className="flex items-center gap-2.5 group">
          <div className="relative h-9 w-9 rounded-lg bg-hero flex items-center justify-center shadow-glow-indigo">
            <Network className="h-4 w-4 text-accent-glow" strokeWidth={2.5} />
            <div className="absolute -inset-0.5 rounded-lg bg-saffron opacity-0 group-hover:opacity-30 blur transition-smooth" />
          </div>
          <div className="flex flex-col leading-none">
            <span className="font-devanagari text-lg text-primary">BharatGraph</span>
            <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Gyaansetu</span>
          </div>
        </a>
        <div className="hidden md:flex items-center gap-8 text-sm">
          <a href="#demo" className="text-muted-foreground hover:text-primary transition-smooth">Demo</a>
          <a href="#pipeline" className="text-muted-foreground hover:text-primary transition-smooth">Pipeline</a>
          <a href="#features" className="text-muted-foreground hover:text-primary transition-smooth">Features</a>
          <a href="#about" className="text-muted-foreground hover:text-primary transition-smooth">About</a>
        </div>
        <a
          href="#demo"
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-xs font-medium text-primary-foreground shadow-soft hover:shadow-elevated hover:-translate-y-0.5 transition-spring"
        >
          Try the demo
        </a>
      </nav>
    </header>
  );
};
