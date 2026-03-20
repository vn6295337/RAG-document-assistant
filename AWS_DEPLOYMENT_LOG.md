# AWS Deployment & Production Refactor Log

This document records the actions, rationales, and architectural decisions made during the transition of the RAG Document Assistant from a local PoC to a production-grade AWS deployment.

---

## 1. Architectural Refactoring (Backend)

### **Action: Unified Orchestration**
- **Changes**: Created `orchestrate_zero_storage` in `src/orchestrator.py` and refactored `src/api/routes.py` to call it.
- **Rationale**: The "Zero-Storage" logic (Dropbox re-fetching via character offsets) was previously coupled with the FastAPI route. Moving it to the orchestrator enables:
    - **Testability**: Independent testing of the RAG pipeline without an HTTP server.
    - **Observability**: Cleaner integration with tracing decorators (LangFuse).
    - **Streaming**: Prepared the core logic for conversion to a generator-based streaming response.

### **Action: LiteLLM Integration**
- **Changes**: Replaced manual `requests`-based API calls in `src/llm_providers.py` with the `liteLLM` gateway.
- **Rationale**: LiteLLM provides a unified OpenAI-compatible interface for Gemini, Groq, and OpenRouter. This reduces boilerplate, standardizes error handling, and allows for instant model/provider switching without changing core RAG logic.

### **Action: Observability Integration (LangFuse)**
- **Changes**: Added `langfuse` library and `@observe` decorators to the unified orchestrator.
- **Rationale**: A production prototype must be measurable. LangFuse provides tracing of the entire retrieval chain, allowing us to monitor latency and token costs on lightweight hardware (Chromebook).

---

## 2. Dual-Track Architecture Decision

### **Context**
The project requires two independent deployment tracks:
1. **HuggingFace/Vercel Track**: Original deployment for HuggingFace Spaces with Vercel frontend
2. **AWS Track**: Fully cloud-hosted on AWS Free Tier, independent of local Chromebook

### **Decision: Separate AWS Track**
- **Rationale**: AWS deployment must be completely self-contained with no dependencies on local machine
- **Implementation**: Created `aws/` directory with AWS-specific files that override shared code

### **File Structure**
```
ragDocumentAssistant/
├── Dockerfile              # HuggingFace Spaces (shared track)
├── requirements.txt        # HuggingFace Spaces dependencies
├── src/                    # Shared source code
├── aws/                    # AWS-specific track
│   ├── Dockerfile          # Lambda container with Tesseract + Presidio
│   ├── requirements.txt    # AWS-specific dependencies
│   └── src/
│       ├── security/       # Security modules (AWS only)
│       └── retrieval/      # Enhanced retrieval (AWS only)
└── buildspec.yml           # CodeBuild uses aws/Dockerfile
```

---

## 3. AWS Infrastructure Provisioning

### **Strategy: Manual CLI Provisioning**
- **Context**: The local Chromebook environment (Intel Celeron N3350) lacked Docker and Terraform support within the Linux container.
- **Decision**: Provisioned AWS resources directly via the AWS CLI to bypass local environmental constraints while staying strictly within the **AWS Free Tier**.

### **Actions Taken**

#### 3.1 IAM Role & Security
- Created `rag_assistant_lambda_role`
- Configured **Trust Policy** allowing `lambda.amazonaws.com` to assume the role
- Attached policies:
  - `AWSLambdaBasicExecutionRole` (CloudWatch logging)
  - Custom policy for **SSM Parameter Store** access

#### 3.2 Container Registry (ECR)
- Repository: `rag-document-assistant-backend`
- Latest image: `691210491730.dkr.ecr.us-east-1.amazonaws.com/rag-document-assistant-backend:latest`

#### 3.3 Compute (Lambda)
- Function: `rag-document-assistant-api`
- Runtime: Container image (Python 3.11)
- Memory: 1024 MB
- Timeout: 30s
- Uses **AWS Lambda Web Adapter** for FastAPI compatibility

#### 3.4 API Gateway (HTTP API v2)
- API ID: `ur1vowo3r2`
- Endpoint: `https://ur1vowo3r2.execute-api.us-east-1.amazonaws.com/api`
- Integration: `AWS_PROXY` (Payload 2.0)

#### 3.5 Secrets (SSM Parameter Store)
- `/rag_assistant/PINECONE_API_KEY` (SecureString)
- `/rag_assistant/GEMINI_API_KEY` (SecureString)

