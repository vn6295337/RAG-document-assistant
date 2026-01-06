# RAG Document Assistant

> **Search your documents with AI. Your data stays yours.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Try%20It-blue)](https://rag-document-assistant.vercel.app/)
[![Privacy](https://img.shields.io/badge/Privacy-Zero%20Storage-green)](#zero-storage-guarantee)

---

## The Problem

Organizations need AI-powered document search but face a critical barrier: **data privacy**.

Traditional solutions require uploading sensitive documents to third-party servers, creating:
- Compliance risks (GDPR, HIPAA, SOX)
- Data breach exposure
- Loss of control over proprietary information

---

## Our Solution: Zero-Storage Architecture

**Your documents stay in YOUR cloud storage. Always.**

```
┌─────────────────────────────────────────────────────────────┐
│              INDEXING (one-time setup)                       │
├─────────────────────────────────────────────────────────────┤
│   YOUR BROWSER                         OUR SERVER            │
│                                                              │
│   1. Files loaded from YOUR Dropbox                          │
│              │                                               │
│              ▼                                               │
│   2. Text chunked locally ─────────→  3. Only embeddings +   │
│              │                           file positions      │
│              ▼                           stored              │
│   4. Original text PURGED                                    │
│      (no trace remains)                                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              QUERY TIME (every search)                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Your Question ──→ Find matching ──→ Re-fetch text from    │
│                     embeddings        YOUR Dropbox           │
│                          │                   │               │
│                          ▼                   ▼               │
│                     File paths ───→ Generate answer          │
│                     + positions      (text never stored)     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Zero-Storage Guarantee

| What Happens | Where | Stored? |
|--------------|-------|---------|
| File reading | Your browser | No |
| Text chunking | Your browser | No |
| Original text | Never | No |
| Embeddings | Server | Yes (irreversible) |
| File paths + positions | Server | Yes (for re-fetch) |
| Text at query time | Re-fetched from YOUR Dropbox | No |

**Why this matters:** Your document content is NEVER stored on our servers. At query time, we use the file paths and positions to re-fetch the exact text from YOUR Dropbox. Disconnect Dropbox = queries stop working = complete data control.

---

## Why This Matters

### For Compliance Teams
- No data leaves user devices = No data breach risk
- Embeddings are not personal data = GDPR-friendly
- Audit-ready architecture

### For Security Teams
- Zero attack surface on document content
- No sensitive data in transit or at rest
- Client-side processing eliminates server vulnerabilities

### For Business Leaders
- Use AI document search without compliance reviews
- No vendor lock-in on your data
- Deploy with confidence

---

## How It Works

1. **Connect Dropbox** - OAuth authentication (we never see credentials)
2. **Select Files** - Choose .txt, .md, or .pdf files (up to 5 MB)
3. **Index** - Text processed in your browser, only embeddings sent to server
4. **Search** - Ask questions in natural language
5. **Get Answers** - Receive cited responses from your indexed content

---

## Use Cases

- **Compliance**: Search regulatory documents without data exposure
- **Legal**: Query contracts while maintaining privilege
- **HR**: Access policy documents securely
- **Research**: Search proprietary research without leakage

---

## Try It Now

**[Launch Demo](https://rag-document-assistant.vercel.app/)**

Your documents. Your device. Your privacy.
