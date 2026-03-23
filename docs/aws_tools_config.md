# RAG Pipeline Tools Configuration — AWS Deployment

## Overview

This document maps RAG pipeline stages to tools, services, and implementation status for the AWS deployment track.

| Symbol | Meaning |
|--------|---------|
| ✅ | Implemented |
| ⚠️ | Partial/Limited |
| ❌ | Not implemented |
| 🔧 | Planned |

---

## 1. Data Preparation

| Step                     | Tool/Service                 | Status | Notes                                       |
| ------------------------ | ---------------------------- | ------ | ------------------------------------------- |
| Source document cleaning | `src/ingestion/cleaner.py`   | ✅      | Whitespace normalization, encoding fixes    |
| Format normalization     | Docling                      | ✅      | Converts DOCX/PPTX/PDF to unified structure |
| Encoding handling        | Python stdlib (`io.BytesIO`) | ✅      | UTF-8 with fallback                         |
| Deduplication            | **DocumentDeduplicator**     | ✅      | `aws/src/ingestion/deduplicator.py`         |
| Quality validation       | **QualityValidator**         | ✅      | `aws/src/ingestion/quality_validator.py`    |

**AWS Resources:** None (runs in Lambda)

---

## 2. Data Ingestion & Indexing

| Step | Tool/Service | Status | Notes |
|------|--------------|--------|-------|
| Document parsing | **Docling** (primary), **PyPDF2** (fallback) | ✅ | `src/ingestion/docling_loader.py` |
| OCR for scanned docs | Tesseract (via Docling) | ✅ | Installed in `aws/Dockerfile` |
| Chunking strategy | Semantic chunking | ✅ | `src/ingestion/chunker.py` |
| Chunk sizing | 512 tokens, 64 overlap | ✅ | Configurable |
| Embedding generation | **HuggingFace API** (`all-MiniLM-L6-v2`) | ✅ | `src/ingestion/embeddings.py` |
| Vector storage | **Pinecone Serverless** | ✅ | 384-dim, cosine similarity |
| Metadata design | file_path, char_start, char_end | ✅ | Zero-storage: positions only, no text |

**AWS Resources:**
- Lambda: `rag-document-assistant-api` (container)
- SSM: `/rag_assistant/PINECONE_API_KEY`

---

## 3. Query Preprocessing

| Step | Tool/Service | Status | Notes |
|------|--------------|--------|-------|
| Query rewriting | LLM (via LiteLLM) | ✅ | `src/query/rewriter.py` |
| Query decomposition | LLM | ✅ | Breaks complex queries |
| Multi-query generation | LLM | ✅ | Generates variants |
| Hypothetical doc generation (HyDE) | `src/retrieval/hyde.py` | ✅ | AWS track only |
| Strategy auto-selection | `src/reasoning/analyzer.py` | ✅ | Determines search approach |
| Spell correction | **SpellCorrector** | ✅ | `aws/src/query/spell_corrector.py` |

**AWS Resources:** None (LLM calls to external providers)

---

## 4. Query Embedding & Context Retrieval

| Step | Tool/Service | Status | Notes |
|------|--------------|--------|-------|
| Query embedding | **HuggingFace API** | ✅ | `src/retrieval/retriever.py` |
| Vector similarity search | **Pinecone** | ✅ | Top-k retrieval |
| Keyword search | **BM25** (`rank-bm25`) | ✅ | `src/retrieval/keyword_search.py` |
| Hybrid search | Vector + BM25 fusion | ✅ | `src/retrieval/hybrid.py` |
| Multi-query merge | Result deduplication | ✅ | `src/orchestrator.py` |
| File-level batching | Dropbox re-fetch batching | ✅ | Groups by source file |

**AWS Resources:**
- Pinecone: `rag-semantic-384` index (external)

---

## 5. Context Enrichment & Assembly

