---
title: RAG PoC
emoji: 🔍
colorFrom: blue
colorTo: purple
sdk: streamlit
sdk_version: "1.40.0"
app_file: app.py
pinned: false
---

# RAG Proof of Concept

A Retrieval-Augmented Generation (RAG) system built with:
- **Semantic Search**: sentence-transformers (all-MiniLM-L6-v2)
- **Vector Database**: Pinecone (384-dim embeddings)
- **LLM Generation**: Gemini, Groq, or OpenRouter
- **UI**: Streamlit

## Features

- ✅ Semantic document retrieval
- ✅ Multi-provider LLM support (automatic fallback)
- ✅ Citation tracking
- ✅ Real-time query interface

## Architecture

```
User Query → Semantic Embedding → Pinecone Search → LLM Generation → Answer + Citations
```

## Try it!

Enter a question like:
- "what is GDPR"
- "what are privacy requirements"
- "how does data protection work"

## Tech Stack

- **Embeddings**: sentence-transformers (free, local)
- **Vector DB**: Pinecone (serverless)
- **LLM**: Gemini 2.5 Flash (primary)
- **Framework**: Streamlit

---

Built with [Claude Code](https://claude.com/claude-code)
