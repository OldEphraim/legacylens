"""Syntax-aware chunking for COBOL, C, config, and test files."""

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Chunk:
    """A chunk of source code with metadata."""
    content: str
    file_path: str
    line_start: int
    line_end: int
    chunk_type: str  # paragraph, section, division, data_definition, comment_block, function, test_case, config
    language: str  # cobol, c, config, test
    function_name: Optional[str] = None
    parent_section: Optional[str] = None
    parent_division: Optional[str] = None
    embedding: Optional[List[float]] = field(default=None, repr=False)

    @property
    def token_estimate(self) -> int:
        """Rough token count: ~4 chars per token."""
        return len(self.content) // 4


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


# ---------------------------------------------------------------------------
# COBOL chunking
# ---------------------------------------------------------------------------

# COBOL paragraph: starts at column 8+ (after 6-7 char margin), uppercase
# alphanumeric with hyphens, ends with period. Could also have a SECTION keyword.
_COBOL_PARAGRAPH_RE = re.compile(
    r"^       [A-Z][A-Z0-9-]*\s*\.\s*$"
)

_COBOL_SECTION_RE = re.compile(
    r"^       [A-Z][A-Z0-9-]*\s+SECTION\s*\.\s*$", re.IGNORECASE
)

_COBOL_DIVISION_RE = re.compile(
    r"^\s+(IDENTIFICATION|ENVIRONMENT|DATA|PROCEDURE)\s+DIVISION", re.IGNORECASE
)

_COBOL_DATA_SECTION_RE = re.compile(
    r"^\s+[A-Z][A-Z0-9-]*\s+SECTION\s*\.\s*$", re.IGNORECASE
)


def _chunk_cobol(lines: List[str], file_path: str) -> List[Chunk]:
    """Chunk COBOL files on paragraph/section boundaries."""
    chunks: List[Chunk] = []
    current_lines: List[str] = []
    current_start = 1
    current_name: Optional[str] = None
    current_type = "code"
    current_section: Optional[str] = None
    current_division: Optional[str] = None
    in_data_division = False
    in_procedure_division = False

    def flush():
        if current_lines:
            text = "\n".join(current_lines)
            if text.strip():
                chunks.append(Chunk(
                    content=text,
                    file_path=file_path,
                    line_start=current_start,
                    line_end=current_start + len(current_lines) - 1,
                    chunk_type=current_type,
                    language="cobol",
                    function_name=current_name,
                    parent_section=current_section,
                    parent_division=current_division,
                ))

    for i, line in enumerate(lines, start=1):
        # Check for division boundaries
        div_match = _COBOL_DIVISION_RE.match(line)
        if div_match:
            flush()
            current_division = div_match.group(1).upper()
            in_data_division = current_division == "DATA"
            in_procedure_division = current_division == "PROCEDURE"
            current_lines = [line]
            current_start = i
            current_name = current_division + " DIVISION"
            current_type = "division"
            current_section = None
            continue

        # Check for section boundaries
        sec_match = _COBOL_SECTION_RE.match(line)
        if sec_match:
            flush()
            # Extract section name
            stripped = line.strip().rstrip(".")
            sec_name = stripped.replace(" SECTION", "").replace(" section", "").strip()
            current_section = sec_name
            current_lines = [line]
            current_start = i
            current_name = sec_name
            current_type = "section"
            continue

        # In procedure division, check for paragraph boundaries
        if in_procedure_division and _COBOL_PARAGRAPH_RE.match(line):
            flush()
            para_name = line.strip().rstrip(".")
            current_lines = [line]
            current_start = i
            current_name = para_name
            current_type = "paragraph"
            continue

        # In data division, check for data section boundaries (WORKING-STORAGE, etc.)
        if in_data_division and _COBOL_DATA_SECTION_RE.match(line):
            flush()
            stripped = line.strip().rstrip(".")
            sec_name = stripped.replace(" SECTION", "").replace(" section", "").strip()
            current_section = sec_name
            current_lines = [line]
            current_start = i
            current_name = sec_name
            current_type = "data_definition"
            continue

        current_lines.append(line)

    flush()
    return chunks


# ---------------------------------------------------------------------------
# C chunking
# ---------------------------------------------------------------------------

