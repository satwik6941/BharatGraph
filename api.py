import re
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from neo4j_graphrag.llm import OpenAILLM
from langdetect import detect, LangDetectException

from query import build_rag

LANG_CODE_MAP = {
    "hi": "hindi",
    "mr": "marathi",
    "te": "telugu",
}


def detect_language(text: str) -> str:
    try:
        code = detect(text)
        return LANG_CODE_MAP.get(code, "hindi")
    except LangDetectException:
        return "hindi"


def parse_chunk(raw: str) -> dict:
    score_match = re.search(r"score=([\d.]+)", raw)
    text_match  = re.search(r"chunkText='(.*?)'(?=\s+\w+=|>)", raw, re.DOTALL)
    source_match = re.search(r"source='(.*?)'", raw)

    score  = float(score_match.group(1))  if score_match  else 0.0
    text   = text_match.group(1).replace("\\n", " ").strip()  if text_match   else raw[:300]
    source = source_match.group(1)        if source_match else "unknown"

    return {"score": round(score, 4), "text": text, "source": source}


# ── Shared state ──
_rag    = None
_driver = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _rag, _driver
    llm = OpenAILLM(
        model_name="gpt-5.4-mini-2026-03-17",
    )
    _rag, _driver, _ = build_rag(llm)
    print("BharatGraph API ready.")
    yield
    _driver.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:8080",
        "https://bharat-graph-nlp.vercel.app",
    ],
    allow_methods=["POST"],
    allow_headers=["*"],
)


# ── Shared secret middleware ──
_API_SECRET = os.environ.get("API_SECRET_KEY", "")

@app.middleware("http")
async def verify_secret(request: Request, call_next):
    # Allow health check without auth
    if request.url.path == "/health":
        return await call_next(request)
    if _API_SECRET:
        client_secret = request.headers.get("X-Secret-Key")
        if client_secret != _API_SECRET:
            raise HTTPException(status_code=403, detail="Unauthorized")
    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok"}


class QueryRequest(BaseModel):
    question: str


class Chunk(BaseModel):
    score: float
    text: str
    source: str


class QueryResponse(BaseModel):
    answer: str
    language: str
    chunks: list[Chunk]


@app.post("/api/query", response_model=QueryResponse)
def query(req: QueryRequest):
    language = detect_language(req.question)

    result = _rag.search(
        query_text=req.question,
        retriever_config={
            "top_k": 10,
            "query_params": {"language": language},
        },
        return_context=True,
    )

    chunks = []
    if result.retriever_result and result.retriever_result.items:
        chunks = [parse_chunk(item.content) for item in result.retriever_result.items]

    return QueryResponse(answer=result.answer, language=language, chunks=chunks)