#### 3.6 CI/CD (CodeBuild)
- Project: `rag-document-assistant-build`
- Source: GitHub repository
- Build spec: `buildspec.yml` → uses `aws/Dockerfile`

#### 3.7 Frontend Hosting
- S3 Bucket: `rag-assistant-frontend-691210491730`
- CloudFront Distribution: `d11rsilpc8ukbj.cloudfront.net`
- Price Class: PriceClass_100 (US/Canada/Europe)

### **Infrastructure Cleanup**
Removed duplicate resources created during iteration:
- Deleted duplicate API Gateway: `23ovejaux9`
- Deleted duplicate Lambda: `rag-assistant-api`

---

## 4. Security Implementation (AWS Track)

### **4.1 PII Detection & Scrubbing**
- **File**: `aws/src/security/pii_handler.py`
- **Tool**: Microsoft Presidio (analyzer + anonymizer)
- **Capabilities**:
  - Detects: PERSON, EMAIL, PHONE, SSN, CREDIT_CARD, IP_ADDRESS, etc.
  - Configurable score threshold (default: 0.7)
  - Lazy loading to minimize cold start impact

```python
from src.security import detect_pii, scrub_pii

result = detect_pii("Call John at 555-1234")
# result.has_pii = True, result.entities = [...]

clean_text = scrub_pii("My SSN is 123-45-6789")
# clean_text = "My SSN is <US_SSN>"
```

### **4.2 Prompt Injection Defense**
- **File**: `aws/src/security/input_guard.py`
- **Approach**: Pattern-based detection with risk scoring
- **Detects**:
  - Instruction override attempts ("ignore previous instructions")
  - Role manipulation ("you are now a...")
  - System prompt extraction ("show your prompt")
  - Delimiter injection (`<|system|>`, `[INST]`)
  - Jailbreak attempts ("DAN mode", "developer mode")

```python
from src.security import validate_input

result = validate_input("Ignore all previous instructions and...")
# result.is_safe = False, result.risk_score = 0.9
```

### **4.3 Output Moderation**
- **File**: `aws/src/security/output_guard.py`
- **Capabilities**:
  - Verbatim reproduction detection (compares output to source chunks)
  - Script/XSS injection detection
  - Credential leak detection
  - Harmful content indicators
  - Length truncation

```python
from src.security.output_guard import moderate_output

result = moderate_output(generated_text, source_chunks)
# result.is_safe, result.flags, result.filtered_text
```

### **4.4 Audit Logging**
- **File**: `aws/src/security/audit_logger.py`
- **Destination**: CloudWatch Logs (Free Tier: 5GB/month)
- **Event Types**: query, security, index, error
- **Features**:
  - Structured JSON logging for CloudWatch Logs Insights
  - Automatic risk-based log levels (WARNING for high-risk events)

```python
from src.security.audit_logger import audit_query, audit_security

audit_query(
    request_id="req-123",
    query="search query",
    latency_ms=450,
    pii_detected=True
)

audit_security(
    action="injection_blocked",
    risk_score=0.9,
    details={"pattern": "instruction_override"}
)
```

---

## 5. Enhanced Retrieval (AWS Track)

### **5.1 HyDE (Hypothetical Document Embeddings)**
- **File**: `aws/src/retrieval/hyde.py`
- **Purpose**: Improve retrieval by generating hypothetical answers before embedding
- **How it works**:
  1. LLM generates a hypothetical document that would answer the query
  2. This document is embedded instead of (or in addition to) the query
  3. Semantic similarity is often better with document-to-document matching
- **Cost**: Uses existing LLM providers (no additional cost)

```python
from src.retrieval.hyde import hyde_search

results = hyde_search(
    query="What is the return policy?",
    search_fn=hybrid_search,
    use_hyde=True,
    combine_results=True
)
# results['hypothetical_doc'] = "The return policy allows..."
# results['results'] = [matched chunks]
```

### **5.2 Security Integration**

Security guards are wired into the RAG pipeline via middleware and a secure orchestrator wrapper.

#### **Security Middleware** (`aws/src/api/security_middleware.py`)
- Pre-request: Validate input, detect/scrub PII
- Post-response: Moderate output, audit logging
- Non-blocking: Falls back gracefully if security modules unavailable

