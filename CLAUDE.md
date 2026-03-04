# LegacyLens

RAG-powered system for querying and understanding the GnuCOBOL legacy codebase.

## Current Status

**MVP: COMPLETE ✅ (submitted Tuesday)**

All 9 MVP requirements pass:
- ✅ Ingested GnuCOBOL codebase (117 files, 128K LOC)
- ✅ Syntax-aware chunking (COBOL paragraphs, C functions, config/test files) → 13,613 chunks
- ✅ Embeddings via Voyage Code 2 (1536 dimensions)
- ✅ Stored in Pinecone (13,613 vectors with full metadata)
- ✅ Semantic search across codebase (~250ms retrieval)
- ✅ Natural language query interface (Next.js web UI with streaming)
- ✅ Code snippets with file/line references in results
- ✅ LLM answer generation via Claude Sonnet 4.5
- ✅ Deployed: frontend on Vercel, backend on Railway

**FINAL SUBMISSION: IN PROGRESS (due Wednesday midnight CT)**

## What Still Needs To Be Built

### 1. Code Understanding Features (implement 4 — the big task)

Add 4 new API endpoints + frontend UI for each. These are mostly different prompt templates on top of the existing retrieval pipeline.

**a) Code Explanation** (`POST /api/explain`)
- Accept a file_path + function_name (or chunk ID)
- Retrieve that specific chunk from Pinecone
- Send to Claude with prompt: "Explain what this code does in plain English, as if explaining to a developer unfamiliar with COBOL/C"
- Return explanation
- Frontend: "Explain" button on each source card in search results

**b) Documentation Gen** (`POST /api/document`)
- Accept a file_path + function_name
- Retrieve the chunk
- Send to Claude with prompt: "Generate technical documentation for this code including: purpose, inputs, outputs, side effects, and usage examples"
- Return generated docs
- Frontend: "Generate Docs" button on each source card

**c) Dependency Mapping** (`POST /api/dependencies`)
- Accept a file_path + function_name
- For COBOL: parse PERFORM statements and COPY directives from the chunk text to find references
- For C: parse function calls from the chunk text
- Search Pinecone for each referenced function/paragraph to find where they're defined
- Return a dependency tree/list: what this code calls, and what calls this code
- Frontend: expandable dependency tree or list view

**d) Business Logic Extract** (`POST /api/business-logic`)
- Accept a file_path + function_name (or a search query)
- Retrieve relevant chunks
- Send to Claude with prompt: "Identify and explain the business rules embedded in this code. What real-world business process does it implement? What conditions, calculations, or validations does it enforce?"
- Return extracted business rules
- Frontend: "Extract Business Logic" button on source cards

### 2. RAG Architecture Doc (1-2 pages)

Generate a PDF/markdown document covering:
- Vector DB Selection (why Pinecone, tradeoffs)
- Embedding Strategy (Voyage Code 2, why code-specific)
- Chunking Approach (COBOL paragraph boundaries, C function boundaries, fallbacks)
- Retrieval Pipeline (query flow, top-k=5, context assembly)
- Failure Modes (what doesn't work well, edge cases)
- Performance Results (actual latency numbers, retrieval precision)

Most content exists in presearch.md — just needs to be condensed and updated with actual measured results.

### 3. AI Cost Analysis

**Development costs (actual):**
- Voyage Code 2 embedding: ~$0.05 (500K tokens for full codebase)
- Claude Sonnet 4.5 answer generation: ~$10-15 (est. 300-500 queries during dev/testing)
- Pinecone: $0 (free tier)
- Total dev spend: ~$10-15

**Production projections (estimate per month):**
Assumptions: 5 queries/user/day, ~2K tokens per query (input+output), Pinecone free tier

| Scale | Embedding | LLM (Claude) | Pinecone | Total |
|-------|-----------|--------------|----------|-------|
| 100 users | ~$0 | ~$45/mo | $0 | ~$45/mo |
| 1,000 users | ~$0 | ~$450/mo | $70/mo | ~$520/mo |
| 10,000 users | ~$1/mo | ~$4,500/mo | $200/mo | ~$4,700/mo |
| 100,000 users | ~$5/mo | ~$45,000/mo | $1,000/mo | ~$46,000/mo |

### 4. README.md

Needs: project description, architecture diagram (text-based is fine), setup guide, deployed link, screenshots.

### 5. Demo Video (3-5 min)

Re-record after code understanding features are implemented. Show:
- Basic queries (entry point, file I/O, error handling)
- Code Explanation feature
- Documentation Gen feature
- Dependency Mapping
- Business Logic Extract
- Brief architecture mention

### 6. Social Post

Write and post on LinkedIn or X. Include: description, features, demo/screenshots, tag @GauntletAI.

## Project Structure

```
legacylens/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI endpoints (query, health, + new feature endpoints)
│   │   ├── ingestion/           # ✅ Complete
│   │   │   ├── discover.py      # File scanner (117 files)
│   │   │   ├── chunker.py       # COBOL/C/config syntax-aware splitting
│   │   │   ├── embedder.py      # Voyage Code 2 batch embedding
│   │   │   ├── store.py         # Pinecone upsert with metadata
│   │   │   └── run.py           # Orchestrator
│   │   ├── retrieval/           # ✅ Complete
│   │   │   └── search.py        # Pinecone similarity search
│   │   ├── generation/          # ✅ Complete (needs new prompt templates)
│   │   │   └── answer.py        # Claude Sonnet 4.5 answer generation
│   │   └── models/
│   ├── requirements.txt
│   └── venv/
├── frontend/                    # ✅ Complete (needs feature buttons added)
├── data/
│   └── gnucobol/                # (gitignored) 117 files, 128K LOC
├── gauntlet-docs/
│   ├── assignment.md
│   └── presearch.md
├── docs/                        # TODO: RAG architecture doc, cost analysis
├── .env.local                   # (gitignored)
├── .gitignore
├── .claudeignore
├── CLAUDE.md
└── README.md                    # TODO: write proper README
```

## Tech Stack

- **Vector DB:** Pinecone (managed, free tier) — 13,613 vectors stored
- **Embeddings:** Voyage Code 2 (1536 dimensions, code-optimized)
- **LLM:** Claude Sonnet 4.5 (via Anthropic API)
- **Backend:** Python 3.11+ / FastAPI
- **Frontend:** Next.js 14+ / TypeScript / Tailwind
- **Deploy:** Railway (backend) + Vercel (frontend)

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

### Ingestion (already done — only re-run if changing chunking strategy)
```bash
cd backend
source venv/bin/activate
python -m app.ingestion.run --data-dir ../data/gnucobol --clear
```

## Environment Variables Required

- VOYAGE_API_KEY
- PINECONE_API_KEY
- PINECONE_INDEX_NAME=legacylens
- ANTHROPIC_API_KEY

## Measured Performance

| Metric | Result | Target |
|--------|--------|--------|
| Retrieval latency | ~250ms | <3s ✅ |
| Total query latency | 10-20s | (LLM generation time) |
| Chunks indexed | 13,613 | — |
| Codebase coverage | 117/117 files | 100% ✅ |
| Ingestion time | ~18 min | <5 min (exceeded due to rate limits) |
| Top result accuracy | Correct file citations | ✅ |