# Pattern for a function name at column 0: identifier followed by space/parens
# GnuCOBOL style: return type on previous line, function name at column 0
_C_FUNC_NAME_RE = re.compile(r"^([a-zA-Z_]\w*)\s*\(")

# Keywords that appear at column 0 but are NOT function definitions
_C_NON_FUNC_KEYWORDS = frozenset([
    "if", "else", "while", "for", "switch", "case", "return", "do",
    "typedef", "extern", "struct", "enum", "union", "static", "const",
    "volatile", "unsigned", "signed", "void", "int", "char", "short",
    "long", "float", "double", "sizeof", "goto", "break", "continue",
    "default", "register", "inline", "include", "define", "undef",
    "ifdef", "ifndef", "endif", "elif", "error", "pragma",
])


def _is_c_func_start(lines: List[str], idx: int) -> Optional[str]:
    """Check if lines[idx] is the start of a C function definition.

    Returns the function name if it is, None otherwise.
    GnuCOBOL pattern: return type on line above, function name at col 0,
    opening brace on same line or within next few lines.
    """
    line = lines[idx]
    if not line or line[0] == ' ' or line[0] == '\t' or line[0] == '#':
        return None

    match = _C_FUNC_NAME_RE.match(line)
    if not match:
        return None

    name = match.group(1)
    if name in _C_NON_FUNC_KEYWORDS:
        return None

    # Look ahead for opening brace within next 5 lines
    for j in range(idx, min(idx + 5, len(lines))):
        if "{" in lines[j]:
            return name
        # If we hit a semicolon first, it's a declaration not definition
        if ";" in lines[j] and "{" not in lines[j]:
            return None

    return None


def _chunk_c(lines: List[str], file_path: str) -> List[Chunk]:
    """Chunk C files on function boundaries using brace tracking."""
    chunks: List[Chunk] = []

    # First pass: find all function start line indices
    func_starts: List[tuple] = []  # (line_idx_0based, func_name)
    for idx in range(len(lines)):
        name = _is_c_func_start(lines, idx)
        if name:
            func_starts.append((idx, name))

    if not func_starts:
        # No functions found — treat as one chunk
        text = "\n".join(lines)
        if text.strip():
            chunks.append(Chunk(
                content=text,
                file_path=file_path,
                line_start=1,
                line_end=len(lines),
                chunk_type="code",
                language="c",
            ))
        return chunks

    # Include type signature lines above the function name
    # (walk backwards from function name to find return type)
    def find_sig_start(func_idx: int) -> int:
        """Walk backwards to include the return type line(s)."""
        start = func_idx
        for k in range(func_idx - 1, max(func_idx - 4, -1), -1):
            prev = lines[k].strip()
            if not prev or prev.startswith("/*") or prev.startswith("*") or prev.endswith("*/"):
                break
            # Return type lines: start with static, const, type names, etc.
            if prev.startswith(("static", "COB_", "const", "unsigned", "signed",
                                "void", "int", "char", "long", "short", "float",
                                "double", "size_t", "cob_", "FILE", "enum", "struct")):
                start = k
            else:
                break
        return start

    # Build chunks: preamble, then each function with inter-function gaps
    prev_end = 0  # 0-based exclusive end of previous chunk

    for i, (func_idx, func_name) in enumerate(func_starts):
        sig_start = find_sig_start(func_idx)

        # Emit any code between previous function end and this function's signature
        if sig_start > prev_end:
            gap_lines = lines[prev_end:sig_start]
            text = "\n".join(gap_lines)
            if text.strip():
                chunks.append(Chunk(
                    content=text,
                    file_path=file_path,
                    line_start=prev_end + 1,
                    line_end=sig_start,
                    chunk_type="code",
                    language="c",
                ))

        # Find function end by tracking braces from the opening {
        brace_depth = 0
        func_end = func_idx
        found_open = False
        for j in range(func_idx, len(lines)):
            brace_depth += lines[j].count("{") - lines[j].count("}")
            if brace_depth > 0:
                found_open = True
            if found_open and brace_depth <= 0:
                func_end = j + 1  # exclusive
                break
        else:
            func_end = len(lines)

        func_lines = lines[sig_start:func_end]
        text = "\n".join(func_lines)
        if text.strip():
            chunks.append(Chunk(
                content=text,
                file_path=file_path,
                line_start=sig_start + 1,
                line_end=func_end,
                chunk_type="function",
                language="c",
                function_name=func_name,
            ))
        prev_end = func_end

    # Trailing code after last function
    if prev_end < len(lines):
        tail = lines[prev_end:]
        text = "\n".join(tail)
        if text.strip():
            chunks.append(Chunk(
                content=text,
                file_path=file_path,
                line_start=prev_end + 1,
                line_end=len(lines),
                chunk_type="code",
                language="c",
            ))
    return chunks


