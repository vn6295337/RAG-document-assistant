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
INDEXING (one-time setup)
══════════════════════════════════════════════════════════════════

  User's Browser                              Our Server
  ──────────────                              ──────────

  1. Connect Dropbox (OAuth)
           │
           ▼
  2. Select files from Dropbox
           │
           ▼
  3. Files loaded in browser
     (never sent to server)
           │
           ▼
  4. Text chunked locally ───────────────► 5. Generate embeddings
     with position tracking                    (384-dim vectors)
           │                                        │
           ▼                                        ▼
  6. Original text                          7. Store in Pinecone:
     PURGED from memory                        - Embeddings (irreversible)
                                               - File paths
                                               - Chunk positions
                                               - NO TEXT

══════════════════════════════════════════════════════════════════

QUERY TIME (every search)
══════════════════════════════════════════════════════════════════

  User's Question                             Our Server
  ───────────────                             ──────────

  "What does the contract say?"
           │
           ▼
  ─────────────────────────────────────► 1. Generate query embedding
                                              │
                                              ▼
                                         2. Search Pinecone
                                            (find similar chunks)
                                              │
                                              ▼
                                         3. Get file paths + positions
                                              │
                                              ▼
                                         4. Re-fetch from USER'S Dropbox
                                            using their access token
                                              │
                                              ▼
                                         5. Extract chunk text
                                            using stored positions
                                              │
                                              ▼
                                         6. Send to LLM for answer
                                              │
                                              ▼
  Answer + Citations ◄─────────────────  7. Return response
                                            (text never stored)

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

## Data Flow: Indexing

```python
# 1. User selects files in browser
files = [
    {id: "abc123", name: "contract.pdf", path: "/Documents/contract.pdf"}
]

# 2. Files fetched from Dropbox (via backend proxy)
content = await fetch("/api/dropbox/file", {path: file.path, access_token})

# 3. Text chunked CLIENT-SIDE with position tracking
chunks = chunkText(content, {chunkSize: 1000, overlap: 100})
# Result:
# {text: "...", startChar: 0, endChar: 1000}
# {text: "...", startChar: 900, endChar: 1900}

# 4. Chunks sent to backend for embedding
await fetch("/api/embed-chunks", {
    chunks: [{
        text: "...",  // Used for embedding only
        metadata: {
            filename: "contract.pdf",
            filePath: "/Documents/contract.pdf",
            fileId: "abc123",
            startChar: 0,
            endChar: 1000
        }
    }]
})

# 5. Backend generates embeddings, stores in Pinecone
# TEXT IS IMMEDIATELY DISCARDED
pinecone.upsert({
    id: "abc123::0",
    values: [0.123, -0.456, ...],  # 384-dim embedding
    metadata: {
        filename: "contract.pdf",
        file_path: "/Documents/contract.pdf",
        file_id: "abc123",
        start_char: 0,
        end_char: 1000
        # NO TEXT STORED
    }
})
```

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

### Data Protection
- **Embeddings**: One-way transformation, cannot reconstruct text
- **Positions**: Only useful with original file access
- **File Paths**: Dropbox paths, require valid access token

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
