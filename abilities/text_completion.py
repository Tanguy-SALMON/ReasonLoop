# abilities/text_completion.py

import logging
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, Any, Union
import requests

from config.settings import get_setting, get_model_for_provider

logger = logging.getLogger(__name__)

# Pricing per 1M tokens (prompt/completion) in USD
PRICING = {
    "xai": {
        "grok-2-1212": (2.00, 10.00),
        "grok-2-vision-1212": (2.00, 10.00),
        "grok-beta": (5.00, 15.00),
    },
    "zai": {
        "glm-4.6": (0.50, 1.50),
        "glm-4-plus": (50.00, 50.00),
        "default": (0.50, 1.50),
    },
    "ollama": {
        "default": (0.00, 0.00),
    },
    "openai": {
        "gpt-4": (30.00, 60.00),
        "gpt-4-turbo": (10.00, 30.00),
        "gpt-3.5-turbo": (0.50, 1.50),
        "default": (0.50, 1.50),
    },
    "anthropic": {
        "claude-opus-4": (15.00, 75.00),
        "claude-sonnet-3.5": (3.00, 15.00),
        "claude-haiku-3": (0.25, 1.25),
        "default": (3.00, 15.00),
    }
}


def estimate_tokens(text: str) -> int:
    """Estimate token count (roughly 4 chars per token)"""
    return len(text) // 4


def calculate_cost(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate cost in USD based on provider pricing"""
    provider_pricing = PRICING.get(provider.lower(), {})
    model_pricing = provider_pricing.get(model, provider_pricing.get("default", (0.0, 0.0)))

    prompt_price, completion_price = model_pricing

    prompt_cost = (prompt_tokens / 1_000_000) * prompt_price
    completion_cost = (completion_tokens / 1_000_000) * completion_price

    return prompt_cost + completion_cost


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.logger = logging.getLogger(f"{__name__}.{provider_name}")

    @abstractmethod
    def complete(self, prompt: str, role: Optional[str] = None) -> str:
        """Execute completion and return response"""
        pass

    @abstractmethod
    def get_usage(self, prompt: str, response: str, api_response: Dict) -> Dict[str, Any]:
        """Extract usage metrics from API response"""
        pass

    def _create_error_response(self, error_msg: str, return_usage: bool = False):
        """Create standardized error response"""
        self.logger.error(error_msg)
        if return_usage:
            return error_msg, {}
        return error_msg

    def execute(self, prompt: str, role: Optional[str] = None, return_usage: bool = False):
        """Execute completion with optional usage tracking"""
        try:
            response, api_response = self.complete(prompt, role)

            if return_usage:
                usage = self.get_usage(prompt, response, api_response)
                return response, usage

            return response

        except Exception as e:
            return self._create_error_response(f"Error calling {self.provider_name} API: {str(e)}", return_usage)


class XAIProvider(LLMProvider):
    """XAI (Grok) provider implementation"""

    def __init__(self):
        super().__init__("xai")
        self.api_key = get_setting("XAI_API_KEY")
        self.api_url = get_setting("XAI_API_URL", "https://api.x.ai/v1/chat/completions")

    def complete(self, prompt: str, role: Optional[str] = None) -> Tuple[str, Dict]:
        if not self.api_key:
            raise ValueError("XAI_API_KEY not configured")

        model = get_model_for_provider("xai", role)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": get_setting("LLM_TEMPERATURE", 0.7),
            "max_tokens": get_setting("LLM_MAX_TOKENS", 4096),
        }

        response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()

        content = result["choices"][0]["message"]["content"]
        return content, result

    def get_usage(self, prompt: str, response: str, api_response: Dict) -> Dict[str, Any]:
        usage = api_response.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", estimate_tokens(prompt))
        completion_tokens = usage.get("completion_tokens", estimate_tokens(response))
        model = api_response.get("model", get_model_for_provider("xai", None))

        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": usage.get("total_tokens", prompt_tokens + completion_tokens),
            "model": model,
            "provider": "xai",
            "cost_usd": calculate_cost("xai", model, prompt_tokens, completion_tokens)
        }


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation"""

    def __init__(self):
        super().__init__("openai")
        self.api_key = get_setting("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/chat/completions"

    def complete(self, prompt: str, role: Optional[str] = None) -> Tuple[str, Dict]:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not configured")

        model = get_model_for_provider("openai", role)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": get_setting("LLM_TEMPERATURE", 0.7),
            "max_tokens": get_setting("LLM_MAX_TOKENS", 4096),
        }

        response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()

        content = result["choices"][0]["message"]["content"]
        return content, result

    def get_usage(self, prompt: str, response: str, api_response: Dict) -> Dict[str, Any]:
        usage = api_response.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", estimate_tokens(prompt))
        completion_tokens = usage.get("completion_tokens", estimate_tokens(response))
        model = api_response.get("model", get_model_for_provider("openai", None))

        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": usage.get("total_tokens", prompt_tokens + completion_tokens),
            "model": model,
            "provider": "openai",
            "cost_usd": calculate_cost("openai", model, prompt_tokens, completion_tokens)
        }