# ---------------------------------------------------------------------------
# Fixed-size chunking (config, test, def files)
# ---------------------------------------------------------------------------

def _chunk_fixed_size(
    lines: List[str],
    file_path: str,
    language: str,
    chunk_size_tokens: int = 400,
    overlap_tokens: int = 200,
) -> List[Chunk]:
    """Chunk files into fixed-size pieces with token overlap."""
    chunk_type = "test" if language == "test" else "config"
    chunks: List[Chunk] = []

    # Build chunks by accumulating lines up to chunk_size_tokens
    current_lines: List[str] = []
    current_tokens = 0
    current_start = 1

    for i, line in enumerate(lines, start=1):
        line_tokens = _estimate_tokens(line)
        if current_tokens + line_tokens > chunk_size_tokens and current_lines:
            text = "\n".join(current_lines)
            chunks.append(Chunk(
                content=text,
                file_path=file_path,
                line_start=current_start,
                line_end=current_start + len(current_lines) - 1,
                chunk_type=chunk_type,
                language=language,
            ))
            # Calculate overlap: walk backwards from end to find overlap point
            overlap_accumulated = 0
            overlap_start_idx = len(current_lines)
            for j in range(len(current_lines) - 1, -1, -1):
                overlap_accumulated += _estimate_tokens(current_lines[j])
                if overlap_accumulated >= overlap_tokens:
                    overlap_start_idx = j
                    break

            overlap_lines = current_lines[overlap_start_idx:]
            current_start = current_start + overlap_start_idx
            current_lines = overlap_lines[:]
            current_tokens = sum(_estimate_tokens(l) for l in current_lines)

        current_lines.append(line)
        current_tokens += line_tokens

    if current_lines:
        text = "\n".join(current_lines)
        if text.strip():
            chunks.append(Chunk(
                content=text,
                file_path=file_path,
                line_start=current_start,
                line_end=current_start + len(current_lines) - 1,
                chunk_type=chunk_type,
                language=language,
            ))

    return chunks


# ---------------------------------------------------------------------------
# Test file chunking (try to split on AT_SETUP boundaries first)
# ---------------------------------------------------------------------------

_AT_SETUP_RE = re.compile(r"^AT_SETUP\(", re.IGNORECASE)


