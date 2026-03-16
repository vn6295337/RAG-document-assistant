# RAG Document Assistant - Architecture

> **Version**: 2.0
> **Last Updated**: January 2026
> **Focus**: Zero-Storage Privacy Architecture

---

## System Overview

A privacy-first RAG (Retrieval-Augmented Generation) system where **no document text is ever stored on our servers**. Documents are processed client-side, and text is re-fetched from the user's cloud storage at query time.

### Key Characteristics

- **Zero-Storage**: Document text never persists on servers
- **Client-Side Processing**: Chunking happens in the browser
- **Query-Time Re-fetch**: Text retrieved from user's Dropbox for each search
- **User Control**: Disconnect cloud storage to revoke all access

---

## Privacy Architecture

```
INDEXING (one-time setup) - SINGLE DOWNLOAD FLOW
══════════════════════════════════════════════════════════════════

  User's Browser                              Our Server (Zero-Disk)
  ──────────────                              ─────────────────────

  1. Connect Dropbox (OAuth)
           │
           ▼
  2. Select files from Dropbox
           │
           ▼
  3. Click "Index Selected Files"
           │
           └──────────────────────────────► 4. SINGLE DOWNLOAD from Dropbox
                                                  │
                                              5. Parse with Docling
                                                 (BytesIO - RAM only)
                                                 (No temp files created)
                                                  │
           ┌──────────────────────────────────────┘
           │
  6. Display parsed structure ◄────────────  Returns:
     for user review                          - parsed_structure
           │                                  - full_text (for chunking)
           ▼
  7. User clicks "Continue"
           │
           ▼
  8. Chunk full_text locally ─────────────► 9. Generate embeddings
     (client-side, uses Docling output)        (384-dim vectors)
           │                                        │
           ▼                                        ▼
  10. Original text                         11. Store in Pinecone:
      PURGED from browser                       - Embeddings (irreversible)
                                                - File paths
                                                - Chunk positions
                                                - NO TEXT

══════════════════════════════════════════════════════════════════

QUERY TIME (every search) - ADVANCED RETRIEVAL PIPELINE
══════════════════════════════════════════════════════════════════

  User's Question                             Our Server (Zero-Disk)
  ───────────────                             ─────────────────────

  "What does the contract say?"
           │
           ▼
  ─────────────────────────────────────► 1. QUERY REWRITING
                                            Expand with synonyms/variants
                                              │
                                              ▼
                                         2. MULTI-QUERY SEARCH
                                            Search Pinecone with all variants
                                            Deduplicate across results
                                              │
                                              ▼
                                         3. RE-FETCH FROM DROPBOX
                                            Download files (BytesIO - RAM only)
                                            Extract text using positions
                                              │
                                              ▼
                                         4. RERANKING
                                            Cross-encoder precision boost
                                            Reorder by relevance to query
                                              │
                                              ▼
                                         5. CONTEXT SHAPING
                                            Token budget enforcement
                                            Deduplication & pruning
                                              │
                                              ▼
                                         6. LLM GENERATION
                                            Build prompt, call LLM
                                              │
                                              ▼
  Answer + Citations ◄─────────────────  7. Return response
                                            (text never stored)

══════════════════════════════════════════════════════════════════

RETRIEVAL FEATURES COMPARISON
══════════════════════════════════════════════════════════════════

  Feature              │ /query-secure  │ /query (legacy)
  ─────────────────────┼────────────────┼─────────────────
  Query Rewriting      │ ✅ Enabled      │ ✅ Enabled
  Semantic Search      │ ✅ Pinecone     │ ✅ Pinecone
  BM25 Keyword Search  │ ❌ N/A          │ ✅ Local corpus
  Hybrid Fusion        │ ❌ N/A          │ ✅ RRF fusion
  Reranking            │ ✅ Post-refetch │ ✅ Pre-generation
  Context Shaping      │ ✅ Token budget │ ✅ Token budget
  Zero-Storage         │ ✅ Yes          │ ❌ No

══════════════════════════════════════════════════════════════════
```

---

## What Gets Stored

| Data | Stored? | Where | Reversible? |
|------|---------|-------|-------------|
| Document files | No | User's Dropbox only | N/A |
| Document text | No | Never stored | N/A |
| Embeddings | Yes | Pinecone | No (one-way transform) |
| File paths | Yes | Pinecone metadata | N/A |
| Chunk positions | Yes | Pinecone metadata | N/A |
| User queries | No | Not logged | N/A |

---

## Technology Stack

### Frontend
- **Framework**: React 18 + Vite
- **Styling**: Tailwind CSS v4
- **Deployment**: Vercel
- **Key Features**:
  - Client-side text chunking
  - Dropbox OAuth integration
  - Position tracking for chunks

### Backend
- **Framework**: FastAPI
- **Deployment**: HuggingFace Spaces (Docker)
- **Key Features**:
  - Zero-storage embedding endpoint
  - Query-time Dropbox re-fetch
  - Multi-provider LLM cascade

