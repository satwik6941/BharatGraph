import os
import sys
from datetime import datetime
from pathlib import Path

import neo4j
from dotenv import load_dotenv
from neo4j_graphrag.retrievers import HybridCypherRetriever
from neo4j_graphrag.llm import OllamaLLM, OpenAILLM
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.embeddings.base import Embedder
from sentence_transformers import SentenceTransformer

import warnings
warnings.filterwarnings("ignore")
load_dotenv()


# ── Tee: write to stdout AND file simultaneously ──
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


OUTPUT_FILE: Path | None = None
_log_handle = None


def start_logging(path: Path):
    global OUTPUT_FILE, _log_handle
    OUTPUT_FILE = path
    path.parent.mkdir(exist_ok=True)
    _log_handle = open(path, "w", encoding="utf-8")
    sys.stdout = Tee(_log_handle)
    print("BharatGraph — GraphRAG Query Results")
    print(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


def stop_logging():
    global _log_handle
    sys.stdout = sys.__stdout__
    if _log_handle:
        _log_handle.close()
        _log_handle = None
    if OUTPUT_FILE:
        print(f"\nResults saved to: {OUTPUT_FILE}")


# ── Wrap Vyakyarth SentenceTransformer so neo4j-graphrag can use it ──
class VyakyarthEmbedder(Embedder):
    """Adapts SentenceTransformer (Vyakyarth) to neo4j-graphrag's Embedder interface."""
    def __init__(self):
        self._model = SentenceTransformer("krutrim-ai-labs/Vyakyarth")

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode(text).tolist()


# ── Neo4j direct driver (required by neo4j-graphrag) ──
driver = neo4j.GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")),
)
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

embedder = VyakyarthEmbedder()

# ── Cypher traversal run after vector search finds the top-k Chunk nodes ──
# `node` = the matched Chunk node, `score` = cosine similarity score
# We expand from Chunk → Entity → RELATES_TO → Entity to get graph context
RETRIEVAL_QUERY = """
// Collect entities linked to this chunk — skip god nodes (degree > 50)
OPTIONAL MATCH (node)-[:HAS_ENTITY]->(e:Entity)
WHERE NOT EXISTS {
    MATCH (e)-[gn:RELATES_TO]-()
    WITH count(gn) AS degree
    WHERE degree > 50
    RETURN degree
}

// Collect relationships, also skipping god-node targets
OPTIONAL MATCH (e)-[r:RELATES_TO]->(e2:Entity)
WHERE NOT EXISTS {
    MATCH (e2)-[gn2:RELATES_TO]-()
    WITH count(gn2) AS degree
    WHERE degree > 50
    RETURN degree
}

RETURN
    score,
    node.text                                   AS chunkText,
    node.chunkId                                AS chunkId,
    node.source                                 AS source,
    collect(DISTINCT e.name)                    AS entities,
    collect(DISTINCT {
        from: e.name,
        rel:  r.type,
        to:   e2.name
    })                                          AS triples
"""

# ── HybridCypherRetriever: vector + fulltext (BM25) search combined ──
retriever = HybridCypherRetriever(
    driver=driver,
    vector_index_name="hindi_chunks",
    fulltext_index_name="hindi_chunks_fulltext",
    retrieval_query=RETRIEVAL_QUERY,
    embedder=embedder,
    neo4j_database=DATABASE,
)

# ── LLM options ──
LLM_OPTIONS = {
    "1": ("Ollama — gemma3:4b  (local, fast, less accurate)", "ollama_4b"),
    "2": ("Ollama — gemma3:12b (local, slower, more accurate)", "ollama_12b"),
    "3": ("OpenAI — gpt-5.4-mini-2026-03-17     (cloud, fastest, most accurate)", "gpt-5.4-mini-2026-03-17"),
}


def select_llm() -> object:
    print("\n── Select LLM ──")
    for key, (label, _) in LLM_OPTIONS.items():
        print(f"  [{key}] {label}")

    while True:
        choice = input("\nEnter choice (1/2/3): ").strip()
        if choice in LLM_OPTIONS:
            break
        print("  Invalid choice. Enter 1, 2, or 3.")

    label, model_id = LLM_OPTIONS[choice]
    print(f"\nUsing: {label}\n")

    if model_id == "ollama_4b":
        return OllamaLLM(
            model_name="gemma3:4b",
            model_params={"options": {"temperature": 0.2}},
        )
    elif model_id == "ollama_12b":
        return OllamaLLM(
            model_name="gemma3:12b",
            model_params={"options": {"temperature": 0.2}},
        )
    elif model_id == "gpt-5.4-mini-2026-03-17":
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise ValueError("OPENAI_API_KEY not found in .env file.")
        return OpenAILLM(
            model_name="gpt-5.4-mini-2026-03-17",
            model_params={"temperature": 0.2},
        )


