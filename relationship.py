import os
import json
import re
import ollama
from dotenv import load_dotenv
from langchain_community.graphs import Neo4jGraph
import warnings
warnings.filterwarnings("ignore")
load_dotenv()

# ── Connect to Neo4j ──
kg = Neo4jGraph(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USERNAME"),
    password=os.getenv("NEO4J_PASSWORD"),
    database=os.getenv("NEO4J_DATABASE"),
)

MODEL_NAME = "gemma3:12b"

# ── Language-aware extraction prompts ──
EXTRACTION_PROMPTS = {
    "hindi": """You are a knowledge graph extraction assistant. Extract all important entities and relationships from the following Hindi text.

Rules:
1. Output ONLY a valid JSON array, nothing else
2. Each object must have exactly 3 keys: "entity1", "relationship", "entity2"
3. Entity names should be in Hindi (as they appear in the text)
4. Relationship should be a short Hindi label (e.g., "की राजधानी", "ने स्थापित किया", "का भाग")
5. Extract at least 3-5 relationships if possible

Text:
{text}

JSON Output:""",

    "marathi": """You are a knowledge graph extraction assistant. Extract all important entities and relationships from the following Marathi text.

Rules:
1. Output ONLY a valid JSON array, nothing else
2. Each object must have exactly 3 keys: "entity1", "relationship", "entity2"
3. Entity names should be in Marathi (as they appear in the text)
4. Relationship should be a short Marathi label (e.g., "ची राजधानी", "ने स्थापित केले", "चा भाग")
5. Extract at least 3-5 relationships if possible

Text:
{text}

JSON Output:""",

    "telugu": """You are a knowledge graph extraction assistant. Extract all important entities and relationships from the following Telugu text.

Rules:
1. Output ONLY a valid JSON array, nothing else
2. Each object must have exactly 3 keys: "entity1", "relationship", "entity2"
3. Entity names should be in Telugu (as they appear in the text)
4. Relationship should be a short Telugu label (e.g., "యొక్క రాజధాని", "స్థాపించారు", "భాగం")
5. Extract at least 3-5 relationships if possible

Text:
{text}

JSON Output:""",
}


def extract_relationships(text: str, language: str = "hindi") -> list[dict]:
    """Use gemma3:12b via Ollama to extract entity-relationship triples."""
    prompt_template = EXTRACTION_PROMPTS.get(language, EXTRACTION_PROMPTS["hindi"])
    prompt = prompt_template.format(text=text[:1500])

    response = ollama.generate(
        model=MODEL_NAME,
        prompt=prompt,
        format="json",
        options={
            "temperature": 0.3,
            "top_p": 0.9,
            "num_predict": 512,
        },
    )

    generated = response.response
    print(f"  [DEBUG] Model output: {generated[:300]}")

    try:
        parsed = json.loads(generated)
        if isinstance(parsed, dict):
            for key in parsed:
                if isinstance(parsed[key], list):
                    parsed = parsed[key]
                    break
        if isinstance(parsed, list):
            return [t for t in parsed if all(k in t for k in ("entity1", "relationship", "entity2"))]
    except json.JSONDecodeError:
        pass

    json_match = re.search(r'\[.*\]', generated, re.DOTALL)
    if json_match:
        try:
            triples = json.loads(json_match.group())
            return [t for t in triples if all(k in t for k in ("entity1", "relationship", "entity2"))]
        except json.JSONDecodeError:
            print(f"  [DEBUG] JSON parse failed: {json_match.group()[:200]}")
    return []


# ── Cypher: language is inherited from the chunk and stored on entities + relationship ──
merge_relationship_query = """
MATCH (c:Chunk {chunkId: $chunkId})
MERGE (e1:Entity {name: $entity1})
    ON CREATE SET e1.language = $language
MERGE (e2:Entity {name: $entity2})
    ON CREATE SET e2.language = $language
MERGE (e1)-[r:RELATES_TO {type: $relationship, source: $chunkId}]->(e2)
    ON CREATE SET r.language = $language
MERGE (c)-[:HAS_ENTITY]->(e1)
MERGE (c)-[:HAS_ENTITY]->(e2)
RETURN e1, r, e2
"""

# ── Fetch all chunks with their language ──
chunks = kg.query("""
    MATCH (c:Chunk)
    RETURN c.chunkId AS chunkId, c.text AS text, c.language AS language
    ORDER BY c.language, c.chunkSeqId
""")

print(f"Processing {len(chunks)} chunks for relationship extraction...\n")

total_relationships = 0

for i, chunk in enumerate(chunks):
    language = chunk.get("language") or "hindi"
    print(f"[{i+1}/{len(chunks)}] Processing chunk: {chunk['chunkId']}  [lang={language}]")

    triples = extract_relationships(chunk["text"], language=language)

    if not triples:
        print(f"  No relationships found.")
        continue

    for triple in triples:
        if not triple.get("entity1") or not triple.get("entity2") or not triple.get("relationship"):
            continue
        entity1 = triple["entity1"].strip()
        entity2 = triple["entity2"].strip()
        relationship = triple["relationship"].strip()

        if not entity1 or not entity2 or not relationship:
            continue

        kg.query(merge_relationship_query, params={
            "chunkId":      chunk["chunkId"],
            "entity1":      entity1,
            "entity2":      entity2,
            "relationship": relationship,
            "language":     language,
        })
        total_relationships += 1
        print(f"  ({entity1}) -[{relationship}]-> ({entity2})")

    print(f"  Extracted {len(triples)} relationships from this chunk.\n")

print(f"\nDone! Total relationships created: {total_relationships}")

# ── Verify the graph ──
print("\n── Graph Statistics ──")
print("Entities:", kg.query("MATCH (e:Entity) RETURN count(e) AS count"))
print("Relationships:", kg.query("MATCH ()-[r:RELATES_TO]->() RETURN count(r) AS count"))
print("Chunk-Entity links:", kg.query("MATCH ()-[r:HAS_ENTITY]->() RETURN count(r) AS count"))

# ── Language breakdown ──
print("\n── Language breakdown ──")
lang_stats = kg.query("""
    MATCH (c:Chunk)
    RETURN c.language AS language, count(c) AS chunks
    ORDER BY chunks DESC
""")
for row in lang_stats:
    print(f"  {row['language']}: {row['chunks']} chunks")
