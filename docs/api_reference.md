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

Execute a zero-storage query. Re-fetches text from user's Dropbox at query time.

**Request Body:**
```json
{
  "query": "What are the payment terms?",
  "access_token": "dropbox_access_token",
  "top_k": 3
}
```

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
  "error": null
}
```

**Flow:**
1. Generate query embedding
2. Search Pinecone for similar chunks
3. Re-fetch files from user's Dropbox using provided token
4. Extract chunk text using stored positions
5. Send to LLM for answer generation
6. Return answer (text never stored)

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
