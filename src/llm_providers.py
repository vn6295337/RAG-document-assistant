
# src/llm_providers.py
# Priority: GEMINI → GROQ → OPENROUTER → fallback

import os
import json
import time
from typing import Optional, Dict, Any

try:
    import requests
    _HAS_REQUESTS = True
except Exception:
    import urllib.request as _urllib_request
    import urllib.error as _urllib_error
    _HAS_REQUESTS = False


def _http_post(url: str, headers: dict, payload: dict, timeout: int = 30):
    """
    Perform HTTP POST request with JSON payload.
    
    Args:
        url: Target URL
        headers: HTTP headers
        payload: JSON-serializable payload
        timeout: Request timeout in seconds
        
    Returns:
        Parsed JSON response
        
    Raises:
        requests.RequestException: If using requests and request fails
        urllib.error.URLError: If using urllib and request fails
        json.JSONDecodeError: If response is not valid JSON
        ValueError: If url is empty or payload is not serializable
    """
    if not url:
        raise ValueError("URL cannot be empty")
        
    try:
        data = json.dumps(payload).encode("utf-8")
    except Exception as e:
        raise ValueError(f"Failed to serialize payload to JSON: {str(e)}")
        
    if _HAS_REQUESTS:
        try:
            r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=timeout)
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            raise
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Failed to decode JSON response: {str(e)}")
    else:
        try:
            req = _urllib_request.Request(url, data=data, headers=headers, method="POST")
            with _urllib_request.urlopen(req, timeout=timeout) as resp:
                response_data = resp.read().decode("utf-8")
                return json.loads(response_data)
        except _urllib_error.URLError:
            raise
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Failed to decode JSON response: {str(e)}")


# GEMINI ------------------------------------------------------------

