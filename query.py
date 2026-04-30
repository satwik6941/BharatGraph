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


# ── Vyakyarth embedder (multilingual Indic, from Krutrim AI Labs) ──
class VyakyarthEmbedder(Embedder):
    def __init__(self):
        self._model = SentenceTransformer("krutrim-ai-labs/Vyakyarth")

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode(text).tolist()


# ── Language selection ──
SUPPORTED_LANGUAGES = {
    "1": "hindi",
    "2": "marathi",
    "3": "telugu",
}


def select_language() -> str:
    print("\n── Select Query Language ──")
    for key, lang in SUPPORTED_LANGUAGES.items():
        print(f"  [{key}] {lang.capitalize()}")
    while True:
        choice = input("\nEnter choice (1/2/3): ").strip()
        if choice in SUPPORTED_LANGUAGES:
            return SUPPORTED_LANGUAGES[choice]
        print("  Invalid choice. Enter 1, 2, or 3.")


# ── Cypher traversal — language-filtered ──
# $language is injected per query via retriever_config["query_params"]
RETRIEVAL_QUERY = """
// Only consider chunks in the requested language
WHERE node.language = $language

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
    node.language                               AS language,
    collect(DISTINCT e.name)                    AS entities,
    collect(DISTINCT {
        from: e.name,
        rel:  r.type,
        to:   e2.name
    })                                          AS triples
"""


# ── Factory: builds driver + retriever + rag, called once at startup ──
def build_rag(llm) -> tuple[GraphRAG, neo4j.Driver, str]:
    """
    Creates and returns (rag, driver, database).
    Callers that need driver for graph_stats / top_entities
    should keep the returned driver reference.
    """
    database = os.getenv("NEO4J_DATABASE", "neo4j")
    driver = neo4j.GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD")),
    )
    embedder = VyakyarthEmbedder()
    retriever = HybridCypherRetriever(
        driver=driver,
        vector_index_name="hindi_chunks",
        fulltext_index_name="hindi_chunks_fulltext",
        retrieval_query=RETRIEVAL_QUERY,
        embedder=embedder,
        neo4j_database=database,
    )
    rag = GraphRAG(retriever=retriever, llm=llm)
    return rag, driver, database


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


def graph_rag_query(rag: GraphRAG, question: str, language: str, top_k: int = 10) -> str:
    print(f"\nQuestion: {question}")
    print("─" * 60)

    result = rag.search(
        query_text=question,
        retriever_config={
            "top_k": top_k,
            "query_params": {"language": language},
        },
        return_context=True,
    )

    print(f"\n[GraphRAG Answer]\n{result.answer}")

    if result.retriever_result and result.retriever_result.items:
        print(f"\n[Retrieved Context — {len(result.retriever_result.items)} chunk(s)]")
        for i, item in enumerate(result.retriever_result.items):
            print(f"\n  [{i+1}] {item.content[:300].strip()}")

    return result.answer


# ── Graph statistics — accept driver + database explicitly ──
def graph_stats(driver: neo4j.Driver, database: str):
    print("\n── Graph Statistics ──")
    with driver.session(database=database) as session:
        counts = {
            "Chunks":     "MATCH (c:Chunk) RETURN count(c) AS n",
            "Entities":   "MATCH (e:Entity) RETURN count(e) AS n",
            "Relations":  "MATCH ()-[r:RELATES_TO]->() RETURN count(r) AS n",
            "HAS_ENTITY": "MATCH ()-[r:HAS_ENTITY]->() RETURN count(r) AS n",
        }
        for label, cypher in counts.items():
            n = session.run(cypher).single()["n"]
            print(f"  {label:<12} {n}")

    print("\n── Chunks by Language ──")
    with driver.session(database=database) as session:
        rows = session.run("""
            MATCH (c:Chunk)
            RETURN c.language AS language, count(c) AS chunks
            ORDER BY chunks DESC
        """)
        for r in rows:
            print(f"  {r['language']:<12} {r['chunks']} chunks")


def top_entities(driver: neo4j.Driver, database: str, language: str, limit: int = 15):
    print(f"\n── Top {limit} Most Connected Entities [{language}] ──")
    with driver.session(database=database) as session:
        rows = session.run("""
            MATCH (e:Entity {language: $language})
            OPTIONAL MATCH (e)-[r:RELATES_TO]-()
            RETURN e.name AS entity, count(r) AS connections
            ORDER BY connections DESC
            LIMIT $limit
        """, language=language, limit=limit)
        for r in rows:
            print(f"  {r['entity']:<40} {r['connections']} connections")


