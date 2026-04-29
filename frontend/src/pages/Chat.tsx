import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Send, Sparkles, Loader2 } from "lucide-react";

type Stage = "ready" | "thinking" | "answered";

interface Message {
  role: "user" | "assistant";
  text: string;
}

const Chat = () => {
  const [stage, setStage] = useState<Stage>("ready");
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);

  const askQuestion = (q: string) => {
    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setInputValue("");
    setStage("thinking");

    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "Backend connection not yet wired. Your question has been received and will be processed once the API is connected.",
        },
      ]);
      setStage("answered");
    }, 1200);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && stage !== "thinking") {
      askQuestion(inputValue.trim());
    }
  };

  const canType = stage !== "thinking";

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Top bar */}
      <header className="sticky top-0 z-10 border-b border-border/60 bg-background/80 backdrop-blur">
        <div className="container flex h-14 items-center gap-4">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-smooth"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </Link>
          <div className="h-4 w-px bg-border" />
          <span className="font-mono text-[10px] uppercase tracking-widest text-accent">
            BharatGraph · Live Demo
          </span>
          <div className="ml-auto flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-accent animate-pulse-glow" />
            <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              Hybrid Graph-RAG
            </span>
          </div>
        </div>
      </header>

      {/* Main layout */}
      <div className="container flex-1 py-8 flex flex-col">
        <div className="flex flex-col flex-1">
          <div className="glass-card rounded-2xl shadow-elevated overflow-hidden flex flex-col flex-1">
            {/* Chrome bar */}
            <div className="flex items-center gap-2 border-b border-border/60 bg-secondary/40 px-5 py-3 flex-shrink-0">
              <div className="flex gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-destructive/70" />
                <span className="h-2.5 w-2.5 rounded-full bg-yellow-400/80" />
                <span className="h-2.5 w-2.5 rounded-full bg-accent/60" />
              </div>
              <span className="ml-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                Hybrid Graph-RAG · Chat
              </span>
            </div>

            {/* Chat body */}
            <div className="p-6 flex-1 overflow-y-auto min-h-[420px] flex flex-col gap-4">
              {messages.length === 0 && (
                <div className="m-auto text-center max-w-sm flex flex-col items-center justify-center h-full">
                  <div className="mx-auto h-12 w-12 rounded-full bg-secondary flex items-center justify-center mb-4">
                    <Sparkles className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <p className="font-display text-xl text-foreground/70">
                    Ask anything
                  </p>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Type a question in Hindi, Marathi, or Telugu below. BharatGraph
                    will retrieve answers using hybrid vector and graph search.
                  </p>
                </div>
              )}

              {messages.map((msg, i) =>
                msg.role === "user" ? (
                  <div key={i} className="flex justify-end">
                    <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-primary px-4 py-3 text-sm text-primary-foreground font-devanagari shadow-soft">
                      {msg.text}
                    </div>
                  </div>
                ) : (
                  <div key={i} className="flex gap-3">
                    <div className="flex-shrink-0 h-8 w-8 rounded-full bg-saffron flex items-center justify-center shadow-glow-saffron">
                      <Sparkles className="h-3.5 w-3.5 text-accent-foreground" />
                    </div>
                    <div className="flex-1 rounded-2xl rounded-tl-sm bg-secondary/60 border border-border/50 px-4 py-3 text-sm leading-relaxed text-foreground font-devanagari">
                      {msg.text}
                    </div>
                  </div>
                )
              )}

              {stage === "thinking" && (
                <div className="flex gap-3">
                  <div className="flex-shrink-0 h-8 w-8 rounded-full bg-saffron flex items-center justify-center">
                    <Loader2 className="h-3.5 w-3.5 text-accent-foreground animate-spin" />
                  </div>
                  <div className="rounded-2xl rounded-tl-sm bg-secondary/60 border border-border/50 px-4 py-3 text-sm text-muted-foreground font-mono">
                    Retrieving from knowledge graph…
                  </div>
                </div>
              )}
            </div>

            {/* Input bar */}
            <div className="border-t border-border/60 bg-secondary/30 p-3 flex-shrink-0">
              <form
                onSubmit={handleSubmit}
                className="flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 shadow-inner focus-within:border-accent/50 transition-smooth"
              >
                <input
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  disabled={!canType}
                  placeholder="अपना प्रश्न यहाँ लिखें… (Type your question)"
                  className="flex-1 bg-transparent text-sm placeholder:text-muted-foreground/60 focus:outline-none font-devanagari disabled:cursor-not-allowed"
                />
                <button
                  type="submit"
                  title="Send question"
                  disabled={!canType || !inputValue.trim()}
                  className="inline-flex items-center justify-center h-8 w-8 rounded-md bg-primary text-primary-foreground disabled:opacity-40 hover:bg-primary/90 transition-smooth"
                >
                  <Send className="h-3.5 w-3.5" />
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Chat;
