# API Reference

Base URL: `https://vn6295337-rag-document-assistant.hf.space/api`

---

## Zero-Storage Endpoints

### POST /embed-chunks

Generate embeddings for text chunks and store in Pinecone. **Text is discarded immediately after embedding.**

**Request Body:**
```json
{
  "chunks": [
    {
      "text": "The actual text content...",
      "metadata": {
        "filename": "document.pdf",
        "filePath": "/Documents/document.pdf",
        "fileId": "dropbox_file_id",
        "chunkIndex": 0,
        "startChar": 0,
        "endChar": 1000
      }
    }
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "vectors_upserted": 5,
  "error": null
}
```

**Privacy Note:** Text is used only for embedding generation, then immediately deleted. Only embeddings and metadata (file paths, positions) are stored.

---

### POST /query-secure

Execute a zero-storage query with advanced retrieval pipeline. Re-fetches text from user's Dropbox at query time.

**Request Body:**
```json
{
  "query": "What are the payment terms?",
  "access_token": "dropbox_access_token",
  "top_k": 3,
  "use_rewriting": true,
  "use_reranking": true,
  "use_context_shaping": true,
  "token_budget": 2000
}
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | User's question |
| `access_token` | string | required | Dropbox OAuth token |
| `top_k` | int | 3 | Number of chunks to return |
| `use_rewriting` | bool | true | Enable query expansion/rewriting |
| `use_reranking` | bool | true | Enable cross-encoder reranking |
| `use_context_shaping` | bool | true | Enable token budget & deduplication |
| `token_budget` | int | 2000 | Max tokens for context |

**Response:**
```json
{
  "answer": "According to the contract, payment is due within 30 days...",
  "citations": [
    {
      "id": "file_id::0",
      "score": 0.85,
      "snippet": "Payment terms: Net 30 days from invoice date..."
    }
  ],
  "pipeline_meta": {
    "rewriting_enabled": true,
    "reranking_enabled": true,
    "context_shaping_enabled": true,
    "query_variants": 2,
    "initial_matches": 9,
    "rerank_model": "cross-encoder",
    "original_tokens": 1500,
    "final_tokens": 1200
  },
  "error": null
}
```

**Pipeline Flow:**
```
1. Query Rewriting ──► Expand query with synonyms/variants
         │
2. Multi-Query Search ──► Search Pinecone with all variants
         │
3. Deduplicate ──► Remove duplicate chunks across variants
         │
4. Re-fetch from Dropbox ──► Get actual text (zero-storage)
         │
5. Reranking ──► Cross-encoder precision boost
         │
6. Context Shaping ──► Token budget, deduplication, pruning
         │
7. LLM Generation ──► Build prompt, generate answer
         │
