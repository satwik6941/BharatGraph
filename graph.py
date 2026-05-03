import os
from dotenv import load_dotenv
from pathlib import Path
from langchain_community.graphs import Neo4jGraph
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from langdetect import detect_langs, DetectorFactory
import warnings
warnings.filterwarnings("ignore")
load_dotenv()

# Make langdetect fully deterministic
DetectorFactory.seed = 0

LANGDETECT_MAP = {"hi": "hindi", "mr": "marathi", "te": "telugu"}


def _filename_language(stem: str) -> str:
    s = stem.lower()
    if "marathi" in s:
        return "marathi"
    if "telugu" in s:
        return "telugu"
    return "hindi"


def detect_language(text: str, fallback: str = "hindi") -> str:
    """Detect language of a chunk; fall back when confidence < 0.8 or text too short."""
    if len(text.strip()) < 30:
        return fallback
    try:
        top = detect_langs(text)[0]
        if top.prob >= 0.8:
            return LANGDETECT_MAP.get(top.lang, fallback)
    except Exception:
        pass
    return fallback


# ── Vyakyarth embedding model (Hindi-specific, from Krutrim AI Labs) ──
print("Loading Vyakyarth embedding model...")
embedding_model = SentenceTransformer("krutrim-ai-labs/Vyakyarth")
EMBEDDING_DIM = embedding_model.get_sentence_embedding_dimension()
print(f"Embedding dimension: {EMBEDDING_DIM}")

# ── Chunking: 500 chars / 50 overlap, language-tagged per chunk ──
files = Path("cleaned_outputs")
chunks_with_metadata = []
for file in files.glob("*.txt"):
    file_language = _filename_language(file.stem)
    with open(file, "r", encoding="utf-8") as f:
        text = f.read()

    # Telugu uses different sentence boundaries; Devanagari uses danda ।
    if file_language == "telugu":
        separators = ["\n\n", "\n", " "]
    else:
        separators = ["।\n", "।", "\n\n", "\n", " "]

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1300,
        chunk_overlap=100,
        separators=separators,
    )
    texts = text_splitter.split_text(text)

    for i, chunk in enumerate(texts):
        # Chunk-level detection with filename as reliable fallback
        language = detect_language(chunk, fallback=file_language)
        chunks_with_metadata.append({
            "chunkId":    f"{file.stem}-chunk-{i}",
            "source":     file.name,
            "chunkSeqId": i,
            "text":       chunk,
            "language":   language,
        })

print(f"Total chunks created: {len(chunks_with_metadata)}")

# Print language distribution
from collections import Counter
lang_dist = Counter(c["language"] for c in chunks_with_metadata)
print(f"Language distribution: {dict(lang_dist)}")
print(f"Sample chunk:\n{chunks_with_metadata[0]}")

# ── Neo4j connection ──
kg = Neo4jGraph(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD"),
    database=os.getenv("NEO4J_DATABASE"),
)

# ── Wipe old graph data and indexes to start fresh ──
print("\nClearing old chunks, entities and indexes...")
kg.query("MATCH (c:Chunk) DETACH DELETE c")
kg.query("MATCH (e:Entity) DETACH DELETE e")
kg.query("DROP INDEX hindi_chunks IF EXISTS")
print("Old data cleared.")

# ── Unique constraint ──
kg.query("""
CREATE CONSTRAINT unique_chunk IF NOT EXISTS
    FOR (c:Chunk) REQUIRE c.chunkId IS UNIQUE
""")

# ── Insert chunks (now includes language property) ──
merge_chunk_node_query = """
MERGE (mergedChunk:Chunk {chunkId: $chunkParam.chunkId})
    ON CREATE SET
        mergedChunk.source     = $chunkParam.source,
        mergedChunk.chunkSeqId = $chunkParam.chunkSeqId,
        mergedChunk.text       = $chunkParam.text,
        mergedChunk.language   = $chunkParam.language
RETURN mergedChunk
"""

for chunk in chunks_with_metadata:
    kg.query(merge_chunk_node_query, params={"chunkParam": chunk})

print(f"Inserted {len(chunks_with_metadata)} chunks into Neo4j.")

# ── Create vector index ──
kg.query(f"""
    CREATE VECTOR INDEX `hindi_chunks` IF NOT EXISTS
    FOR (c:Chunk) ON (c.textEmbedding)
    OPTIONS {{ indexConfig: {{
        `vector.dimensions`: {EMBEDDING_DIM},
        `vector.similarity_function`: 'cosine'
    }} }}
""")
print(f"Vector index created with {EMBEDDING_DIM} dimensions.")

# ── Create fulltext index for hybrid (BM25) search ──
kg.query("""
    CREATE FULLTEXT INDEX hindi_chunks_fulltext IF NOT EXISTS
    FOR (c:Chunk) ON EACH [c.text]
""")
print("Fulltext index created.")
print(kg.query("SHOW INDEXES"))

# ── Generate and store Vyakyarth embeddings ──
chunks_without_embeddings = kg.query("""
    MATCH (chunk:Chunk) WHERE chunk.textEmbedding IS NULL
    RETURN chunk.chunkId AS chunkId, chunk.text AS text
""")

print(f"\nGenerating embeddings for {len(chunks_without_embeddings)} chunks...")

for i, chunk in enumerate(chunks_without_embeddings):
    vector = embedding_model.encode(chunk["text"]).tolist()
    kg.query("""
        MATCH (c:Chunk {chunkId: $chunkId})
        CALL db.create.setNodeVectorProperty(c, "textEmbedding", $vector)
    """, params={"chunkId": chunk["chunkId"], "vector": vector})

    if (i + 1) % 100 == 0:
        print(f"  Embedded {i+1}/{len(chunks_without_embeddings)} chunks...")

print(f"Done! Generated embeddings for {len(chunks_without_embeddings)} chunks.")

kg.refresh_schema()
print(kg.schema)


# ── Quick test search ──
def neo4j_vector_search(question: str, top_k: int = 5):
    question_embedding = embedding_model.encode(question).tolist()
    results = kg.query("""
        CALL db.index.vector.queryNodes($index_name, $top_k, $embedding) YIELD node, score
        RETURN score, node.language AS language, node.text AS text
    """, params={
        "index_name": "hindi_chunks",
        "embedding": question_embedding,
        "top_k": top_k,
    })
    return results


print("\nTest search: 'भारत के संविधान की उद्देशिका क्या है?'")
results = neo4j_vector_search("भारत के संविधान की उद्देशिका क्या है?")
for r in results:
    print(f"  Score: {r['score']:.4f} | lang={r['language']} | {r['text'][:100].strip()}")