| Step | Tool/Service | Status | Notes |
|------|--------------|--------|-------|
| Cross-encoder reranking | `sentence-transformers/CrossEncoder` | ✅ | `src/retrieval/reranker.py` |
| LLM-based reranking | **LLMReranker** | ✅ | `aws/src/retrieval/llm_reranker.py` |
| Semantic deduplication | Embedding similarity | ✅ | `src/context/shaper.py` |
| Token budget allocation | tiktoken-based | ✅ | Fits context to model limit |
| Sentence pruning | **SentencePruner** | ✅ | `aws/src/context/sentence_pruner.py` |
| Parent-child retrieval | **ParentChildRetriever** | ✅ | `aws/src/retrieval/parent_child.py` |
| Context window management | `src/context/shaper.py` | ✅ | Prioritizes high-score chunks |

**AWS Resources:** None (runs in Lambda)

---

## 6. Answer Generation & Grounding

| Step | Tool/Service | Status | Notes |
|------|--------------|--------|-------|
| Prompt template | `src/prompts/rag_prompt.py` | ✅ | Grounding + citation instructions |
| Grounding enforcement | Prompt engineering | ✅ | "Only use provided context" |
| Citation instruction | Inline tagging `[1]`, `[2]` | ✅ | Embedded in prompt |
| Citation extraction | Regex parsing | ✅ | `src/orchestrator.py` |
| Multi-LLM cascade | Priority fallback | ✅ | Groq → Gemini |
| LLM gateway | **LiteLLM** | ✅ | `src/llm_providers.py` |
| Streaming support | SSE generator | ✅ | `call_llm_stream()` |
| Structured response | JSON parsing | ✅ | Citations + answer |

**AWS Resources:**
- SSM: `/rag_assistant/GEMINI_API_KEY`, `GROQ_API_KEY`

**LLM Provider Cascade:**
```
1. groq/llama-3.1-8b-instant (primary)
2. gemini/gemini-2.5-flash (fallback)
```

---

## 7. Security & Governance

| Step                         | Tool/Service                 | Status | Notes                                  |
| ---------------------------- | ---------------------------- | ------ | -------------------------------------- |
| Authentication               | Dropbox OAuth                | ✅      | User-owned tokens                      |
| Role-based access            | **RBACManager**              | ✅      | `aws/src/security/rbac.py`             |
| Input validation             | Pydantic + InputGuard        | ✅      | `aws/src/security/input_guard.py`      |
| Prompt injection defense     | **InputGuard**               | ✅      | Pattern-based detection + sanitization |
| PII detection (input)        | **Presidio Analyzer**        | ✅      | `aws/src/security/pii_handler.py`      |
| PII scrubbing (output)       | **Presidio Anonymizer**      | ✅      | Configurable entity types              |
| Content safety               | **OutputGuard**              | ✅      | `aws/src/security/output_guard.py`     |
| Verbatim reproduction check  | **OutputGuard**              | ✅      | Compares output to source chunks       |
| Data exfiltration prevention | Zero-storage architecture    | ✅      | No text persisted                      |
| Token/cost governance        | **TokenBudgetManager**       | ✅      | `aws/src/governance/token_budget.py`   |
| Audit trail                  | **AuditLogger** + CloudWatch | ✅      | `aws/src/security/audit_logger.py`     |

**AWS Resources:**
- IAM: Lambda execution role (least privilege)
- SSM: SecureString parameters
- CloudWatch: Logs

**Security Modules (AWS Track):**
- `aws/src/security/pii_handler.py` — Presidio PII detection/scrubbing
- `aws/src/security/input_guard.py` — Prompt injection defense
- `aws/src/security/output_guard.py` — Output moderation + verbatim check
- `aws/src/security/audit_logger.py` — CloudWatch structured logging
- `aws/src/orchestrator_secure.py` — Secure orchestrator wrapper

---

## 8. Observability & Monitoring

