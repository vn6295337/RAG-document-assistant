# src/llm_providers.py
import os
import time
import logging
from typing import Optional, Dict, Any, List, Tuple
from litellm import completion

logger = logging.getLogger(__name__)

# Model mapping for LiteLLM
# LiteLLM uses prefixes like "gemini/" and "groq/"
PROVIDER_MAP = {
    "gemini": "gemini/",
    "groq": "groq/",
    "openrouter": "openrouter/"
}


def _default_model_for_provider(provider: str) -> str:
    if provider == "groq":
        return os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    if provider == "gemini":
        return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    return os.getenv("OPENROUTER_MODEL", "google/gemma-3-27b-it:free")


def _build_attempts(provider: Optional[str], model: Optional[str]) -> List[Tuple[str, str]]:
    """Build ordered provider/model attempts for the non-streaming call path."""
    if provider:
        return [(provider, model or _default_model_for_provider(provider))]

    attempts: List[Tuple[str, str]] = []
    if os.getenv("GROQ_API_KEY"):
        attempts.append(("groq", model or _default_model_for_provider("groq")))
    if os.getenv("GEMINI_API_KEY"):
        attempts.append(("gemini", model or _default_model_for_provider("gemini")))
    return attempts

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
        provider: 'groq' or 'gemini' (default: groq primary, gemini fallback)
        model: Specific model name (optional)
        temperature: Sampling temperature
        max_tokens: Max output tokens
        
    Returns:
        Dict with 'text' and 'meta'
    """
    attempts = _build_attempts(provider, model)
    if not attempts:
        return {
            "text": "",
            "meta": {"error": "No configured LLM providers available"}
        }

    # Construct messages once
    messages = []
    system_content = "You are a helpful assistant that answers questions based on the provided context."
    if context:
        system_content += f"\n\nContext:\n{context}"
    
    messages.append({"role": "system", "content": system_content})
    messages.append({"role": "user", "content": prompt})

    last_error = None
    for selected_provider, selected_model in attempts:
        litellm_model = f"{PROVIDER_MAP.get(selected_provider, '')}{selected_model}"
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
                    "provider": selected_provider,
                    "model": selected_model,
                    "elapsed_s": elapsed,
                    "usage": dict(response.get("usage", {}))
                }
            }
        except Exception as e:
            last_error = e
            logger.error(f"LiteLLM call failed for {litellm_model}: {str(e)}")

    return {
        "text": "",
        "meta": {
            "error": str(last_error) if last_error else "LLM call failed",
            "provider": attempts[-1][0],
            "model": attempts[-1][1]
        }
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
    # Streaming keeps a single provider selection.
    if not provider:
        provider = "groq" if os.getenv("GROQ_API_KEY") else "gemini"
    
    if not model:
        model = _default_model_for_provider(provider)

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
