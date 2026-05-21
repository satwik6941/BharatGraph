"""
comparison.py — Retrieval quality comparison across three pipelines.

Pipelines:
  1. Simple RAG      — ChromaDB vector search only (dense)
  2. Hybrid RAG      — ChromaDB vector + BM25 keyword (dense + sparse, score averaged)
  3. Hybrid Graph RAG — Neo4j vector + fulltext + Cypher entity graph traversal

All three use the Vyakyarth embedding model (krutrim-ai-labs/Vyakyarth).
Results are saved to comparison_results/ in the same format as query_results/.

Usage:
    python comparison.py
"""

import os
import re
import sys
import math
from collections import Counter
from datetime import datetime
from pathlib import Path

import neo4j
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from neo4j_graphrag.retrievers import HybridCypherRetriever
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.embeddings.base import Embedder

import warnings
warnings.filterwarnings("ignore")
load_dotenv()

TOP_K = 10
OUTPUT_DIR = Path("comparison_results")


# ── Tee: write to stdout AND file simultaneously ──────────────────────────────
class Tee:
    def __init__(self, file):
        self._file = file
        self._stdout = sys.stdout

    def write(self, data):
        self._stdout.write(data)
        self._file.write(data)

    def flush(self):
        self._stdout.flush()
        self._file.flush()


# ── Vyakyarth embedding model ─────────────────────────────────────────────────
print("Loading Vyakyarth embedding model…")
_model = SentenceTransformer("krutrim-ai-labs/Vyakyarth")
print("Model loaded.\n")


def embed(text: str) -> list[float]:
    return _model.encode(text).tolist()


class VyakyarthEmbedder(Embedder):
    def embed_query(self, text: str) -> list[float]:
        return embed(text)


# ── Neo4j connection ──────────────────────────────────────────────────────────
driver = neo4j.GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")),
)
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


def fetch_all_chunks(language: str) -> list[dict]:
    with driver.session(database=DATABASE) as session:
        rows = session.run(
            "MATCH (c:Chunk {language: $language}) "
            "RETURN c.chunkId AS chunkId, c.text AS text, c.source AS source",
            language=language,
        )
        return [{"chunkId": r["chunkId"], "text": r["text"], "source": r["source"]}
                for r in rows]


# ── ChromaDB — built in-memory from Neo4j chunks ─────────────────────────────
chroma_client = chromadb.Client(Settings(anonymized_telemetry=False))
_chroma_collections: dict[str, chromadb.Collection] = {}