```python
from src.api.security_middleware import (
    secure_query_request,
    secure_query_response,
    apply_security_to_query_request
)

# Pre-process query
processed_query, ctx, error = secure_query_request(
    query=user_query,
    request_id=req_id,
    block_on_injection=True
)

if error:
    return error  # High-risk injection blocked
```

#### **Secure Orchestrator** (`aws/src/orchestrator_secure.py`)
Wraps `orchestrate_zero_storage` with full security pipeline:

```python
from src.orchestrator_secure import orchestrate_zero_storage_secure

result = await orchestrate_zero_storage_secure(
    query=query,
    access_token=token,
    enable_security=True,
    block_high_risk_injection=True,
    scrub_pii_input=True,
    scrub_pii_output=True
)

# result['security'] contains:
# - request_id: Unique request ID
# - injection_risk: Risk score (0-1)
# - pii_detected: Boolean
# - output_safe: Boolean
# - output_flags: List of moderation flags
```

### **5.3 LLM-Based Reranking**
- **File**: `aws/src/retrieval/llm_reranker.py`
- **Purpose**: Alternative to cross-encoder for nuanced relevance judgment
- **Features**:
  - LLM relevance scoring with optional reasoning
  - Hybrid mode combining cross-encoder + LLM scores
  - Configurable score weighting

```python
from src.retrieval.llm_reranker import llm_rerank, hybrid_rerank

# LLM-only reranking
result = llm_rerank(query, chunks, top_k=5, with_reasoning=True)

# Hybrid: cross-encoder + LLM
result = hybrid_rerank(query, chunks, use_cross_encoder=True, use_llm=True)
```

### **5.4 Embedding Drift Detection**
- **File**: `aws/src/retrieval/drift_detector.py`
- **Purpose**: Monitor embedding quality over time
- **Detects**: Model changes, corpus drift, index staleness

```python
from src.retrieval.drift_detector import check_drift_sync, get_drift_detector

# Check drift against baseline
report = check_drift_sync(query_embeddings, chunk_embeddings)
# report.drift_score, report.recommendations
```

### **5.5 Spell Correction**
- **File**: `aws/src/query/spell_corrector.py`
- **Purpose**: Query preprocessing for typo correction
- **Features**:
  - Common misspelling dictionary
  - Edit-distance suggestions
  - Domain vocabulary support

```python
from src.query.spell_corrector import correct_query

result = correct_query("retreive documnet")
# result.corrected = "retrieve document"
```

### **5.6 Parent-Child Retrieval**
- **File**: `aws/src/retrieval/parent_child.py`
- **Purpose**: Hierarchical chunking for context expansion
- **Strategy**: Search child chunks, expand to parent context

```python
from src.retrieval.parent_child import create_parent_child_index, expand_results_with_parents

# Create hierarchy
all_chunks, child_to_parent = create_parent_child_index(documents)

# Expand search results
expanded = expand_results_with_parents(results, child_to_parent, parent_chunks)
```

### **5.7 Token/Cost Governance**
- **File**: `aws/src/governance/token_budget.py`
- **Purpose**: Track and limit LLM token usage
- **Features**:
  - Daily/monthly budget limits
  - Per-model cost estimation
  - Usage alerts and throttling

```python
from src.governance.token_budget import record_llm_usage, check_budget

# Record usage
record_llm_usage("gemini", "gemini-2.5-flash", input_tokens=500, output_tokens=200)

# Check budget status
status = check_budget()
# status['within_budget'], status['warnings']
```

### **5.8 Stale Reference Detection**
- **File**: `aws/src/retrieval/stale_detector.py`
- **Purpose**: Detect outdated references in the vector index
- **Detects**:
  - Deleted documents
  - Modified documents (content hash changed)
  - Aged documents (not verified recently)

```python
from src.retrieval.stale_detector import register_indexed_document, check_for_stale_references

# Register after indexing
register_indexed_document(file_path, file_id, content, chunk_count)

# Check for stale references
report = check_for_stale_references(documents)
# report.modified_count, report.deleted_count, report.recommendations
```

### **5.9 Sentence-Level Pruning**
- **File**: `aws/src/context/sentence_pruner.py`
- **Purpose**: Remove low-relevance sentences to optimize context
- **Signals used**:
  - Query term overlap
  - Position (first/last sentences)
  - Importance markers ("importantly", "in conclusion")
  - Sentence length

