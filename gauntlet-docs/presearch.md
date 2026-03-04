# LegacyLens: Pre-Search Document

*RAG Architecture Discovery & Stack Decision Record*

| | | | |
|---|---|---|---|
| **Developer** | Alan (solo) | **Date** | March 2, 2026 |
| **Target Codebase** | GnuCOBOL | **Vector DB** | Pinecone (managed) |
| **Embeddings** | Voyage Code 2 (1536d) | **RAG Framework** | LangChain |
| **LLM** | Claude (primary) + GPT-4o (fallback) | **Backend** | Python/FastAPI |
| **Frontend** | Next.js | **Deploy** | Vercel + Railway |

---

## Phase 1: Define Your Constraints

### 1. Scale & Load Profile

**Target codebase:** GnuCOBOL — the open-source COBOL compiler. This is a substantial codebase with 100,000+ lines of COBOL and C across hundreds of files, well exceeding the 10,000 LOC / 50 file minimum. It includes the compiler itself, runtime libraries, and test suites — providing rich variety for RAG retrieval testing.

**Expected query volume:** 5-20 concurrent users during Gauntlet evaluation. Post-submission, this is a portfolio project, so sustained traffic is near-zero with occasional spikes during interviews/demos.

**Ingestion model:** Batch ingestion at startup. The codebase is static (we pick a specific commit/release), so there's no need for incremental updates during the evaluation window. Re-ingestion is only needed if we change chunking strategy.

**Latency requirements:** <3 seconds end-to-end per the assignment spec. This is achievable with Pinecone's managed infrastructure (typical p99 query latency is 50-100ms) plus LLM generation time (1-2s for Claude). The bottleneck will be LLM answer generation, not vector search.

### 2. Budget & Cost Ceiling

**Approach:** Free tier wherever possible, consistent with previous weeks.

**Pinecone:** Free tier provides 2GB storage and 100K vectors on a single index. GnuCOBOL at ~100K LOC with function-level chunking will produce roughly 2,000-5,000 chunks — well within limits.

**Voyage Code 2:** ~$0.10 per million tokens. Embedding the entire GnuCOBOL codebase (estimated ~500K tokens) costs approximately $0.05. Negligible.

**Claude API (answer generation):** This is the primary cost driver. At ~1,000 tokens per response with retrieved context, each query costs ~$0.01-0.03. During development and testing (maybe 200-500 queries), total spend ~$5-15.

**GPT-4o (fallback):** Similar per-query costs. Only used if Claude is rate-limited or unavailable.

**Total estimated development spend:** $15-25, dominated by LLM answer generation during testing.

**Trading money for time:** Using Pinecone (managed) over self-hosted Qdrant/Weaviate saves significant DevOps time. Using Voyage Code 2 (API) over local sentence-transformers avoids GPU/inference setup. Both are correct tradeoffs for a 3-day sprint.

### 3. Time to Ship

**MVP deadline:** Tuesday midnight CT. This is the hard gate.

**Final deadline (G4):** Wednesday midnight CT. This is extremely compressed — essentially 48 hours from MVP to final.

**Must-have for MVP:** Basic ingestion pipeline, Pinecone storage, semantic search, CLI or web query interface, LLM answer generation with code snippets and file/line references. Deployed.

**Nice-to-have for final:** Syntax highlighting, re-ranking, 4+ code understanding features, evaluation metrics, polished UI.

**Framework learning curve:** LangChain is well-documented with extensive code examples. The Pinecone integration is a first-class citizen in LangChain. Learning curve is acceptable for the timeline — most patterns are template-able with AI assistance.

**Schedule reality:** MVP must be submitted Tuesday EOD. Final is Wednesday midnight, but pre-existing plans exist for Wednesday evening. This means the Tuesday overnight session is critical — MVP by Tuesday EOD, then push through to final submission by Wednesday afternoon/early evening. Much more intense sprint than first two weeks.

### 4. Data Sensitivity

