# src/llm_providers.py
import os
import time
import logging
from typing import Optional, Dict, Any, List
from litellm import completion

logger = logging.getLogger(__name__)

# Model mapping for LiteLLM
# LiteLLM uses prefixes like "gemini/", "groq/", "openrouter/"
PROVIDER_MAP = {
    "gemini": "gemini/",
    "groq": "groq/",
    "openrouter": "openrouter/"
}

def call_llm(
    prompt: str,
    context: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: int = 512,
    **kwargs
) -> Dict[str, Any]:
    """
    Unified LLM call using LiteLLM.
    
    Args:
        prompt: User question
        context: Retrieved document context
        provider: 'gemini', 'groq', or 'openrouter' (default: priority cascade)
        model: Specific model name (optional)
        temperature: Sampling temperature
        max_tokens: Max output tokens
        
    Returns:
        Dict with 'text' and 'meta'
    """
    # 1. Determine provider and model from environment if not provided
    if not provider:
        if os.getenv("GEMINI_API_KEY"):
            provider = "gemini"
        elif os.getenv("GROQ_API_KEY"):
            provider = "groq"
        else:
            provider = "openrouter"

    if not model:
        if provider == "gemini":
            model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        elif provider == "groq":
            model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        else:
            model = os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct:free")

    # 2. Build LiteLLM model string
    litellm_model = f"{PROVIDER_MAP.get(provider, '')}{model}"

    # 3. Construct messages
    messages = []
    system_content = "You are a helpful assistant that answers questions based on the provided context."
    if context:
        system_content += f"\n\nContext:\n{context}"
    
    messages.append({"role": "system", "content": system_content})
    messages.append({"role": "user", "content": prompt})

    # 4. Execute call
    start_time = time.time()
    try:
        response = completion(
            model=litellm_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        text = response.choices[0].message.content
        elapsed = time.time() - start_time
        
        return {
            "text": text,
            "meta": {
                "provider": provider,
                "model": model,
                "elapsed_s": elapsed,
                "usage": dict(response.get("usage", {}))
            }
        }
    except Exception as e:
        logger.error(f"LiteLLM call failed for {litellm_model}: {str(e)}")
        return {
            "text": "",
            "meta": {"error": str(e), "provider": provider, "model": model}
        }

def call_llm_stream(
    prompt: str,
    context: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: int = 512,
    **kwargs
):
    """
    Streaming version of unified LLM call.
    Yields chunks of text.
    """
    # Logic similar to call_llm but returns a generator
    if not provider:
        provider = "gemini" if os.getenv("GEMINI_API_KEY") else "groq"
    
    if not model:
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash") if provider == "gemini" else os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    litellm_model = f"{PROVIDER_MAP.get(provider, '')}{model}"

    messages = [{"role": "user", "content": f"Context:\n{context}\n\nQuestion: {prompt}" if context else prompt}]

    try:
        response = completion(
            model=litellm_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs
        )
        for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    except Exception as e:
        yield f"Error: {str(e)}"
