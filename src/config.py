import os
from dotenv import load_dotenv

# Load local .env for development
load_dotenv()

# Support Streamlit Cloud secrets
try:
    import streamlit as st
    _HAS_STREAMLIT = True
except ImportError:
    _HAS_STREAMLIT = False

def get_required(key: str) -> str:
    """
    Get required config value from environment or Streamlit secrets.
    
    Args:
        key: Configuration key to retrieve
        
    Returns:
        Configuration value
        
    Raises:
        RuntimeError: If key is not found in any configuration source
    """
    # Try Streamlit secrets first (for Streamlit Cloud)
    if _HAS_STREAMLIT and hasattr(st, 'secrets'):
        try:
            if key in st.secrets:
                return st.secrets[key]
        except Exception:
            pass  # Secrets not configured, fall back to env vars

    # Fall back to environment variables (for local/other deployments)
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value

def get_optional(key: str, default=None):
    """
    Get optional config value from environment or Streamlit secrets.
    
    Args:
        key: Configuration key to retrieve
        default: Default value if key is not found
        
    Returns:
        Configuration value or default
    """
    # Try Streamlit secrets first
    if _HAS_STREAMLIT and hasattr(st, 'secrets'):
        try:
            if key in st.secrets:
                return st.secrets[key]
        except Exception:
            pass  # Secrets not configured, fall back to env vars

    # Fall back to environment variables
    return os.getenv(key, default)

# Pinecone (Required)
PINECONE_API_KEY = get_required("PINECONE_API_KEY")
PINECONE_INDEX_NAME = get_optional("PINECONE_INDEX_NAME", "rag-semantic-384")

# LLM provider keys (at least one required)
GEMINI_API_KEY = get_optional("GEMINI_API_KEY")
GROQ_API_KEY = get_optional("GROQ_API_KEY")
OPENROUTER_API_KEY = get_optional("OPENROUTER_API_KEY")

# Model names
GEMINI_MODEL = get_optional("GEMINI_MODEL", "gemini-2.5-flash")
GROQ_MODEL = get_optional("GROQ_MODEL", "llama-3.1-8b-instant")
OPENROUTER_MODEL = get_optional("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct:free")

# Supabase (Optional - not used in current deployment)
SUPABASE_URL = get_optional("SB_PROJECT_URL")
SUPABASE_ANON_KEY = get_optional("SB_ANON_KEY")

# Document source configuration
DOCS_DIR = get_optional("DOCS_DIR", "sample_docs/")
CHUNKS_PATH = get_optional("CHUNKS_PATH", "data/chunks.jsonl")