| Step                       | Tool/Service                  | Status | Notes                                    |
| -------------------------- | ----------------------------- | ------ | ---------------------------------------- |
| Pipeline latency tracing   | **LangFuse**                  | ✅      | `@observe` decorators                    |
| Retrieval quality tracking | `src/evaluation/metrics.py`   | ✅      | Precision/recall                         |
| Answer quality evaluation  | `src/evaluation/diagnosis.py` | ✅      | Faithfulness scoring                     |
| Embedding drift detection  | **DriftDetector**             | ✅      | `aws/src/retrieval/drift_detector.py`    |
| LLM performance monitoring | LangFuse                      | ✅      | Token usage, latency                     |
| Failover frequency         | **FailoverTracker**           | ✅      | `aws/src/monitoring/failover_tracker.py` |
| Anomaly detection          | **AnomalyDetector**           | ✅      | `aws/src/monitoring/anomaly_detector.py` |
| Dashboard                  | CloudWatch (basic)            | ⚠️     | Lambda metrics only                      |

**AWS Resources:**
- CloudWatch Logs: `/aws/lambda/rag-document-assistant-api`
- LangFuse Cloud: External (free tier)

---

## 9. Document Lifecycle Management

| Step                      | Tool/Service                | Status | Notes                                       |
| ------------------------- | --------------------------- | ------ | ------------------------------------------- |
| Stale reference detection | **StaleDetector**           | ✅      | `aws/src/retrieval/stale_detector.py`       |
| Change detection          | **Dropbox Webhooks**        | ✅      | `aws/src/sync/dropbox_webhook.py`           |
| Re-indexing strategy      | Manual trigger              | ⚠️     | User-initiated only                         |
| Embedding versioning      | **EmbeddingVersionManager** | ✅      | `aws/src/retrieval/embedding_versioning.py` |
| Index cleanup/GC          | **IndexCleaner**            | ✅      | `aws/src/retrieval/index_cleanup.py`        |
| Parser consistency        | Docling version pinning     | ⚠️     | Not strictly enforced                       |
| Backup and recovery       | **QdrantBackupManager**     | ✅      | `aws/src/backup/qdrant_backup.py`           |

**AWS Resources:** None

---

## AWS Infrastructure Summary

| Service | Resource | Purpose |
|---------|----------|---------|
| **Lambda** | `rag-document-assistant-api` | API + RAG pipeline |
| **API Gateway** | `ur1vowo3r2` (HTTP API) | REST endpoint |
| **ECR** | `rag-document-assistant-backend` | Container image |
| **CodeBuild** | `rag-document-assistant-build` | CI/CD |
| **SSM** | `/rag_assistant/*` | Secrets |
| **S3** | `rag-assistant-frontend-*` | Static frontend |
| **CloudFront** | `d11rsilpc8ukbj` | CDN |
| **CloudWatch** | Logs + Metrics | Basic monitoring |

---

## External Services

| Service | Tier | Purpose |
|---------|------|---------|
| **Pinecone** | Serverless (free) | Vector storage |
| **HuggingFace** | Inference API (free) | Embeddings |
| **Gemini** | Free tier | Primary LLM |
| **Groq** | Free tier | Fallback LLM |
| **LangFuse** | Cloud (free) | Tracing |
| **Dropbox** | OAuth | Document source |

---

## AWS Track File Structure

