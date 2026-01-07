# RAG-document-assistant/ingestion/chunker.py
"""
Text chunking utility for RAG ingestion.
Inputs: list of docs from load_docs.py or docling_loader.py
Output: list of chunks with metadata

Supports:
- Simple character-based chunking (legacy)
- Structure-aware chunking using Docling elements
"""

from typing import List, Dict, Optional, Any

def chunk_text(
    text: str,
    max_tokens: int = 300,
    overlap: int = 50
) -> List[str]:
    """
    Simple whitespace-based chunking.
    Assumes ~1 token ≈ 4 chars (rough approximation).
    
    Args:
        text: Text to chunk
        max_tokens: Maximum tokens per chunk
        overlap: Number of tokens to overlap between chunks
        
    Returns:
        List of text chunks
        
    Raises:
        ValueError: If max_tokens or overlap are not positive
    """
    if max_tokens <= 0:
        raise ValueError(f"max_tokens must be positive, got {max_tokens}")
    if overlap < 0:
        raise ValueError(f"overlap must be non-negative, got {overlap}")
    if overlap >= max_tokens:
        raise ValueError(f"overlap ({overlap}) must be less than max_tokens ({max_tokens})")
        
    approx_chars = max_tokens * 4
    approx_overlap = overlap * 4

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + approx_chars
        chunk = text[start:end]

        if chunk.strip():
            chunks.append(chunk.strip())

        # next window with overlap
        start = start + approx_chars - approx_overlap
        # Ensure we don't go backwards
        if start <= 0:
            start = approx_chars

    return chunks


def chunk_documents(docs: List[Dict], max_tokens: int = 300, overlap: int = 50):
    """
    Chunk a list of documents into smaller pieces for embedding.
    
    Args:
        docs: List of document dictionaries with 'filename' and 'text' keys
        max_tokens: Maximum tokens per chunk
        overlap: Number of tokens to overlap between chunks
        
    Returns:
        List of chunk dictionaries with filename, chunk_id, text, and chars keys
        
    Raises:
        TypeError: If docs is not a list or contains non-dict elements
        KeyError: If required keys are missing from document dictionaries
    """
    if not isinstance(docs, list):
        raise TypeError("docs must be a list")
        
    all_chunks = []
    for d in docs:
        if not isinstance(d, dict):
            raise TypeError("Each document must be a dictionary")
            
        if d.get("status") != "OK":
            continue

        filename = d["filename"]
        text = d["text"]
        raw_chunks = chunk_text(text, max_tokens=max_tokens, overlap=overlap)

        for i, ch in enumerate(raw_chunks):
            all_chunks.append({
                "filename": filename,
                "chunk_id": i,
                "text": ch,
                "chars": len(ch)
            })
    return all_chunks


