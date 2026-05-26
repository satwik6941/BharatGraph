import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Send, Sparkles, Loader2, FileText, Construction } from "lucide-react";

const BACKEND_ACTIVE = false;

type Stage = "ready" | "thinking" | "answered";

interface Chunk {
  score: number;
  text: string;
  source: string;
}

interface AssistantMessage {
  role: "assistant";
  answer: string;
  language: string;
  chunks: Chunk[];
}

interface UserMessage {
  role: "user";
  text: string;
}

type Message = UserMessage | AssistantMessage;

const LANG_LABEL: Record<string, string> = {
  hindi: "हिन्दी · Hindi",
  marathi: "मराठी · Marathi",
  telugu: "తెలుగు · Telugu",
};

const Chat = () => {
  const [stage, setStage] = useState<Stage>("ready");
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);

  const askQuestion = async (q: string) => {
    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setInputValue("");
    setStage("thinking");

    try {
      const apiUrl = import.meta.env.VITE_API_URL ?? "/api/query";
      const res = await fetch(
        apiUrl.startsWith("http") ? `${apiUrl}/api/query` : apiUrl,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: q }),
        }
      );

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          answer: data.answer,
          language: data.language,
          chunks: data.chunks,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          answer: `Error: could not reach the backend. (${err})`,
          language: "unknown",
          chunks: [],
        },
      ]);
    } finally {
      setStage("answered");
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && stage !== "thinking") {
      askQuestion(inputValue.trim());
    }
  };

  const canType = stage !== "thinking" && BACKEND_ACTIVE;

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
            <span className={`h-2 w-2 rounded-full ${BACKEND_ACTIVE ? "bg-accent animate-pulse-glow" : "bg-destructive/70"}`} />
            <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              {BACKEND_ACTIVE ? "Hybrid Graph-RAG" : "Backend Offline"}
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

            {/* Offline banner */}
            {!BACKEND_ACTIVE && (
              <div className="flex items-start gap-3 border-b border-destructive/20 bg-destructive/5 px-5 py-3 flex-shrink-0">
                <Construction className="h-4 w-4 text-destructive/70 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-xs font-semibold text-destructive/80 uppercase tracking-wide">Backend Offline — Under Expansion</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    The GCP backend is currently inactive as BharatGraph is being expanded to support additional Indian languages and document types. The live query interface will be restored upon redeployment. Full source code and benchmark results are available on GitHub.
                  </p>
                </div>
              </div>
            )}

            {/* Chat body */}
            <div className="p-6 flex-1 overflow-y-auto min-h-[420px] flex flex-col gap-6">

              {/* Empty state */}
              {messages.length === 0 && (
                <div className="m-auto text-center max-w-sm flex flex-col items-center justify-center h-full">
                  <div className="mx-auto h-12 w-12 rounded-full bg-secondary flex items-center justify-center mb-4">
                    {BACKEND_ACTIVE
                      ? <Sparkles className="h-5 w-5 text-muted-foreground" />
                      : <Construction className="h-5 w-5 text-muted-foreground" />
                    }
                  </div>
                  {BACKEND_ACTIVE ? (
                    <>
                      <p className="font-display text-xl text-foreground/70">Ask anything</p>
                      <p className="mt-2 text-sm text-muted-foreground">
                        Type a question in Hindi, Marathi, or Telugu. BharatGraph will
                        detect the language automatically and retrieve answers using
                        hybrid vector and graph search.
                      </p>
                    </>
                  ) : (
                    <>
                      <p className="font-display text-xl text-foreground/70">Demo Temporarily Unavailable</p>
                      <p className="mt-2 text-sm text-muted-foreground">
                        The backend is currently offline while the project is under active expansion.
                        Check back soon — or explore the benchmark results and source code on GitHub.
                      </p>
                    </>
                  )}
                </div>
              )}

              {/* Message thread */}
              {messages.map((msg, i) =>
                msg.role === "user" ? (
                  /* ── User bubble ── */
                  <div key={i} className="flex justify-end">
                    <div className="max-w-[75%] rounded-2xl rounded-tr-sm bg-primary px-4 py-3 text-sm text-primary-foreground font-devanagari shadow-soft">
                      {msg.text}
                    </div>
                  </div>
                ) : (
                  /* ── Assistant response ── */
                  <div key={i} className="flex gap-3">
                    <div className="flex-shrink-0 h-8 w-8 rounded-full bg-saffron flex items-center justify-center shadow-glow-saffron mt-1">
                      <Sparkles className="h-3.5 w-3.5 text-accent-foreground" />
                    </div>

                    <div className="flex-1 space-y-4 min-w-0">

                      {/* Language badge */}
                      <div className="inline-flex items-center gap-1.5 rounded-full border border-accent/30 bg-accent/8 px-2.5 py-1 text-[10px] font-mono uppercase tracking-widest text-accent">
                        <span className="h-1.5 w-1.5 rounded-full bg-accent" />
                        {LANG_LABEL[msg.language] ?? msg.language}
                      </div>

                      {/* Retrieved chunks */}
                      {msg.chunks.length > 0 && (
                        <div>
                          <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
                            Retrieved context — {msg.chunks.length} chunk{msg.chunks.length !== 1 ? "s" : ""}
                          </p>
                          <div className="space-y-2">
                            {msg.chunks.map((chunk, ci) => (
                              <div
                                key={ci}
                                className="rounded-lg border border-border bg-card/60 p-3 space-y-2"
                              >
                                {/* Score row */}
                                <div className="flex items-center gap-3">
                                  <span className="font-mono text-[10px] text-muted-foreground w-4">{ci + 1}</span>
                                  <div className="flex-1 h-1.5 rounded-full bg-secondary overflow-hidden">
                                    <div
                                      className={`h-full rounded-full ${
                                        chunk.score >= 0.95
                                          ? "bg-accent"
                                          : chunk.score >= 0.85
                                          ? "bg-yellow-400"
                                          : "bg-muted-foreground/50"
                                      }`}
                                      style={{ width: `${chunk.score * 100}%` }}
                                    />
                                  </div>
                                  <span className="font-mono text-[11px] text-foreground/70 tabular-nums w-12 text-right">
                                    {chunk.score.toFixed(4)}
                                  </span>
                                </div>

                                {/* Chunk text */}
                                <p className="text-xs text-foreground/80 font-devanagari leading-relaxed line-clamp-3">
                                  {chunk.text}
                                </p>

                                {/* Source */}
                                <div className="flex items-center gap-1 text-[10px] font-mono text-muted-foreground/70">
                                  <FileText className="h-3 w-3" />
                                  {chunk.source}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Final answer */}
                      <div>
                        <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
                          Answer
                        </p>
                        <div className="rounded-2xl rounded-tl-sm bg-secondary/60 border border-border/50 px-4 py-3 text-sm leading-relaxed text-foreground font-devanagari whitespace-pre-wrap">
                          {msg.answer}
                        </div>
                      </div>

                    </div>
                  </div>
                )
              )}

              {/* Thinking indicator */}
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
                  placeholder={BACKEND_ACTIVE ? "अपना प्रश्न यहाँ लिखें… (Type your question)" : "Backend offline — query unavailable"}
                  className="flex-1 bg-transparent text-sm placeholder:text-muted-foreground/60 focus:outline-none font-devanagari disabled:cursor-not-allowed"
                />
                <button
                  type="submit"
                  title="Send question"
                  disabled={!canType || !inputValue.trim()}
                  className="inline-flex items-center justify-center h-8 w-8 rounded-md bg-primary text-primary-foreground disabled:opacity-40 hover:bg-primary/90 transition-smooth"
                >
                  {stage === "thinking"
                    ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    : <Send className="h-3.5 w-3.5" />
                  }
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
