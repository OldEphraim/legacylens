"""Semantic search over the GnuCOBOL codebase via Pinecone."""

import os
import time
from dataclasses import dataclass
from typing import List, Optional

import voyageai
from pinecone import Pinecone

VOYAGE_MODEL = "voyage-code-2"


@dataclass
class SearchResult:
    """A single search result with chunk content and metadata."""
    content: str
    file_path: str
    line_start: int
    line_end: int
    chunk_type: str
    language: str
    function_name: Optional[str]
    parent_section: Optional[str]
    parent_division: Optional[str]
    score: float

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "chunk_type": self.chunk_type,
            "language": self.language,
            "function_name": self.function_name,
            "parent_section": self.parent_section,
            "parent_division": self.parent_division,
            "score": self.score,
        }


class SearchEngine:
    """Handles query embedding and Pinecone similarity search."""

    def __init__(self):
        voyage_key = os.environ.get("VOYAGE_API_KEY")
        pinecone_key = os.environ.get("PINECONE_API_KEY")
        index_name = os.environ.get("PINECONE_INDEX_NAME", "legacylens")

        if not voyage_key:
            raise ValueError("VOYAGE_API_KEY not set")
        if not pinecone_key:
            raise ValueError("PINECONE_API_KEY not set")

        self.voyage = voyageai.Client(api_key=voyage_key)
        pc = Pinecone(api_key=pinecone_key)
        self.index = pc.Index(index_name)

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """Embed query and search Pinecone for similar chunks.

        Args:
            query: Natural language question about the codebase.
            top_k: Number of results to return.

        Returns:
            List of SearchResult ordered by descending similarity.
        """
        # Embed query with same model used during ingestion
        result = self.voyage.embed([query], model=VOYAGE_MODEL, input_type="query")
        query_vec = result.embeddings[0]

        # Query Pinecone
        matches = self.index.query(
            vector=query_vec,
            top_k=top_k,
            include_metadata=True,
        )

        results = []
        for match in matches.matches:
            meta = match.metadata or {}
            results.append(SearchResult(
                content=meta.get("content", ""),
                file_path=meta.get("file_path", ""),
                line_start=int(meta.get("line_start", 0)),
                line_end=int(meta.get("line_end", 0)),
                chunk_type=meta.get("chunk_type", ""),
                language=meta.get("language", ""),
                function_name=meta.get("function_name"),
                parent_section=meta.get("parent_section"),
                parent_division=meta.get("parent_division"),
                score=match.score,
            ))

        return results

    def get_index_stats(self) -> dict:
        """Return Pinecone index statistics."""
        stats = self.index.describe_index_stats()
        return {
            "total_vector_count": stats.get("total_vector_count", 0),
            "dimension": stats.get("dimension", 0),
        }
