"""LLM answer generation using Claude with retrieved context."""

import os
from typing import AsyncIterator, List

import anthropic

from app.retrieval.search import SearchResult

MODEL = "claude-sonnet-4-5-20250929"

SYSTEM_PROMPT = (
    "You are a COBOL and C code expert analyzing the GnuCOBOL compiler codebase. "
    "Given code chunks retrieved from the codebase, answer the user's question. "
    "Always cite specific file paths and line numbers. "
    "If the retrieved chunks don't contain enough information to answer fully, "
    "say so honestly rather than guessing."
)


def _format_context(sources: List[SearchResult]) -> str:
    """Format retrieved chunks into a context string for the LLM."""
    parts = []
    for i, src in enumerate(sources, 1):
        header = f"[{src.file_path}:{src.line_start}-{src.line_end}]"
        type_info = src.chunk_type
        if src.function_name:
            type_info += f": {src.function_name}"
        header += f" ({type_info})"

        parts.append(f"--- Source {i} (score: {src.score:.3f}) ---\n{header}\n{src.content}")

    return "\n\n".join(parts)


def _build_user_message(query: str, sources: List[SearchResult]) -> str:
    """Build the user message with query and context."""
    context = _format_context(sources)
    return (
        f"Question: {query}\n\n"
        f"Retrieved code chunks from the GnuCOBOL codebase:\n\n{context}"
    )


class AnswerGenerator:
    """Generates answers using Claude with retrieved code context."""

    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.async_client = anthropic.AsyncAnthropic(api_key=api_key)

    def generate(self, query: str, sources: List[SearchResult]) -> str:
        """Generate a complete answer (non-streaming)."""
        message = self.client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": _build_user_message(query, sources)}
            ],
        )
        return message.content[0].text

    async def generate_stream(
        self, query: str, sources: List[SearchResult]
    ) -> AsyncIterator[str]:
        """Generate an answer with streaming tokens."""
        async with self.async_client.messages.stream(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": _build_user_message(query, sources)}
            ],
        ) as stream:
            async for text in stream.text_stream:
                yield text