8. Return ──► Answer + citations (text never stored)
```

**Note:** BM25 keyword search is not available in zero-storage mode (requires local text corpus). Use `/query` endpoint for full hybrid search with local storage.

---

### DELETE /clear-index

Clear all vectors from Pinecone index.

**Response:**
```json
{
  "status": "success",
  "message": "Index cleared"
}
```

---

## Dropbox Integration Endpoints

### POST /dropbox/token

Exchange Dropbox authorization code for access token. Client secret is kept server-side.

**Request Body:**
```json
{
  "code": "authorization_code_from_oauth",
  "redirect_uri": "https://your-app.com/callback"
}
```

**Response:**
```json
{
  "access_token": "sl.xxxxx",
  "token_type": "bearer",
  "expires_in": 14400
}
```

---

### POST /dropbox/folder

List contents of a Dropbox folder (proxy to avoid CORS).

**Request Body:**
```json
{
  "path": "",
  "access_token": "dropbox_access_token"
}
```

**Response:**
```json
{
  "entries": [
    {
      ".tag": "file",
      "name": "document.pdf",
      "id": "id:xxxxx",
      "path_lower": "/documents/document.pdf",
      "size": 12345
    }
  ],
  "has_more": false
}
```

---

### POST /dropbox/file

Download file content from Dropbox. Supports text files and PDFs (with text extraction).

**Request Body:**
```json
{
  "path": "/documents/document.pdf",
  "access_token": "dropbox_access_token"
}
```

**Response:**
```json
{
  "content": "Extracted text content from the file..."
}
```

**Supported File Types:**
- `.txt` - Plain text
- `.md` - Markdown
- `.pdf` - PDF (text extraction via PyPDF2)

---

## Document Parsing Endpoints (Zero-Disk)

These endpoints use **zero-disk processing** - files are parsed entirely in memory using `BytesIO` and `DocumentStream`. No temporary files are created.

### POST /eval/parsing

Evaluate Docling parsing on a single file from Dropbox.

**Request Body:**
```json
{
  "path": "/Documents/contract.pdf",
  "access_token": "dropbox_access_token"
}
```

**Response:**
```json
{
  "status": "OK",
  "filename": "contract.pdf",
  "format": ".pdf",
  "total_elements": 42,
  "total_chars": 15234,
  "total_words": 2156,
  "page_count": 5,
  "element_types": {
    "paragraph": 30,
    "heading": 8,
    "list": 4
  },
  "sample_elements": [
    {
      "type": "heading",
      "text": "Agreement Terms...",
      "level": 1
    }
  ],
  "error": null
}
```

**Zero-Disk Note:** File bytes are processed using `BytesIO` → `DocumentStream` → Docling. No temp files created. Logs show: `Zero-disk processing: contract.pdf (X bytes) - No temp file created`

---

### POST /parse-docling

Parse multiple files with Docling and return complete parsed output. **This is the primary endpoint for the single-download indexing flow.**

**Request Body:**
```json
{
  "files": [
    {"path": "/Documents/doc1.pdf", "name": "doc1.pdf"},
    {"path": "/Documents/doc2.docx", "name": "doc2.docx"}
  ],
  "access_token": "dropbox_access_token"
}
```

**Response:**
```json
{
  "results": [
    {
      "filename": "doc1.pdf",
      "path": "/Documents/doc1.pdf",
      "status": "OK",
      "format": ".pdf",
      "total_elements": 42,
      "total_chars": 15234,
      "total_words": 2156,
      "page_count": 5,
      "element_types": {"paragraph": 30, "heading": 8},
      "elements": [
        {
          "type": "heading",
          "text": "Full heading text here",
          "level": 1,
          "metadata": {}
        }
      ],
      "full_text": "Full concatenated text from all elements...",
      "error": null
    }
  ]
}
```

**Key Fields:**
- `elements` - Structured document elements (for display/preview)
- `full_text` - Concatenated text from all elements (for client-side chunking)
- `parse_method` - Which parser succeeded: `docling`, `fallback_pypdf2`, `fallback_text`, or `failed`

**Supported Formats:** PDF, DOCX, PPTX, XLSX, HTML, Markdown, PNG, JPG, TIFF, BMP

**Parsing Pipeline:**
1. Try Docling (primary, structure-aware, zero-disk)
2. If Docling fails → Fallback to PyPDF2 (for PDFs) or raw text decode (for TXT/MD)
3. If both fail → Return `status: "ERROR"` with `full_text: ""`

**Single-Download Flow:** This endpoint enables the unified indexing flow:
1. Browser calls `/parse-docling` once
2. Server downloads from Dropbox, parses with Docling (BytesIO - zero-disk)
3. Returns both structure (`elements`) and text (`full_text`)
4. Browser chunks `full_text` client-side
5. No separate `/dropbox/file` call needed

**Error Scenarios:**

| Scenario | Status | Error Message |
|----------|--------|---------------|
| Docling succeeds | `OK` | `null` |
| Docling fails, PyPDF2 succeeds | `OK` | `null` |
| Scanned PDF (no OCR) | `ERROR` | `No text extracted` |
| Encrypted PDF | `ERROR` | `Could not extract text` |
| Unsupported format | `ERROR` | `Unsupported format` |

**Zero-Disk Note:** Each file processed in memory using `DocumentStream(BytesIO)`. No temp files created.

---

### GET /eval/formats

Get list of supported document formats for Docling parsing.

**Response:**
```json
{
  "formats": [".pdf", ".docx", ".pptx", ".xlsx", ".html", ".md", ".png", ".jpg"]
}
```

---

## Utility Endpoints

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "ok"
}
```

---

### GET /status

Get current index status.

**Query Parameters:**
- `chunks_path` (optional): Path to chunks file (default: `data/chunks.jsonl`)

**Response:**
```json
{
  "exists": true,
  "chunks": 44,
  "documents": 5,
  "path": "data/chunks.jsonl",
  "error": null
}
```

---

## Legacy Endpoints

### POST /query

Standard RAG query (uses local chunks file, not zero-storage).

**Request Body:**
```json
{
  "query": "What is GDPR?",
  "top_k": 3,
  "use_hybrid": false,
  "use_reranking": false
}
```

---

### POST /ingest

Ingest documents from a directory (server-side processing).

**Request Body:**
```json
{
  "docs_dir": "sample_docs",
  "output_path": "data/chunks.jsonl",
  "provider": "sentence-transformers"
}
```

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "status": "error",
  "error": "Description of the error"
}
```

Common error codes:
- Missing required parameters
- Invalid access token
- Dropbox API errors
- Pinecone connection errors
- LLM provider failures

---

## Rate Limits

- **Embedding**: No explicit limit (Pinecone free tier: 100K operations/month)
- **Queries**: Subject to LLM provider limits:
  - Gemini: 15 RPM
  - Groq: 30 RPM
  - OpenRouter: Varies by model

---

## Environment Variables

Required on backend:
- `PINECONE_API_KEY` - Pinecone vector database
- `DROPBOX_APP_KEY` - Dropbox OAuth app key
- `DROPBOX_APP_SECRET` - Dropbox OAuth app secret
- `GEMINI_API_KEY` - Google Gemini API (primary LLM)
- `GROQ_API_KEY` - Groq API (fallback LLM)
