import { useState } from "react";
import {
  FileText,
  Upload,
  Send,
  Loader2,
  CheckCircle2,
  Quote,
  Sparkles,
  Network,
} from "lucide-react";

type Stage = "idle" | "uploading" | "ready" | "thinking" | "answered";

interface MockDoc {
  name: string;
  pages: number;
  chunks: number;
  entities: number;
  relations: number;
}

interface MockAnswer {
  question: string;
  answer: string;
  entities: string[];
  citations: { doc: string; page: number; snippet: string }[];
  hops: { from: string; rel: string; to: string }[];
}

const SAMPLE_DOC: MockDoc = {
  name: "भारत_का_संविधान.pdf",
  pages: 142,
  chunks: 318,
  entities: 47,
  relations: 89,
};

const SAMPLE_QUESTIONS = [
  "मौलिक अधिकार और मौलिक कर्तव्य में क्या संबंध है?",
  "अनुच्छेद 14 की व्याख्या किस अनुच्छेद से जुड़ी है?",
  "संविधान सभा के अध्यक्ष कौन थे और उन्होंने क्या भूमिका निभाई?",
];

const SAMPLE_ANSWER: MockAnswer = {
  question: "मौलिक अधिकार और मौलिक कर्तव्य में क्या संबंध है?",
  answer:
    "मौलिक अधिकार (अनुच्छेद 12–35) और मौलिक कर्तव्य (अनुच्छेद 51A) भारतीय संविधान के दो पूरक स्तंभ हैं। जहाँ मौलिक अधिकार नागरिकों को राज्य के विरुद्ध संरक्षण देते हैं, वहीं मौलिक कर्तव्य प्रत्येक नागरिक से राष्ट्र के प्रति निष्ठा और संविधान के आदर्शों के पालन की अपेक्षा करते हैं। 42वें संविधान संशोधन (1976) के माध्यम से जोड़े गए मौलिक कर्तव्य, स्वर्ण सिंह समिति की सिफारिश पर आधारित थे और इनका उद्देश्य अधिकारों के साथ-साथ ज़िम्मेदारियों का संतुलन स्थापित करना था।",
  entities: [
    "मौलिक अधिकार",
    "मौलिक कर्तव्य",
    "अनुच्छेद 51A",
    "42वाँ संशोधन",
    "स्वर्ण सिंह समिति",
  ],
  citations: [
    {
      doc: "भारत_का_संविधान.pdf",
      page: 23,
      snippet:
        "भाग III में वर्णित मौलिक अधिकार राज्य की शक्तियों पर सीमा आरोपित करते हैं…",
    },
    {
      doc: "भारत_का_संविधान.pdf",
      page: 87,
      snippet:
        "अनुच्छेद 51A के अनुसार प्रत्येक नागरिक का यह कर्तव्य होगा कि वह संविधान का पालन करे…",
    },
    {
      doc: "भारत_का_संविधान.pdf",
      page: 112,
      snippet:
        "42वें संशोधन (1976) के द्वारा भाग IV-A जोड़ा गया जिसमें दस मौलिक कर्तव्य सम्मिलित किए गए…",
    },
  ],
  hops: [
    { from: "मौलिक अधिकार", rel: "पूरक है", to: "मौलिक कर्तव्य" },
    { from: "मौलिक कर्तव्य", rel: "जोड़ा गया", to: "42वाँ संशोधन" },
    { from: "42वाँ संशोधन", rel: "सिफारिश", to: "स्वर्ण सिंह समिति" },
  ],
};

