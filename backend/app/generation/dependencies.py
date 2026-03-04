"""Parse dependency references from COBOL and C code chunks."""

import re
from typing import List

# COBOL: PERFORM paragraph-name, COPY copybook-name
_COBOL_PERFORM_RE = re.compile(
    r"\bPERFORM\s+([A-Z][A-Z0-9-]+)", re.IGNORECASE
)
_COBOL_COPY_RE = re.compile(
    r"\bCOPY\s+([A-Za-z0-9_-]+)", re.IGNORECASE
)
_COBOL_CALL_RE = re.compile(
    r"\bCALL\s+['\"]([^'\"]+)['\"]", re.IGNORECASE
)

# C: function calls — identifier followed by (
# Exclude common keywords and control flow
_C_KEYWORDS = {
    "if", "else", "for", "while", "do", "switch", "case", "return",
    "sizeof", "typedef", "struct", "enum", "union", "static", "extern",
    "const", "void", "int", "char", "long", "short", "unsigned", "signed",
    "float", "double", "break", "continue", "goto", "default", "volatile",
    "register", "auto", "inline", "restrict", "NULL", "defined",
}
_C_CALL_RE = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")


def parse_cobol_references(content: str) -> List[str]:
    """Extract paragraph/section names referenced via PERFORM, COPY, CALL."""
    refs = set()
    for m in _COBOL_PERFORM_RE.finditer(content):
        refs.add(m.group(1).upper())
    for m in _COBOL_COPY_RE.finditer(content):
        refs.add(m.group(1))
    for m in _COBOL_CALL_RE.finditer(content):
        refs.add(m.group(1))
    return sorted(refs)


def parse_c_references(content: str) -> List[str]:
    """Extract function call names from C code."""
    refs = set()
    for m in _C_CALL_RE.finditer(content):
        name = m.group(1)
        if name.lower() not in _C_KEYWORDS and not name.startswith("__"):
            refs.add(name)
    return sorted(refs)


def parse_references(content: str, language: str) -> List[str]:
    """Parse references from a chunk based on its language."""
    if language == "cobol":
        return parse_cobol_references(content)
    elif language == "c":
        return parse_c_references(content)
    return []
