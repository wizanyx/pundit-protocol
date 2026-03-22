from __future__ import annotations

"""Shared LLM gateway for backend agents.

This module centralizes provider selection and fallback behavior:
- LLM_PROVIDER=openai -> OpenAI first, then Gemini fallback.
- LLM_PROVIDER=gemini (default) -> Gemini first, then OpenAI fallback.
"""

import importlib
from typing import Any

try:
    from .config import (
        MODERATOR_GEMINI_MODEL,
        MODERATOR_OPENAI_MODEL,
        PUNDIT_GEMINI_MODEL,
        PUNDIT_OPENAI_MODEL,
        llm_provider,
    )
except ImportError:
    from config import (
        MODERATOR_GEMINI_MODEL,
        MODERATOR_OPENAI_MODEL,
        PUNDIT_GEMINI_MODEL,
        PUNDIT_OPENAI_MODEL,
        llm_provider,
    )

_openai_client: Any | None = None
_gemini_models: dict[str, Any] = {}


def _provider() -> str:
    """Return normalized provider name with gemini as safe default."""
    return llm_provider()


def _get_openai_client() -> Any | None:
    """Lazy-init and cache OpenAI client; return None when unavailable."""

    global _openai_client
    if _openai_client is not None:
        return _openai_client

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        openai_module = importlib.import_module("openai")
        openai_cls = getattr(openai_module, "OpenAI")
        _openai_client = openai_cls(api_key=api_key)
        return _openai_client
    except Exception:
        return None


def _get_gemini_model(model_name: str) -> Any | None:
    """Lazy-init and cache Gemini model instance for a specific model name."""

    cached = _gemini_models.get(model_name)
    if cached is not None:
        return cached

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    try:
        genai = importlib.import_module("google.generativeai")
        genai.configure(api_key=api_key)
        model_cls = getattr(genai, "GenerativeModel")
        model = model_cls(model_name)
        _gemini_models[model_name] = model
        return model
    except Exception:
        return None


def _call_gemini(
    *,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
) -> str | None:
    """Run a text generation request on Gemini and return stripped text."""

    model = _get_gemini_model(model_name)
    if model is None:
        return None

    try:
        genai = importlib.import_module("google.generativeai")
        cfg_cls = getattr(getattr(genai, "types"), "GenerationConfig")
        response = model.generate_content(
            f"System:\n{system_prompt}\n\nUser:\n{user_prompt}",
            generation_config=cfg_cls(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        text = getattr(response, "text", None)
        if text and text.strip():
            return text.strip()
    except Exception:
        return None
    return None


def _call_openai(
    *,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
) -> str | None:
    """Run a text generation request on OpenAI Chat Completions."""

    client = _get_openai_client()
    if client is None:
        return None

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = response.choices[0].message.content
        if text and text.strip():
            return text.strip()
    except Exception:
        return None
    return None


def call_llm_text(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    profile: str,
) -> str | None:
    """Generate text with provider-aware fallback using env-configured model names.

    Args:
        system_prompt: Instructional system prompt.
        user_prompt: End-user/content prompt.
        temperature: Sampling temperature.
        max_tokens: Output token cap.
        profile: Model profile name. Supported: "pundit", "moderator".
    """

    if profile == "moderator":
        openai_model = MODERATOR_OPENAI_MODEL
        gemini_model = MODERATOR_GEMINI_MODEL
    else:
        openai_model = PUNDIT_OPENAI_MODEL
        gemini_model = PUNDIT_GEMINI_MODEL

    if _provider() == "openai":
        return _call_openai(
            model_name=openai_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        ) or _call_gemini(
            model_name=gemini_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    return _call_gemini(
        model_name=gemini_model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    ) or _call_openai(
        model_name=openai_model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )
