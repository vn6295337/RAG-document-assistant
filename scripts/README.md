# Scripts Directory

This directory contains utility scripts for various operational tasks related to the RAG Document Assistant.

## Script Organization

Scripts are organized by functional category:

### Ingestion
- `test_ingestion.py` - Test the document ingestion pipeline
- `ingest_documents.py` - Run the full document ingestion process
- `regenerate_with_semantic.py` - Regenerate embeddings using semantic model

### Search
- `search_documents.py` - Perform local similarity search over embeddings

### Verification
- `check_pinecone.py` - Verify Pinecone connectivity
- `check_index_metadata.py` - Check index metadata

## Usage

Most scripts can be run directly with Python:

```bash
python scripts/script_name.py [arguments]
```

Refer to each script's documentation for specific usage instructions.