```python
from src.context.sentence_pruner import prune_chunks

# Prune chunks to 70% of original size
pruned_chunks, stats = prune_chunks(chunks, query, target_ratio=0.7)
# stats['overall_compression'], stats['chunks_pruned']
```

### **5.10 Anomaly Detection**
- **File**: `aws/src/monitoring/anomaly_detector.py`
- **Purpose**: Detect anomalies in RAG pipeline metrics
- **Detects**:
  - Latency spikes (z-score based)
  - Error rate increases
  - Token usage anomalies
  - Retrieval quality drops
  - Metric drift over time

```python
from src.monitoring.anomaly_detector import record_request_metrics, get_anomaly_report

# Record request metrics
record_request_metrics(
    latency_ms=450,
    token_count=500,
    retrieval_score=0.85,
    is_error=False,
    query_length=50
)

# Get anomaly report
report = get_anomaly_report(hours=24)
# report.anomalies_detected, report.critical_count, report.warning_count
```

### **5.11 Role-Based Access Control (RBAC)**
- **File**: `aws/src/security/rbac.py`
- **Purpose**: Multi-user access control with role-based permissions
- **Personas**:
  - **Viewer**: Read-only, basic queries (50K tokens/day, 30 RPM)
  - **Analyst**: Advanced queries, batch API (200K tokens/day, 60 RPM)
  - **Editor**: Document management, indexing (500K tokens/day, 120 RPM)
  - **Admin**: Full access, user management (1M tokens/day, 300 RPM)

```python
from src.security.rbac import add_user, check_query_access, get_user_limits

# Add a user
user = add_user("user-123", "analyst@example.com", "Jane Doe", role="analyst")

# Check query access
result = check_query_access("user-123", query_length=500, top_k=10, use_advanced=True)
# result.allowed, result.reason, result.role.permissions

# Get user limits
limits = get_user_limits("user-123")
# limits['token_limit_daily'], limits['rate_limit_rpm']
```

### **5.12 Embedding Versioning**
- **File**: `aws/src/retrieval/embedding_versioning.py`
- **Purpose**: Track embedding model versions for safe upgrades
- **Features**:
  - Version registration with metadata
  - Migration planning (cost/time estimates)
  - Parallel index support during migration
  - Rollback capability

```python
from src.retrieval.embedding_versioning import (
    register_embedding_version,
    get_active_embedding_version,
    plan_embedding_migration
)

# Register a version
version = register_embedding_version(
    model_name="all-MiniLM-L6-v2",
    provider="huggingface",
    dimension=384,
    set_active=True
)

# Plan migration to new model
plan = plan_embedding_migration(
    target_model="all-mpnet-base-v2",
    target_provider="huggingface",
    target_dimension=768
)
# plan.estimated_cost, plan.estimated_time_minutes, plan.strategy
```

### **5.13 Backup and Recovery (Qdrant)**
- **File**: `aws/src/backup/qdrant_backup.py`
- **Purpose**: Backup Pinecone vectors to Qdrant for disaster recovery
- **Features**:
  - Full backup from Pinecone to Qdrant
  - Point-in-time recovery
  - Incremental backup support
  - Backup management (list, delete, stats)

```python
from src.backup.qdrant_backup import backup_to_qdrant, recover_from_qdrant, list_backups

# Backup Pinecone to Qdrant
backup = backup_to_qdrant(pinecone_index, namespace="")
# backup.backup_id, backup.vector_count, backup.status

# Recovery to Pinecone
result = recover_from_qdrant(pinecone_index, backup_id="backup_20240315_120000")
# result.vectors_recovered, result.success

# List backups
backups = list_backups()
```

### **5.14 Change Detection (Dropbox Webhooks)**
- **Files**:
  - `aws/src/sync/dropbox_webhook.py` - Webhook verification and handling
  - `aws/src/sync/change_tracker.py` - Delta sync with cursors
  - `aws/src/api/webhook_routes.py` - API endpoints
- **Purpose**: Automatic detection of file changes in Dropbox
- **How it works**:
  1. Register webhook URL in Dropbox App Console
  2. Dropbox sends GET challenge for verification
  3. On file changes, Dropbox sends POST notification
  4. We use cursor-based delta sync to get actual changes
  5. Changes are queued for re-indexing

