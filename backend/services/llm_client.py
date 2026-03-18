"""
LLM client for agent prompts. Supports OpenAI and Gemini.
Uses whichever API key is set in .env; optional LLM_PROVIDER=openai|gemini to force.
Model selection: default model per provider, or gen_sql model for the Gen-SQL agent.
"""

import logging
import os

from backend.config import _load_dotenv

logger = logging.getLogger(__name__)

# Default models per provider (overridable via .env)
GEMINI_MODEL_DEFAULT = "gemini-2.0-flash"      # all agents except gen_sql
GEMINI_MODEL_GEN_SQL = "gemini-1.5-pro"      # gen_sql agent (use gemini-2.0-pro etc. in env if desired)
OPENAI_MODEL_DEFAULT = "gpt-4.1-mini"          # all agents except gen_sql
OPENAI_MODEL_GEN_SQL = "gpt-4.1"              # gen_sql agent

AGENT_GEN_SQL = "gen_sql"


def _get_provider() -> str:
    """Return 'gemini' or 'openai'. Uses LLM_PROVIDER if set; else whichever key is set (prefer gemini if both)."""
    _load_dotenv()
    forced = os.getenv("LLM_PROVIDER", "").strip().lower()
    if forced in ("gemini", "openai"):
        logger.info("Using LLM provider: %s (from LLM_PROVIDER)", forced)
        return forced
    has_gemini = bool((os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip())
    has_openai = bool((os.getenv("OPENAI_API_KEY") or "").strip())
    if has_gemini and has_openai:
        logger.info("Using LLM provider: gemini (both keys set, default is Gemini)")
        return "gemini"  # prefer Gemini when both set
    if has_gemini:
        logger.info("Using LLM provider: gemini")
        return "gemini"
    if has_openai:
        logger.info("Using LLM provider: openai")
        return "openai"
    raise ValueError(
        "No LLM API key set. Add GEMINI_API_KEY or OPENAI_API_KEY to .env."
    )


def _get_model(provider: str, agent_name: str | None) -> str:
    """Resolve model for provider and optional agent_name (e.g. gen_sql)."""
    _load_dotenv()
    if provider == "gemini":
        if agent_name == AGENT_GEN_SQL:
            return os.getenv("GEMINI_MODEL_GEN_SQL", GEMINI_MODEL_GEN_SQL)
        return os.getenv("GEMINI_MODEL", GEMINI_MODEL_DEFAULT)
    else:
        if agent_name == AGENT_GEN_SQL:
            return os.getenv("OPENAI_MODEL_GEN_SQL", OPENAI_MODEL_GEN_SQL)
        return os.getenv("OPENAI_MODEL", OPENAI_MODEL_DEFAULT)


def _chat_openai(messages: list[dict], model: str) -> str:
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set.")
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
    )
    choice = response.choices[0] if response.choices else None
    if not choice or not choice.message:
        raise RuntimeError("OpenAI returned no content")
    return (choice.message.content or "").strip()


def _chat_gemini(messages: list[dict], model: str) -> str:
    import re
    import time
    from google import genai
    from google.genai import types
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY (or GOOGLE_API_KEY) is not set.")
    client = genai.Client(api_key=api_key)
    system_parts = []
    user_parts = []
    for m in messages:
        role = (m.get("role") or "").lower()
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
        elif role in ("user", "assistant"):
            user_parts.append(content)
    user_text = "\n\n".join(user_parts) if user_parts else ""
    if not user_text:
        raise ValueError("No user or assistant content in messages.")
    config_kwargs = {"temperature": 0.2}
    if system_parts:
        config_kwargs["system_instruction"] = "\n\n".join(system_parts)
    last_error = None
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_text,
                config=types.GenerateContentConfig(**config_kwargs),
            )
            if not response or not response.text:
                raise RuntimeError("Gemini returned no content")
            return response.text.strip()
        except Exception as e:
            last_error = e
            err_str = str(e)
            is_429 = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower()
            if is_429 and attempt == 0:
                wait_s = 45
                match = re.search(r"retry in (\d+(?:\.\d+)?)s", err_str, re.I)
                if match:
                    wait_s = min(120, max(45, int(float(match.group(1)))))
                logger.warning("Gemini rate limit (429), waiting %ds then retrying once.", wait_s)
                time.sleep(wait_s)
            else:
                raise
    raise last_error


def chat_completion(
    messages: list[dict],
    model: str | None = None,
    agent_name: str | None = None,
) -> str:
    """
    Send chat messages to the LLM and return the assistant reply as text.
    messages: list of {"role": "system"|"user"|"assistant", "content": "..."}.
    model: optional override; if not set, uses provider default or gen_sql model when agent_name="gen_sql".
    agent_name: optional; use "gen_sql" for Gen-SQL agent (uses provider's gen_sql model).
    Provider: Gemini if GEMINI_API_KEY (or GOOGLE_API_KEY) set, else OpenAI if OPENAI_API_KEY set.
    Set LLM_PROVIDER=gemini|openai to force when both keys are present.
    """
    _load_dotenv()
    provider = _get_provider()
    resolved_model = model or _get_model(provider, agent_name)
    logger.debug("Using provider=%s model=%s", provider, resolved_model)

    if provider == "gemini":
        return _chat_gemini(messages, resolved_model)
    return _chat_openai(messages, resolved_model)