**Codebase:** GnuCOBOL is fully open source (GPL). No restrictions on sending code to external APIs. No data residency concerns.

**Can send to external APIs:** Yes, unrestricted. This is public open-source code. We can freely embed it via Voyage, store in Pinecone, and send chunks to Claude/GPT-4o for answer generation.

**User queries:** No PII concerns. Queries are about code structure, not personal data. No GDPR/compliance considerations for the evaluation use case.

### 5. Team & Skill Constraints

**Solo developer.** AI-assisted development with Claude Code as the primary coding agent.

**Vector database experience:** No prior production experience with vector databases, but strong PostgreSQL background. Pinecone's managed API abstracts away the operational complexity. The conceptual model (embed → store → query → retrieve) is straightforward.

**RAG framework experience:** No prior LangChain or LlamaIndex experience. LangChain was chosen over LlamaIndex specifically because it has more tutorials and community resources, which means Claude Code and web search can resolve blockers faster. The tradeoff is that LlamaIndex might be slightly better suited for document-focused RAG, but LangChain's flexibility and ecosystem win on a tight timeline.

**COBOL familiarity:** None. This is by design — the assignment tests whether the RAG system can make an unfamiliar codebase understandable. The developer's own unfamiliarity with COBOL serves as a natural test: if the RAG system helps me understand the code, it works.

**AI coding tools:** Claude Code (primary), claude.ai for architecture discussions and document generation. ChatGPT for independent review (same workflow as Weeks 1-2).

---

## Phase 2: Architecture Discovery

### 6. Vector Database Selection

**Decision: Pinecone (managed cloud)**

**Why Pinecone over alternatives:**

| Considered | Verdict | Reason |
|---|---|---|
| Pinecone | **Selected** | Managed, free tier, fastest to production, excellent LangChain integration |
| pgvector | Runner-up | Familiar (strong Postgres background), but requires self-hosting a Postgres instance and managing extensions. Adds operational overhead not worth it for a 3-day sprint |
| ChromaDB | Considered | Simplest local dev, but lacks production deployment story. Weaker interview answer than Pinecone |
| Qdrant | Considered | Great filtering, Rust-based performance. But self-hosting adds complexity. Cloud version exists but Pinecone's free tier is more generous |
| Weaviate | Dismissed | GraphQL API adds unnecessary abstraction layer for this use case |
| Milvus | Dismissed | Overkill for scale. GPU acceleration irrelevant for ~5K vectors |

**Filtering and metadata:** Pinecone supports metadata filtering natively. We'll store file_path, line_start, line_end, function_name, chunk_type (function/paragraph/section), and language as metadata on each vector. This enables filtered queries like "find all PERFORM statements in the compiler module."

**Hybrid search:** Pinecone supports hybrid search (vector + keyword) via sparse-dense vectors. This is valuable for code search where exact identifier names matter. Will implement as a post-MVP enhancement if time permits.

**Scaling:** Pinecone's free tier handles our needs. The serverless architecture means no capacity planning. If we needed to scale beyond 100K vectors (unlikely for this project), paid tiers are straightforward.

### 7. Embedding Strategy

**Decision: Voyage Code 2 (1536 dimensions)**

**Why Voyage Code 2:**

| Model | Considered | Verdict |
|---|---|---|
| Voyage Code 2 | **Selected** | Purpose-built for code understanding. Trained on code across languages. 1536 dimensions matches Pinecone's sweet spot. Strong interview story: "I chose a code-specific embedding model because general-purpose models lose semantic meaning in COBOL's verbose syntax" |
| OpenAI text-embedding-3-small | Runner-up | Good general-purpose, well-documented, slightly cheaper. But not optimized for code — would likely produce lower retrieval precision on COBOL |
| OpenAI text-embedding-3-large | Dismissed | 3072 dimensions is overkill for ~5K chunks. Doubles storage cost with marginal quality improvement at this scale |
| sentence-transformers (local) | Dismissed | Free but requires local GPU/inference setup. Adds deployment complexity. Quality varies significantly by model choice |
| Cohere embed-english-v3 | Dismissed | Optimized for English prose, not code. Wrong tool for the job |

