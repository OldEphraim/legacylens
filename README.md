# LegacyLens

RAG-powered exploration of legacy enterprise codebases.

LegacyLens indexes the GnuCOBOL compiler codebase (128K lines of code across 117 files) and lets developers query it in natural language. It returns AI-generated answers with specific file paths, line numbers, and relevance-scored source citations.

**Live demo:** [legacylens-app.vercel.app](https://legacylens-app.vercel.app)

## Features

- Natural language search across 13,613 indexed code chunks
- Streaming AI answers with source citations (file paths, line numbers, relevance scores)
- Code Explanation — plain-English walkthrough of any function or paragraph
- Documentation Generation — auto-generated technical docs for undocumented code
- Dependency Mapping — parses PERFORM/COPY/CALL statements and C function calls to show what a function calls and what calls it
- Business Logic Extraction — identifies business rules, validations, and calculations embedded in code
- Syntax-aware chunking: COBOL paragraphs, C function boundaries, config/test file splitting

## Architecture

```
User Query
    |
    v
Voyage Code 2 Embedding (1536d)
    |
    v
Pinecone Vector Search (cosine, top-k=5)
    |
    v
Context Assembly (chunks + file/line metadata)
    |
    v
Claude Sonnet 4.5 (streaming answer generation)
    |
    v
Streamed Response (SSE) --> Next.js Frontend
```

**Stack:** Python 3.11 / FastAPI, Next.js 16 / TypeScript, Pinecone (serverless), Voyage Code 2 embeddings, Claude Sonnet 4.5, Railway (backend) + Vercel (frontend).

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- API keys: [Voyage AI](https://www.voyageai.com/), [Pinecone](https://www.pinecone.io/), [Anthropic](https://console.anthropic.com/)

### Setup

```bash
git clone https://github.com/OldEphraim/legacylens.git
cd legacylens
```

Create `.env.local` in the project root:

```
VOYAGE_API_KEY=your_key
PINECONE_API_KEY=your_key
PINECONE_INDEX_NAME=legacylens
ANTHROPIC_API_KEY=your_key
```

**Backend:**

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Frontend:**

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

### Ingest the codebase

```bash
cd data
git clone https://github.com/OCamlPro/gnucobol.git gnucobol
cd ../backend
source venv/bin/activate
python -m app.ingestion.run --data-dir ../data/gnucobol
```

### Run

```bash
# Terminal 1 — backend
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Performance

| Metric | Result |
|--------|--------|
| Retrieval latency | ~250ms |
| Total query latency | 10-20s (streamed) |
| Chunks indexed | 13,613 |
| Files covered | 117/117 (100%) |
| Avg chunk size | 379 tokens |
| Ingestion time | ~18 min |

## Project Structure

```
legacylens/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI endpoints
│   │   ├── ingestion/
│   │   │   ├── discover.py      # File scanner (117 files)
│   │   │   ├── chunker.py       # COBOL/C/config syntax-aware splitting
│   │   │   ├── embedder.py      # Voyage Code 2 batch embedding
│   │   │   ├── store.py         # Pinecone upsert with metadata
│   │   │   └── run.py           # Orchestrator
│   │   ├── retrieval/
│   │   │   └── search.py        # Pinecone similarity search
│   │   └── generation/
│   │       ├── answer.py        # Claude Sonnet 4.5 answer generation
│   │       └── dependencies.py  # COBOL/C dependency parser
│   └── requirements.txt
├── frontend/                    # Next.js / TypeScript
├── data/
│   └── gnucobol/                # (gitignored) target codebase
├── docs/
│   └── rag-architecture.md      # RAG architecture document
├── gauntlet-docs/               # Assignment spec + pre-search
├── .env.local                   # (gitignored) API keys
└── CLAUDE.md
```

## Built for

Gauntlet AI Week 3 — RAG Systems for Legacy Enterprise Codebases.