def chunk_by_structure(
    elements: List[Any],
    max_tokens: int = 300,
    overlap: int = 50,
    keep_tables_intact: bool = True,
    include_heading_context: bool = True
) -> List[Dict]:
    """
    Structure-aware chunking using Docling document elements.

    Groups content by semantic boundaries (headings, tables) rather than
    arbitrary character counts. Falls back to character-based splitting
    for oversized elements.

    Args:
        elements: List of DocumentElement objects from docling_loader
        max_tokens: Maximum tokens per chunk (approx 4 chars/token)
        overlap: Token overlap for split elements
        keep_tables_intact: Keep tables as single chunks even if large
        include_heading_context: Prepend parent heading to chunks

    Returns:
        List of chunk dicts with element_type and section metadata
    """
    if not elements:
        return []

    max_chars = max_tokens * 4
    chunks = []
    current_heading = ""
    current_section = []
    current_chars = 0

    def flush_section():
        """Flush accumulated section content as a chunk."""
        nonlocal current_section, current_chars
        if not current_section:
            return

        combined_text = "\n\n".join(el.text for el in current_section)
        if combined_text.strip():
            # Prepend heading context if available
            if include_heading_context and current_heading:
                combined_text = f"## {current_heading}\n\n{combined_text}"

            chunks.append({
                "text": combined_text.strip(),
                "chars": len(combined_text),
                "element_type": "section",
                "section_heading": current_heading,
                "element_count": len(current_section)
            })

        current_section = []
        current_chars = 0

    for element in elements:
        el_type = getattr(element, "element_type", "paragraph")
        el_text = getattr(element, "text", str(element))
        el_chars = len(el_text)

        # Handle headings - start new section
        if el_type == "heading":
            flush_section()
            current_heading = el_text
            continue

        # Handle tables - keep intact if configured
        if el_type == "table" and keep_tables_intact:
            flush_section()
            table_text = el_text
            if include_heading_context and current_heading:
                table_text = f"## {current_heading}\n\n{el_text}"

            chunks.append({
                "text": table_text.strip(),
                "chars": len(table_text),
                "element_type": "table",
                "section_heading": current_heading,
                "element_count": 1
            })
            continue

        # Check if adding this element exceeds limit
        if current_chars + el_chars > max_chars and current_section:
            flush_section()

        # Handle oversized single elements
        if el_chars > max_chars:
            flush_section()
            # Split large element using character-based chunking
            sub_chunks = chunk_text(el_text, max_tokens=max_tokens, overlap=overlap)
            for i, sub_text in enumerate(sub_chunks):
                prefix = ""
                if include_heading_context and current_heading:
                    prefix = f"## {current_heading}\n\n"
                chunks.append({
                    "text": f"{prefix}{sub_text}".strip(),
                    "chars": len(sub_text) + len(prefix),
                    "element_type": f"{el_type}_split",
                    "section_heading": current_heading,
                    "split_index": i,
                    "element_count": 1
                })
            continue

        # Accumulate element in current section
        current_section.append(element)
        current_chars += el_chars

    # Flush remaining content
    flush_section()

    return chunks


def chunk_documents_with_structure(
    docs: List[Dict],
    max_tokens: int = 300,
    overlap: int = 50,
    keep_tables_intact: bool = True,
    use_structure: bool = True
) -> List[Dict]:
    """
    Chunk documents using structure-aware or legacy chunking.

    Args:
        docs: List of document dicts (from docling_loader or load_docs)
        max_tokens: Maximum tokens per chunk
        overlap: Token overlap between chunks
        keep_tables_intact: Keep tables as single chunks
        use_structure: Use structure-aware chunking if elements available

    Returns:
        List of chunk dicts with metadata
    """
    if not isinstance(docs, list):
        raise TypeError("docs must be a list")

    all_chunks = []

    for d in docs:
        if not isinstance(d, dict):
            raise TypeError("Each document must be a dictionary")

        status = d.get("status", "")
        if status != "OK":
            continue

        filename = d.get("filename", "unknown")
        elements = d.get("elements", [])

        # Use structure-aware chunking if elements available
        if use_structure and elements:
            raw_chunks = chunk_by_structure(
                elements,
                max_tokens=max_tokens,
                overlap=overlap,
                keep_tables_intact=keep_tables_intact
            )
            for i, ch in enumerate(raw_chunks):
                all_chunks.append({
                    "filename": filename,
                    "chunk_id": i,
                    "text": ch["text"],
                    "chars": ch["chars"],
                    "element_type": ch.get("element_type", "section"),
                    "section_heading": ch.get("section_heading", ""),
                    "format": d.get("format", ""),
                    "page_count": d.get("page_count", 0)
                })
        else:
            # Fallback to legacy text-based chunking
            text = d.get("text", "")
            if not text:
                continue

            raw_chunks = chunk_text(text, max_tokens=max_tokens, overlap=overlap)
            for i, ch in enumerate(raw_chunks):
                all_chunks.append({
                    "filename": filename,
                    "chunk_id": i,
                    "text": ch,
                    "chars": len(ch),
                    "element_type": "text",
                    "section_heading": "",
                    "format": d.get("format", ".md"),
                    "page_count": 0
                })

    return all_chunks


if __name__ == "__main__":
    # Minimal test
    sample = "This is a test text " * 200
    chunks = chunk_text(sample, max_tokens=50, overlap=10)
    print(f"Generated {len(chunks)} chunks")
    print(chunks[0])