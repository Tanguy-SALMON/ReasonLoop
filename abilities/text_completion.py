# abilities/text_completion.py

import logging
from typing import Optional

from config.settings import get_setting, get_zai_model

try:
    from zai import ZaiClient
    import zai.core

    ZAI_AVAILABLE = True
except ImportError:
    ZAI_AVAILABLE = False

logger = logging.getLogger(__name__)


def text_completion_ability(prompt: str, role: Optional[str] = None) -> str:
    """
    Handle text completion using LLM providers

    Args:
        prompt: The text prompt to complete
        role: The agent role (orchestrator, planner, executor, reviewer) for model selection

    Returns:
        The LLM's response as a string
    """
    provider = get_setting("LLM_PROVIDER", "zai").lower()

    if provider == "zai":
        return _zai_completion(prompt, role)
    elif provider == "ollama":
        return _ollama_completion(prompt, role)
    elif provider == "anthropic":
        return _anthropic_completion(prompt)
    else:
        logger.error(f"Unknown LLM provider: {provider}")
        return f"Error: Unknown LLM provider '{provider}'"


def _zai_completion(prompt: str, role: Optional[str] = None) -> str:
    """Handle Z.ai completions using the official SDK"""
    if not ZAI_AVAILABLE:
        logger.error("zai-sdk not installed. Please install with: pip install zai-sdk")
        return "Error: zai-sdk not installed"

    api_key = get_setting("ZAI_API_KEY")
    if not api_key:
        logger.error("ZAI_API_KEY not configured")
        return "Error: ZAI_API_KEY not configured"

    base_url = get_setting("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4/")
    timeout = get_setting("ZAI_TIMEOUT", 30.0)
    max_retries = get_setting("ZAI_MAX_RETRIES", 3)

    # Use role-specific model if provided, otherwise use default
    model = get_zai_model(role)

    try:
        # Initialize Z.ai client with proper configuration
        client = ZaiClient(
            api_key=api_key, base_url=base_url, timeout=timeout, max_retries=max_retries
        )

        # Create messages for the chat completion
        messages = [{"role": "user", "content": prompt}]

        # Call the Z.ai API
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=get_setting("LLM_TEMPERATURE", 0.7),
            max_tokens=get_setting("LLM_MAX_TOKENS", 4096),
        )

        return response.choices[0].message.content

    except zai.core.APIStatusError as err:
        logger.error(f"Z.ai API status error: {err}")
        return f"Error: Z.ai API status error - {err}"
    except zai.core.APITimeoutError as err:
        logger.error(f"Z.ai API timeout error: {err}")
        return f"Error: Z.ai API timeout - {err}"
    except Exception as e:
        logger.error(f"Z.ai API error: {str(e)}")
        return f"Error calling Z.ai API: {str(e)}"


def _ollama_completion(prompt: str, role: Optional[str] = None) -> str:
    """Handle Ollama completions (fallback option)"""
    import requests
    import json

    api_url = get_setting("OLLAMA_API_URL")
    # Use role-specific model if provided, otherwise use default
    if role:
        model = get_zai_model(role)  # Reuse Z.ai model config for consistency
    else:
        model = get_setting("OLLAMA_MODEL", "llama3")

    # Get all the parameters with defaults if not set
    temperature = get_setting("LLM_TEMPERATURE", 0.7)
    max_tokens = get_setting("LLM_MAX_TOKENS", 4096)

    headers = {"Content-Type": "application/json"}
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "temperature": temperature,
        "num_predict": max_tokens,
    }

    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result.get("response", "")
    except Exception as e:
        logger.error(f"Ollama API error: {str(e)}")
        return f"Error calling Ollama API: {str(e)}"


def _anthropic_completion(prompt: str) -> str:
    """Handle Anthropic completions (fallback option)"""
    import requests
    import json

    api_url = get_setting("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages")
    api_key = get_setting("ANTHROPIC_API_KEY")
    model = get_setting("ANTHROPIC_MODEL", "claude-instant-1.2")

    if not api_key:
        return "Error: ANTHROPIC_API_KEY not configured"

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }

    data = {
        "model": model,
        "max_tokens": get_setting("LLM_MAX_TOKENS", 4096),
        "temperature": get_setting("LLM_TEMPERATURE", 0.7),
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result.get("content", [{}])[0].get("text", "")
    except Exception as e:
        logger.error(f"Anthropic API error: {str(e)}")
        return f"Error calling Anthropic API: {str(e)}"


def stream_text_completion(prompt: str, role: Optional[str] = None) -> str:
    """
    Handle streaming text completion using Z.ai SDK

    Args:
        prompt: The text prompt to complete
        role: The agent role for model selection

    Returns:
        The complete response text
    """
    if not ZAI_AVAILABLE:
        logger.error("zai-sdk not installed for streaming")
        return "Error: zai-sdk not installed"

    api_key = get_setting("ZAI_API_KEY")
    base_url = get_setting("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4/")
    timeout = get_setting("ZAI_TIMEOUT", 30.0)
    model = get_zai_model(role)

    try:
        client = ZaiClient(api_key=api_key, base_url=base_url, timeout=timeout)

        messages = [{"role": "user", "content": prompt}]

        # Create streaming request
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=get_setting("LLM_TEMPERATURE", 0.7),
            max_tokens=get_setting("LLM_MAX_TOKENS", 4096),
            stream=True,
        )

        full_response = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                print(content, end="", flush=True)

        print()  # New line after streaming
        return full_response

    except Exception as e:
        logger.error(f"Z.ai streaming error: {str(e)}")
        return f"Error in streaming: {str(e)}"
