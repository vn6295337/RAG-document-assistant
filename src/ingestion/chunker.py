# RAG-document-assistant/ingestion/chunker.py
"""
Text chunking utility for RAG ingestion.
Inputs: list of docs from load_docs.py
Output: list of chunks with metadata
"""

from typing import List, Dict

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


if __name__ == "__main__":
    # Minimal test
    sample = "This is a test text " * 200
    chunks = chunk_text(sample, max_tokens=50, overlap=10)
    print(f"Generated {len(chunks)} chunks")
    print(chunks[0])