### Vector Database
- **Service**: Pinecone Serverless
- **Index**: `rag-semantic-384`
- **Dimensions**: 384
- **Metric**: Cosine similarity

### Embeddings
- **Model**: `all-MiniLM-L6-v2` (sentence-transformers)
- **Dimensions**: 384
- **Processing**: Server-side (text discarded immediately)

### LLM Providers (Cascade)
1. **Gemini 2.5 Flash** (Primary)
2. **Groq** - llama-3.1-8b-instant (Fallback 1)
3. **OpenRouter** - Mistral 7B (Fallback 2)

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Sidebar    │  │  QueryPanel  │  │   App.jsx    │          │
│  │              │  │              │  │              │          │
│  │ - CloudConnect  │ - Search UI   │ - State mgmt  │          │
│  │ - File select   │ - Results     │ - Token flow  │          │
│  │ - Index button  │ - Citations   │ - Privacy UI  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────────────────────────────────────────┐           │
│  │                  API Layer                        │           │
│  │  chunker.js  │  dropbox.js  │  client.js         │           │
│  └──────────────────────────────────────────────────┘           │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │ HTTPS
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────┐         │
│  │                   API Routes                        │         │
│  │                                                     │         │
│  │  POST /embed-chunks    - Generate embeddings        │         │
│  │  POST /query-secure    - Zero-storage query         │         │
│  │  POST /dropbox/token   - OAuth token exchange       │         │
│  │  POST /dropbox/folder  - List folder contents       │         │
│  │  POST /dropbox/file    - Download file content      │         │
│  │  DELETE /clear-index   - Clear Pinecone index       │         │
│  └────────────────────────────────────────────────────┘         │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │ Pinecone │    │ Dropbox  │    │   LLM    │
        │ (vectors)│    │  (files) │    │ Providers│
        └──────────┘    └──────────┘    └──────────┘
```

---

## Data Flow: Indexing (Single Download)

```python
# 1. User selects files in browser
files = [
    {id: "abc123", name: "contract.pdf", path: "/Documents/contract.pdf"}
]

# 2. SINGLE DOWNLOAD: Parse with Docling (zero-disk)
response = await fetch("/api/parse-docling", {
    files: [{path: "/Documents/contract.pdf", name: "contract.pdf"}],
    access_token: "..."
})
# Server: Downloads once → BytesIO → DocumentStream → Docling
# Returns: {results: [{full_text: "...", elements: [...], ...}]}

# 3. Display parsed structure for user review
showDoclingOutput(response.results)

# 4. User clicks "Continue" → Chunk full_text CLIENT-SIDE
fileContents = response.results.map(r => ({
    name: r.filename,
    path: r.path,
    content: r.full_text  // Docling-parsed text (higher quality)
}))
chunks = chunkFiles(fileContents)
# Result: [{text: "...", startChar: 0, endChar: 500}, ...]

# 5. Chunks sent to backend for embedding
await fetch("/api/embed-chunks", {
    chunks: [{
        text: "...",  // Used for embedding only
        metadata: {
            filename: "contract.pdf",
            filePath: "/Documents/contract.pdf",
            startChar: 0,
            endChar: 500
        }
    }]
})

# 6. Backend generates embeddings, stores in Pinecone
# TEXT IS IMMEDIATELY DISCARDED
pinecone.upsert({
    id: "contract.pdf::0",
    values: [0.123, -0.456, ...],  # 384-dim embedding
    metadata: {
        filename: "contract.pdf",
        file_path: "/Documents/contract.pdf",
        start_char: 0,
        end_char: 500
        # NO TEXT STORED
    }
})
```

**Key Improvement:** Single download eliminates double-fetch. Docling output (higher quality than PyPDF2) used for chunking.

---

## Document Parsing Pipeline

```
File received from Dropbox
         │
         ▼
┌─────────────────────────┐
│  Try Docling (Primary)  │
│  - Zero-disk (BytesIO)  │
│  - Structure-aware      │
│  - Multi-format support │
└───────────┬─────────────┘
            │
            ▼
      Success? ──────────────────────────────┐
         │                                    │
         │ No                                 │ Yes
         ▼                                    ▼
┌─────────────────────────┐          Return full_text
│  Fallback: PyPDF2/Text  │          + elements
│  - PDF: PyPDF2 extract  │
│  - TXT/MD: Raw decode   │
└───────────┬─────────────┘
            │
            ▼
      Success? ──────────────────────────────┐
         │                                    │
         │ No                                 │ Yes
         ▼                                    ▼
   Return ERROR:                      Return full_text
   "No text extracted"                (parse_method: fallback)