class AnthropicProvider(LLMProvider):
    """Anthropic provider implementation"""

    def __init__(self):
        super().__init__("anthropic")
        self.api_key = get_setting("ANTHROPIC_API_KEY")
        self.api_url = get_setting("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages")

    def complete(self, prompt: str, role: Optional[str] = None) -> Tuple[str, Dict]:
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        model = get_setting("ANTHROPIC_MODEL", "claude-sonnet-3.5")

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        data = {
            "model": model,
            "max_tokens": get_setting("LLM_MAX_TOKENS", 4096),
            "temperature": get_setting("LLM_TEMPERATURE", 0.7),
            "messages": [{"role": "user", "content": prompt}],
        }

        response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()

        content = result.get("content", [{}])[0].get("text", "")
        return content, result

    def get_usage(self, prompt: str, response: str, api_response: Dict) -> Dict[str, Any]:
        usage = api_response.get("usage", {})
        prompt_tokens = usage.get("input_tokens", estimate_tokens(prompt))
        completion_tokens = usage.get("output_tokens", estimate_tokens(response))
        model = api_response.get("model", get_setting("ANTHROPIC_MODEL", "claude-sonnet-3.5"))

        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "model": model,
            "provider": "anthropic",
            "cost_usd": calculate_cost("anthropic", model, prompt_tokens, completion_tokens)
        }


class OllamaProvider(LLMProvider):
    """Ollama local provider implementation"""

    def __init__(self):
        super().__init__("ollama")
        self.api_url = get_setting("OLLAMA_API_URL", "http://localhost:11434/api/generate")

    def complete(self, prompt: str, role: Optional[str] = None) -> Tuple[str, Dict]:
        model = get_model_for_provider("ollama", role)

        headers = {"Content-Type": "application/json"}
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "temperature": get_setting("LLM_TEMPERATURE", 0.7),
            "num_predict": get_setting("LLM_MAX_TOKENS", 4096),
        }

        response = requests.post(self.api_url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        result = response.json()

        content = result.get("response", "")
        return content, result

    def get_usage(self, prompt: str, response: str, api_response: Dict) -> Dict[str, Any]:
        prompt_tokens = api_response.get("prompt_eval_count", estimate_tokens(prompt))
        completion_tokens = api_response.get("eval_count", estimate_tokens(response))
        model = api_response.get("model", get_model_for_provider("ollama", None))

        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "model": model,
            "provider": "ollama",
            "cost_usd": 0.0  # Local models are free
        }


