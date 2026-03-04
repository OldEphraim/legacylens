"""FastAPI app: query interface for the LegacyLens RAG pipeline."""

import json
import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Load environment variables
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(_project_root, ".env.local"))

from app.retrieval.search import SearchEngine
from app.generation.answer import AnswerGenerator
from app.generation.dependencies import parse_references

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


class ChunkRequest(BaseModel):
    file_path: str
    function_name: str | None = None


# ── System prompts for code understanding features ───────────────────

EXPLAIN_PROMPT = (
    "You are an expert code analyst. Explain what this code does in plain English, "
    "as if explaining to a developer unfamiliar with COBOL and C. Cover: what it does, "
    "how it works step by step, and why it matters in the context of the GnuCOBOL compiler."
)

DOCUMENT_PROMPT = (
    "Generate professional technical documentation for this code. Include: "
    "Purpose, Parameters/Inputs, Return Values/Outputs, Side Effects, "
    "Algorithm/Logic Description, Usage Context, and Example Usage if applicable. "
    "Format as clean markdown."
)

BUSINESS_LOGIC_PROMPT = (
    "Analyze this code and extract the business rules and logic it implements. "
    "For each rule, explain: what business process it represents, what conditions "
    "or validations it enforces, what calculations it performs, and what the "
    "real-world implications are. Focus on the 'why' not just the 'what'."
)


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


# ── Code Understanding Endpoints ─────────────────────────────────────

def _retrieve_chunk(req: ChunkRequest):
    """Retrieve the best matching chunk for a file_path + function_name."""
    search = get_search_engine()
    results = search.search_by_function(req.file_path, req.function_name, top_k=1)
    if not results:
        raise HTTPException(status_code=404, detail="No matching chunk found")
    return results[0]


def _stream_feature(system_prompt: str, chunk):
    """Create an SSE stream for a code understanding feature."""
    generator = get_answer_generator()
    code_context = (
        f"[{chunk.file_path}:{chunk.line_start}-{chunk.line_end}] "
        f"({chunk.chunk_type}"
        f"{': ' + chunk.function_name if chunk.function_name else ''})\n\n"
        f"{chunk.content}"
    )

    async def event_stream():
        t0 = time.time()
        # Send the chunk info first
        yield f"data: {json.dumps({'type': 'chunk', 'chunk': chunk.to_dict()})}\n\n"
        async for token in generator.generate_with_prompt_stream(
            system_prompt, code_context
        ):
            yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
        latency = int((time.time() - t0) * 1000)
        yield f"data: {json.dumps({'type': 'done', 'latency_ms': latency})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/explain")
async def explain(req: ChunkRequest):
    """Explain a code chunk in plain English."""
    chunk = _retrieve_chunk(req)
    return _stream_feature(EXPLAIN_PROMPT, chunk)


@app.post("/api/document")
async def document(req: ChunkRequest):
    """Generate technical documentation for a code chunk."""
    chunk = _retrieve_chunk(req)
    return _stream_feature(DOCUMENT_PROMPT, chunk)


@app.post("/api/business-logic")
async def business_logic(req: ChunkRequest):
    """Extract business rules from a code chunk."""
    chunk = _retrieve_chunk(req)
    return _stream_feature(BUSINESS_LOGIC_PROMPT, chunk)


@app.post("/api/dependencies")
async def dependencies(req: ChunkRequest):
    """Map dependencies for a code chunk."""
    chunk = _retrieve_chunk(req)
    search = get_search_engine()

    # Parse references from the chunk
    refs = parse_references(chunk.content, chunk.language)

    # For each reference, find where it's defined
    calls = []
    for ref_name in refs[:15]:  # limit to avoid too many API calls
        matches = search.search_by_function(
            file_path="",  # search all files
            function_name=ref_name,
            top_k=1,
        )
        if matches:
            m = matches[0]
            calls.append({
                "name": ref_name,
                "file_path": m.file_path,
                "line_start": m.line_start,
                "line_end": m.line_end,
                "chunk_type": m.chunk_type,
            })
        else:
            calls.append({"name": ref_name, "file_path": None, "line_start": None,
                          "line_end": None, "chunk_type": None})

    # Find reverse dependencies — who calls this function
    called_by = []
    target_name = chunk.function_name or req.function_name
    if target_name:
        reverse = search.search_references(target_name, top_k=10)
        for r in reverse:
            # Skip self
            if r.file_path == chunk.file_path and r.line_start == chunk.line_start:
                continue
            called_by.append({
                "name": r.function_name or f"{r.file_path}:{r.line_start}",
                "file_path": r.file_path,
                "line_start": r.line_start,
                "line_end": r.line_end,
                "chunk_type": r.chunk_type,
            })

    return {
        "target": {
            "name": chunk.function_name or req.function_name,
            "file_path": chunk.file_path,
            "line_start": chunk.line_start,
            "line_end": chunk.line_end,
        },
        "calls": calls,
        "called_by": called_by,
    }