def get_chroma_collection(language: str) -> chromadb.Collection:
    if language in _chroma_collections:
        return _chroma_collections[language]
    chunks = fetch_all_chunks(language)
    if not chunks:
        raise ValueError(f"No chunks in Neo4j for language='{language}'")
    collection = chroma_client.create_collection(
        name=f"bharatgraph_{language}",
        metadata={"hnsw:space": "cosine"},
    )
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i: i + batch_size]
        collection.add(
            ids=[c["chunkId"] for c in batch],
            embeddings=[embed(c["text"]) for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[{"source": c["source"]} for c in batch],
        )
    print(f"  Chroma [{language}]: {len(chunks)} chunks indexed.")
    _chroma_collections[language] = collection
    return collection


# ── BM25 — pure Python ────────────────────────────────────────────────────────
class BM25:
    def __init__(self, corpus: list[str]):
        self.k1, self.b = 1.5, 0.75
        self.corpus = corpus
        # tokenise by characters (works for Devanagari / Telugu without word segmenter)
        self.tok = [list(doc) for doc in corpus]
        self.N = len(corpus)
        self.avgdl = sum(len(d) for d in self.tok) / max(self.N, 1)
        self.df: Counter = Counter()
        for doc in self.tok:
            for term in set(doc):
                self.df[term] += 1

    def scores(self, query: str) -> list[float]:
        result = []
        for idx in range(self.N):
            doc, dl = self.tok[idx], len(self.tok[idx])
            tf: Counter = Counter(doc)
            s = 0.0
            for term in query:
                if term not in self.df:
                    continue
                idf = math.log((self.N - self.df[term] + 0.5) / (self.df[term] + 0.5) + 1)
                num = tf[term] * (self.k1 + 1)
                den = tf[term] + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                s += idf * num / den
            result.append(s)
        return result


_bm25_cache: dict[str, tuple[BM25, list[dict]]] = {}


def get_bm25(language: str) -> tuple[BM25, list[dict]]:
    if language in _bm25_cache:
        return _bm25_cache[language]
    chunks = fetch_all_chunks(language)
    _bm25_cache[language] = (BM25([c["text"] for c in chunks]), chunks)
    return _bm25_cache[language]


# ── Pipeline 1 — Simple RAG (dense vector only) ───────────────────────────────
def simple_rag(question: str, language: str) -> list[dict]:
    collection = get_chroma_collection(language)
    res = collection.query(
        query_embeddings=[embed(question)],
        n_results=TOP_K,
        include=["documents", "distances", "metadatas"],
    )
    chunks = []
    for doc, dist, meta in zip(
        res["documents"][0], res["distances"][0], res["metadatas"][0]
    ):
        chunks.append({
            "score":  round(1.0 - dist, 4),   # cosine distance → similarity
            "text":   doc,
            "source": meta["source"],
        })
    return chunks


# ── Pipeline 2 — Hybrid RAG (dense + BM25, score-averaged) ───────────────────
def hybrid_rag(question: str, language: str) -> list[dict]:
    collection = get_chroma_collection(language)
    bm25, all_chunks = get_bm25(language)

    # Dense scores for all chunks
    dense_res = collection.query(
        query_embeddings=[embed(question)],
        n_results=len(all_chunks),
        include=["documents", "distances", "metadatas"],
    )
    # Build chunkId → dense_score map via text matching
    dense_score_map: dict[str, float] = {}
    for doc, dist in zip(dense_res["documents"][0], dense_res["distances"][0]):
        for c in all_chunks:
            if c["text"] == doc:
                dense_score_map[c["chunkId"]] = round(1.0 - dist, 4)
                break

    # BM25 scores — normalise to [0, 1]
    bm25_raw = bm25.scores(question)
    max_bm25 = max(bm25_raw) if bm25_raw else 1.0
    if max_bm25 == 0:
        max_bm25 = 1.0

    # Combine: average of dense + normalised BM25
    combined = []
    for idx, c in enumerate(all_chunks):
        d_score = dense_score_map.get(c["chunkId"], 0.0)
        b_score = bm25_raw[idx] / max_bm25
        avg = round((d_score + b_score) / 2, 4)
        combined.append({"score": avg, "text": c["text"], "source": c["source"]})

    combined.sort(key=lambda x: x["score"], reverse=True)
    return combined[:TOP_K]


# ── Pipeline 3 — Hybrid Graph RAG (Neo4j) ────────────────────────────────────
RETRIEVAL_QUERY = """
WHERE node.language = $language
OPTIONAL MATCH (node)-[:HAS_ENTITY]->(e:Entity)
WHERE NOT EXISTS {
    MATCH (e)-[gn:RELATES_TO]-()
    WITH count(gn) AS degree WHERE degree > 50 RETURN degree
}
OPTIONAL MATCH (e)-[r:RELATES_TO]->(e2:Entity)
WHERE NOT EXISTS {
    MATCH (e2)-[gn2:RELATES_TO]-()
    WITH count(gn2) AS degree WHERE degree > 50 RETURN degree
}
RETURN
    score,
    node.text                          AS chunkText,
    node.chunkId                       AS chunkId,
    node.source                        AS source,
    node.language                      AS language,
    collect(DISTINCT e.name)           AS entities,
    collect(DISTINCT {from: e.name, rel: r.type, to: e2.name}) AS triples
"""


def parse_graph_item(raw: str) -> dict:
    score_m  = re.search(r"score=([\d.]+)", raw)
    text_m   = re.search(r"chunkText='(.*?)'(?=\s+\w+=|>)", raw, re.DOTALL)
    source_m = re.search(r"source='(.*?)'", raw)
    return {
        "score":  round(float(score_m.group(1)), 4) if score_m else 0.0,
        "text":   text_m.group(1).replace("\\n", " ").strip() if text_m else raw[:300],
        "source": source_m.group(1) if source_m else "unknown",
    }


# ── LLM answer ────────────────────────────────────────────────────────────────
def generate_answer(llm: OpenAILLM, question: str, chunks: list[dict]) -> str:
    context = "\n\n".join(
        f"[{i+1}] {c['text']}" for i, c in enumerate(chunks)
    )
    prompt = (
        f"Answer the following question using only the provided context.\n"
        f"Question: {question}\n\nContext:\n{context}\n\nAnswer:"
    )
    response = llm.invoke(prompt)
    return response.content if hasattr(response, "content") else str(response)


# ── Print helpers (matching query_results format) ─────────────────────────────
def print_chunks(chunks: list[dict]):
    for i, c in enumerate(chunks):
        print(f"\n  [{i+1}] score={c['score']}  source='{c['source']}'")
        preview = c["text"].replace("\n", " ")
        print(f"       {preview[:400]}")


def run_comparison(question: str, language: str, llm: OpenAILLM, graph_rag: GraphRAG):
    print(f"\n{'═' * 60}")
    print(f"[{language.upper()}]")
    print(f"\nQuestion: {question}")
    print("─" * 60)

    # ── 1. Simple RAG ──────────────────────────────────────────────────────────
    print(f"\n{'─' * 60}")
    print("PIPELINE 1 — Simple RAG  (ChromaDB dense vector only)")
    print("─" * 60)

    s_chunks = simple_rag(question, language)
    print(f"\n[Retrieved Context — {len(s_chunks)} chunk(s)]")
    print_chunks(s_chunks)
    print(f"\n[Simple RAG Answer]")
    print(generate_answer(llm, question, s_chunks))

    # ── 2. Hybrid RAG ──────────────────────────────────────────────────────────
    print(f"\n{'─' * 60}")
    print("PIPELINE 2 — Hybrid RAG  (ChromaDB dense + BM25 sparse)")
    print("─" * 60)

    h_chunks = hybrid_rag(question, language)
    print(f"\n[Retrieved Context — {len(h_chunks)} chunk(s)]")
    print_chunks(h_chunks)
    print(f"\n[Hybrid RAG Answer]")
    print(generate_answer(llm, question, h_chunks))

    # ── 3. Hybrid Graph RAG ────────────────────────────────────────────────────
    print(f"\n{'─' * 60}")
    print("PIPELINE 3 — Hybrid Graph RAG  (Neo4j vector + fulltext + entity graph)")
    print("─" * 60)

    g_result = graph_rag.search(
        query_text=question,
        retriever_config={"top_k": TOP_K, "query_params": {"language": language}},
        return_context=True,
    )
    g_chunks = []
    if g_result.retriever_result and g_result.retriever_result.items:
        g_chunks = [parse_graph_item(item.content)
                    for item in g_result.retriever_result.items]

    print(f"\n[Retrieved Context — {len(g_chunks)} chunk(s)]")
    print_chunks(g_chunks)
    print(f"\n[Hybrid Graph RAG Answer]")
    print(g_result.answer)

    # ── Score summary ──────────────────────────────────────────────────────────
    def avg(chunks):
        return round(sum(c["score"] for c in chunks) / len(chunks), 4) if chunks else 0.0

    print(f"\n── Score Summary ──")
    print(f"  Simple RAG       avg: {avg(s_chunks)}")
    print(f"  Hybrid RAG       avg: {avg(h_chunks)}")
    print(f"  Hybrid Graph RAG avg: {avg(g_chunks)}")


SAMPLE_QUESTIONS = {
    "hindi": [
        ("Easy",   "संविधान की उद्देशिका में 'समाजवादी' और 'पंथनिरपेक्ष' शब्द कब जोड़े गए?"),
        ("Medium", "NCF 2005 के अनुसार बच्चों में सीखने की प्रक्रिया को प्रभावित करने वाले कारक कौन से हैं?"),
        ("Hard",   "42वें संविधान संशोधन अधिनियम 1976 ने उद्देशिका में क्या परिवर्तन किए और उनका महत्त्व क्या है?"),
    ],
    "marathi": [
        ("Easy",   "खनिजतेल कशापासून तयार होते?"),
        ("Medium", "खनिजतेलाच्या ज्वलनामुळे कोणते वायू तयार होतात आणि त्याचा पर्यावरणावर काय परिणाम होतो?"),
        ("Hard",   "नरसिंह मेहेता यांचे भक्तिमार्गातील योगदान काय होते आणि त्यांच्या जीवनातील प्रमुख घटना कोणत्या होत्या?"),
    ],
    "telugu": [
        ("Easy",   "గరుడ పురాణంలో మూడు కాండలు ఏవి?"),
        ("Medium", "ప్రేతకాండలో మరణానంతర ఆత్మ ప్రయాణం ఏ విధంగా వర్ణించబడింది?"),
        ("Hard",   "గరుడ పురాణం వైష్ణవ పురాణంగా ఎందుకు పరిగణించబడుతుంది మరియు ఇందులో విష్ణువు యొక్క అవతారాలు ఎలా వర్ణించబడ్డాయి?"),
    ],
}


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    log_handle = open(out_path, "w", encoding="utf-8")
    sys.stdout = Tee(log_handle)

    print("BharatGraph — Retrieval Comparison Results")
    print(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print("Pipelines compared:")
    print("  1. Simple RAG       — ChromaDB dense vector search")
    print("  2. Hybrid RAG       — ChromaDB dense + BM25 sparse")
    print("  3. Hybrid Graph RAG — Neo4j vector + fulltext + entity graph")
    print("=" * 60)

    print("\nInitialising LLM and Graph RAG…")
    llm = OpenAILLM(
        model_name="gpt-5.4-mini-2026-03-17",
        model_params={"temperature": 0.2},
    )
    embedder  = VyakyarthEmbedder()
    retriever = HybridCypherRetriever(
        driver=driver,
        vector_index_name="hindi_chunks",
        fulltext_index_name="hindi_chunks_fulltext",
        retrieval_query=RETRIEVAL_QUERY,
        embedder=embedder,
        neo4j_database=DATABASE,
    )
    graph_rag = GraphRAG(retriever=retriever, llm=llm)

    print("\nBuilding Chroma + BM25 indexes from Neo4j chunks…")
    for lang in ["hindi", "marathi", "telugu"]:
        get_chroma_collection(lang)
        get_bm25(lang)

    print("\n" + "=" * 60)
    print("COMPARISON RESULTS — ALL LANGUAGES")
    print("=" * 60)

    for language, questions in SAMPLE_QUESTIONS.items():
        print(f"\n{'█' * 60}")
        print(f"  LANGUAGE: {language.upper()}")
        print(f"{'█' * 60}")
        for level, question in questions:
            print(f"\n{'█' * 60}")
            print(f"  [{language.upper()} — {level}]")
            print(f"{'█' * 60}")
            run_comparison(question, language, llm, graph_rag)

    driver.close()
    sys.stdout = sys.__stdout__
    log_handle.close()
    print(f"\nResults saved to: {out_path}")
