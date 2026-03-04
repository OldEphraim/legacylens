# LegacyLens Demo Video Script (Final Submission)

Target length: 3-5 minutes. Record after deploying the 4 code understanding features.

---

## [0:00 - 0:25] Intro

"This is LegacyLens — a RAG-powered system for querying and understanding legacy enterprise codebases. I built it for Gauntlet AI Week 3.

It indexes the GnuCOBOL compiler — 128,000 lines of COBOL and C across 117 files — and lets developers explore unfamiliar legacy code through natural language.

The app is deployed and publicly accessible — frontend on Vercel, backend on Railway."

**[Show: browser with deployed Vercel URL visible in address bar: legacylens-app.vercel.app]**

---

## [0:25 - 1:00] Query 1: Main Entry Point

Type: "Where is the main entry point of this program?"

While tokens stream in:

"When you submit a query, it gets embedded with Voyage Code 2 — a code-specific embedding model — and Pinecone returns the top 5 most similar chunks from the indexed codebase. Claude Sonnet 4.5 then generates an answer grounded in those retrieved chunks.

Retrieval takes about 250 milliseconds. The streaming you're seeing is Claude generating the answer."

Once complete, scroll to sources:

"Each result shows the file path, line numbers, chunk type, and a similarity score. The code snippet is displayed inline so you can verify the answer against the actual source."

**[Point out: file path header (e.g. `cobc/cobc.c:1234-1300`), the `function` chunk type badge, and the similarity score (e.g. 0.84)]**

---

## [1:00 - 1:30] Query 2: File I/O Operations

Type: "Find all file I/O operations"

"This query tests cross-file retrieval. File I/O in GnuCOBOL spans multiple C source files in the runtime library — you can see results from fileio.c and other modules. The system searches across all 13,613 indexed chunks, not just a single file."

