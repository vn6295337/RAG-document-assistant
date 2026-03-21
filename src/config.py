import os
from typing import Optional
from dotenv import load_dotenv

# Load local .env for development
load_dotenv()

# Support Streamlit Cloud secrets
try:
    import streamlit as st
    _HAS_STREAMLIT = True
except ImportError:
    _HAS_STREAMLIT = False

# Support AWS SSM
_SSM_CACHE = {}
def get_from_ssm(key: str) -> Optional[str]:
    """Fetch parameter from AWS SSM."""
    if key in _SSM_CACHE:
        return _SSM_CACHE[key]
    
    try:
        import boto3
        ssm = boto3.client('ssm', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        param_path = f"/rag_assistant/{key}"
        response = ssm.get_parameter(Name=param_path, WithDecryption=True)
        value = response['Parameter']['Value']
        _SSM_CACHE[key] = value
        return value
    except Exception:
        return None

def get_required(key: str) -> str:
    """
    Get required config value from environment, Streamlit secrets, or AWS SSM.
    """
    # 1. Try environment variables
    value = os.getenv(key)
    if value:
        return value

    # 2. Try Streamlit secrets
    if _HAS_STREAMLIT and hasattr(st, 'secrets'):
        try:
            if key in st.secrets:
                return st.secrets[key]
        except Exception:
            pass

    # 3. Try AWS SSM (Production)
    value = get_from_ssm(key)
    if value:
        return value

    raise RuntimeError(f"Missing required configuration: {key}")

def get_optional(key: str, default=None):
    """
    Get optional config value from environment, Streamlit secrets, or AWS SSM.
    """
    # 1. Try environment variables
    value = os.getenv(key)
    if value:
        return value

    # 2. Try Streamlit secrets
    if _HAS_STREAMLIT and hasattr(st, 'secrets'):
        try:
            if key in st.secrets:
                return st.secrets[key]
        except Exception:
            pass

    # 3. Try AWS SSM
    value = get_from_ssm(key)
    if value:
        return value

    return default

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