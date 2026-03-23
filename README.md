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
INDEXING (one-time) - Single Download
───────────────────────────────────────────────────────────
Your Device                           Server (Zero-Disk)
───────────────────────────────────────────────────────────
  1. Select files
     from Dropbox
         │
         └────────────────────────→ 2. Download ONCE from
                                      your Dropbox
                                         │
                                      3. Parse with Docling
                                         (BytesIO - RAM only)
                                         │
         ┌───────────────────────────────┘
         │
  4. Display structure ◄─────────── Returns: structure +
     for review                     full_text (for chunking)
         │
  5. Chunk text
     locally (browser)
         │
         └────────────────────────→ 6. Generate embeddings
                                      (text discarded)
                                         │
                                      7. Store in Pinecone:
                                         - Embeddings only
                                         - File positions
                                         - NO TEXT
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

1. **Single Download**: Each file downloaded once, parsed with Docling, returns text + structure
2. **Zero-Disk Processing**: Parsing uses BytesIO/DocumentStream (RAM only, no temp files)
3. **Client-Side Chunking**: Docling output chunked in your browser
4. **Embeddings Only**: Only mathematical vectors stored (irreversible)
5. **No Text Stored**: Only file paths and character positions kept
6. **Query-Time Re-fetch**: Text retrieved fresh from YOUR Dropbox for each query
7. **You Control Access**: Disconnect Dropbox = queries stop working = your data stays yours

> **Note**: Zero-disk guarantee requires swap to be disabled on the deployment server. See [SECURITY.md](SECURITY.md) for details.

## How It Works

1. **Connect** - Link your Dropbox account (OAuth - we never see your password)
2. **Select** - Choose files to index (.txt, .md, .pdf up to 5 MB)
3. **Process** - Text is chunked and embedded in your browser
4. **Search** - Query your documents with natural language
5. **Answer** - Get cited responses from your indexed content

## Supported File Types

| Format | Support | Notes |
|--------|---------|-------|
| PDF (text-based) | ✅ Full | Docling with PyPDF2 fallback |
| PDF (scanned/image) | ⚠️ Limited | Requires OCR (Tesseract) |
| DOCX, PPTX, XLSX | ✅ Full | Via Docling |
| TXT, Markdown | ✅ Full | Direct text extraction |
| HTML | ✅ Full | Via Docling |
| Images (PNG, JPG) | ⚠️ Limited | Requires OCR |

> **Note**: Scanned PDFs and images require Tesseract OCR installed on the server for text extraction.

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
- **LLM**: Multi-provider fallback (Groq primary, Gemini fallback)

## Documentation

- [Architecture](docs/architecture.md) - Technical design
- [API Reference](docs/api_reference.md) - Backend endpoints
- [Business Overview](BUSINESS_README.md) - Use cases and value

## License

MIT License - see [LICENSE](LICENSE)