**Dimension tradeoffs:** 1536 dimensions provides a good balance. Higher dimensions capture more semantic nuance but increase storage and query cost. At our scale (~5K chunks), the cost difference is negligible, but 1536 is the standard that Pinecone indexes are optimized for.

**Batch processing:** Will embed chunks in batches of 100-200 via the Voyage API. Total embedding time for the full codebase should be under 2 minutes. The API supports batch requests natively.

**Consistency:** Critical to use the same model for both ingestion and query embedding. Will wrap in a shared utility function to prevent accidental model mismatch.

### 8. Chunking Approach

**Decision: Hierarchical chunking with COBOL-aware syntax splitting**

This is the most technically interesting decision in the project. COBOL's structure is uniquely suited to syntax-aware chunking because the language has rigid, well-defined hierarchical boundaries:

**COBOL structure (from largest to smallest):**
- DIVISION (IDENTIFICATION, ENVIRONMENT, DATA, PROCEDURE)
- SECTION (within each division)
- PARAGRAPH (within sections — the primary executable unit)
- SENTENCE/STATEMENT (individual operations)

**Primary chunking strategy:** Function/paragraph-level. Each COBOL PARAGRAPH becomes one chunk. This is the natural boundary for COBOL — paragraphs are the equivalent of functions in modern languages. They're invoked via PERFORM statements and represent discrete units of business logic.

**Secondary strategy:** Section-level chunks for the DATA DIVISION, where variable definitions and record layouts live. These are critical for understanding data flow but don't have paragraph boundaries.

**Fallback:** Fixed-size with 200-token overlap for any content that doesn't fit the above patterns (comments, copybooks, configuration).

**Chunk size targets:** 200-500 tokens per chunk. This fits well within Voyage Code 2's context window and provides enough context for meaningful retrieval without diluting the embedding with irrelevant code.

**Metadata to preserve per chunk:**
- file_path (relative to repo root)
- line_start, line_end
- chunk_type (paragraph | section | division | data_definition | comment_block)
- parent_section and parent_division
- function_name (paragraph name, if applicable)
- dependencies (PERFORM targets, COPY references)

**GnuCOBOL-specific considerations:** GnuCOBOL's source includes both COBOL files (.cob, .cbl) and C files (.c, .h) for the runtime. The C files can use standard function-level chunking. The COBOL files use the paragraph-level approach above. Will need file extension detection in the ingestion pipeline to route to the correct chunker.

### 9. Retrieval Pipeline

**Top-k:** Start with k=5, which aligns with the assignment's ">70% relevant chunks in top-5" target. Can increase to k=10 for complex queries that span multiple files.

**Re-ranking:** Will implement a lightweight LLM-based re-ranker as a post-MVP enhancement. For MVP, raw cosine similarity from Pinecone is sufficient. The re-ranker sends the query + top-10 raw results to Claude and asks it to reorder by relevance — simple but effective.

**Context window management:** Retrieved chunks will be assembled with surrounding context (2-3 lines before and after each chunk from the original file). This helps the LLM understand the chunk in context without requiring the full file. Total context assembly target: ~2,000-4,000 tokens per query to leave room for the LLM's response.

**Query expansion:** Will implement basic query expansion for MVP — if a query mentions a COBOL identifier, also search for its definition in the DATA DIVISION. This is critical because COBOL separates data definitions from procedure logic.

### 10. Answer Generation

**Primary LLM: Claude (claude-sonnet-4-5-20250929 via Anthropic API)**

Claude is the natural choice for the Gauntlet ecosystem. Sonnet 4.5 provides strong code understanding at reasonable cost. Will use structured prompts that include the original query, retrieved code chunks with file/line metadata, instructions to cite specific files and line numbers, and COBOL-specific context explaining COBOL conventions if the query seems to come from a non-COBOL developer.

**Fallback: GPT-4o**

