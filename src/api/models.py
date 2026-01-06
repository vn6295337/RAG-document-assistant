"""Pydantic models for API request/response."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel


# Request models
class QueryRequest(BaseModel):
    query: str
    top_k: int = 3
    use_hybrid: bool = True
    use_reranking: bool = True


class IngestRequest(BaseModel):
    docs_dir: str
    output_path: str = "data/chunks.jsonl"
    provider: str = "sentence-transformers"


class SyncRequest(BaseModel):
    chunks_path: str = "data/chunks.jsonl"
    batch_size: int = 100


# Response models
class Citation(BaseModel):
    id: Optional[str] = None
    score: float = 0.0
    snippet: str = ""


class QueryResponse(BaseModel):
    answer: str
    sources: List[Citation] = []
    citations: List[Citation] = []
    query_rewrite: Optional[Dict[str, Any]] = None
    retrieval_meta: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class IngestResponse(BaseModel):
    status: str
    documents: int = 0
    chunks: int = 0
    output_path: str = ""
    errors: List[str] = []


class SyncResponse(BaseModel):
    status: str
    vectors_upserted: int = 0
    errors: List[str] = []


class StatusResponse(BaseModel):
    exists: bool = False
    chunks: int = 0
    documents: int = 0
    path: Optional[str] = None
    error: Optional[str] = None
