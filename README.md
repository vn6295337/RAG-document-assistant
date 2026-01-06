---
title: RAG Document Assistant
emoji: 🔒
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
license: mit
app_port: 7860
short_description: Privacy-first document search with zero storage
---

# RAG Document Assistant

**Privacy-first document search. Your data never leaves your device.**

[![Privacy](https://img.shields.io/badge/Privacy-Zero%20Storage-green)](#privacy-first-architecture)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

| Resource | Link |
|----------|------|
| Live Demo | [rag-document-assistant.vercel.app](https://rag-document-assistant.vercel.app/) |
| Product Demo Video | [Pre-recorded Demo](https://github.com/vn6295337/RAG-document-assistant/issues/2) |
| Business Guide | [BUSINESS_README.md](BUSINESS_README.md) |

---

## Privacy-First Architecture

```
INDEXING (one-time)
───────────────────────────────────────────────────────────
Your Device                           Server
───────────────────────────────────────────────────────────
  Dropbox ──→ Files loaded
              in browser
                 │
                 ▼
           Text chunked ─────────────→ Embeddings +
           locally                     file positions only
                 │                     (no text stored)
                 ▼
           Original text
           PURGED ✓
───────────────────────────────────────────────────────────

QUERY TIME (every search)
───────────────────────────────────────────────────────────
Your Question ──→ Find matching ──→ Re-fetch text
                  embeddings        from YOUR Dropbox
                       │                  │
                       ▼                  ▼
                  File paths ───→ Extract chunks ──→ Answer
                  + positions     using positions    generated
───────────────────────────────────────────────────────────
```

### True Zero-Storage Privacy

1. **Client-Side Chunking**: Documents are read and chunked entirely in your browser
2. **Embeddings Only**: Only mathematical vectors are stored (irreversible)
3. **No Text Stored**: Only file paths and character positions are kept
4. **Query-Time Re-fetch**: Text is retrieved fresh from YOUR Dropbox for each query
5. **You Control Access**: Disconnect Dropbox = queries stop working = your data stays yours

## How It Works

1. **Connect** - Link your Dropbox account (OAuth - we never see your password)
2. **Select** - Choose files to index (.txt, .md, .pdf up to 5 MB)
3. **Process** - Text is chunked and embedded in your browser
4. **Search** - Query your documents with natural language
5. **Answer** - Get cited responses from your indexed content

## What Gets Stored

| Data | Stored? | Where |
|------|---------|-------|
| Your files | No | Stay in YOUR Dropbox |
| Document text | No | Re-fetched at query time |
| Embeddings | Yes | Pinecone (encrypted) |
| File paths | Yes | Pinecone metadata |
| Chunk positions | Yes | Pinecone metadata |
| Queries | No | Not logged |

Embeddings are mathematical vectors that cannot be reversed to reconstruct text. File paths and positions are used to re-fetch the exact text from your Dropbox when you search.

## Quick Start

```bash
git clone https://github.com/vn6295337/RAG-document-assistant.git
cd RAG-document-assistant

# Backend
pip install -r requirements.txt
uvicorn src.api.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

## Tech Stack

- **Frontend**: React + Vite + Tailwind CSS
- **Backend**: FastAPI on HuggingFace Spaces
- **Vector DB**: Pinecone (embeddings only)
- **File Source**: Dropbox OAuth
- **LLM**: Multi-provider fallback (Gemini, Groq, OpenRouter)

## Documentation

- [Architecture](docs/architecture.md) - Technical design
- [API Reference](docs/api_reference.md) - Backend endpoints
- [Business Overview](BUSINESS_README.md) - Use cases and value

## License

MIT License - see [LICENSE](LICENSE)