**[Leave this result visible — we'll use the fileio.c source cards for the next 4 features]**

---

## [1:30 - 2:00] Query 3: COBOL Dialects (Config File Retrieval)

Type: "What COBOL dialects does GnuCOBOL support?"

"This is interesting because it hits the dialect configuration files, not source code. During ingestion, I used syntax-aware chunking — COBOL files are split on paragraph boundaries, C files on function boundaries, and config and test files use fixed-size chunks with overlap. All 117 files were indexed, including .conf dialect definitions and .at test suites."

---

## [2:00 - 2:30] Code Understanding Feature 1: Code Explanation

Go back to the file I/O results. Click the **"Explain"** button on the `cob_sys_read_file` source card from `libcob/fileio.c`.

"LegacyLens has four code understanding features beyond basic search. The first is Code Explanation — I click 'Explain' on any source card, and Claude analyzes the code chunk and explains what it does in plain English."

As streaming output appears:

"This is `cob_sys_read_file`, which implements the COBOL library routine `CBL_READ_FILE`. The explanation covers how it acts as a bridge between COBOL's high-level file operations and low-level C system calls — handling endianness conversion for cross-platform compatibility, a dual-purpose flag that switches between reading data and querying file size, and translating POSIX return codes into COBOL status codes like `COB_STATUS_10_END_OF_FILE`."

**[Key phrases to highlight in the output: "bridge between COBOL and C", "endianness", "dual-purpose flag", "COB_STATUS" codes]**

---

## [2:30 - 3:00] Code Understanding Feature 2: Documentation Generation

Click **"Docs"** on the `lineseq_read` source card from `libcob/fileio.c` (or use the same `cob_sys_read_file` card).

"Second is Documentation Generation. This generates professional technical docs for any function — useful for undocumented legacy code where the original developers are long gone."

As output streams:

"It produces structured documentation with Purpose, Parameters, Return Values, Side Effects, and an Algorithm section describing the logic step by step. For `lineseq_read`, it documents how the function reads a line-sequential file record — handling line delimiters, buffer management, and the difference between reading lines with and without newline characters."

**[Key phrases to highlight: "Purpose", "Parameters", "Return Values", "Side Effects", "Algorithm" section headers in the markdown output]**

---

## [3:00 - 3:30] Code Understanding Feature 3: Dependency Mapping

Switch to the **Code Understanding** tab. Type file path `cobc/cobc.c` and function name `process_command_line`, then click **"Dependencies"**.

"Third is Dependency Mapping. Unlike the other features, this doesn't use an LLM — it parses the code directly for function calls in C, or PERFORM statements and COPY directives in COBOL. Then it searches the Pinecone index to find where each dependency is defined."

When results appear:

"For `process_command_line` in `cobc.c`, we see 8 outgoing calls — functions like `cob_getopt_long_long` for argument parsing, `cobc_print_usage` and `cobc_print_shortversion` for help output. And 2 incoming callers — the `main` function in both `cobc.c` and `cobcrun.c`. This gives you a call graph for navigating unfamiliar code."

**[Point out the two sections: "Calls (8)" with file paths for each, and "Called By (2)" showing both callers]**

---

## [3:30 - 3:55] Code Understanding Feature 4: Business Logic Extraction

Go back to the **Search** tab with the file I/O results still visible. Click **"Business Logic"** on the `cob_sys_read_file` source card.

"Fourth is Business Logic Extraction — the killer feature for COBOL modernization. This identifies the real-world business rules embedded in the code."

As output streams:

"For `cob_sys_read_file`, it extracts 7 distinct business rules: parameter validation that enforces the API contract, a file-size query mode for batch processing, endianness handling for cross-platform data interchange between mainframes and modern servers, direct file positioning for random record access, and end-of-file detection that distinguishes 'file processed completely' from 'file corrupted mid-read'. It explains *why* each rule matters — for example, byte-order errors could cause a $1,000 value to be read as $16 million."

**[Key phrases to highlight: numbered "Rule" sections, "Business Process", "Real-world Implications", the specific dollar figure example]**

---

## [3:55 - 4:15] Code Understanding Tab (Direct Access)

"I showed dependency mapping from the Code Understanding tab already, but let me demonstrate that all four features work here too. You enter a file path and function name directly, without running a search first — useful when you already know which function you want to analyze."

Type file path `cobc/cobc.c` and function name `main`, click **"Explain"** to show it working.

"This is the same streaming explanation, but accessed directly by file and function name rather than from search results."

---

## [4:15 - 4:40] Architecture Summary

"Quick architecture overview: the ingestion pipeline processes 117 files with syntax-aware chunking, producing 13,613 chunks embedded with Voyage Code 2 at 1536 dimensions, stored in Pinecone. Retrieval runs at about 250 milliseconds. Answer generation uses Claude Sonnet 4.5 with streaming.

I chose Pinecone for its managed infrastructure and free tier, Voyage Code 2 because general-purpose embeddings lose semantic meaning in COBOL's verbose syntax, and LangChain for its Pinecone integration and community resources.

Total development cost was under $7."

---

## [4:40 - 5:00] Wrap

"LegacyLens — making legacy enterprise codebases queryable through natural language. Built with Python, FastAPI, Next.js, Pinecone, Voyage Code 2, and Claude.

GitHub link and documentation are in the repo. Thanks for watching."

---

## Demo Tips

- **Run the file I/O query early** — the fileio.c results give you `cob_sys_read_file` and `lineseq_read` source cards to use for 3 of the 4 code understanding features.
- **Use the Code Understanding tab for Dependencies** — entering `cobc/cobc.c` + `process_command_line` directly is cleaner than hoping the right function appears in search results.
- **Don't wait for full streaming** — you can start narrating what the output covers while tokens are still appearing. Each feature takes 15-35 seconds to fully stream.
- **Hard refresh** (Cmd+Shift+R) before recording to ensure the latest deployment is loaded.

---

## Requirements Coverage Matrix

| # | Requirement | How It's Met | Shown In Video |
|---|-------------|-------------|----------------|
| **MVP Requirements** | | | |
| 1 | Ingest at least one legacy codebase | GnuCOBOL: 117 files, 128K LOC | 0:00-0:25 intro, 1:30-2:00 dialect query |
| 2 | Chunk code files with syntax-aware splitting | COBOL paragraph boundaries, C function boundaries, fixed-size fallback for config/test | 1:30-2:00 (mentioned during dialect query), 4:15-4:40 architecture |
| 3 | Generate embeddings for all chunks | 13,613 chunks via Voyage Code 2 (1536d) | 0:25-1:00 (explained during first query), 4:15-4:40 |
| 4 | Store embeddings in a vector database | Pinecone managed, free tier | 0:25-1:00, 4:15-4:40 |
| 5 | Implement semantic search across codebase | Voyage Code 2 query embedding → Pinecone top-k=5 | 0:25-1:00 (first query demonstrates search) |
| 6 | Natural language query interface (CLI or web) | Next.js web UI with streaming | Visible throughout entire demo |
| 7 | Return relevant code snippets with file/line references | Source cards with file path, line numbers, code snippet, similarity score | 0:25-1:00 (scroll to sources after first query) |
| 8 | Basic answer generation using retrieved context | Claude Sonnet 4.5 streaming answers with citations | Every query in demo |
| 9 | Deployed and publicly accessible | Frontend on Vercel, backend on Railway | 0:00-0:25 (Vercel URL visible in address bar) |
| **Code Understanding Features (4+ required)** | | | |
| 10 | Code Explanation | POST /api/explain — streaming plain-English walkthrough | 2:00-2:30 (cob_sys_read_file) |
| 11 | Documentation Gen | POST /api/document — streaming structured docs | 2:30-3:00 (lineseq_read) |
| 12 | Dependency Mapping | POST /api/dependencies — parses function calls, finds definitions in index | 3:00-3:30 (process_command_line: 8 calls, 2 callers) |
| 13 | Business Logic Extract | POST /api/business-logic — streaming business rule analysis | 3:30-3:55 (cob_sys_read_file: 7 rules extracted) |
| **Query Interface Requirements** | | | |
| 14 | Natural language input | Text input with submit button and Enter key support | Visible throughout |
| 15 | Display retrieved code snippets with syntax highlighting | Source cards with monospace code blocks | 0:25-1:00 |
| 16 | Show file paths and line numbers | Displayed on each source card header | 0:25-1:00 |
| 17 | Confidence/relevance scores | Similarity score badge on each source card | 0:25-1:00 |
| 18 | Generated explanation/answer from LLM | Streaming Claude answer at top of results | Every query |
| 19 | Ability to drill down into full file context | Code Understanding tab allows direct function lookup | 3:00-3:30, 3:55-4:15 |
| **Submission Deliverables** | | | |
| 20 | GitHub Repository with setup guide | README.md with setup instructions and deployed link | Mentioned at 4:40-5:00 |
| 21 | Demo Video (3-5 min) | This video | — |
| 22 | Pre-Search Document | Completed 16-section presearch.md | Not shown (submitted separately) |
| 23 | RAG Architecture Doc | 1-2 page architecture breakdown (docs/rag-architecture.md) | Not shown (submitted separately) |
| 24 | AI Cost Analysis | Dev spend + projections at 4 scales | Not shown (submitted separately) |
| 25 | Deployed Application | Vercel + Railway | 0:00-0:25 |
| 26 | Social Post | LinkedIn/X post with @GauntletAI | Not shown (posted separately) |