def _call_gemini(prompt: str, temperature: float, max_tokens: int, context: Optional[str]):
    """
    Call Gemini API with prompt and context.
    
    Args:
        prompt: User prompt
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens to generate
        context: Additional context for the prompt
        
    Returns:
        Dict with 'text' and 'meta' keys
        
    Raises:
        RuntimeError: If GEMINI_API_KEY is not set
        Exception: If API call fails
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY missing")

    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    content = prompt
    if context:
        content = f"Context:\n{context}\n\nUser question:\n{prompt}"

    payload = {
        "contents": [{"parts": [{"text": content}]}],
        "generationConfig": {
            "temperature": float(temperature),
            "maxOutputTokens": int(max_tokens)
        }
    }

    start = time.time()
    try:
        j = _http_post(url, {"Content-Type": "application/json"}, payload)
    except Exception as e:
        raise RuntimeError(f"Gemini API call failed: {str(e)}")
    elapsed = time.time() - start

    try:
        text = j["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as e:
        text = json.dumps(j)[:1000]
        raise RuntimeError(f"Unexpected Gemini API response format: {str(e)}. Response: {text}")

    return {"text": text, "meta": {"provider": "gemini", "model": model, "elapsed_s": elapsed}}


# GROQ --------------------------------------------------------------

def _call_groq(prompt: str, temperature: float, max_tokens: int, context: Optional[str]):
    """
    Call Groq API with prompt and context.
    
    Args:
        prompt: User prompt
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens to generate
        context: Additional context for the prompt
        
    Returns:
        Dict with 'text' and 'meta' keys
        
    Raises:
        RuntimeError: If GROQ_API_KEY is not set
        Exception: If API call fails
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY missing")

    url = "https://api.groq.com/openai/v1/chat/completions"
    model = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")

    system_msg = "You are a concise assistant. Include citations if context is provided."
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": f"Context:\n{context}\n\n{prompt}" if context else prompt}
    ]

    payload = {
        "model": model,
        "messages": messages,
        "temperature": float(temperature),
        "max_tokens": int(max_tokens)
    }

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    start = time.time()
    try:
        j = _http_post(url, headers, payload)
    except Exception as e:
        raise RuntimeError(f"Groq API call failed: {str(e)}")
    elapsed = time.time() - start

    try:
        text = j["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        text = json.dumps(j)[:1000]
        raise RuntimeError(f"Unexpected Groq API response format: {str(e)}. Response: {text}")

    return {"text": text, "meta": {"provider": "groq", "model": model, "elapsed_s": elapsed}}


# OPENROUTER --------------------------------------------------------

def _call_openrouter(prompt: str, temperature: float, max_tokens: int, context: Optional[str]):
    """
    Call OpenRouter API with prompt and context.
    
    Args:
        prompt: User prompt
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens to generate
        context: Additional context for the prompt
        
    Returns:
        Dict with 'text' and 'meta' keys
        
    Raises:
        RuntimeError: If OPENROUTER_API_KEY is not set
        Exception: If API call fails
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY missing")

    url = os.getenv("OPENROUTER_URL", "https://api.openrouter.ai/v1/chat/completions")
    model = os.getenv("OPENROUTER_MODEL", "gpt-4o-mini")

    system_msg = "You are a concise assistant. Use supplied context."

    user_content = f"Context:\n{context}\n\n{prompt}" if context else prompt
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_content}
    ]

    payload = {
        "model": model,
        "messages": messages,
        "temperature": float(temperature),
        "max_tokens": int(max_tokens)
    }

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    start = time.time()
    try:
        j = _http_post(url, headers, payload)
    except Exception as e:
        raise RuntimeError(f"OpenRouter API call failed: {str(e)}")
    elapsed = time.time() - start

    try:
        text = j["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        text = json.dumps(j)[:1000]
        raise RuntimeError(f"Unexpected OpenRouter API response format: {str(e)}. Response: {text}")

    return {"text": text, "meta": {"provider": "openrouter", "model": model, "elapsed_s": elapsed}}


# FALLBACK ----------------------------------------------------------

def _fallback(prompt: str, context: Optional[str]):
    """
    Simple fallback responder when all LLM providers fail.
    
    Args:
        prompt: User prompt
        context: Additional context
        
    Returns:
        Dict with 'text' and 'meta' keys
    """
    ctx = (context or "")[:800]
    text = f"[offline] {prompt}\n\nContext snippet:\n{ctx}"
    return {"text": text, "meta": {"provider": "local-fallback"}}


# PUBLIC ENTRYPOINT -------------------------------------------------

def call_llm(prompt: str, temperature: float = 0.0, max_tokens: int = 512, context: Optional[str] = None, **kwargs):
    """
    Call LLM with automatic fallback cascade: Gemini → Groq → OpenRouter → Local.
    If one provider fails, automatically tries the next one.
    
    Args:
        prompt: User prompt
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens to generate
        context: Additional context for the prompt
        **kwargs: Additional arguments passed to provider functions
        
    Returns:
        Dict with 'text' and 'meta' keys containing the response and metadata
        
    Raises:
        Exception: If all providers fail
    """
    if not prompt or not isinstance(prompt, str):
        raise ValueError("prompt must be a non-empty string")
        
    # Validate temperature and max_tokens
    temperature = max(0.0, min(1.0, float(temperature)))  # Clamp to [0.0, 1.0]
    max_tokens = max(1, int(max_tokens))  # Ensure positive
    
    errors = []

    # Try Gemini first
    if os.getenv("GEMINI_API_KEY"):
        try:
            return _call_gemini(prompt, temperature, max_tokens, context)
        except Exception as e:
            errors.append(f"gemini: {str(e)}")
            # Continue to next provider

    # Try Groq second
    if os.getenv("GROQ_API_KEY"):
        try:
            return _call_groq(prompt, temperature, max_tokens, context)
        except Exception as e:
            errors.append(f"groq: {str(e)}")
            # Continue to next provider

    # Try OpenRouter third
    if os.getenv("OPENROUTER_API_KEY"):
        try:
            return _call_openrouter(prompt, temperature, max_tokens, context)
        except Exception as e:
            errors.append(f"openrouter: {str(e)}")
            # Continue to fallback

    # All providers failed, use local fallback
    error_summary = "; ".join(errors) if errors else "No API keys configured"
    return {
        "text": f"[All providers failed: {error_summary}] Using local fallback.",
        "meta": {"provider": "local-fallback", "errors": errors}
    }