```
aws/
├── Dockerfile              # Lambda container with Tesseract + Presidio
├── requirements.txt        # AWS-specific dependencies
└── src/
    ├── orchestrator_secure.py  # Secure orchestrator wrapper
    ├── api/
    │   ├── __init__.py
    │   ├── main.py             # FastAPI app with webhooks
    │   ├── security_middleware.py  # Security middleware
    │   └── webhook_routes.py   # Dropbox webhook endpoints
    ├── backup/
    │   ├── __init__.py
    │   └── qdrant_backup.py    # Qdrant backup/recovery
    ├── context/
    │   ├── __init__.py
    │   └── sentence_pruner.py  # Sentence-level pruning
    ├── ingestion/
    │   ├── __init__.py
    │   ├── deduplicator.py     # Source-level deduplication
    │   └── quality_validator.py # Pre-ingestion quality checks
    ├── monitoring/
    │   ├── __init__.py
    │   ├── failover_tracker.py # LLM failover tracking
    │   └── anomaly_detector.py # Z-score anomaly detection
    ├── query/
    │   ├── __init__.py
    │   └── spell_corrector.py  # Spell correction
    ├── retrieval/
    │   ├── __init__.py
    │   ├── hyde.py             # HyDE retrieval
    │   ├── llm_reranker.py     # LLM-based reranking
    │   ├── drift_detector.py   # Embedding drift detection
    │   ├── parent_child.py     # Parent-child retrieval
    │   ├── stale_detector.py   # Stale reference detection
    │   ├── index_cleanup.py    # Index garbage collection
    │   └── embedding_versioning.py # Model versioning/migration
    ├── governance/
    │   ├── __init__.py
    │   └── token_budget.py     # Token/cost governance
    ├── security/
    │   ├── __init__.py
    │   ├── pii_handler.py      # Presidio PII detection
    │   ├── input_guard.py      # Prompt injection defense
    │   ├── output_guard.py     # Output moderation
    │   ├── audit_logger.py     # CloudWatch audit logging
    │   └── rbac.py             # Role-based access control
    └── sync/
        ├── __init__.py
        ├── dropbox_webhook.py  # Webhook verification & handling
        └── change_tracker.py   # Delta sync with cursors
```

**Build:** `docker build -f aws/Dockerfile -t <image> .`

---

## Implementation Status

### ✅ Completed
1. ~~Prompt injection defense~~ → `aws/src/security/input_guard.py`
2. ~~PII detection with Presidio~~ → `aws/src/security/pii_handler.py`
3. ~~OCR support~~ → Tesseract in `aws/Dockerfile`
4. ~~Output moderation layer~~ → `aws/src/security/output_guard.py`
5. ~~Audit logging to CloudWatch~~ → `aws/src/security/audit_logger.py`
6. ~~Content safety classification~~ → OutputGuard patterns
7. ~~HyDE for better retrieval~~ → `aws/src/retrieval/hyde.py`
8. ~~Security integration~~ → `aws/src/orchestrator_secure.py`
9. ~~LLM-based reranking~~ → `aws/src/retrieval/llm_reranker.py`
10. ~~Embedding drift detection~~ → `aws/src/retrieval/drift_detector.py`
11. ~~Parent-child retrieval~~ → `aws/src/retrieval/parent_child.py`
12. ~~Spell correction~~ → `aws/src/query/spell_corrector.py`
13. ~~Token/cost governance~~ → `aws/src/governance/token_budget.py`
14. ~~Stale reference detection~~ → `aws/src/retrieval/stale_detector.py`
15. ~~Sentence-level pruning~~ → `aws/src/context/sentence_pruner.py`
16. ~~Deduplication~~ → `aws/src/ingestion/deduplicator.py`
17. ~~Quality validation~~ → `aws/src/ingestion/quality_validator.py`
18. ~~Failover tracking~~ → `aws/src/monitoring/failover_tracker.py`
19. ~~Index cleanup/GC~~ → `aws/src/retrieval/index_cleanup.py`
20. ~~Anomaly detection~~ → `aws/src/monitoring/anomaly_detector.py`
21. ~~Role-based access~~ → `aws/src/security/rbac.py` (4 personas: viewer, analyst, editor, admin)
22. ~~Embedding versioning~~ → `aws/src/retrieval/embedding_versioning.py`
23. ~~Backup and recovery~~ → `aws/src/backup/qdrant_backup.py` (Pinecone ↔ Qdrant)
24. ~~Change detection~~ → `aws/src/sync/dropbox_webhook.py` (Dropbox webhooks)

### 🔧 Remaining (Out of Scope)
25. Custom domain + WAF (outside Free Tier)