```

### Parse Methods

| Method | Description | Quality |
|--------|-------------|---------|
| `docling` | Docling structure-aware parsing | High |
| `fallback_pypdf2` | PyPDF2 text extraction for PDFs | Medium |
| `fallback_text` | Raw text decode for TXT/MD | High |
| `failed` | No text could be extracted | N/A |

### Limitations

| Scenario | Result | Solution |
|----------|--------|----------|
| Scanned PDF (image-based) | No text extracted | Install Tesseract OCR |
| Image files (PNG, JPG) | No text extracted | Install Tesseract OCR |
| Encrypted PDF | Parse error | Decrypt before upload |
| Corrupted file | Parse error | Re-export from source |

---

## Data Flow: Query

```python
# 1. User submits query with access token
request = {
    query: "What is the payment term?",
    access_token: "user_dropbox_token"
}

# 2. Generate query embedding
query_embedding = sentence_transformer.encode(query)

# 3. Search Pinecone
results = pinecone.query(
    vector=query_embedding,
    top_k=3,
    include_metadata=True
)
# Returns: file paths + positions (NO TEXT)

# 4. Re-fetch files from USER'S Dropbox
for file_path in unique_file_paths:
    content = dropbox.download(file_path, access_token)

    # 5. Extract chunks using stored positions
    for chunk in chunks_from_file:
        text = content[chunk.start_char:chunk.end_char]

# 6. Build prompt with re-fetched text
prompt = f"""
Context:
1. {chunk1_text}
2. {chunk2_text}

Question: {query}
"""

# 7. Call LLM
answer = llm.generate(prompt)

# 8. Return answer (text never stored)
return {answer, citations}
```

---

## Security & Privacy

### User Control
- **OAuth Scopes**: Read-only access to user-selected files
- **Token Storage**: Access token stored only in browser session
- **Revocation**: Disconnect Dropbox = immediate access revocation

### Server Security
- **No Persistent Storage**: Text never written to disk or database
- **Memory Only**: Text exists in memory only during processing
- **Immediate Purge**: Explicit deletion after embedding generation

### Zero-Disk Processing (Docling)

Document parsing uses in-memory streams to ensure files never touch disk:

```python
# Implementation in src/ingestion/docling_loader.py

def load_document_from_bytes(file_bytes: bytes, filename: str) -> ParsedDocument:
    """Load document from in-memory bytes (zero-disk-touch)."""
    from io import BytesIO
    from docling.datamodel.base_models import DocumentStream

    # Zero-disk: BytesIO wrapper keeps bytes in RAM
    buf = BytesIO(file_bytes)
    stream = DocumentStream(name=filename, stream=buf)
    result = converter.convert(stream)  # No disk I/O

    # Metadata flags for audit
    return ParsedDocument(
        path="<memory>",
        metadata={"zero_disk": True}
    )
```

**Key Implementation Details:**

| Aspect | Before (Temp Files) | After (Zero-Disk) |
|--------|---------------------|-------------------|
| **File handling** | `tempfile.NamedTemporaryFile()` | `BytesIO()` |
| **Docling input** | File path string | `DocumentStream` |
| **Disk I/O** | Write to `/tmp/` | None |
| **Cleanup** | `os.unlink()` (insecure) | Automatic (GC) |
| **Forensic recovery** | Possible | Not possible |

**API Endpoints Using Zero-Disk:**
- `POST /eval/parsing` - Document parsing evaluation
- `POST /parse-docling` - Batch document parsing

**Audit Logging:**
```
INFO: Zero-disk processing: contract.pdf (2,456,789 bytes) - No temp file created
```

### Data Protection
- **Embeddings**: One-way transformation, cannot reconstruct text
- **Positions**: Only useful with original file access
- **File Paths**: Dropbox paths, require valid access token

### Deployment Requirements

For guaranteed zero-disk operation:

1. **Swap Disabled**: Prevents RAM from being paged to disk
   ```bash
   swapoff -a
   ```

2. **Memory Sizing**:
   ```
   Required RAM = Base (2GB) + (50MB × concurrent_users × 3)
   ```
   Factor of 3 accounts for Docling parsing overhead.

3. **File Size Limits**: 50MB maximum per file

### Security Caveats

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Swap enabled | Medium | Verify `swapon --show` is empty |
| Memory dump | Low | Requires root access during processing |
| Cold boot | Very Low | Physical access + timing attack |

See [SECURITY.md](../SECURITY.md) for full security policy.

---

## Deployment

### Frontend (Vercel)
- Automatic deploys from GitHub
- Environment: `VITE_API_URL` pointing to backend

### Backend (HuggingFace Spaces)
- Docker-based deployment
- Environment variables for API keys:
  - `PINECONE_API_KEY`
  - `DROPBOX_APP_KEY`
  - `DROPBOX_APP_SECRET`
  - `GEMINI_API_KEY`
  - `GROQ_API_KEY`

---

## References

- **Live Demo**: https://rag-document-assistant.vercel.app/
- **Backend API**: https://vn6295337-rag-document-assistant.hf.space/
- **GitHub**: https://github.com/vn6295337/RAG-document-assistant
