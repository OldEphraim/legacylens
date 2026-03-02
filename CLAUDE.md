# LegacyLens

RAG-powered system for querying and understanding the GnuCOBOL legacy codebase.

## Project Structure

```
legacylens/
├── backend/          # Python/FastAPI - RAG pipeline, API endpoints
│   ├── app/
│   │   ├── main.py           # FastAPI app entry point
│   │   ├── ingestion/        # File discovery, chunking, embedding
│   │   │   ├── discover.py   # Recursive file scanner
│   │   │   ├── chunker.py    # COBOL-aware syntax splitting
│   │   │   └── embedder.py   # Voyage Code 2 embedding generation
│   │   ├── retrieval/        # Query processing, search, re-ranking
│   │   │   ├── search.py     # Pinecone similarity search
│   │   │   └── reranker.py   # LLM-based re-ranking (post-MVP)
│   │   ├── generation/       # LLM answer generation
│   │   │   └── answer.py     # Claude for answer generation
│   │   └── models/           # Pydantic models for API
│   ├── requirements.txt
│   └── venv/                 # (gitignored)
├── frontend/         # Next.js/TypeScript - query interface
├── data/
│   └── gnucobol/     # (gitignored) cloned GnuCOBOL source
├── gauntlet-docs/    # Assignment spec + pre-search in markdown
│   ├── assignment.md
│   └── presearch.md
├── docs/             # Generated project documentation
├── .env.local        # (gitignored) API keys
├── .gitignore
├── .claudeignore
├── CLAUDE.md         # This file
└── README.md
```

## Tech Stack

- **Vector DB:** Pinecone (managed, free tier)
- **Embeddings:** Voyage Code 2 (1536 dimensions, code-optimized)
- **LLM:** Claude Sonnet 4.5 (via Anthropic API)
- **RAG Framework:** LangChain
- **Backend:** Python 3.11+ / FastAPI
- **Frontend:** Next.js 14+ / TypeScript / Tailwind
- **Deploy:** Railway (backend) + Vercel (frontend)

## Key Architecture Decisions

### Chunking Strategy

COBOL files use syntax-aware chunking based on COBOL's hierarchical structure:
- PARAGRAPH-level chunks (primary) — these are COBOL's equivalent of functions
- SECTION-level chunks for DATA DIVISION definitions
- Fixed-size with 200-token overlap as fallback
- C files (.c, .h) in GnuCOBOL use standard function-level chunking
- Config files (.conf) chunked per dialect definition
- Test files (.at) chunked per test case

COBOL paragraph headers match pattern: column 8+, uppercase alphanumeric with hyphens, ending with period.
Example: `       PROCESS-TRANSACTION.`

### File types to ingest

- `.cob`, `.cbl` — COBOL source files
- `.cpy` — COBOL copybooks (like header files)
- `.c`, `.h` — C source for the compiler and runtime
- `.conf` — dialect configuration files
- `.at` — Autotest files containing embedded COBOL test cases
- `.def` — definition files

### Metadata per chunk

- file_path, line_start, line_end
- chunk_type (paragraph | section | division | data_definition | comment_block | function | test_case | config)
- parent_section, parent_division (for COBOL files)
- function_name (paragraph name or C function name if applicable)
- language (cobol | c | config | test)

### Retrieval

- Top-k=5 for similarity search (target: >70% precision in top-5)
- Query embedding via same Voyage Code 2 model (critical: must match ingestion model)
- Context assembly: retrieved chunks + 2-3 surrounding lines from original file
- Target <3 seconds end-to-end latency

### Answer Generation

Claude Sonnet 4.5 receives retrieved chunks with metadata and generates answers citing specific file paths and line numbers. If chunks don't contain enough info, it says so rather than hallucinating.

## Commands

### Backend
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm run dev
```

### Ingestion (run once, or when changing chunking strategy)
```bash
cd backend
source venv/bin/activate
python -m app.ingestion.run
```

## Environment Variables Required

- VOYAGE_API_KEY
- PINECONE_API_KEY
- PINECONE_INDEX_NAME=legacylens
- ANTHROPIC_API_KEY

## MVP Requirements (all must pass — due Tuesday midnight CT)

- [ ] Ingest GnuCOBOL codebase (117 files, 128K LOC)
- [ ] Syntax-aware chunking (COBOL paragraphs, C functions, config/test files)
- [ ] Embeddings via Voyage Code 2
- [ ] Store in Pinecone with metadata
- [ ] Semantic search across codebase
- [ ] Natural language query interface (web)
- [ ] Return code snippets with file/line references
- [ ] LLM answer generation with retrieved context
- [ ] Deployed and publicly accessible

## MVP Build Order

### Step 1: Ingestion Pipeline
Build `backend/app/ingestion/` — this is the foundation everything depends on.
1. `discover.py` — recursively find all target files (.cob, .cbl, .cpy, .c, .h, .conf, .at, .def)
2. `chunker.py` — COBOL-aware splitter: detect PARAGRAPH boundaries for .cob/.cbl, function boundaries for .c/.h, fixed-size fallback for others. Attach metadata (file_path, line_start, line_end, chunk_type, function_name, language).
3. `embedder.py` — batch embed all chunks using Voyage Code 2 via `langchain_voyageai`. Batch size 100.
4. `store.py` — upsert embedded chunks into Pinecone with metadata.
5. `run.py` — orchestrator script: discover → chunk → embed → store. Should complete in <5 minutes for the full codebase.

### Step 2: Retrieval + Answer Generation
Build `backend/app/retrieval/` and `backend/app/generation/`.
1. `search.py` — accept query string, embed with Voyage Code 2, query Pinecone top-k=5, return chunks with metadata and similarity scores.
2. `answer.py` — take retrieved chunks, assemble context with file/line metadata, send to Claude Sonnet 4.5 with the COBOL expert prompt template, return generated answer.

### Step 3: API Endpoints
Build `backend/app/main.py` with FastAPI.
1. `POST /api/query` — accept natural language query, run retrieval + generation pipeline, return answer with source chunks.
2. `GET /api/health` — health check endpoint.
3. CORS middleware for frontend access.

### Step 4: Frontend
Build minimal Next.js query interface.
1. Text input for natural language queries.
2. Submit button, loading state.
3. Display: generated answer, retrieved code snippets with syntax highlighting, file paths and line numbers, similarity scores.
4. Keep it simple — function over form for MVP.

### Step 5: Deploy
1. Backend to Railway — FastAPI with environment variables.
2. Frontend to Vercel — update NEXT_PUBLIC_API_URL to Railway URL.
3. Run ingestion script against deployed backend (or pre-ingest and verify Pinecone has data).
4. End-to-end test with the 6 test scenarios from the assignment.

## Code Understanding Features (implement 4+ for final, post-MVP)

1. Code Explanation — explain what a paragraph/function does
2. Documentation Gen — generate docs for undocumented code
3. Dependency Mapping — parse PERFORM/COPY to show call graph
4. Business Logic Extract — identify business rules in code
5. (Stretch) Translation Hints — suggest modern language equivalents

## Test Scenarios (use these to verify retrieval quality)

1. "Where is the main entry point of this program?"
2. "What functions modify the CUSTOMER-RECORD?"
3. "Explain what the CALCULATE-INTEREST paragraph does"
4. "Find all file I/O operations"
5. "What are the dependencies of MODULE-X?"
6. "Show me error handling patterns in this codebase"