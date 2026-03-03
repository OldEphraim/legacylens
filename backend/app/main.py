"""FastAPI app: query interface for the LegacyLens RAG pipeline."""

import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Load environment variables
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(_project_root, ".env.local"))

from app.retrieval.search import SearchEngine
from app.generation.answer import AnswerGenerator

app = FastAPI(title="LegacyLens", description="RAG-powered GnuCOBOL codebase query API")

# CORS — allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy-initialized singletons
_search_engine: SearchEngine | None = None
_answer_generator: AnswerGenerator | None = None


def get_search_engine() -> SearchEngine:
    global _search_engine
    if _search_engine is None:
        _search_engine = SearchEngine()
    return _search_engine


def get_answer_generator() -> AnswerGenerator:
    global _answer_generator
    if _answer_generator is None:
        _answer_generator = AnswerGenerator()
    return _answer_generator


# ── Request/Response models ─────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    stream: bool = False


class SourceChunk(BaseModel):
    content: str
    file_path: str
    line_start: int
    line_end: int
    chunk_type: str
    language: str
    function_name: str | None = None
    parent_section: str | None = None
    parent_division: str | None = None
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    latency_ms: int


class HealthResponse(BaseModel):
    status: str
    vectors_count: int


# ── Endpoints ────────────────────────────────────────────────────────

@app.post("/api/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    """Run the full RAG pipeline: retrieve relevant chunks, generate answer."""
    t0 = time.time()

    search = get_search_engine()
    generator = get_answer_generator()

    # Retrieve
    results = search.search(req.query, top_k=req.top_k)

    # Stream response if requested
    if req.stream:
        async def event_stream():
            import json
            # Send sources first
            sources = [r.to_dict() for r in results]
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
            # Stream answer tokens
            async for token in generator.generate_stream(req.query, results):
                yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
            latency = int((time.time() - t0) * 1000)
            yield f"data: {json.dumps({'type': 'done', 'latency_ms': latency})}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    # Generate answer (non-streaming)
    answer = generator.generate(req.query, results)

    latency_ms = int((time.time() - t0) * 1000)

    return QueryResponse(
        answer=answer,
        sources=[SourceChunk(**r.to_dict()) for r in results],
        latency_ms=latency_ms,
    )


@app.get("/api/health", response_model=HealthResponse)
async def health():
    """Health check — verifies Pinecone connectivity and returns vector count."""
    search = get_search_engine()
    stats = search.get_index_stats()
    return HealthResponse(
        status="ok",
        vectors_count=stats["total_vector_count"],
    )