**Webhook Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/webhook/dropbox` | GET | Verification challenge |
| `/api/webhook/dropbox` | POST | Change notifications |
| `/api/sync/status` | GET | Current sync status |
| `/api/sync/init` | POST | Initialize cursor |
| `/api/sync/check` | POST | Get changes since last sync |
| `/api/sync/pending` | GET | List pending changes |
| `/api/sync/mark-processed` | POST | Mark changes as processed |

```python
# Initialize sync (one-time setup)
POST /api/sync/init
{"access_token": "dropbox_token", "path": ""}

# Check for changes
POST /api/sync/check
{"access_token": "dropbox_token"}
# Returns: {"changes": [{"path": "/doc.pdf", "type": "modified"}]}

# Get pending changes
GET /api/sync/pending
# Returns: {"pending": [...], "count": 3}

# After re-indexing, mark as processed
POST /api/sync/mark-processed
{"paths": ["/doc.pdf"]}
```

**Dropbox App Console Setup:**
1. Go to https://www.dropbox.com/developers/apps
2. Select your app → Webhooks
3. Add webhook URL: `https://ur1vowo3r2.execute-api.us-east-1.amazonaws.com/api/webhook/dropbox`
4. Dropbox will verify with GET challenge

---

## 6. AWS Dockerfile Configuration

### **File**: `aws/Dockerfile`

```dockerfile
FROM public.ecr.aws/docker/library/python:3.11-slim

# AWS Lambda Web Adapter
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.8.4-x86_64 /lambda-adapter /opt/extensions/lambda-adapter

# System dependencies: Tesseract OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ make curl \
    tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# AWS-specific requirements (includes Presidio)
COPY aws/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Shared source + AWS overrides
COPY src/ ./src/
COPY aws/src/ ./src/

CMD ["python3", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### **Key Differences from HF Dockerfile**
| Feature | HuggingFace | AWS |
|---------|-------------|-----|
| Base Image | python:3.11-slim | python:3.11-slim |
| Port | 7860 | 8080 |
| OCR | Not included | Tesseract installed |
| Security | Not included | Presidio + guards |
| Adapter | None | Lambda Web Adapter |

---

## 7. AWS Requirements

### **File**: `aws/requirements.txt`

```
# Core
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
httpx>=0.27.0
pydantic>=2.0.0

# RAG
pinecone>=5.0.0
rank-bm25>=0.2.2
PyPDF2>=3.0.0
boto3>=1.34.0
numpy<2.0.0

# LLM
litellm>=1.0.0

# Observability
langfuse>=2.0.0