If Claude is rate-limited or returns errors, fall back to GPT-4o with the same prompt template. This provides resilience during demo/evaluation when reliability matters.

**Prompt template design:**

```
You are a COBOL code expert analyzing the GnuCOBOL codebase.
Given the following code chunks retrieved from the codebase, answer the user's question.
Always cite specific file paths and line numbers.
If the retrieved chunks don't contain enough information, say so.

Retrieved chunks:
{chunks_with_metadata}

User question: {query}
```

**Streaming:** Will implement streaming responses for the web interface (better UX) and batch for the CLI. LangChain supports both via the standard callback pattern.

### 11. Framework Selection

**Decision: LangChain**

| Framework | Considered | Verdict |
|---|---|---|
| LangChain | **Selected** | Most tutorials, best Pinecone integration, flexible pipeline composition. Community resources mean Claude Code can resolve issues faster |
| LlamaIndex | Runner-up | Better document-focused abstractions, but steeper learning curve and fewer community examples for code-specific RAG |
| Haystack | Dismissed | Production-focused, but heavier setup. Better for teams, not solo sprints |
| Custom | Dismissed | Maximum control and better interview story, but too risky for a 24-hour MVP. Would consider for a longer timeline |

**Key LangChain components we'll use:**
- `langchain.document_loaders` — custom loader for COBOL files
- `langchain.text_splitter` — custom COBOL-aware splitter (extending RecursiveCharacterTextSplitter)
- `langchain_pinecone` — Pinecone vector store integration
- `langchain_voyageai` — Voyage embeddings integration
- `langchain_anthropic` — Claude for answer generation
- `langchain.chains` — RetrievalQA chain for the core query pipeline

