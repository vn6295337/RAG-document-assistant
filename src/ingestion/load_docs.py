# RAG-document-assistant/ingestion/load_docs.py
"""
Simple markdown document loader for Day-3 ingestion step.

Functions:
- load_markdown_docs(dir_path, ext='.md', max_chars=20000)
  -> returns list of dicts: { "filename", "path", "text", "chars", "words" }

CLI:
> python3 load_docs.py /full/path/to/your/markdown/folder
prints a summary table for each file and exits with code 0.
"""

import os
import glob
import argparse
import re
from typing import List, Dict

def _clean_markdown(text: str) -> str:
    """
    Clean markdown text by removing code blocks, HTML tags, and other non-content elements.
    
    Args:
        text: Raw markdown text to clean
        
    Returns:
        Cleaned text with markdown syntax removed
    """
    # Remove code fences and their contents
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Remove images/links syntax but keep alt/text
    text = re.sub(r"!\[([^\]]*)\]\([^\)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", text)
    # Remove front-matter delimited by --- at top
    text = re.sub(r"^---.*?---\s*", " ", text, flags=re.DOTALL)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

def load_markdown_docs(dir_path: str, ext: str = ".md", max_chars: int = 20000) -> List[Dict]:
    """
    Load markdown files from dir_path (non-recursive). Returns list of metadata+clean text.
    Skips files larger than max_chars (useful to enforce 'under 5 pages' rule roughly).
    
    Args:
        dir_path: Path to directory containing markdown files
        ext: File extension to look for (default: ".md")
        max_chars: Maximum number of characters to accept (default: 20000)
        
    Returns:
        List of document dictionaries with metadata and cleaned text
        
    Raises:
        FileNotFoundError: If directory does not exist
        ValueError: If max_chars is not positive
        OSError: If there are issues reading files
    """
    if max_chars <= 0:
        raise ValueError(f"max_chars must be positive, got {max_chars}")
        
    path = os.path.expanduser(dir_path)
    if not os.path.isdir(path):
        raise FileNotFoundError(f"Directory not found: {path}")

    pattern = os.path.join(path, f"*{ext}")
    files = sorted(glob.glob(pattern))
    docs = []
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                raw = f.read()
        except Exception as e:
            # Skip files that cannot be read
            docs.append({
                "filename": os.path.basename(fp),
                "path": fp,
                "text": None,
                "chars": 0,
                "words": 0,
                "status": f"ERROR_READING_FILE: {str(e)}"
            })
            continue
            
        cleaned = _clean_markdown(raw)
        chars = len(cleaned)
        words = len(cleaned.split())
        if chars == 0:
            # skip empty files
            continue
        if chars > max_chars:
            # skip or trim large files; here we skip and report
            docs.append({
                "filename": os.path.basename(fp),
                "path": fp,
                "text": None,
                "chars": chars,
                "words": words,
                "status": "SKIPPED_TOO_LARGE"
            })
            continue
        docs.append({
            "filename": os.path.basename(fp),
            "path": fp,
            "text": cleaned,
            "chars": chars,
            "words": words,
            "status": "OK"
        })
    return docs

def print_summary(docs: List[Dict]):
    if not docs:
        print("No markdown files found or all were skipped.")
        return
    print(f"{'FILENAME':40} {'STATUS':15} {'CHARS':>8} {'WORDS':>8}")
    print("-" * 80)
    for d in docs:
        name = d.get("filename", "")[:40]
        status = d.get("status", "")
        chars = d.get("chars", 0)
        words = d.get("words", 0)
        print(f"{name:40} {status:15} {chars:8d} {words:8d}")
    ok_count = sum(1 for d in docs if d.get("status") == "OK")
    skipped = len(docs) - ok_count
    print("-" * 80)
    print(f"Total files: {len(docs)}  OK: {ok_count}  Skipped: {skipped}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load and summarize markdown docs for RAG ingestion.")
    parser.add_argument("dir", help="Directory containing markdown (.md) files")
    parser.add_argument("--ext", default=".md", help="File extension to load")
    parser.add_argument("--max-chars", type=int, default=20000, help="Max cleaned characters to accept (default 20k)")
    args = parser.parse_args()

    docs = load_markdown_docs(args.dir, ext=args.ext, max_chars=args.max_chars)
    print_summary(docs)