"""Upsert embedded chunks into Pinecone vector database."""

import os
import time
import uuid
from typing import List

from pinecone import Pinecone
from pinecone import ServerlessSpec

from app.ingestion.chunker import Chunk

BATCH_SIZE = 100  # Pinecone upsert batch size
EMBEDDING_DIM = 1536  # Voyage Code 2 dimension


def get_pinecone_index(create_if_missing: bool = True):
    """Create Pinecone client and return the target index.

    If create_if_missing is True, creates the index if it doesn't exist.
    """
    api_key = os.environ.get("PINECONE_API_KEY")
    index_name = os.environ.get("PINECONE_INDEX_NAME", "legacylens")
    if not api_key:
        raise ValueError("PINECONE_API_KEY environment variable is not set")

    pc = Pinecone(api_key=api_key)

    # Check if index exists, create if not
    if create_if_missing:
        existing = [idx.name for idx in pc.list_indexes()]
        if index_name not in existing:
            print(f"  Creating Pinecone index '{index_name}' (dim={EMBEDDING_DIM})...")
            pc.create_index(
                name=index_name,
                dimension=EMBEDDING_DIM,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            # Wait for index to be ready
            while not pc.describe_index(index_name).status.get("ready", False):
                print("  Waiting for index to be ready...")
                time.sleep(2)
            print(f"  Index '{index_name}' created and ready.")

    index = pc.Index(index_name)
    return index


def upsert_chunks(chunks: List[Chunk], index=None) -> int:
    """Upsert embedded chunks into Pinecone.

    Returns the number of vectors successfully upserted.
    """
    if index is None:
        index = get_pinecone_index()

    # Filter to only chunks that have embeddings
    valid = [c for c in chunks if c.embedding is not None]
    if not valid:
        print("  No chunks with embeddings to upsert.")
        return 0

    total = len(valid)
    upserted = 0

    for i in range(0, total, BATCH_SIZE):
        batch = valid[i : i + BATCH_SIZE]
        vectors = []
        for chunk in batch:
            vec_id = str(uuid.uuid4())
            metadata = {
                "file_path": chunk.file_path,
                "line_start": chunk.line_start,
                "line_end": chunk.line_end,
                "chunk_type": chunk.chunk_type,
                "language": chunk.language,
                "content": chunk.content[:40000],  # Pinecone metadata limit
            }
            if chunk.function_name:
                metadata["function_name"] = chunk.function_name
            if chunk.parent_section:
                metadata["parent_section"] = chunk.parent_section
            if chunk.parent_division:
                metadata["parent_division"] = chunk.parent_division

            vectors.append({
                "id": vec_id,
                "values": chunk.embedding,
                "metadata": metadata,
            })

        try:
            index.upsert(vectors=vectors)
            upserted += len(batch)
        except Exception as e:
            print(f"  Error upserting batch {i}-{i+len(batch)}: {e}")
            continue

        if (i + BATCH_SIZE) % 500 == 0 or i + BATCH_SIZE >= total:
            print(f"  Upserted {min(i + BATCH_SIZE, total)}/{total} vectors")

    return upserted


def delete_all(index=None):
    """Delete all vectors from the index (use before re-ingestion)."""
    if index is None:
        index = get_pinecone_index()
    try:
        index.delete(delete_all=True)
        print("  Deleted all vectors from index.")
    except Exception as e:
        # Serverless indexes may return 404 if namespace is empty
        if "not found" in str(e).lower() or "404" in str(e):
            print("  Index is already empty, nothing to delete.")
        else:
            raise