**Evaluation and observability:** LangSmith (LangChain's observability platform) has a free tier. Will integrate for tracing retrieval quality during development. This also gives us built-in precision/recall metrics.

---

## Phase 3: Post-Stack Refinement

### 12. Failure Mode Analysis

**When retrieval finds nothing relevant:** Return an honest "I couldn't find relevant code for this query" message with suggestions to rephrase. Don't hallucinate code references. This is critical for trust — a RAG system that confidently returns wrong file/line numbers is worse than one that admits uncertainty.

**Ambiguous queries:** Use query classification to detect ambiguity. If a query like "show me the main logic" is too vague, prompt the user to be more specific: "Could you clarify which module? The codebase has X main entry points." LangChain's ConversationalRetrievalChain supports follow-up questions natively.

**COBOL-specific failure modes:**
- COPY statements (COBOL's include mechanism) create implicit dependencies that may not be captured in individual chunks. Mitigation: index copybook files separately and include them in dependency metadata.
- COBOL's verbose naming (e.g., WS-CUSTOMER-RECORD-FIRST-NAME) means embeddings might not capture semantic similarity with natural language queries like "customer first name." Mitigation: include a COBOL-to-English glossary in the system prompt.
- Fixed-format COBOL (columns 1-6 are sequence numbers, column 7 is indicator) requires preprocessing to strip column metadata before embedding.

**Rate limiting and error handling:** Implement exponential backoff for all API calls (Voyage, Pinecone, Claude, GPT-4o). Cache embeddings locally to avoid re-embedding on retry. Circuit breaker pattern for LLM calls — if Claude fails 3x, switch to GPT-4o automatically.

### 13. Evaluation Strategy

**Retrieval precision measurement:** Create a ground truth dataset of 20-30 query/expected-result pairs based on the testing scenarios in the assignment spec. For each query, manually identify which files/functions should be retrieved. Measure precision@5 (what fraction of top-5 results are relevant).

**Automated evaluation:** Use LangSmith's built-in evaluation tools to run the test suite on each chunking/retrieval change. Track precision over time to ensure changes improve rather than regress.

**User feedback:** Add thumbs up/down on each query result in the web interface. Store feedback in a simple database (or even a JSON file) for post-submission analysis. This also serves as a demo feature showing awareness of production feedback loops.

### 14. Performance Optimization

**Embedding cache:** Cache all computed embeddings locally (pickle or JSON). If we re-run ingestion with the same chunking strategy, skip the Voyage API call. This saves both time and money during development iteration.

**Pinecone index optimization:** Use a single namespace per codebase. If we add multiple codebases later, use namespaces to partition the index without creating multiple indexes (which would use multiple free-tier slots).

**Query preprocessing:** Normalize COBOL identifiers in queries (strip hyphens, handle common abbreviations). Add a COBOL keyword detector to boost keyword matches alongside semantic search.

### 15. Observability

**Logging:** Structured JSON logging for every query, including: query text, retrieved chunk IDs, similarity scores, LLM model used, response time breakdown (embedding time, Pinecone query time, LLM generation time), and any errors.

**Metrics to track:**
- End-to-end query latency (target: <3s)
- Retrieval precision@5 (target: >70%)
- LLM response quality (manual review + user feedback)
- API costs per query (for cost analysis requirement)
- Error rates by component (embedding, vector search, LLM)

**Dashboard:** If time permits, add a simple /metrics endpoint that shows aggregate stats. This impresses evaluators and demonstrates production awareness.

### 16. Deployment & DevOps

**Backend (Python/FastAPI):** Deploy to Railway. Railway supports Python natively, has a free tier, and handles environment variables securely. The FastAPI backend will expose REST endpoints for the Next.js frontend.

**Frontend (Next.js):** Deploy to Vercel. Standard approach, consistent with previous weeks. The frontend calls the Railway-hosted API.

**CI/CD:** GitHub Actions for basic CI (lint, type-check, run evaluation suite on push). Index updates are manual — run the ingestion script locally or via a one-off Railway job.

**Environment management:** `.env.local` for local development, Railway/Vercel environment variables for production. Keys needed: VOYAGE_API_KEY, PINECONE_API_KEY, ANTHROPIC_API_KEY.

**Secrets handling:** All API keys in environment variables, never committed. `.gitignore` and `.claudeignore` configured from day one (learned from Week 1 setup).

---

## Code Understanding Features (4+ Required)

**Selected features (prioritized by implementation difficulty and demo impact):**

1. **Code Explanation** — Explain what a COBOL paragraph/section does in plain English. This is the core RAG use case and comes nearly free with the answer generation pipeline.

2. **Documentation Gen** — Generate documentation for undocumented code. Feed a chunk to Claude with a "write documentation for this code" prompt. High demo impact, low implementation cost.

3. **Dependency Mapping** — Parse PERFORM statements and COPY directives to build a call graph. Display as a simple tree or list showing what calls what. Requires a lightweight COBOL parser but is very impressive in demos.

4. **Business Logic Extract** — Identify and explain business rules embedded in code (e.g., "this paragraph calculates compound interest using a 360-day year convention"). Feed function chunks to Claude with an "extract the business rules" prompt.

5. **(Stretch) Translation Hints** — Suggest Python/TypeScript equivalents for COBOL constructs. Great interview talking point for the fintech modernization narrative.

---

## AI Generation Process

**Process:** This Pre-Search document was generated through an interactive conversation with Claude (Anthropic, claude.ai Opus). The assignment PDF was provided, and Claude extracted the 16-item Pre-Search checklist. Claude then asked targeted questions to establish key decision points (codebase selection, backend language, vector database, embedding model, RAG framework, LLM choice). Based on those answers and knowledge of the developer's existing skill set (TypeScript, React, Next.js, Python, PostgreSQL) and career goals (fintech), Claude generated a comprehensive first draft covering all 16 sections with decisions, tradeoff analysis, and comparison tables.

**Review cycle:** Will be shared with ChatGPT (OpenAI) for independent review, consistent with the Week 1 and Week 2 workflow.

**Tools used:** Claude (claude.ai, Opus) for primary document generation. ChatGPT (OpenAI) for independent review. The full AI conversation is saved as a reference document.