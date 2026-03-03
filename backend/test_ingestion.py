"""Quick test script to verify the ingestion pipeline works end-to-end.

Usage:
    cd backend
    source venv/bin/activate
    python test_ingestion.py
"""

import os
import sys

from dotenv import load_dotenv

# Load env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env.local"))

from app.ingestion.discover import discover_files
from app.ingestion.chunker import chunk_file
from app.ingestion.embedder import embed_chunks, embed_query, get_client
from app.ingestion.store import get_pinecone_index


def test_discovery():
    """Test file discovery."""
    print("=" * 50)
    print("TEST: File Discovery")
    print("=" * 50)
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "gnucobol")
    files = discover_files(data_dir)
    assert len(files) > 100, f"Expected >100 files, got {len(files)}"

    by_lang = {}
    for fp, lang in files:
        by_lang.setdefault(lang, []).append(fp)
        assert lang in ("cobol", "c", "config", "test"), f"Unknown language: {lang}"

    print(f"  PASS: Found {len(files)} files")
    for lang, paths in sorted(by_lang.items()):
        print(f"    {lang}: {len(paths)}")
    return files


def test_chunking(files):
    """Test chunking on sample files."""
    print("\n" + "=" * 50)
    print("TEST: Chunking")
    print("=" * 50)

    all_chunks = []
    for fp, lang in files:
        chunks = chunk_file(fp, lang)
        assert len(chunks) > 0, f"No chunks from {fp}"
        for c in chunks:
            assert c.content.strip(), f"Empty chunk from {fp}"
            assert c.file_path == fp
            assert c.language == lang
            assert c.line_start > 0
            assert c.line_end >= c.line_start
        all_chunks.extend(chunks)

    # Verify no oversized chunks
    tokens = [c.token_estimate for c in all_chunks]
    max_tok = max(tokens)
    assert max_tok < 1000, f"Oversized chunk: {max_tok} tokens"

    print(f"  PASS: {len(all_chunks)} chunks created")
    print(f"  Token range: {min(tokens)}-{max_tok}, avg={sum(tokens)//len(tokens)}")
    return all_chunks


def test_embedding():
    """Test embedding on a small batch."""
    print("\n" + "=" * 50)
    print("TEST: Embedding (small batch)")
    print("=" * 50)
    client = get_client()

    # Create a few test chunks
    from app.ingestion.chunker import Chunk
    test_chunks = [
        Chunk(
            content="PERFORM CALCULATE-INTEREST",
            file_path="test.cob",
            line_start=1,
            line_end=1,
            chunk_type="paragraph",
            language="cobol",
        ),
        Chunk(
            content="static void cob_init(void) { /* initialize runtime */ }",
            file_path="test.c",
            line_start=1,
            line_end=1,
            chunk_type="function",
            language="c",
        ),
    ]

    result = embed_chunks(test_chunks, client=client)
    for c in result:
        assert c.embedding is not None, "Embedding should not be None"
        assert len(c.embedding) == 1536, f"Expected 1536 dims, got {len(c.embedding)}"

    # Test query embedding
    qvec = embed_query("Where is the main entry point?", client=client)
    assert len(qvec) == 1536

    print("  PASS: Embeddings generated (1536 dims)")
    return client


def test_pinecone_search():
    """Test that we can query the Pinecone index."""
    print("\n" + "=" * 50)
    print("TEST: Pinecone Search")
    print("=" * 50)

    index = get_pinecone_index(create_if_missing=False)
    stats = index.describe_index_stats()
    total_vectors = stats.get("total_vector_count", 0)
    print(f"  Index has {total_vectors} vectors")

    if total_vectors == 0:
        print("  SKIP: No vectors in index (run full ingestion first)")
        return

    # Try a query
    client = get_client()
    qvec = embed_query("Where is the main entry point of the program?", client=client)
    results = index.query(vector=qvec, top_k=5, include_metadata=True)

    print(f"  Query returned {len(results.matches)} results:")
    for match in results.matches:
        meta = match.metadata
        print(f"    score={match.score:.3f} | {meta.get('file_path', '?')}:"
              f"{meta.get('line_start', '?')}-{meta.get('line_end', '?')} "
              f"[{meta.get('chunk_type', '?')}] {meta.get('function_name', '')}")

    assert len(results.matches) > 0, "Expected at least 1 result"
    print("  PASS: Search works")


def main():
    print("LegacyLens Ingestion Pipeline Tests")
    print("=" * 50)

    files = test_discovery()
    chunks = test_chunking(files)
    test_embedding()
    test_pinecone_search()

    print("\n" + "=" * 50)
    print("ALL TESTS PASSED")
    print("=" * 50)


if __name__ == "__main__":
    main()
