"""
LLM abstraction layer — swap providers without touching agent code.

Supports: Groq (free tier), Ollama (local/free), Anthropic (paid)
Set LLM_PROVIDER in .env to choose. Defaults to groq.
"""

import json
import os
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional

PROVIDER = os.environ.get("LLM_PROVIDER", "groq").lower()

# ─── Model defaults per provider ──────────────────────────────────────────────

MODELS = {
    "groq":      os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile"),
    "ollama":    os.environ.get("LLM_MODEL", "llama3.2"),
    "anthropic": os.environ.get("LLM_MODEL", "claude-sonnet-4-6"),
}

# ─── Core call function ───────────────────────────────────────────────────────

def call_llm(
    system: str,
    user: str,
    max_tokens: int = 4096,
    provider: Optional[str] = None,
) -> str:
    """
    Call the configured LLM and return the response text.
    Raises on failure.
    """
    p = (provider or PROVIDER).lower()

    if p == "groq":
        return _call_groq(system, user, max_tokens)
    elif p == "ollama":
        return _call_ollama(system, user, max_tokens)
    elif p == "anthropic":
        return _call_anthropic(system, user, max_tokens)
    else:
        raise ValueError(f"Unknown LLM provider: {p}. Set LLM_PROVIDER to groq, ollama, or anthropic.")


# ─── Groq (free tier — llama-3.3-70b-versatile) ───────────────────────────────

def _groq_session() -> requests.Session:
    """Build a requests session with retry + backoff for DNS/connection errors."""
    session = requests.Session()
    retry = Retry(
        total=4,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"],
        raise_on_status=False,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def _call_groq(system: str, user: str, max_tokens: int) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY not set. Get a free key at console.groq.com")

    session = _groq_session()
    resp = session.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODELS["groq"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ─── Ollama (local, fully free) ───────────────────────────────────────────────

def _call_ollama(system: str, user: str, max_tokens: int) -> str:
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

    resp = requests.post(
        f"{base_url}/api/chat",
        json={
            "model": MODELS["ollama"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "stream": False,
            "options": {"num_predict": max_tokens},
        },
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


# ─── Anthropic (paid) ─────────────────────────────────────────────────────────

def _call_anthropic(system: str, user: str, max_tokens: int) -> str:
    try:
        import anthropic as anthropic_sdk
    except ImportError:
        raise ImportError("pip install anthropic")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your_anthropic_api_key_here":
        raise EnvironmentError("ANTHROPIC_API_KEY not set.")

    client = anthropic_sdk.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODELS["anthropic"],
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


# ─── Provider check ───────────────────────────────────────────────────────────

def check_provider() -> dict:
    """Return status of configured provider."""
    p = PROVIDER
    status = {"provider": p, "model": MODELS.get(p, "unknown"), "ready": False, "error": None}

    if p == "groq":
        key = os.environ.get("GROQ_API_KEY")
        if not key:
            status["error"] = "GROQ_API_KEY not set — get free key at console.groq.com"
        else:
            status["ready"] = True

    elif p == "ollama":
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=3)
            resp.raise_for_status()
            status["ready"] = True
        except Exception as e:
            status["error"] = f"Ollama not running: {e}"

    elif p == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key or key == "your_anthropic_api_key_here":
            status["error"] = "ANTHROPIC_API_KEY not set"
        else:
            status["ready"] = True

    return status