export const DemoSection = () => {
  const [stage, setStage] = useState<Stage>("idle");
  const [doc, setDoc] = useState<MockDoc | null>(null);
  const [question, setQuestion] = useState("");
  const [streamed, setStreamed] = useState("");
  const [answer, setAnswer] = useState<MockAnswer | null>(null);

  const simulateUpload = () => {
    setStage("uploading");
    setTimeout(() => {
      setDoc(SAMPLE_DOC);
      setStage("ready");
    }, 1600);
  };

  const askQuestion = (q: string) => {
    setQuestion(q);
    setStage("thinking");
    setStreamed("");
    setAnswer(null);

    // Simulate token-by-token streaming
    setTimeout(() => {
      const chars = SAMPLE_ANSWER.answer.split("");
      let i = 0;
      const id = setInterval(() => {
        i += Math.max(2, Math.floor(Math.random() * 5));
        setStreamed(chars.slice(0, i).join(""));
        if (i >= chars.length) {
          clearInterval(id);
          setAnswer(SAMPLE_ANSWER);
          setStage("answered");
        }
      }, 28);
    }, 900);
  };

  return (
    <section id="demo" className="relative py-24 md:py-32">
      <div className="container">
        <SectionHeader
          eyebrow="Live Demo"
          devanagari="प्रदर्शन"
          title="Upload a document. Ask anything."
          description="A walkthrough using sample Hindi text. Click below to simulate the full pipeline — ingestion, graph construction, and hybrid retrieval."
        />

        <div className="mt-14 grid lg:grid-cols-5 gap-6">
          {/* Left: upload + doc info */}
          <div className="lg:col-span-2 space-y-4">
            <UploadCard stage={stage} doc={doc} onUpload={simulateUpload} />
            {doc && <DocStatsCard doc={doc} />}
          </div>

          {/* Right: chat / answer */}
          <div className="lg:col-span-3">
            <div className="glass-card rounded-2xl shadow-elevated overflow-hidden">
              <div className="flex items-center gap-2 border-b border-border/60 bg-secondary/40 px-5 py-3">
                <div className="flex gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-full bg-destructive/70" />
                  <span className="h-2.5 w-2.5 rounded-full bg-gold/80" />
                  <span className="h-2.5 w-2.5 rounded-full bg-primary-glow/60" />
                </div>
                <span className="ml-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                  Hybrid Graph-RAG · Chat
                </span>
              </div>

              <div className="p-6 min-h-[480px] flex flex-col">
                {stage === "idle" && <EmptyChatState />}

                {stage === "ready" && (
                  <ReadyState onAsk={askQuestion} questions={SAMPLE_QUESTIONS} />
                )}

                {(stage === "thinking" || stage === "answered") && (
                  <AnswerView
                    question={question}
                    streamed={streamed}
                    answer={answer}
                    isStreaming={stage === "thinking"}
                    onAskAnother={() => setStage("ready")}
                  />
                )}

                {stage === "uploading" && <UploadingChatState />}
              </div>

              {/* Input bar (visual only) */}
              <div className="border-t border-border/60 bg-secondary/30 p-3">
                <div className="flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 shadow-inner">
                  <input
                    disabled
                    placeholder={
                      stage === "ready" || stage === "answered"
                        ? "अपना प्रश्न यहाँ लिखें… (Type your question)"
                        : "Upload a document to begin…"
                    }
                    className="flex-1 bg-transparent text-sm placeholder:text-muted-foreground/60 focus:outline-none font-devanagari"
                  />
                  <button
                    disabled
                    className="inline-flex items-center justify-center h-8 w-8 rounded-md bg-primary text-primary-foreground opacity-50"
                  >
                    <Send className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

/* ────────── Subcomponents ────────── */

const SectionHeader = ({
  eyebrow,
  devanagari,
  title,
  description,
}: {
  eyebrow: string;
  devanagari: string;
  title: string;
  description: string;
}) => (
  <div className="mx-auto max-w-2xl text-center">
    <div className="inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.25em] text-accent">
      <span className="h-px w-6 bg-accent/40" />
      {eyebrow}
      <span className="h-px w-6 bg-accent/40" />
    </div>
    <h2 className="mt-4 font-devanagari text-4xl md:text-5xl text-primary">
      {devanagari}
    </h2>
    <p className="mt-2 font-display text-2xl md:text-3xl text-foreground/80">
      {title}
    </p>
    <p className="mt-4 text-muted-foreground leading-relaxed">{description}</p>
  </div>
);

const UploadCard = ({
  stage,
  doc,
  onUpload,
}: {
  stage: Stage;
  doc: MockDoc | null;
  onUpload: () => void;
}) => {
  const uploaded = doc !== null;
  return (
    <div className="glass-card rounded-2xl p-6 shadow-soft">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          Step 1 · Ingest
        </span>
        {uploaded && (
          <span className="inline-flex items-center gap-1 text-xs text-accent">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Indexed
          </span>
        )}
      </div>

      <button
        onClick={onUpload}
        disabled={stage === "uploading" || uploaded}
        className={`mt-4 group relative w-full rounded-xl border-2 border-dashed p-8 text-center transition-spring ${
          uploaded
            ? "border-accent/30 bg-accent/5"
            : "border-border hover:border-accent/50 hover:bg-accent/5"
        } ${stage === "uploading" ? "animate-pulse" : ""}`}
      >
        <div
          className={`mx-auto flex h-12 w-12 items-center justify-center rounded-full transition-spring ${
            uploaded
              ? "bg-accent/15 text-accent"
              : "bg-secondary text-muted-foreground group-hover:bg-accent/15 group-hover:text-accent group-hover:scale-110"
          }`}
        >
          {stage === "uploading" ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : uploaded ? (
            <FileText className="h-5 w-5" />
          ) : (
            <Upload className="h-5 w-5" />
          )}
        </div>
        <p className="mt-4 text-sm font-medium text-foreground">
          {stage === "uploading"
            ? "Processing…"
            : uploaded
            ? doc!.name
            : "Click to load sample Hindi PDF"}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          {stage === "uploading"
            ? "Chunking, embedding, extracting entities"
            : uploaded
            ? `${doc!.pages} pages · ready for queries`
            : "PDF · TXT · Devanagari & Indic scripts"}
        </p>
      </button>

      {stage === "uploading" && (
        <div className="mt-4 space-y-2">
          <ProgressLine label="Parsing PDF" pct={100} />
          <ProgressLine label="Chunking text" pct={92} />
          <ProgressLine label="Generating embeddings" pct={68} />
          <ProgressLine label="Extracting entities · building graph" pct={34} />
        </div>
      )}
    </div>
  );
};

const ProgressLine = ({ label, pct }: { label: string; pct: number }) => (
  <div>
    <div className="flex items-center justify-between text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
      <span>{label}</span>
      <span>{pct}%</span>
    </div>
    <div className="mt-1 h-1 rounded-full bg-secondary overflow-hidden">
      <div
        className="h-full bg-saffron"
        style={{
          width: `${pct}%`,
          backgroundSize: "200% 100%",
          animation: "shimmer 2s linear infinite",
        }}
      />
    </div>
  </div>
);

const DocStatsCard = ({ doc }: { doc: MockDoc }) => (
  <div className="ink-card rounded-2xl p-6 shadow-elevated">
    <span className="font-mono text-[10px] uppercase tracking-widest text-accent-glow">
      Knowledge Index
    </span>
    <div className="mt-4 grid grid-cols-2 gap-4">
      <Stat label="Pages" value={doc.pages} />
      <Stat label="Chunks" value={doc.chunks} />
      <Stat label="Entities" value={doc.entities} />
      <Stat label="Relations" value={doc.relations} />
    </div>
    <div className="mt-5 flex items-center gap-2 rounded-lg bg-primary-foreground/5 px-3 py-2 text-[11px] text-primary-foreground/80">
      <Network className="h-3.5 w-3.5 text-accent-glow" />
      Graph stored in Neo4j · Vectors in pgvector
    </div>
  </div>
);

const Stat = ({ label, value }: { label: string; value: number }) => (
  <div>
    <div className="font-display text-3xl text-accent-glow">{value}</div>
    <div className="font-mono text-[10px] uppercase tracking-widest text-primary-foreground/60">
      {label}
    </div>
  </div>
);

const EmptyChatState = () => (
  <div className="m-auto text-center max-w-sm">
    <div className="mx-auto h-12 w-12 rounded-full bg-secondary flex items-center justify-center mb-4">
      <Sparkles className="h-5 w-5 text-muted-foreground" />
    </div>
    <p className="font-display text-xl text-foreground/70">
      Load a document to begin
    </p>
    <p className="mt-2 text-sm text-muted-foreground">
      Once indexed, you can ask questions in Hindi or English and explore the
      extracted knowledge graph.
    </p>
  </div>
);

const UploadingChatState = () => (
  <div className="m-auto text-center">
    <Loader2 className="mx-auto h-6 w-6 text-accent animate-spin" />
    <p className="mt-3 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
      Building knowledge graph…
    </p>
  </div>
);

const ReadyState = ({
  onAsk,
  questions,
}: {
  onAsk: (q: string) => void;
  questions: string[];
}) => (
  <div className="animate-fade-in">
    <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
      Suggested questions
    </p>
    <div className="mt-3 space-y-2">
      {questions.map((q) => (
        <button
          key={q}
          onClick={() => onAsk(q)}
          className="w-full text-left rounded-lg border border-border bg-card/60 hover:bg-accent/5 hover:border-accent/40 p-4 text-sm transition-smooth font-devanagari group"
        >
          <span className="text-foreground/90">{q}</span>
          <span className="float-right opacity-0 group-hover:opacity-100 text-accent text-xs font-mono uppercase tracking-widest transition-smooth">
            ask →
          </span>
        </button>
      ))}
    </div>
    <p className="mt-6 text-xs text-muted-foreground italic">
      Tip: each question runs vector + graph retrieval, then synthesizes a
      cited, multi-hop answer.
    </p>
  </div>
);

const AnswerView = ({
  question,
  streamed,
  answer,
  isStreaming,
  onAskAnother,
}: {
  question: string;
  streamed: string;
  answer: MockAnswer | null;
  isStreaming: boolean;
  onAskAnother: () => void;
}) => {
  return (
    <div className="space-y-5 animate-fade-in">
      {/* User question */}
      <div className="flex gap-3 justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-primary px-4 py-3 text-sm text-primary-foreground font-devanagari shadow-soft">
          {question}
        </div>
      </div>

      {/* Assistant answer */}
      <div className="flex gap-3">
        <div className="flex-shrink-0 h-8 w-8 rounded-full bg-saffron flex items-center justify-center shadow-glow-saffron">
          <Sparkles className="h-3.5 w-3.5 text-accent-foreground" />
        </div>
        <div className="flex-1 space-y-4">
          <div className="rounded-2xl rounded-tl-sm bg-secondary/60 border border-border/50 px-4 py-3 text-sm leading-relaxed text-foreground font-devanagari">
            {streamed}
            {isStreaming && (
              <span className="inline-block ml-0.5 w-1.5 h-4 bg-accent align-middle animate-type-cursor" />
            )}
          </div>

          {answer && (
            <>
              {/* Entity chips */}
              <div>
                <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
                  Entities mentioned
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {answer.entities.map((e) => (
                    <span
                      key={e}
                      className="inline-flex items-center gap-1 rounded-full border border-accent/30 bg-accent/8 px-2.5 py-1 text-xs font-devanagari text-foreground"
                    >
                      <span className="h-1.5 w-1.5 rounded-full bg-accent" />
                      {e}
                    </span>
                  ))}
                </div>
              </div>

              {/* Multi-hop reasoning */}
              <div>
                <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
                  Graph reasoning path
                </p>
                <div className="rounded-lg border border-border bg-card/60 p-3 space-y-2">
                  {answer.hops.map((h, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 text-xs font-devanagari"
                    >
                      <span className="rounded bg-primary/10 px-2 py-0.5 text-primary">
                        {h.from}
                      </span>
                      <span className="font-mono text-[9px] uppercase tracking-widest text-muted-foreground">
                        — {h.rel} →
                      </span>
                      <span className="rounded bg-accent/10 px-2 py-0.5 text-accent">
                        {h.to}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Citations */}
              <div>
                <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-2">
                  Source citations
                </p>
                <div className="space-y-2">
                  {answer.citations.map((c, i) => (
                    <div
                      key={i}
                      className="flex gap-3 rounded-lg border border-border bg-background/60 p-3 hover:border-accent/40 transition-smooth"
                    >
                      <Quote className="h-3.5 w-3.5 text-accent flex-shrink-0 mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-devanagari text-foreground/90 leading-relaxed">
                          {c.snippet}
                        </p>
                        <p className="mt-1 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                          {c.doc} · p.{c.page}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <button
                onClick={onAskAnother}
                className="text-xs font-mono uppercase tracking-widest text-accent hover:text-primary transition-smooth"
              >
                ← Ask another question
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
