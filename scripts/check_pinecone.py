# RAG-document-assistant/scripts/check_pinecone.py
"""
Pinecone connectivity check for pinecone>=5.x SDK.

Purpose:
    Verifies Pinecone connectivity by reading the API key and attempting to list indexes.
    Useful for initial setup verification and troubleshooting connection issues.

Inputs:
    Reads API key from ~/secrets/pinecone.key

Outputs:
    Prints connectivity status and list of available indexes
    Exits with code 0 for success, non-zero for errors

Usage:
    python scripts/check_pinecone.py
"""

import os
import sys
from pathlib import Path

KEY_PATH = os.path.expanduser("~/secrets/pinecone.key")

def read_key(path):
    if not os.path.exists(path):
        print(f"ERROR: Pinecone key not found at {path}")
        sys.exit(2)
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

def main():
    key = read_key(KEY_PATH)

    try:
        from pinecone import Pinecone
    except Exception as e:
        print("Pinecone client not installed or import failed:", str(e))
        print("Install in aienv with: pip install 'pinecone>=5.0.0'")
        sys.exit(3)

    try:
        # Create client instance. If you use a specific region (ServerlessSpec), set via env or here.
        pc = Pinecone(api_key=key)

        # list_indexes() may return a response object; attempt to extract names robustly
        idxs_resp = pc.list_indexes()
        # try common patterns
        if hasattr(idxs_resp, "names"):
            idxs = idxs_resp.names()
        elif isinstance(idxs_resp, (list, tuple)):
            idxs = list(idxs_resp)
        elif hasattr(idxs_resp, "indexes"):
            idxs = list(idxs_resp.indexes)
        else:
            # fallback: stringify
            idxs = [str(idxs_resp)]
    except Exception as e:
        print("Pinecone init/list_indexes failed:", str(e))
        sys.exit(4)

    print("Pinecone connectivity OK. Indexes found:", len(idxs))
    for idx in idxs[:20]:
        print(" -", idx)
    sys.exit(0)

if __name__ == "__main__":
    main()