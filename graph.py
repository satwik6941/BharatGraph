import os
from dotenv import load_dotenv
from pathlib import Path
from langchain_community.graphs import Neo4jGraph
from langchain_community.vectorstores import Neo4jVector
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
import warnings
warnings.filterwarnings("ignore")
load_dotenv()

files = Path("cleaned_outputs")
chunks_with_metadata = []
for file in files.glob("*.txt"):
    with open(file, "r", encoding="utf-8") as f:
        text = f.read()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
        texts = text_splitter.split_text(text)

        for i, chunk in enumerate(texts):
            chunks_with_metadata.append({
                "chunkId": f"{file.stem}-chunk-{i}",
                "source": file.name,
                "chunkSeqId": i,
                "text": chunk
            })

print(f"Total chunks created: {len(chunks_with_metadata)}")
print(f"Sample chunk with metadata: {chunks_with_metadata[0]}")

merge_chunk_node_query = """
MERGE(mergedChunk:Chunk {chunkId: $chunkParam.chunkId})
    ON CREATE SET 
        mergedChunk.source = $chunkParam.source,
        mergedChunk.chunkSeqId = $chunkParam.chunkSeqId,
        mergedChunk.text = $chunkParam.text
RETURN mergedChunk
"""

kg = Neo4jGraph(
    url=os.getenv("NEO4J_URI"), username=os.getenv("NEO4J_USERNAME"), password=os.getenv("NEO4J_PASSWORD"), database=os.getenv("NEO4J_DATABASE")
)

for chunk in chunks_with_metadata:
    kg.query(merge_chunk_node_query, params={'chunkParam': chunk})

print(f"Inserted {len(chunks_with_metadata)} chunks into Neo4j.")

kg.query("""
CREATE CONSTRAINT unique_chunk IF NOT EXISTS 
    FOR (c:Chunk) REQUIRE c.chunkId IS UNIQUE
""")

print(kg.query("""
         MATCH (n)
         RETURN count(n) as nodeCount
         """))

kg.query("""
         CREATE VECTOR INDEX `hindi_chunks` IF NOT EXISTS
          FOR (c:Chunk) ON (c.textEmbedding)
          OPTIONS { indexConfig: {
            `vector.dimensions`: 1024,
            `vector.similarity_function`: 'cosine'
         }}
""")

print(kg.query("SHOW INDEXES"))

embedding_model = HuggingFaceEmbeddings(
    model_name="intfloat/multilingual-e5-large",
    model_kwargs={"device": "cuda"},
)

# Generate embeddings locally and store in Neo4j
chunks_without_embeddings = kg.query("""
    MATCH (chunk:Chunk) WHERE chunk.textEmbedding IS NULL
    RETURN chunk.chunkId AS chunkId, chunk.text AS text
""")

for chunk in chunks_without_embeddings:
    # multilingual-e5 expects "query: " or "passage: " prefix
    vector = embedding_model.embed_query("passage: " + chunk["text"])
    kg.query("""
        MATCH (c:Chunk {chunkId: $chunkId})
        CALL db.create.setNodeVectorProperty(c, "textEmbedding", $vector)
    """, params={"chunkId": chunk["chunkId"], "vector": vector})

print(f"Generated embeddings for {len(chunks_without_embeddings)} chunks.")

kg.refresh_schema()
print(kg.schema)

def neo4j_vector_search(question):
  """Search for similar nodes using the Neo4j vector index"""
  question_embedding = embedding_model.embed_query("query: " + question)
  vector_search_query = """
    CALL db.index.vector.queryNodes($index_name, $top_k, $embedding) yield node, score
    RETURN score, node.text AS text
  """
  similar = kg.query(vector_search_query, 
                     params={
                        'question': question,
                        'index_name': 'hindi_chunks',
                        'embedding': question_embedding, 
                        'top_k': 10})
  return similar

search_results = neo4j_vector_search(
    'भारत के संविधान की उद्देशिका क्या है?'
)

print(f"Search results: {search_results}")
print(f"Search results: {search_results[0]}")
