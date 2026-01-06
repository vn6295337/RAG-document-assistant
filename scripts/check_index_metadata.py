# RAG-document-assistant/scripts/check_index_metadata.py
"""
Check Pinecone index metadata using pinecone>=5.x SDK.

Purpose:
    Checks and displays metadata for the configured Pinecone index, including dimensions,
    metric type, and vector count. Ensures the index configuration matches the ingestion pipeline.

Inputs:
    Uses configuration from src.config (PINECONE_API_KEY, PINECONE_INDEX_NAME)

Outputs:
    Prints index metadata and statistics to stdout

Usage:
    python scripts/check_index_metadata.py
"""

import os
import sys
from pinecone import Pinecone

# Add parent to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import src.config as cfg

def main():
    pc = Pinecone(api_key=cfg.PINECONE_API_KEY)

    index_name = cfg.PINECONE_INDEX_NAME
    idx = pc.Index(index_name)

    # Stats call provides useful metadata
    stats = idx.describe_index_stats()

    print("Index:", index_name)
    print("describe_index_stats():")
    print(stats)

if __name__ == "__main__":
    main()