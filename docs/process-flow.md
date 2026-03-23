# RAG Document Assistant - Process Flow

## What It Does

Privacy-first document search assistant. Users connect their Dropbox, and the system lets them ask natural language questions about their documents — without ever storing the actual document content on the server.

## Step-by-Step Flow

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      1. USER CONNECTS DROPBOX                                    │
├────────────────────────────────────────────────┬─────────────────────────────────────────────────┤
│  Description                                   │  Tools/Systems                                  │
├────────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│  User logs in via Dropbox OAuth                │  • Dropbox OAuth 2.0 API                        │
│  → System gets permission to read files        │  • FastAPI backend                              │
│  → Documents stay in Dropbox (never copied)    │                                                 │
└────────────────────────────────────────────────┴─────────────────────────────────────────────────┘
                                                 ↓
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      2. DOCUMENT INDEXING                                        │
├────────────────────────────────────────────────┬─────────────────────────────────────────────────┤
│  Description                                   │  Tools/Systems                                  │
├────────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│  System reads documents (PDF, Word, etc.)      │  • Docling (multi-format parser)                │
│  → Docling parses document structure           │  • Chunker (src/ingestion/chunker.py)           │
│  → Text split into chunks                      │  • Sentence-Transformers (embeddings)           │
│  → Chunks converted to embeddings              │  • Pinecone (vector database)                   │
│  → Only embeddings + metadata saved            │                                                 │
│                                                │                                                 │
│  Privacy: Actual words NOT stored on server    │                                                 │
└────────────────────────────────────────────────┴─────────────────────────────────────────────────┘
                                                 ↓
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      3. USER ASKS A QUESTION                                     │
├────────────────────────────────────────────────┬─────────────────────────────────────────────────┤
│  Description                                   │  Tools/Systems                                  │
├────────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│  Example: "What were the Q3 revenue numbers?"  │  • React frontend (Vite + Tailwind)             │
│                                                │  • FastAPI /query endpoint                      │
└────────────────────────────────────────────────┴─────────────────────────────────────────────────┘
                                                 ↓
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      4. QUERY PROCESSING                                         │
├────────────────────────────────────────────────┬─────────────────────────────────────────────────┤
│  Description                                   │  Tools/Systems                                  │
├────────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│  Question may be rewritten or expanded:        │  • Query Rewriter (src/query/rewriter.py)       │
│  → "Q3 revenue" becomes "Q3 revenue earnings"  │  • Query Analyzer (src/reasoning/analyzer.py)   │
│  → Complex questions split into sub-questions  │  • Strategies: expand, multi, decompose, auto   │
└────────────────────────────────────────────────┴─────────────────────────────────────────────────┘
                                                 ↓
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      5. FINDING RELEVANT CHUNKS                                  │
├────────────────────────────────────────────────┬─────────────────────────────────────────────────┤
│  Description                                   │  Tools/Systems                                  │
├────────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│  Two search methods run together:              │  • Pinecone (semantic vector search)            │
│                                                │  • BM25 / rank-bm25 (keyword search)            │
│  Semantic: "What chunks MEAN similar things?"  │  • Hybrid Search (src/retrieval/hybrid.py)      │
│  Keyword: "What chunks CONTAIN these words?"   │  • Reciprocal Rank Fusion (RRF)                 │
│                                                │                                                 │
│  Results combined (hybrid search)              │                                                 │
└────────────────────────────────────────────────┴─────────────────────────────────────────────────┘
                                                 ↓
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      6. RE-RANKING                                               │
├────────────────────────────────────────────────┬─────────────────────────────────────────────────┤
│  Description                                   │  Tools/Systems                                  │
├────────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│  A smarter model re-scores the chunks          │  • Cross-encoder: ms-marco-MiniLM-L-6-v2        │
│  → Picks the most relevant ones                │  • Reranker (src/retrieval/reranker.py)         │
│  → Filters out noise                           │  • Fallback: LLM-based reranking                │
└────────────────────────────────────────────────┴─────────────────────────────────────────────────┘
                                                 ↓
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      7. CONTEXT SHAPING                                          │
├────────────────────────────────────────────────┬─────────────────────────────────────────────────┤
│  Description                                   │  Tools/Systems                                  │
├────────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│  Prepares chunks for the AI:                   │  • Context Shaper (src/context/shaper.py)       │
│  → Removes duplicates                          │  • Tiktoken (token counting)                    │
│  → Fits within token budget                    │                                                 │
│  → Orders by relevance                         │                                                 │
└────────────────────────────────────────────────┴─────────────────────────────────────────────────┘
                                                 ↓
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      8. ANSWER GENERATION                                        │
├────────────────────────────────────────────────┬─────────────────────────────────────────────────┤
│  Description                                   │  Tools/Systems                                  │
├────────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│  LLM reads chunks + question                   │  • LLM Providers (src/llm_providers.py)         │
│  → Writes natural language answer              │    Priority: Groq → Gemini                       │
│  → Includes citations [ID:chunk_123]           │  • RAG Prompt (src/prompts/rag_prompt.py)       │
│  → Abstains if info not found                  │  • Chain-of-thought (src/reasoning/chain.py)    │
└────────────────────────────────────────────────┴─────────────────────────────────────────────────┘
                                                 ↓
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      9. RESPONSE TO USER                                         │
├────────────────────────────────────────────────┬─────────────────────────────────────────────────┤
│  Description                                   │  Tools/Systems                                  │
├────────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│  User sees:                                    │  • Citation extractor (regex-based)             │
│  → Answer to their question                    │  • Snippet enrichment (chunks.jsonl)            │
│  → Citations pointing to source documents      │  • FastAPI JSON response                        │
│  → (Optionally) evaluation scores              │  • React frontend                               │
└────────────────────────────────────────────────┴─────────────────────────────────────────────────┘
```

## Current Evaluation

After generating an answer, the system can optionally check quality:

```
┌─────────────────────────┬───────────────────────────────────────────────────┐
│  Check                  │  What It Does                                     │
├─────────────────────────┼───────────────────────────────────────────────────┤
│  Retrieval score        │  Did we find enough relevant chunks?              │
├─────────────────────────┼───────────────────────────────────────────────────┤
│  Citation check         │  Do the citations point to real chunks?           │
├─────────────────────────┼───────────────────────────────────────────────────┤
│  Keyword coverage       │  Does the answer contain expected terms?          │
├─────────────────────────┼───────────────────────────────────────────────────┤
│  Format check           │  Are citations properly formatted?                │
└─────────────────────────┴───────────────────────────────────────────────────┘
```

These are basic heuristic checks — fast but not deeply intelligent.