# ── Sample questions per language ──
SAMPLE_QUESTIONS = {
    "hindi": [
        ("Easy",   "संविधान की उद्देशिका में 'समाजवादी' और 'पंथनिरपेक्ष' शब्द कब जोड़े गए?"),
        ("Easy",   "मनोविज्ञान किसे कहते हैं और इसकी मुख्य विशेषताएं क्या हैं?"),
        ("Easy",   "भारत के संविधान को कब अंगीकृत किया गया था?"),
        ("Medium", "NCF 2005 के अनुसार बच्चों में सीखने की प्रक्रिया को प्रभावित करने वाले कारक कौन से हैं?"),
        ("Medium", "अधिगम (learning) क्या है और मनोविज्ञान में इसे किस प्रकार परिभाषित किया गया है?"),
        ("Medium", "पादपों में पोषण की कौन-कौन सी विधियाँ होती हैं और स्वपोषी तथा परपोषी में क्या अंतर है?"),
        ("Hard",   "D.L.Ed. पाठ्यक्रम में समावेशी शिक्षा को किस प्रकार लागू किया गया है और इसके पीछे क्या दार्शनिक आधार है?"),
        ("Hard",   "42वें संविधान संशोधन अधिनियम 1976 ने उद्देशिका में क्या परिवर्तन किए और उनका महत्त्व क्या है?"),
        ("Hard",   "मानव स्मृति की प्रक्रिया क्या है और स्मृति के विभिन्न प्रकार एवं उनकी विशेषताएं क्या हैं?"),
    ],
    "marathi": [
        ("Easy",   "खनिजतेल कशापासून तयार होते?"),
        ("Easy",   "कार्बन आणि हायड्रोजनच्या अणूंपासून तेलाचे रेणू कसे तयार होतात?"),
        ("Easy",   "नरसिंह मेहेता यांचा जन्म कोठे झाला आणि ते कोणत्या राजाच्या दरबारात होते?"),
        ("Medium", "खनिजतेलाच्या ज्वलनामुळे कोणते वायू तयार होतात आणि त्याचा पर्यावरणावर काय परिणाम होतो?"),
        ("Medium", "खनिजतेलाचे शुद्धीकरण कसे केले जाते आणि त्यापासून कोणते उपउत्पादने मिळतात?"),
        ("Medium", "नरसिंह मेहेता यांनी मीराबाई किंवा इतर संतांशी कसे नाते जोडले होते?"),
        ("Hard",   "नरसिंह मेहेता यांचे भक्तिमार्गातील योगदान काय होते आणि त्यांच्या जीवनातील प्रमुख घटना कोणत्या होत्या?"),
        ("Hard",   "खनिजतेलाच्या अतिवापरामुळे भविष्यात कोणत्या समस्या निर्माण होऊ शकतात आणि पर्यायी उर्जास्रोत कोणते आहेत?"),
        ("Hard",   "खनिजतेलाच्या शोधाचा इतिहास काय आहे आणि सुरुवातीच्या काळात त्याचा उपयोग कसा केला जात होता?"),
    ],
    "telugu": [
        ("Easy",   "గరుడ పురాణంలో మూడు కాండలు ఏవి?"),
        ("Easy",   "గరుడ పురాణంలో ఆచారకాండలో ఎన్ని అధ్యాయాలు ఉన్నాయి?"),
        ("Easy",   "గరుడ పురాణం ఏ దేవతకు సమర్పించబడింది?"),
        ("Medium", "ప్రేతకాండలో మరణానంతర ఆత్మ ప్రయాణం ఏ విధంగా వర్ణించబడింది?"),
        ("Medium", "గరుడ పురాణంలో పురాణ పంచలక్షణాలు ఏవి మరియు ఇవి ఈ పురాణంలో ఎలా కనిపిస్తాయి?"),
        ("Medium", "గరుడ పురాణంలో ఆచారకాండలో ఏయే విషయాలపై జ్ఞానం ఇవ్వబడింది?"),
        ("Hard",   "గరుడ పురాణం వైష్ణవ పురాణంగా ఎందుకు పరిగణించబడుతుంది మరియు ఇందులో విష్ణువు యొక్క అవతారాలు ఎలా వర్ణించబడ్డాయి?"),
        ("Hard",   "గరుడ పురాణంలో బ్రహ్మకాండ మోక్షప్రాప్తి గురించి ఏమి చెబుతుంది మరియు మాయ, అవిద్యల పాత్ర ఏమిటి?"),
        ("Hard",   "గరుడ పురాణంలో కర్మ సిద్ధాంతం మరియు నరక వర్ణన ఏ విధంగా జీవాత్మ మోక్షానికి సంబంధించినవి?"),
    ],
}


# ── Main ──
if __name__ == "__main__":
    llm = select_llm()
    rag, driver, database = build_rag(llm)

    output_path = Path("query_results") / f"results_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    start_logging(output_path)

    graph_stats(driver, database)

    print("\n" + "=" * 60)
    print("GRAPHRAG QUERY RESULTS — ALL LANGUAGES")
    print("=" * 60)

    for language in SUPPORTED_LANGUAGES.values():
        print(f"\n{'█' * 60}")
        print(f"  LANGUAGE: {language.upper()}")
        print(f"{'█' * 60}")

        top_entities(driver, database, language)

        for level, question in SAMPLE_QUESTIONS[language]:
            print(f"\n{'═' * 60}")
            print(f"[{language.upper()} — {level}]")
            graph_rag_query(rag, question, language=language, top_k=10)
            print()

    driver.close()
    stop_logging()
