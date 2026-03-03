"""Test the full RAG pipeline: retrieval + answer generation.

Usage:
    cd backend
    source venv/bin/activate
    python test_rag.py
"""

import os
import time

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env.local"))

from app.retrieval.search import SearchEngine
from app.generation.answer import AnswerGenerator


def test_query(search: SearchEngine, generator: AnswerGenerator, query: str):
    print(f"\n{'='*70}")
    print(f"QUERY: {query}")
    print(f"{'='*70}")

    t0 = time.time()

    # Retrieve
    results = search.search(query, top_k=5)
    retrieval_ms = int((time.time() - t0) * 1000)

    print(f"\nRetrieved {len(results)} chunks in {retrieval_ms}ms:")
    for i, r in enumerate(results, 1):
        name = r.function_name or ""
        print(f"  {i}. [{r.score:.3f}] {r.file_path}:{r.line_start}-{r.line_end} "
              f"({r.chunk_type}) {name}")

    # Generate
    t1 = time.time()
    answer = generator.generate(query, results)
    gen_ms = int((time.time() - t1) * 1000)
    total_ms = int((time.time() - t0) * 1000)

    print(f"\nAnswer (generated in {gen_ms}ms, total {total_ms}ms):")
    print(f"{'-'*70}")
    print(answer)
    print(f"{'-'*70}")

    return total_ms


def main():
    print("LegacyLens RAG Pipeline Test")
    print("Initializing search engine and answer generator...")

    search = SearchEngine()
    generator = AnswerGenerator()

    queries = [
        "Where is the main entry point of this program?",
        "Find all file I/O operations",
        "Show me error handling patterns in this codebase",
    ]

    latencies = []
    for q in queries:
        ms = test_query(search, generator, q)
        latencies.append(ms)

    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    for q, ms in zip(queries, latencies):
        status = "PASS" if ms < 30000 else "SLOW"
        print(f"  [{status}] {ms}ms — {q}")
    print(f"  Average latency: {sum(latencies)//len(latencies)}ms")


if __name__ == "__main__":
    main()
