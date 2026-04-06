import os
import json
import re
import requests
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

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma3:12b"

# ── Prompt template for entity-relationship extraction ──
EXTRACTION_PROMPT = """You are a knowledge graph extraction assistant. Extract all important entities and relationships from the following Hindi text.

Rules:
1. Output ONLY a valid JSON array, nothing else
2. Each object must have exactly 3 keys: "entity1", "relationship", "entity2"
3. Entity names should be in Hindi (as they appear in the text)
4. Relationship should be a short Hindi label (e.g., "की राजधानी", "ने स्थापित किया", "का भाग")
5. Extract at least 3-5 relationships if possible

Text:
{text}

JSON Output:"""


def extract_relationships(text: str) -> list[dict]:
    """Use gemma3:12b via Ollama to extract entity-relationship triples."""
    prompt = EXTRACTION_PROMPT.format(text=text[:1500])

    response = requests.post(OLLAMA_URL, json={
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "top_p": 0.9,
            "num_predict": 512,
        },
        "format": "json",
    })

    generated = response.json().get("response", "")

    # DEBUG: Print what the model outputs
    print(f"  [DEBUG] Model output: {generated[:300]}")

    # Try parsing the full response as JSON first
    try:
        parsed = json.loads(generated)
        # Handle if model wraps array in an object
        if isinstance(parsed, dict):
            for key in parsed:
                if isinstance(parsed[key], list):
                    parsed = parsed[key]
                    break
        if isinstance(parsed, list):
            return [t for t in parsed if all(k in t for k in ("entity1", "relationship", "entity2"))]
    except json.JSONDecodeError:
        pass

    # Fallback: extract JSON array from text
    json_match = re.search(r'\[.*\]', generated, re.DOTALL)
    if json_match:
        try:
            triples = json.loads(json_match.group())
            return [t for t in triples if all(k in t for k in ("entity1", "relationship", "entity2"))]
        except json.JSONDecodeError:
            print(f"  [DEBUG] JSON parse failed: {json_match.group()[:200]}")
    return []


# ── Cypher queries for creating entities and relationships ──
merge_relationship_query = """
MATCH (c:Chunk {chunkId: $chunkId})
MERGE (e1:Entity {name: $entity1})
MERGE (e2:Entity {name: $entity2})
MERGE (e1)-[r:RELATES_TO {type: $relationship, source: $chunkId}]->(e2)
MERGE (c)-[:HAS_ENTITY]->(e1)
MERGE (c)-[:HAS_ENTITY]->(e2)
RETURN e1, r, e2
"""

# ── Fetch first 50 chunks ──
chunks = kg.query("""
    MATCH (c:Chunk)
    RETURN c.chunkId AS chunkId, c.text AS text
    ORDER BY c.chunkSeqId
    LIMIT 50
""")

print(f"Processing {len(chunks)} chunks for relationship extraction...\n")

total_relationships = 0

for i, chunk in enumerate(chunks):
    print(f"[{i+1}/{len(chunks)}] Processing chunk: {chunk['chunkId']}")

    triples = extract_relationships(chunk["text"])

    if not triples:
        print(f"  No relationships found.")
        continue

    for triple in triples:
        entity1 = triple["entity1"].strip()
        entity2 = triple["entity2"].strip()
        relationship = triple["relationship"].strip()

        if not entity1 or not entity2 or not relationship:
            continue

        kg.query(merge_relationship_query, params={
            "chunkId": chunk["chunkId"],
            "entity1": entity1,
            "entity2": entity2,
            "relationship": relationship,
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

# ── Sample query ──
print("\n── Sample: Entities related to 'भारत' ──")
results = kg.query("""
    MATCH (e1:Entity)-[r:RELATES_TO]->(e2:Entity)
    WHERE e1.name CONTAINS 'भारत' OR e2.name CONTAINS 'भारत'
    RETURN e1.name AS entity1, r.type AS relationship, e2.name AS entity2
    LIMIT 10
""")
for r in results:
    print(f"  ({r['entity1']}) -[{r['relationship']}]-> ({r['entity2']})")