class ZAIProvider(LLMProvider):
    """Z.ai provider implementation using official SDK"""

    def __init__(self):
        super().__init__("zai")
        try:
            from zai import ZaiClient
            import zai.core
            self.ZaiClient = ZaiClient
            self.zai_core = zai.core
            self.available = True
        except ImportError:
            self.available = False

        self.api_key = get_setting("ZAI_API_KEY")
        self.base_url = get_setting("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4/")
        self.timeout = get_setting("ZAI_TIMEOUT", 30.0)
        self.max_retries = get_setting("ZAI_MAX_RETRIES", 3)

    def complete(self, prompt: str, role: Optional[str] = None) -> Tuple[str, Dict]:
        if not self.available:
            raise ImportError("zai-sdk not installed. Install with: pip install zai-sdk")

        if not self.api_key:
            raise ValueError("ZAI_API_KEY not configured")

        model = get_model_for_provider("zai", role)

        client = self.ZaiClient(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries
        )

        messages = [{"role": "user", "content": prompt}]

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=get_setting("LLM_TEMPERATURE", 0.7),
            max_tokens=get_setting("LLM_MAX_TOKENS", 4096),
        )

        content = response.choices[0].message.content
        # Convert SDK response to dict-like structure
        return content, {"response": response, "model": model}

    def get_usage(self, prompt: str, response: str, api_response: Dict) -> Dict[str, Any]:
        sdk_response = api_response.get("response")
        model = api_response.get("model")

        usage = getattr(sdk_response, 'usage', None)
        if usage:
            prompt_tokens = getattr(usage, 'prompt_tokens', estimate_tokens(prompt))
            completion_tokens = getattr(usage, 'completion_tokens', estimate_tokens(response))
        else:
            prompt_tokens = estimate_tokens(prompt)
            completion_tokens = estimate_tokens(response)

        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "model": model,
            "provider": "zai",
            "cost_usd": calculate_cost("zai", model, prompt_tokens, completion_tokens)
        }


class ProviderFactory:
    """Factory to create appropriate provider instances"""

    _providers = {
        "xai": XAIProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "ollama": OllamaProvider,
        "zai": ZAIProvider,
    }

    @classmethod
    def get_provider(cls, provider_name: str) -> LLMProvider:
        """Get provider instance by name"""
        provider_class = cls._providers.get(provider_name.lower())
        if not provider_class:
            raise ValueError(f"Unknown LLM provider: {provider_name}")
        return provider_class()


def text_completion_ability(
    prompt: str,
    role: Optional[str] = None,
    return_usage: bool = False
) -> Union[str, Tuple[str, Dict[str, Any]]]:
    """
    Handle text completion using LLM providers

    Args:
        prompt: The text prompt to complete
        role: The agent role (orchestrator, planner, executor, reviewer) for model selection
        return_usage: If True, return tuple of (response, usage_dict)

    Returns:
        The LLM's response as a string, or tuple (response, usage_dict) if return_usage=True
    """
    provider_name = get_setting("LLM_PROVIDER", "xai").lower()

    try:
        provider = ProviderFactory.get_provider(provider_name)
        return provider.execute(prompt, role, return_usage)
    except ValueError as e:
        error_msg = str(e)
        logger.error(error_msg)
        if return_usage:
            return error_msg, {}
        return error_msg


def stream_text_completion(prompt: str, role: Optional[str] = None) -> str:
    """
    Handle streaming text completion (currently only Z.ai SDK supports this)
    """
    provider_name = get_setting("LLM_PROVIDER", "xai").lower()

    if provider_name != "zai":
        logger.warning(f"Streaming not supported for {provider_name}, using regular completion")
        result = text_completion_ability(prompt, role, return_usage=False)
        print(result)
        return result

    # Z.ai streaming implementation
    try:
        from zai import ZaiClient
    except ImportError:
        logger.error("zai-sdk not installed for streaming")
        return "Error: zai-sdk not installed"

    api_key = get_setting("ZAI_API_KEY")
    base_url = get_setting("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4/")
    timeout = get_setting("ZAI_TIMEOUT", 30.0)
    model = get_model_for_provider("zai", role)

    try:
        client = ZaiClient(api_key=api_key, base_url=base_url, timeout=timeout)
        messages = [{"role": "user", "content": prompt}]

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

        print()
        return full_response

    except Exception as e:
        logger.error(f"Z.ai streaming error: {str(e)}")
        return f"Error in streaming: {str(e)}"
