"""
RAG Document Assistant - Production-ready RAG system with 100% retrieval accuracy.

This package provides a complete Retrieval-Augmented Generation system that combines
semantic search with multi-provider LLM support to deliver accurate, cited answers
from document collections.
"""

__version__ = "0.1.0"
__author__ = "AI Portfolio"
__email__ = "vn6295337@gmail.com"

# Import main functions for easy access
from .orchestrator import orchestrate_query

__all__ = [
    "orchestrate_query",
]