def _chunk_test(lines: List[str], file_path: str) -> List[Chunk]:
    """Chunk .at test files on AT_SETUP boundaries, with fixed-size fallback."""
    # Try to find test case boundaries
    boundaries = []
    for i, line in enumerate(lines):
        if _AT_SETUP_RE.match(line.strip()):
            boundaries.append(i)

    if len(boundaries) < 2:
        # Not enough structure, use fixed-size
        return _chunk_fixed_size(lines, file_path, "test")

    chunks: List[Chunk] = []
    # Add preamble if any
    if boundaries[0] > 0:
        preamble = lines[:boundaries[0]]
        text = "\n".join(preamble)
        if text.strip():
            chunks.append(Chunk(
                content=text,
                file_path=file_path,
                line_start=1,
                line_end=boundaries[0],
                chunk_type="test",
                language="test",
                function_name="preamble",
            ))

    # Each test case
    for idx, start in enumerate(boundaries):
        end = boundaries[idx + 1] if idx + 1 < len(boundaries) else len(lines)
        test_lines = lines[start:end]
        text = "\n".join(test_lines)
        # Extract test name from AT_SETUP([...])
        name_match = re.search(r"AT_SETUP\(\[(.+?)\]", test_lines[0])
        test_name = name_match.group(1) if name_match else None

        if text.strip():
            chunk = Chunk(
                content=text,
                file_path=file_path,
                line_start=start + 1,
                line_end=start + len(test_lines),
                chunk_type="test_case",
                language="test",
                function_name=test_name,
            )
            # If this test case is too large, split it further
            if chunk.token_estimate > 800:
                sub_chunks = _chunk_fixed_size(test_lines, file_path, "test")
                for sc in sub_chunks:
                    sc.line_start += start
                    sc.line_end += start
                    sc.function_name = test_name
                    sc.chunk_type = "test_case"
                chunks.extend(sub_chunks)
            else:
                chunks.append(chunk)

    return chunks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def chunk_file(file_path: str, language: str) -> List[Chunk]:
    """Chunk a single file using the appropriate strategy.

    Args:
        file_path: Path to the source file.
        language: One of "cobol", "c", "config", "test".

    Returns:
        List of Chunk objects with metadata.
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except Exception as e:
        print(f"  Warning: could not read {file_path}: {e}")
        return []

    if not lines:
        return []

    if language == "cobol":
        chunks = _chunk_cobol(lines, file_path)
    elif language == "c":
        chunks = _chunk_c(lines, file_path)
    elif language == "test":
        chunks = _chunk_test(lines, file_path)
    else:
        chunks = _chunk_fixed_size(lines, file_path, language)

    # Merge tiny chunks (<50 tokens) with adjacent chunks
    chunks = _merge_small_chunks(chunks, min_tokens=50)

    # Split oversized chunks (>800 tokens) using fixed-size fallback
    chunks = _split_oversized_chunks(chunks, max_tokens=800)

    return chunks


def _split_oversized_chunks(chunks: List[Chunk], max_tokens: int = 800) -> List[Chunk]:
    """Split chunks that exceed max_tokens using fixed-size splitting."""
    result: List[Chunk] = []
    for chunk in chunks:
        if chunk.token_estimate > max_tokens:
            sub_lines = chunk.content.splitlines()
            sub_chunks = _chunk_fixed_size(
                sub_lines, chunk.file_path, chunk.language,
                chunk_size_tokens=400, overlap_tokens=100,
            )
            for sc in sub_chunks:
                sc.line_start += chunk.line_start - 1
                sc.line_end += chunk.line_start - 1
                sc.chunk_type = chunk.chunk_type
                sc.function_name = chunk.function_name
                sc.parent_section = chunk.parent_section
                sc.parent_division = chunk.parent_division
            result.extend(sub_chunks)
        else:
            result.append(chunk)
    return result


def _merge_small_chunks(chunks: List[Chunk], min_tokens: int = 50) -> List[Chunk]:
    """Merge chunks smaller than min_tokens into adjacent chunks."""
    if len(chunks) <= 1:
        return chunks

    merged: List[Chunk] = []
    for chunk in chunks:
        if merged and chunk.token_estimate < min_tokens:
            # Merge with previous chunk
            prev = merged[-1]
            merged[-1] = Chunk(
                content=prev.content + "\n" + chunk.content,
                file_path=prev.file_path,
                line_start=prev.line_start,
                line_end=chunk.line_end,
                chunk_type=prev.chunk_type,
                language=prev.language,
                function_name=prev.function_name or chunk.function_name,
                parent_section=prev.parent_section or chunk.parent_section,
                parent_division=prev.parent_division or chunk.parent_division,
            )
        elif chunk.token_estimate < min_tokens and not merged:
            # First chunk is tiny, just add it — it'll merge with next
            merged.append(chunk)
        else:
            # Check if previous chunk is tiny and should be merged forward
            if merged and merged[-1].token_estimate < min_tokens:
                prev = merged[-1]
                merged[-1] = Chunk(
                    content=prev.content + "\n" + chunk.content,
                    file_path=chunk.file_path,
                    line_start=prev.line_start,
                    line_end=chunk.line_end,
                    chunk_type=chunk.chunk_type,
                    language=chunk.language,
                    function_name=chunk.function_name or prev.function_name,
                    parent_section=chunk.parent_section or prev.parent_section,
                    parent_division=chunk.parent_division or prev.parent_division,
                )
            else:
                merged.append(chunk)

    return merged


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m app.ingestion.chunker <file_path> [language]")
        sys.exit(1)

    fp = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) > 2 else "cobol"
    chunks = chunk_file(fp, lang)
    print(f"Produced {len(chunks)} chunks from {fp}:")
    for c in chunks:
        print(f"  L{c.line_start}-{c.line_end} [{c.chunk_type}] "
              f"name={c.function_name} ~{c.token_estimate} tokens")