def graph_rag_query(rag: GraphRAG, question: str, top_k: int = 5) -> str:
    """
    Run a GraphRAG query:
    1. Embeds the question with bge-m3
    2. VectorCypherRetriever finds top-k similar Chunk nodes via the vector index
    3. For each chunk, the RETRIEVAL_QUERY expands to entities + relationship triples
    4. All context (triples + text) is passed to the selected LLM to generate an answer
    """
    print(f"\nQuestion: {question}")
    print("─" * 60)

    result = rag.search(
        query_text=question,
        retriever_config={"top_k": top_k},
        return_context=True,
    )

    print(f"\n[GraphRAG Answer]\n{result.answer}")

    if result.retriever_result and result.retriever_result.items:
        print(f"\n[Retrieved Context — {len(result.retriever_result.items)} chunk(s)]")
        for i, item in enumerate(result.retriever_result.items):
            print(f"\n  [{i+1}] {item.content[:300].strip()}")

    return result.answer


# ── Graph statistics (uses driver directly) ──
def graph_stats():
    print("\n── Graph Statistics ──")
    with driver.session(database=DATABASE) as session:
        counts = {
            "Chunks":     "MATCH (c:Chunk) RETURN count(c) AS n",
            "Entities":   "MATCH (e:Entity) RETURN count(e) AS n",
            "Relations":  "MATCH ()-[r:RELATES_TO]->() RETURN count(r) AS n",
            "HAS_ENTITY": "MATCH ()-[r:HAS_ENTITY]->() RETURN count(r) AS n",
        }
        for label, cypher in counts.items():
            n = session.run(cypher).single()["n"]
            print(f"  {label:<12} {n}")


def top_entities(limit: int = 15):
    print(f"\n── Top {limit} Most Connected Entities ──")
    with driver.session(database=DATABASE) as session:
        rows = session.run("""
            MATCH (e:Entity)
            OPTIONAL MATCH (e)-[r:RELATES_TO]-()
            RETURN e.name AS entity, count(r) AS connections
            ORDER BY connections DESC
            LIMIT $limit
        """, limit=limit)
        for r in rows:
            print(f"  {r['entity']:<40} {r['connections']} connections")


# ── Main ──
if __name__ == "__main__":
    # LLM selection happens BEFORE logging starts (input() needs real stdout)
    llm = select_llm()
    rag = GraphRAG(retriever=retriever, llm=llm)

    output_path = Path("query_results") / f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    start_logging(output_path)

    graph_stats()
    top_entities()

    print("\n" + "=" * 60)
    print("GRAPHRAG QUERY RESULTS")
    print("=" * 60)

    questions = [
        # Easy
        ("Easy",   "कम्प्यूटर शब्द की उत्पत्ति किस अंग्रेजी शब्द से हुई है?"),
        ("Easy",   "हार्डवेयर और सॉफ्टवेयर में क्या अंतर है?"),
        ("Easy",   "भारत के संविधान को कब अंगीकृत किया गया था?"),
        # Medium
        ("Medium", "राष्ट्रीय पाठ्यचर्या की रूपरेखा 2005 के अनुसार शिक्षक की भूमिका क्या है?"),
        ("Medium", "कोठारी आयोग 1964-66 ने शिक्षा के बारे में क्या कहा था?"),
        ("Medium", "सी.पी.यू. के तीन मुख्य भाग कौन से हैं?"),
        # Hard
        ("Hard",   "भारत के संविधान की उद्देशिका में कौन-से न्याय का उल्लेख है?"),
        ("Hard",   "42वें संविधान संशोधन अधिनियम 1976 ने उद्देशिका में क्या परिवर्तन किए?"),
        ("Hard",   "D.L.Ed. पाठ्यक्रम में क्या बदलाव किए गए और उनके पीछे क्या कारण थे?"),
    ]

    for level, question in questions:
        print(f"\n{'═' * 60}")
        print(f"[{level}]")
        graph_rag_query(rag, question, top_k=10)
        print()

    driver.close()
    stop_logging()