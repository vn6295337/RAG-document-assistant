"""API routes for RAG application."""

import os
import shutil
import httpx
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from src.api.models import (
    QueryRequest, QueryResponse,
    IngestRequest, IngestResponse,
    SyncRequest, SyncResponse,
    StatusResponse, Citation
)
from src.orchestrator import orchestrate_query, set_chunks_path, orchestrate_zero_storage
from src.ingestion.api import ingest_from_directory, sync_to_pinecone, get_index_status
from src.retrieval.keyword_search import reload_index

router = APIRouter()

# Upload directory for user documents
if os.getenv("ENV") == "production":
    UPLOAD_DIR = Path("/tmp/uploads")
else:
    UPLOAD_DIR = Path("uploads")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "environment": os.getenv("ENV", "development")}


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Execute RAG query and return answer with citations."""
    try:
        result = orchestrate_query(
            query=request.query,
            top_k=request.top_k,
            use_hybrid=request.use_hybrid,
            use_reranking=request.use_reranking
        )

        # Convert sources/citations to Citation models
        sources = [
            Citation(
                id=s.get("id"),
                score=s.get("score", 0.0),
                snippet=s.get("snippet", "")
            )
            for s in result.get("sources", [])
        ]

        citations = [
            Citation(
                id=c.get("id"),
                score=c.get("score", 0.0),
                snippet=c.get("snippet", "")
            )
            for c in result.get("citations", [])
        ]

        return QueryResponse(
            answer=result.get("answer", ""),
            sources=sources,
            citations=citations,
            query_rewrite=result.get("query_rewrite"),
            retrieval_meta=result.get("retrieval_meta"),
            error=result.get("llm_meta", {}).get("error")
        )
    except Exception as e:
        return QueryResponse(answer="", error=str(e))


@router.post("/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest):
    """Ingest documents from directory and create chunks."""
    try:
        output_path = request.output_path
        # Use /tmp in production if default path is used
        if os.getenv("ENV") == "production" and output_path == "data/chunks.jsonl":
            output_path = "/tmp/chunks.jsonl"

        result = ingest_from_directory(
            docs_dir=request.docs_dir,
            output_path=output_path,
            provider=request.provider,
            use_docling=request.use_docling,
            use_structure=request.use_structure
        )

        # Reload BM25 index if successful
        if result.status == "success":
            reload_index(output_path)
            set_chunks_path(output_path)

        return IngestResponse(
            status=result.status,
            documents=result.documents,
            chunks=result.chunks,
            output_path=output_path,
            errors=result.errors
        )
    except Exception as e:
        return IngestResponse(status="error", errors=[str(e)])


@router.post("/sync-pinecone", response_model=SyncResponse)
async def sync_pinecone(request: SyncRequest):
    """Sync embeddings to Pinecone vector database."""
    try:
        chunks_path = request.chunks_path
        # Use /tmp in production if default path is used
        if os.getenv("ENV") == "production" and chunks_path == "data/chunks.jsonl":
            # Check if /tmp/chunks.jsonl exists, otherwise fall back to bundled data if it exists
            if os.path.exists("/tmp/chunks.jsonl"):
                chunks_path = "/tmp/chunks.jsonl"

        result = sync_to_pinecone(
            chunks_path=chunks_path,
            batch_size=request.batch_size,
            store_text=request.store_text
        )
        return SyncResponse(
            status=result.status,
            vectors_upserted=result.vectors_upserted,
            errors=result.errors
        )
    except Exception as e:
        return SyncResponse(status="error", errors=[str(e)])


@router.get("/status", response_model=StatusResponse)
async def status(chunks_path: str = "data/chunks.jsonl"):
    """Get current index status."""
    try:
        result = get_index_status(chunks_path)
        return StatusResponse(
            exists=result.get("exists", False),
            chunks=result.get("chunks", 0),
            documents=result.get("documents", 0),
            path=result.get("path"),
            error=result.get("error")
        )
    except Exception as e:
        return StatusResponse(error=str(e))


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@router.delete("/clear-index")
async def clear_index():
    """
    Clear all vectors from Pinecone index.
    Use before uploading new documents to avoid stale data.
    """
    from pinecone import Pinecone
    import src.config as cfg

    try:
        pc = Pinecone(api_key=cfg.PINECONE_API_KEY)
        idx_meta = pc.describe_index(cfg.PINECONE_INDEX_NAME)
        host = getattr(idx_meta, "host", None) or idx_meta.get("host")
        index = pc.Index(host=host)

        # Delete all vectors
        index.delete(delete_all=True)

        return {"status": "success", "message": "Index cleared"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/embed-chunks")
async def embed_chunks(request: dict):
    """
    Embed pre-chunked text and upsert to Pinecone.

    ZERO-STORAGE PRIVACY:
    - Text is used ONLY for embedding generation
    - Only embeddings + file metadata stored in Pinecone
    - NO text content stored anywhere
    - Original text must be re-fetched from Dropbox at query time
    """
    from src.ingestion.embeddings import batch_embed_chunks
    from pinecone import Pinecone
    import src.config as cfg

    chunks = request.get("chunks", [])
    if not chunks:
        return {"status": "error", "error": "No chunks provided", "vectors_upserted": 0}

    try:
        # Prepare chunks for embedding
        chunk_data = []
        for i, chunk in enumerate(chunks):
            text = chunk.get("text", "")
            metadata = chunk.get("metadata", {})
            chunk_data.append({
                "text": text,
                "filename": metadata.get("filename", f"doc_{i}"),
                "chunk_id": metadata.get("chunkIndex", i),
                "chars": len(text),
            })

        # Generate embeddings (text processed in memory only)
        embedded = batch_embed_chunks(chunk_data, provider="sentence-transformers", dim=384)

        # Prepare vectors for Pinecone - NO TEXT STORED
        vectors = []
        for j, emb in enumerate(embedded):
            chunk_meta = chunks[j].get("metadata", {})
            # Use filename for readable IDs (sanitize for Pinecone compatibility)
            filename = chunk_meta.get("filename", "doc")
            vectors.append({
                "id": f"{filename}::{chunk_meta.get('chunkIndex', j)}",
                "values": emb["embedding"],
                "metadata": {
                    # File info for re-fetching
                    "filename": chunk_meta.get("filename", ""),
                    "file_path": chunk_meta.get("filePath", ""),  # Dropbox path
                    "file_id": chunk_meta.get("fileId", ""),
                    # Chunk position for extraction
                    "chunk_index": chunk_meta.get("chunkIndex", j),
                    "start_char": chunk_meta.get("startChar", 0),
                    "end_char": chunk_meta.get("endChar", 0),
                    # NO TEXT STORED - zero storage compliance
                }
            })

        # Upsert to Pinecone
        pc = Pinecone(api_key=cfg.PINECONE_API_KEY)
        idx_meta = pc.describe_index(cfg.PINECONE_INDEX_NAME)
        host = getattr(idx_meta, "host", None) or idx_meta.get("host")
        index = pc.Index(host=host)

        # Batch upsert
        batch_size = 100
        upserted = 0
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            index.upsert(vectors=batch)
            upserted += len(batch)

        # PRIVACY: Explicitly delete all text references from memory
        del chunks
        del chunk_data
        del embedded

        return {
            "status": "success",
            "vectors_upserted": upserted,
            "error": None
        }

    except Exception as e:
        return {
            "status": "error",
            "vectors_upserted": 0,
            "error": str(e)
        }


@router.post("/query-secure")
async def query_secure(request: dict):
    """
    ZERO-STORAGE QUERY with advanced retrieval pipeline.

    Features:
    - Query rewriting with multiple strategies (expand, multi, decompose, auto)
    - Reranking (cross-encoder precision boost after re-fetch)
    - Context shaping (token budget, deduplication)
    - Zero-storage: Re-fetches text from Dropbox at query time

    Parameters:
    - query: User question (required)
    - access_token: Dropbox OAuth token (required)
    - top_k: Number of chunks to retrieve (default: 3)
    - use_rewriting: Enable query rewriting (default: true)
    - rewrite_strategy: Strategy for query rewriting (default: "auto")
        - "expand": Rule-based synonym expansion (fast, no LLM)
        - "multi": LLM generates multiple query variants
        - "decompose": LLM breaks complex queries into sub-queries
        - "auto": Automatically choose based on query complexity
        - "none": Disable rewriting
    - use_reranking: Enable cross-encoder reranking (default: true)
    - use_context_shaping: Enable token budget & dedup (default: true)
    - token_budget: Max tokens for context (default: 2000)

    Flow:
    1. Query rewriting (optional, strategy-based)
    2. Generate query embedding(s) for all variants
    3. Search Pinecone with all query variants
    4. Deduplicate results across variants
    5. Re-fetch files from Dropbox
    6. Extract chunk text using stored positions
    7. Rerank chunks with cross-encoder (optional)
    8. Shape context (token budget, dedup, pruning)
    9. Send to LLM for answer generation
    10. Return answer (text never stored)
    """
    from src.ingestion.embeddings import get_embedding
    from pinecone import Pinecone
    import src.config as cfg

    query = request.get("query", "")
    access_token = request.get("access_token")
    top_k = request.get("top_k", 3)

    # Advanced retrieval options
    use_rewriting = request.get("use_rewriting", True)
    rewrite_strategy = request.get("rewrite_strategy", "auto")  # expand, multi, decompose, auto, none
    use_reranking = request.get("use_reranking", True)
    use_context_shaping = request.get("use_context_shaping", True)
    token_budget = request.get("token_budget", 2000)

    if not query:
        return {"error": "No query provided", "answer": ""}

    if not access_token:
        return {"error": "Dropbox access token required for zero-storage queries", "answer": ""}

    # Call the unified orchestrator
    result = await orchestrate_zero_storage(
        query=query,
        access_token=access_token,
        top_k=top_k,
        use_rewriting=use_rewriting,
        rewrite_strategy=rewrite_strategy,
        use_reranking=use_reranking,
        use_context_shaping=use_context_shaping,
        token_budget=token_budget
    )
    return result


@router.post("/dropbox/token")
async def dropbox_token_exchange(request: dict):
    """
    Exchange Dropbox authorization code for access token.
    Client secret is kept server-side for security.
    """
    code = request.get("code")
    redirect_uri = request.get("redirect_uri")

    if not code:
        return {"error": "No authorization code provided"}

    app_key = os.environ.get("DROPBOX_APP_KEY")
    app_secret = os.environ.get("DROPBOX_APP_SECRET")

    if not app_key or not app_secret:
        return {"error": "Dropbox credentials not configured on server"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.dropboxapi.com/oauth2/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": app_key,
                    "client_secret": app_secret,
                    "redirect_uri": redirect_uri,
                }
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Dropbox API error: {response.text}"}

    except Exception as e:
        return {"error": str(e)}


@router.post("/dropbox/folder")
async def dropbox_folder(request: dict):
    """
    Proxy Dropbox folder API calls to avoid CORS issues.
    """
    path = request.get("path", "")
    access_token = request.get("access_token")

    if not access_token:
        return {"error": "No access token provided"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.dropboxapi.com/2/files/list_folder",
                json={"path": path, "limit": 100},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Dropbox API error: {response.text}", "status": response.status_code}

    except Exception as e:
        return {"error": str(e)}


@router.post("/eval/parsing")
async def eval_parsing(request: dict):
    """
    Evaluate Docling parsing on a file from Dropbox.

    Request:
        - path: Dropbox file path
        - access_token: Dropbox access token

    Returns parsing metrics and element breakdown.
    """
    from pathlib import Path

    file_path = request.get("path")
    access_token = request.get("access_token")

    if not access_token or not file_path:
        return {"error": "Missing path or access_token"}

    try:
        # Download file from Dropbox
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "https://content.dropboxapi.com/2/files/download",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Dropbox-API-Arg": f'{{"path": "{file_path}"}}'
                }
            )

            if response.status_code != 200:
                return {"error": f"Dropbox download failed: {response.text}"}

        # Zero-disk processing: parse directly from memory
        from src.ingestion.docling_loader import load_document_from_bytes
        from collections import Counter

        filename = Path(file_path).name
        doc = load_document_from_bytes(response.content, filename)

        # Count element types
        type_counts = Counter(el.element_type for el in doc.elements)

        # Sample elements
        samples = []
        for el in doc.elements[:10]:
            samples.append({
                "type": el.element_type,
                "text": el.text[:200] + "..." if len(el.text) > 200 else el.text,
                "level": el.level
            })

        result = {
            "status": doc.status,
            "filename": doc.filename,
            "format": doc.format,
            "total_elements": len(doc.elements),
            "total_chars": doc.chars,
            "total_words": doc.words,
            "page_count": doc.page_count,
            "element_types": dict(type_counts),
            "sample_elements": samples,
            "error": doc.error
        }

        return result

    except Exception as e:
        return {"error": str(e)}


@router.get("/eval/formats")
async def eval_formats():
    """Get supported document formats for Docling parsing."""
    from src.ingestion.api import get_supported_formats
    return get_supported_formats()


@router.post("/parse-docling")
async def parse_docling(request: dict):
    """
    Parse files with Docling and return COMPLETE output.

    Request:
        - files: Array of {path, name} objects
        - access_token: Dropbox access token

    Returns array of parsed documents with ALL elements (not samples).
    """
    from pathlib import Path
    from collections import Counter

    files = request.get("files", [])
    access_token = request.get("access_token")

    if not access_token or not files:
        return {"error": "Missing files or access_token"}

    results = []

    for file_info in files:
        file_path = file_info.get("path")
        file_name = file_info.get("name", Path(file_path).name if file_path else "unknown")

        if not file_path:
            results.append({
                "filename": file_name,
                "status": "ERROR",
                "error": "Missing file path"
            })
            continue

        try:
            # Download file from Dropbox
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    "https://content.dropboxapi.com/2/files/download",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Dropbox-API-Arg": f'{{"path": "{file_path}"}}'
                    }
                )

                if response.status_code != 200:
                    results.append({
                        "filename": file_name,
                        "status": "ERROR",
                        "error": f"Dropbox download failed: {response.text}"
                    })
                    continue

            # Zero-disk processing: parse directly from memory
            # Try Docling first, fallback to PyPDF2 if Docling fails
            doc = None
            fallback_text = None
            parse_method = "docling"

            try:
                from src.ingestion.docling_loader import load_document_from_bytes
                doc = load_document_from_bytes(response.content, file_name)

                # If Docling returned error or no text, try fallback
                if doc.status != "OK" or not doc.full_text.strip():
                    raise ValueError(f"Docling parsing failed: {doc.error or 'No text extracted'}")

            except Exception as docling_err:
                # Fallback to PyPDF2 for PDFs, or raw text for others
                parse_method = "fallback"
                import io

                ext = Path(file_name).suffix.lower()
                if ext == ".pdf":
                    try:
                        from PyPDF2 import PdfReader
                        pdf_file = io.BytesIO(response.content)
                        reader = PdfReader(pdf_file)
                        text_parts = []
                        for page in reader.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text_parts.append(page_text)
                        fallback_text = "\n\n".join(text_parts)
                    except Exception as pdf_err:
                        fallback_text = None
                elif ext in [".txt", ".md", ".markdown"]:
                    try:
                        fallback_text = response.content.decode("utf-8")
                    except Exception:
                        fallback_text = None

            # Build response based on what worked
            if doc and doc.status == "OK" and doc.full_text.strip():
                # Docling succeeded
                type_counts = Counter(el.element_type for el in doc.elements)
                all_elements = []
                for el in doc.elements:
                    all_elements.append({
                        "type": el.element_type,
                        "text": el.text,
                        "level": el.level,
                        "page": getattr(el, 'page', None),
                        "metadata": getattr(el, 'metadata', {})
                    })

                results.append({
                    "filename": file_name,
                    "path": file_path,
                    "status": "OK",
                    "format": doc.format,
                    "total_elements": len(doc.elements),
                    "total_chars": doc.chars,
                    "total_words": doc.words,
                    "page_count": doc.page_count,
                    "element_types": dict(type_counts),
                    "elements": all_elements,
                    "full_text": doc.full_text,
                    "parse_method": "docling",
                    "error": None
                })
            elif fallback_text and fallback_text.strip():
                # Fallback succeeded
                results.append({
                    "filename": file_name,
                    "path": file_path,
                    "status": "OK",
                    "format": Path(file_name).suffix.lower(),
                    "total_elements": 1,
                    "total_chars": len(fallback_text),
                    "total_words": len(fallback_text.split()),
                    "page_count": 0,
                    "element_types": {"paragraph": 1},
                    "elements": [{"type": "paragraph", "text": fallback_text[:500] + "..." if len(fallback_text) > 500 else fallback_text, "level": 0}],
                    "full_text": fallback_text,
                    "parse_method": "fallback_pypdf2" if Path(file_name).suffix.lower() == ".pdf" else "fallback_text",
                    "error": None
                })
            else:
                # Both failed
                results.append({
                    "filename": file_name,
                    "path": file_path,
                    "status": "ERROR",
                    "format": Path(file_name).suffix.lower(),
                    "total_elements": 0,
                    "total_chars": 0,
                    "total_words": 0,
                    "page_count": 0,
                    "element_types": {},
                    "elements": [],
                    "full_text": "",
                    "parse_method": "failed",
                    "error": f"Could not extract text from {file_name}"
                })

        except Exception as e:
            results.append({
                "filename": file_name,
                "status": "ERROR",
                "error": str(e),
                "full_text": "",  # Empty for consistency
                "elements": [],
                "total_elements": 0,
                "total_chars": 0
            })

    return {"results": results}


@router.post("/dropbox/file")
async def dropbox_file(request: dict):
    """
    Proxy Dropbox file download to avoid CORS issues.
    Supports text files (.txt, .md) and PDFs with text extraction.
    """
    import io
    path = request.get("path")
    access_token = request.get("access_token")

    if not access_token or not path:
        return {"error": "Missing path or access_token"}

    # Check if file is a PDF
    is_pdf = path.lower().endswith('.pdf')

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://content.dropboxapi.com/2/files/download",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Dropbox-API-Arg": f'{{"path": "{path}"}}'
                }
            )

            if response.status_code == 200:
                if is_pdf:
                    # Extract text from PDF
                    try:
                        from PyPDF2 import PdfReader
                        pdf_file = io.BytesIO(response.content)
                        reader = PdfReader(pdf_file)
                        text_parts = []
                        for page in reader.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text_parts.append(page_text)
                        content = "\n\n".join(text_parts)
                        if not content.strip():
                            return {"error": "PDF contains no extractable text (may be scanned/image-based)"}
                        return {"content": content}
                    except Exception as pdf_err:
                        return {"error": f"PDF extraction failed: {str(pdf_err)}"}
                else:
                    # Return text content directly
                    return {"content": response.text}
            else:
                return {"error": f"Dropbox API error: {response.text}", "status": response.status_code}

    except Exception as e:
        return {"error": str(e)}
