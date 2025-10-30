# utils/llm_utils.py

import requests
import json
import time
import logging
from config.settings import get_setting

logger = logging.getLogger(__name__)


def test_llm_service():
    """Test if LLM service is available and responding correctly

    Returns:
        tuple: (bool, str) - (success, message)
    """
    provider = get_setting("LLM_PROVIDER", "zai").lower()

    if provider == "ollama":
        return _test_ollama()
    elif provider == "anthropic":
        return _test_anthropic()
    elif provider == "openai":
        return _test_openai()
    elif provider == "zai":
        return _test_zai()
    else:
        return False, f"Unknown LLM provider: {provider}"


def _test_zai():
    """Test Z.ai service using official SDK"""
    try:
        from zai import ZaiClient
        import zai.core
    except ImportError:
        return False, "Z.ai SDK not installed. Install with: pip install zai-sdk"

    api_key = get_setting("ZAI_API_KEY")
    if not api_key:
        return False, "Z.ai API key is not set"

    model = get_setting("ZAI_MODEL", "glm-4.6")
    base_url = get_setting("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4/")
    timeout = get_setting("ZAI_TIMEOUT", 30.0)

    logger.info(f"Testing Z.ai service with model {model}")

    test_prompt = "Respond with 'OK' if you can read this message."

    try:
        # Initialize Z.ai client
        client = ZaiClient(api_key=api_key, base_url=base_url, timeout=timeout)

        # Create test request
        start_time = time.time()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": test_prompt}],
            temperature=0.7,
            max_tokens=10,
        )
        response_time = time.time() - start_time

        if response and hasattr(response, "choices") and len(response.choices) > 0:
            content = response.choices[0].message.content
            logger.info(f"Z.ai test successful. Response time: {response_time:.2f}s")
            return (
                True,
                f"Z.ai service is available. Response time: {response_time:.2f}s",
            )
        else:
            return False, f"Unexpected response format from Z.ai"

    except zai.core.APIStatusError as err:
        if "401" in str(err) or "Authorization" in str(err):
            return False, "Z.ai API key is invalid or expired"
        else:
            return False, f"Z.ai API status error: {err}"
    except zai.core.APITimeoutError as err:
        return False, f"Z.ai API timeout: {err}"
    except requests.exceptions.ConnectionError:
        return False, "Failed to connect to Z.ai service. Check network connectivity."
    except requests.exceptions.Timeout:
        return False, "Connection to Z.ai service timed out."
    except Exception as e:
        return False, f"Error testing Z.ai service: {str(e)}"


def _test_ollama():
    """Test Ollama service"""
    api_url = get_setting("OLLAMA_API_URL")
    model = get_setting("OLLAMA_MODEL", "llama3")

    # Get parameters with defaults
    temperature = get_setting("LLM_TEMPERATURE", 0.7)
    max_tokens = 10  # Small for testing

    logger.info(f"Testing Ollama service at {api_url} with model {model}")

    test_prompt = "Respond with 'OK' if you can read this message."

    try:
        headers = {"Content-Type": "application/json"}
        data = {
            "model": model,
            "prompt": test_prompt,
            "stream": False,
            "temperature": temperature,
            "num_predict": max_tokens,
        }

        start_time = time.time()
        response = requests.post(api_url, headers=headers, json=data, timeout=10)
        response_time = time.time() - start_time

        if response.status_code != 200:
            return False, f"Ollama service returned status code {response.status_code}"

        try:
            result = response.json()
            if "response" in result:
                logger.info(
                    f"Ollama test successful. Response time: {response_time:.2f}s"
                )
                return (
                    True,
                    f"Ollama service is available. Response time: {response_time:.2f}s",
                )
            else:
                return False, f"Unexpected response format: {result}"
        except json.JSONDecodeError:
            return False, "Failed to parse JSON response from Ollama"

    except requests.exceptions.ConnectionError:
        return False, "Failed to connect to Ollama service. Check if Ollama is running."
    except requests.exceptions.Timeout:
        return False, "Connection to Ollama service timed out."
    except Exception as e:
        return False, f"Error testing Ollama service: {str(e)}"


def _test_anthropic():
    """Test Anthropic service"""
    api_url = get_setting("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages")
    api_key = get_setting("ANTHROPIC_API_KEY")
    model = get_setting("ANTHROPIC_MODEL", "claude-instant-1.2")

    if not api_key:
        return False, "Anthropic API key is not set"

    logger.info(f"Testing Anthropic service with model {model}")

    test_prompt = "Respond with 'OK' if you can read this message."

    try:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }

        data = {
            "model": model,
            "messages": [{"role": "user", "content": test_prompt}],
            "max_tokens": 10,
            "temperature": 0.7,
        }

        start_time = time.time()
        response = requests.post(api_url, headers=headers, json=data, timeout=10)
        response_time = time.time() - start_time

        if response.status_code != 200:
            return (
                False,
                f"Anthropic service returned status code {response.status_code}",
            )

        try:
            result = response.json()
            if "content" in result:
                logger.info(
                    f"Anthropic test successful. Response time: {response_time:.2f}s"
                )
                return (
                    True,
                    f"Anthropic service is available. Response time: {response_time:.2f}s",
                )
            else:
                return False, f"Unexpected response format: {result}"
        except json.JSONDecodeError:
            return False, "Failed to parse JSON response from Anthropic"

    except requests.exceptions.ConnectionError:
        return False, "Failed to connect to Anthropic service."
    except requests.exceptions.Timeout:
        return False, "Connection to Anthropic service timed out."
    except Exception as e:
        return False, f"Error testing Anthropic service: {str(e)}"


def _test_openai():
    """Test OpenAI-compatible service"""
    api_url = get_setting(
        "OPENAI_API_URL", "https://api.openai.com/v1/chat/completions"
    )
    api_key = get_setting("OPENAI_API_KEY")
    model = get_setting("OPENAI_MODEL", "gpt-3.5-turbo")

    if not api_key:
        return False, "OpenAI API key is not set"

    logger.info(f"Testing OpenAI service with model {model}")

    test_prompt = "Respond with 'OK' if you can read this message."

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        data = {
            "model": model,
            "messages": [{"role": "user", "content": test_prompt}],
            "temperature": 0.7,
            "max_tokens": 10,
        }

        start_time = time.time()
        response = requests.post(api_url, headers=headers, json=data, timeout=10)
        response_time = time.time() - start_time

        if response.status_code != 200:
            return False, f"OpenAI service returned status code {response.status_code}"

        try:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                logger.info(
                    f"OpenAI test successful. Response time: {response_time:.2f}s"
                )
                return (
                    True,
                    f"OpenAI service is available. Response time: {response_time:.2f}s",
                )
            else:
                return False, f"Unexpected response format: {result}"
        except json.JSONDecodeError:
            return False, "Failed to parse JSON response from OpenAI"

    except requests.exceptions.ConnectionError:
        return False, "Failed to connect to OpenAI service."
    except requests.exceptions.Timeout:
        return False, "Connection to OpenAI service timed out."
    except Exception as e:
        return False, f"Error testing OpenAI service: {str(e)}"