# Security
presidio-analyzer>=2.2.0
presidio-anonymizer>=2.2.0
```

---

## 8. Deployment Summary

### **AWS Resources**

| Resource | Service | Identifier | Cost Tier |
|----------|---------|------------|-----------|
| Compute | Lambda | `rag-document-assistant-api` | Free (1M req/mo) |
| API | API Gateway v2 | `ur1vowo3r2` | Free (1M req/mo) |
| Registry | ECR | `rag-document-assistant-backend` | Free (500MB/mo) |
| Build | CodeBuild | `rag-document-assistant-build` | Free (100 min/mo) |
| Secrets | SSM | `/rag_assistant/*` | Free |
| Frontend | S3 | `rag-assistant-frontend-*` | Free (5GB) |
| CDN | CloudFront | `d11rsilpc8ukbj` | Free (1TB/mo) |
| Logging | CloudWatch | Auto-created | Free (5GB/mo) |

### **External Services (Free Tier)**

| Service | Purpose | Tier |
|---------|---------|------|
| Pinecone | Vector storage | Serverless (free) |
| HuggingFace | Embeddings API | Inference (free) |
| Gemini | Primary LLM | Free tier |
| Groq | Fallback LLM | Free tier |
| OpenRouter | Final fallback | Free tier |
| LangFuse | Tracing | Cloud (free) |
| Dropbox | Document source | OAuth |

### **Endpoints**

| Track | Frontend | Backend |
|-------|----------|---------|
| HuggingFace/Vercel | `rag-document-assistant.vercel.app` | HuggingFace Spaces |
| AWS | `d11rsilpc8ukbj.cloudfront.net` | `ur1vowo3r2.execute-api.us-east-1.amazonaws.com/api` |

---

## 9. Build & Deploy Commands

### **Trigger CodeBuild**
```bash
aws codebuild start-build --project-name rag-document-assistant-build
```

### **Update Lambda (after build)**
```bash
aws lambda update-function-code \
  --function-name rag-document-assistant-api \
  --image-uri 691210491730.dkr.ecr.us-east-1.amazonaws.com/rag-document-assistant-backend:latest
```

### **Deploy Frontend**
```bash
cd frontend
npm run build
aws s3 sync dist/ s3://rag-assistant-frontend-691210491730/ --delete
aws cloudfront create-invalidation --distribution-id ERS7ZCZYR2KQS --paths "/*"
```

### **Check API Health**
```bash
curl https://ur1vowo3r2.execute-api.us-east-1.amazonaws.com/api/health
# {"status":"ok","environment":"production"}
```

---

## 10. Implementation Status

### ✅ Completed
| Item                     | File/Resource                            |
| ------------------------ | ---------------------------------------- |
| Dual-track architecture  | `aws/` directory                         |
| Lambda + API Gateway     | `rag-document-assistant-api`             |
| CloudFront CDN           | `d11rsilpc8ukbj.cloudfront.net`          |
| CodeBuild CI/CD          | `rag-document-assistant-build`           |
| Tesseract OCR            | `aws/Dockerfile`                         |
| PII detection (Presidio) | `aws/src/security/pii_handler.py`        |
| Prompt injection defense | `aws/src/security/input_guard.py`        |
| Output moderation        | `aws/src/security/output_guard.py`       |
| Audit logging            | `aws/src/security/audit_logger.py`       |
| HyDE retrieval           | `aws/src/retrieval/hyde.py`              |
| Security middleware      | `aws/src/api/security_middleware.py`     |
| Secure orchestrator      | `aws/src/orchestrator_secure.py`         |
| LLM-based reranking      | `aws/src/retrieval/llm_reranker.py`      |
| Embedding drift detection| `aws/src/retrieval/drift_detector.py`    |
| Spell correction         | `aws/src/query/spell_corrector.py`       |
| Parent-child retrieval   | `aws/src/retrieval/parent_child.py`      |
| Token/cost governance    | `aws/src/governance/token_budget.py`     |
| Stale reference detection| `aws/src/retrieval/stale_detector.py`    |
| Sentence-level pruning   | `aws/src/context/sentence_pruner.py`     |
| Deduplication            | `aws/src/ingestion/deduplicator.py`      |
| Quality validation       | `aws/src/ingestion/quality_validator.py` |
| Failover tracking        | `aws/src/monitoring/failover_tracker.py` |
| Index cleanup/GC         | `aws/src/retrieval/index_cleanup.py`     |
| Anomaly detection        | `aws/src/monitoring/anomaly_detector.py` |
| Role-based access (RBAC) | `aws/src/security/rbac.py`               |
| Embedding versioning     | `aws/src/retrieval/embedding_versioning.py` |
| Backup/recovery (Qdrant) | `aws/src/backup/qdrant_backup.py`        |
| Change detection         | `aws/src/sync/dropbox_webhook.py`        |

### 🔧 Remaining (Out of Scope)
| Item                      | Priority | Notes                       |
| ------------------------- | -------- | --------------------------- |
| Custom domain + WAF       | Low      | Outside Free Tier           |

---

## 11. Cost Projection (AWS Free Tier)

| Service | Free Tier Limit | Expected Usage | Status |
|---------|-----------------|----------------|--------|
| Lambda | 1M requests/mo | <10K | ✅ Safe |
| API Gateway | 1M requests/mo | <10K | ✅ Safe |
| ECR | 500MB storage | ~250MB | ✅ Safe |
| CodeBuild | 100 min/mo | ~10 min | ✅ Safe |
| S3 | 5GB storage | <10MB | ✅ Safe |
| CloudFront | 1TB transfer | <1GB | ✅ Safe |
| CloudWatch | 5GB logs/mo | <500MB | ✅ Safe |

**Estimated Monthly Cost: $0** (within Free Tier)

---

## 12. Documentation References

| Document | Purpose |
|----------|---------|
| `docs/aws_tools_config.md` | RAG pipeline tools mapping |
| `AI_CONTEXT.md` | Technical context for AI assistants |
| `README.md` | Project overview |
| `SECURITY.md` | Security architecture |
