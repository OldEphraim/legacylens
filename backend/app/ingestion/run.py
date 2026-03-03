"""Orchestrator: discover → chunk → embed → store.

Usage:
    cd backend
    source venv/bin/activate
    python -m app.ingestion.run [--data-dir ../data/gnucobol] [--clear]
"""

import argparse
import functools
import os
import sys
import time

# Force unbuffered output so progress is visible in background runs
print = functools.partial(print, flush=True)

from dotenv import load_dotenv

# Load environment variables from .env.local in project root
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_env_path = os.path.join(_project_root, ".env.local")
load_dotenv(_env_path)

from app.ingestion.discover import discover_files
from app.ingestion.chunker import chunk_file, Chunk
from app.ingestion.embedder import embed_chunks, get_client
from app.ingestion.store import upsert_chunks, get_pinecone_index, delete_all


def run(data_dir: str, clear: bool = False):
    overall_start = time.time()

    # ------------------------------------------------------------------
    # Step 1: Discover files
    # ------------------------------------------------------------------
    print("=" * 60)
    print("STEP 1: Discovering files")
    print("=" * 60)
    t0 = time.time()
    files = discover_files(data_dir)
    print(f"  Found {len(files)} files in {time.time() - t0:.1f}s")

    by_lang = {}
    for fp, lang in files:
        by_lang.setdefault(lang, []).append(fp)
    for lang, paths in sorted(by_lang.items()):
        print(f"    {lang}: {len(paths)} files")

    # ------------------------------------------------------------------
    # Step 2: Chunk all files
    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    print("STEP 2: Chunking files")
    print("=" * 60)
    t0 = time.time()
    all_chunks: list[Chunk] = []
    for i, (fp, lang) in enumerate(files):
        chunks = chunk_file(fp, lang)
        all_chunks.extend(chunks)
        if (i + 1) % 20 == 0 or i + 1 == len(files):
            print(f"  Processed {i + 1}/{len(files)} files, "
                  f"{len(all_chunks)} chunks so far")

    print(f"  Total: {len(all_chunks)} chunks in {time.time() - t0:.1f}s")

    # Print chunk stats
    by_type = {}
    for c in all_chunks:
        by_type.setdefault(c.chunk_type, 0)
        by_type[c.chunk_type] += 1
    for ct, count in sorted(by_type.items()):
        print(f"    {ct}: {count} chunks")

    token_counts = [c.token_estimate for c in all_chunks]
    if token_counts:
        print(f"  Token stats: min={min(token_counts)}, max={max(token_counts)}, "
              f"avg={sum(token_counts)//len(token_counts)}, "
              f"total={sum(token_counts)}")

    # ------------------------------------------------------------------
    # Step 3: Generate embeddings
    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    print("STEP 3: Generating embeddings (Voyage Code 2)")
    print("=" * 60)
    t0 = time.time()
    voyage_client = get_client()
    all_chunks = embed_chunks(all_chunks, client=voyage_client)
    embedded_count = sum(1 for c in all_chunks if c.embedding is not None)
    print(f"  Embedded {embedded_count}/{len(all_chunks)} chunks in {time.time() - t0:.1f}s")

    # ------------------------------------------------------------------
    # Step 4: Store in Pinecone
    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    print("STEP 4: Storing in Pinecone")
    print("=" * 60)
    t0 = time.time()
    index = get_pinecone_index()

    if clear:
        print("  Clearing existing vectors...")
        delete_all(index)
        time.sleep(2)  # Let Pinecone process the delete

    upserted = upsert_chunks(all_chunks, index=index)
    print(f"  Stored {upserted} vectors in {time.time() - t0:.1f}s")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    total_time = time.time() - overall_start
    print()
    print("=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    print(f"  Files discovered:  {len(files)}")
    print(f"  Chunks created:    {len(all_chunks)}")
    print(f"  Embeddings:        {embedded_count}")
    print(f"  Vectors upserted:  {upserted}")
    print(f"  Total time:        {total_time:.1f}s")

    # Verify index stats
    try:
        stats = index.describe_index_stats()
        print(f"  Pinecone index:    {stats.get('total_vector_count', 'N/A')} vectors")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Run the ingestion pipeline")
    parser.add_argument(
        "--data-dir",
        default=os.path.join(_project_root, "data", "gnucobol"),
        help="Path to the GnuCOBOL source directory",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all existing vectors before ingestion",
    )
    args = parser.parse_args()
    run(args.data_dir, clear=args.clear)


if __name__ == "__main__":
    main()
