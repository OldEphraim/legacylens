"""File discovery for GnuCOBOL codebase ingestion."""

import os
from pathlib import Path
from typing import List, Tuple

# Extension to language mapping
EXTENSION_MAP = {
    ".cob": "cobol",
    ".cbl": "cobol",
    ".cpy": "cobol",
    ".c": "c",
    ".h": "c",
    ".conf": "config",
    ".at": "test",
    ".def": "config",
}

TARGET_EXTENSIONS = set(EXTENSION_MAP.keys())


def discover_files(root_dir: str) -> List[Tuple[str, str]]:
    """Recursively find all target files in root_dir.

    Returns list of (file_path, language) tuples where language is
    one of: "cobol", "c", "config", "test".
    """
    root = Path(root_dir)
    if not root.exists():
        raise FileNotFoundError(f"Directory not found: {root_dir}")

    results: List[Tuple[str, str]] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for filename in sorted(filenames):
            ext = Path(filename).suffix.lower()
            if ext in TARGET_EXTENSIONS:
                full_path = os.path.join(dirpath, filename)
                language = EXTENSION_MAP[ext]
                results.append((full_path, language))

    results.sort(key=lambda x: x[0])
    return results


if __name__ == "__main__":
    import sys

    root = sys.argv[1] if len(sys.argv) > 1 else "data/gnucobol"
    files = discover_files(root)
    print(f"Found {len(files)} files:")
    by_lang = {}
    for fp, lang in files:
        by_lang.setdefault(lang, []).append(fp)
    for lang, paths in sorted(by_lang.items()):
        print(f"  {lang}: {len(paths)} files")
