"""Batch embedding generation using Voyage Code 2."""

import functools
import json
import os
import time
from pathlib import Path
from typing import List, Optional

import voyageai

# Force unbuffered output
print = functools.partial(print, flush=True)

from app.ingestion.chunker import Chunk

MODEL = "voyage-code-2"

# Rate limit config: with payment method, standard limits apply.
# Voyage Code 2 supports batch_size up to 128.
BATCH_SIZE = int(os.environ.get("EMBED_BATCH_SIZE", "100"))
DELAY_BETWEEN_BATCHES = float(os.environ.get("EMBED_DELAY", "0.5"))
MAX_RETRIES = 5

# Progress checkpoint file
CHECKPOINT_DIR = Path(__file__).parent.parent.parent / ".checkpoints"


def get_client() -> voyageai.Client:
    """Create a Voyage AI client using the API key from environment."""
    api_key = os.environ.get("VOYAGE_API_KEY")
    if not api_key:
        raise ValueError("VOYAGE_API_KEY environment variable is not set")
    return voyageai.Client(api_key=api_key)


def _embed_with_retry(
    client: voyageai.Client,
    texts: List[str],
    max_retries: int = MAX_RETRIES,
) -> List[List[float]]:
    """Embed texts with exponential backoff retry on rate limit errors."""
    for attempt in range(max_retries):
        try:
            result = client.embed(texts, model=MODEL, input_type="document")
            return result.embeddings
        except Exception as e:
            if attempt < max_retries - 1:
                wait = min(2 ** attempt * 10, 120)  # 10, 20, 40, 80, 120
                print(f"    Rate limited, waiting {wait}s "
                      f"(attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
            else:
                raise


def _save_checkpoint(checkpoint_path: Path, batch_idx: int, embeddings_map: dict):
    """Save embedding progress to disk."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    with open(checkpoint_path, "w") as f:
        json.dump({"batch_idx": batch_idx, "count": len(embeddings_map)}, f)


def _load_checkpoint(checkpoint_path: Path) -> Optional[int]:
    """Load last completed batch index from checkpoint."""
    if checkpoint_path.exists():
        with open(checkpoint_path) as f:
            data = json.load(f)
            return data.get("batch_idx", 0)
    return None


def embed_chunks(
    chunks: List[Chunk],
    client: voyageai.Client = None,
    batch_size: int = None,
    delay: float = None,
) -> List[Chunk]:
    """Generate embeddings for all chunks using Voyage Code 2.

    Modifies chunks in-place by setting the `embedding` field.
    Returns the same list of chunks.
    """
    if not chunks:
        return chunks

    if client is None:
        client = get_client()

    if batch_size is None:
        batch_size = BATCH_SIZE
    if delay is None:
        delay = DELAY_BETWEEN_BATCHES

    total = len(chunks)
    embedded_count = 0
    failed_count = 0
    start_time = time.time()

    # Check for checkpoint to resume from
    checkpoint_path = CHECKPOINT_DIR / "embed_progress.json"
    resume_from = _load_checkpoint(checkpoint_path)
    start_batch = 0
    if resume_from is not None:
        start_batch = resume_from + 1
        # Count already-embedded chunks
        already_done = min(start_batch * batch_size, total)
        embedded_count = sum(1 for c in chunks[:already_done] if c.embedding is not None)
        if start_batch * batch_size < total:
            print(f"  Resuming from batch {start_batch} "
                  f"(~{already_done} chunks already done)")

    for batch_num, i in enumerate(range(start_batch * batch_size, total, batch_size)):
        batch = chunks[i : i + batch_size]
        texts = [c.content for c in batch]

        # Truncate very long texts to avoid API limits
        texts = [t[:32000] if len(t) > 32000 else t for t in texts]

        try:
            embeddings = _embed_with_retry(client, texts)
            for chunk, vec in zip(batch, embeddings):
                chunk.embedding = vec
            embedded_count += len(batch)
            # Save checkpoint
            current_batch_idx = (i // batch_size)
            _save_checkpoint(checkpoint_path, current_batch_idx, {})
        except Exception as e:
            error_msg = str(e)[:200]
            print(f"  Failed batch {i}-{i+len(batch)}: {error_msg}")
            failed_count += len(batch)

        # Progress logging
        done = min(i + batch_size, total)
        elapsed = time.time() - start_time
        rate = (embedded_count - (start_batch * batch_size if resume_from else 0))
        rate = rate / elapsed if elapsed > 0 else 0
        remaining = total - done
        eta = remaining / rate if rate > 0 else 0
        if done % 100 < batch_size or done >= total:
            print(f"  Progress: {embedded_count}/{total} embedded "
                  f"({failed_count} failed) "
                  f"[{rate:.1f}/s, ETA {eta/60:.0f}m]")

        # Rate limit delay
        if i + batch_size < total:
            time.sleep(delay)

    # Clean up checkpoint on completion
    if checkpoint_path.exists() and failed_count == 0:
        checkpoint_path.unlink()

    return chunks


def embed_query(query: str, client: voyageai.Client = None) -> List[float]:
    """Embed a single query string for retrieval."""
    if client is None:
        client = get_client()
    result = client.embed([query], model=MODEL, input_type="query")
    return result.embeddings[0]
