# LegacyLens — RAG Architecture Document

## 1. Vector DB Selection

**Decision: Pinecone (serverless, AWS us-east-1, cosine metric)**

Pinecone was selected as a managed vector database to eliminate DevOps overhead on a 3-day sprint. The free tier comfortably handles our 13,613 vectors with room to spare. Native metadata filtering enables queries scoped by `file_path`, `chunk_type`, `function_name`, and `language` — critical for the code understanding features that retrieve specific functions by metadata rather than semantic search alone. Pinecone's first-class LangChain integration simplified initial prototyping, though the final implementation uses the Pinecone SDK directly for finer control.

**Alternatives considered:** pgvector (familiar from PostgreSQL experience, but self-hosted operational overhead was unjustifiable for this timeline), ChromaDB (simplest local development story, but no credible production deployment path), Qdrant (strong filtering capabilities and Rust-based performance, but added deployment complexity with no clear benefit at our 13K-vector scale).

## 2. Embedding Strategy

**Decision: Voyage Code 2 (1536 dimensions)**

Voyage Code 2 is a code-specific embedding model trained across programming languages. General-purpose text embeddings lose semantic meaning in COBOL's verbose naming conventions — an identifier like `WS-CUSTOMER-RECORD-FIRST-NAME` carries structural meaning that code-trained models capture more effectively than prose-trained ones. The 1536-dimension output matches Pinecone's optimized index configuration.

Chunks are batch-embedded at 100 per API request with 0.5s inter-batch delay to stay within rate limits. Total codebase embedding cost was approximately $0.05 for ~500K tokens. **Consistency is enforced by using the same model and shared client for both ingestion (`input_type="document"`) and query embedding (`input_type="query"`)** — a model mismatch between these two paths would silently degrade retrieval quality with no obvious error.

## 3. Chunking Approach

This is the most architecturally significant component. A naive fixed-size splitter would cut through COBOL paragraph boundaries and C function signatures, destroying the semantic units that make retrieval meaningful.

**COBOL files (.cob, .cbl, .cpy):** Paragraph-level splitting. COBOL paragraphs are the language's equivalent of functions, invoked via `PERFORM` statements. Boundaries are detected by regex matching identifiers at column 8+, uppercase alphanumeric with hyphens, ending with a period (e.g., `       PROCESS-TRANSACTION.`). Section-level chunks capture `DATA DIVISION` definitions where variable declarations live. Division headers are preserved as metadata on child chunks.

**C files (.c, .h):** Function boundary detection. GnuCOBOL's C code uses a multi-line signature style (return type on one line, function name at column 0 on the next), which required custom detection logic rather than a simple regex. Brace-depth tracking delineates function bodies.

**Config and test files (.conf, .at, .def):** Fixed-size chunking with 200-token overlap. Test files additionally attempt `AT_SETUP` boundary detection to keep test cases intact.

**Post-processing:** Chunks smaller than 50 tokens are merged with adjacent chunks to avoid fragments that embed poorly. Chunks exceeding 800 tokens are split with a 100-token overlap fallback. Result: **13,613 chunks averaging 379 tokens from 117 files**, with a maximum of 799 tokens per chunk.

**Metadata preserved per chunk:** `file_path`, `line_start`, `line_end`, `chunk_type` (function, paragraph, section, division, test_case, config), `function_name`, `parent_section`, `parent_division`, `language` (cobol, c, config, test).

## 4. Retrieval Pipeline

**Query flow:** User query is embedded with Voyage Code 2 (`input_type="query"`) and sent to Pinecone for cosine similarity search with `top_k=5`. Retrieved chunks are assembled with file/line metadata into a structured context block, then sent to Claude Sonnet 4.5 with a system prompt instructing it to cite specific file paths and line numbers. The answer is streamed to the user via SSE.

**Retrieval latency is ~250ms** (Pinecone query). Total end-to-end latency is 10-20s, dominated entirely by LLM generation — streaming mitigates perceived wait time.

**Code understanding features** use a 3-tier function lookup: (1) exact metadata filter on `file_path` + `function_name`, (2) `function_name` filter with client-side path substring matching, (3) fallback to pure semantic search filtered by filename. This gracefully handles path format mismatches between user input and stored metadata.

## 5. Failure Modes

- **COPY statement dependencies:** COBOL's `COPY` directive includes external copybook files, creating implicit dependencies not visible within individual chunks. Copybooks are indexed separately but cross-chunk dependency tracking is incomplete.
- **Verbose naming vs. natural language:** COBOL identifiers like `WS-CUSTOMER-RECORD-FIRST-NAME` may not semantically match natural language queries like "customer first name" despite referring to the same concept. Code-specific embeddings mitigate but don't eliminate this gap.
- **Fixed-format column noise:** COBOL columns 1-7 contain sequence numbers and indicators, not executable code. These are embedded alongside meaningful code, adding noise to the vector representation.
- **Compiler vs. business application:** GnuCOBOL is a compiler, not a business application. Queries about business data structures correctly return "not found" rather than hallucinating — a deliberate design choice in the system prompt.
- **Regex-based dependency parsing:** The dependency mapper uses regex to extract `PERFORM`, `COPY`, `CALL`, and C function calls. This misses indirect calls, macro-generated references, and function pointers.

## 6. Performance Results

| Metric | Measured | Target |
|--------|----------|--------|
| Retrieval latency | ~250ms | <3s |
| Total query latency | 10-20s (streamed) | — |
| Chunks indexed | 13,613 | — |
| Files covered | 117/117 (100%) | 100% |
| Avg chunk size | 379 tokens | 200-500 |
| Max chunk size | 799 tokens | <800 |
| Ingestion time | ~18 min | <5 min* |
| Embedding cost | ~$0.05 | — |

*Ingestion exceeded target due to Voyage API rate limits on the free tier; resolved by upgrading to paid tier mid-ingestion.

**First query verification:** "Where is the main entry point?" returned `cobcrun.c:main` (score: 0.780) and `cobc.c:main` (score: 0.769) as the top two results — both correct, as GnuCOBOL has two entry points (the compiler and the runtime executor).
