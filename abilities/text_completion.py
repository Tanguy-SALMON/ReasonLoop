# abilities/text_completion.py

import json
import logging
from typing import Optional, Tuple, Dict, Any, Union
import requests

from config.settings import get_setting, get_model_for_provider

logger = logging.getLogger(__name__)

# Pricing per 1M tokens (prompt/completion) in USD
PRICING = {
    "xai": {
        "grok-2-1212": (200.00, 1000.00),
        "grok-2-vision-1212": (200.00, 1000.00),
        "grok-beta": (500.00, 1500.00),
        "grok-4-1-fast-non-reasoning": (0.20, 0.50),  # Input $0.20 per 1M tokens, Output $0.50 per 1M tokens
    }
}


def estimate_tokens(text: str) -> int:
    """Estimate token count (roughly 4 chars per token)"""
    return len(text) // 4


def calculate_cost(provider: str, model: str, prompt_tokens: int, completion_tokens: int, cached_tokens: int = 0) -> float:
    """Calculate cost in USD based on provider pricing (per 1M tokens)"""
    provider_pricing = PRICING.get(provider.lower(), {})
    model_pricing = provider_pricing.get(model, provider_pricing.get("default", (0.0, 0.0)))

    prompt_price, completion_price = model_pricing

    # Regular prompt cost (non-cached)
    regular_prompt_tokens = max(0, prompt_tokens - cached_tokens)
    prompt_cost = (regular_prompt_tokens / 1_000_000) * prompt_price

    # Cached input cost (cheaper)
    cached_cost = (cached_tokens / 1_000_000) * 0.05  # $0.05 per M for cached input

    # Completion/output cost
    completion_cost = (completion_tokens / 1_000_000) * completion_price

    return prompt_cost + cached_cost + completion_cost



class XAIProvider:
    """XAI (Grok) provider implementation"""

    def __init__(self):
        self.provider_name = "xai"
        self.logger = logging.getLogger(f"{__name__}.{self.provider_name}")
        self.api_key = get_setting("XAI_API_KEY")
        self.api_url = get_setting("XAI_API_URL", "https://api.x.ai/v1/chat/completions")

    def complete(self, prompt: str, role: Optional[str] = None) -> Tuple[str, Dict]:
        """Execute completion and return response with usage data"""
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

        # Log the full API response for debugging
        self.logger.debug(f"XAI API Response: {json.dumps(result, indent=2)}")

        content = result["choices"][0]["message"]["content"]
        return content, result

    def get_usage(self, prompt: str, response: str, api_response: Dict) -> Dict[str, Any]:
        """Extract usage metrics from API response"""
        usage = api_response.get("usage", {})

        # Log usage data extraction for debugging
        self.logger.debug(f"XAI API Response keys: {list(api_response.keys())}")
        self.logger.debug(f"Usage data found: {usage}")

        # Extract tokens with fallbacks
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")

        self.logger.debug(f"Extracted prompt_tokens: {prompt_tokens}")
        self.logger.debug(f"Extracted completion_tokens: {completion_tokens}")
        self.logger.debug(f"Extracted total_tokens: {total_tokens}")

        # If no usage data, estimate and mark it
        if not prompt_tokens or not completion_tokens:
            prompt_tokens = estimate_tokens(prompt)
            completion_tokens = estimate_tokens(response)
            total_tokens = prompt_tokens + completion_tokens
            self.logger.warning("No usage data from XAI API, using estimates")
        else:
            if not total_tokens:
                total_tokens = prompt_tokens + completion_tokens

        model = api_response.get("model", get_model_for_provider("xai", None))

        # Use actual cost from API if available, otherwise calculate
        cost_usd = usage.get("cost_in_usd_ticks", 0)
        if cost_usd:
            # Convert from ticks to USD (ticks ÷ 10,000 = USD)
            # XAI provides cost_in_usd_ticks, need to convert to USD
            cost_usd = cost_usd / 10000.0
        else:
            # Get cached tokens from API response
            cached_tokens = usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)
            cost_usd = calculate_cost("xai", model, prompt_tokens, completion_tokens, cached_tokens)

        # Get cached tokens from API for logging
        cached_tokens = usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)

        result = {
            "prompt_tokens": int(prompt_tokens),
            "completion_tokens": int(completion_tokens),
            "total_tokens": int(total_tokens),
            "model": model,
            "provider": "xai",
            "cost_usd": cost_usd,
            "cached_tokens": int(cached_tokens),
            "usage_source": "api" if usage else "estimated"
        }

        self.logger.debug(f"Final usage result: {result}")
        return result

    def execute(self, prompt: str, role: Optional[str] = None, return_usage: bool = False):
        """Execute completion with optional usage tracking"""
        try:
            response, api_response = self.complete(prompt, role)

            if return_usage:
                usage = self.get_usage(prompt, response, api_response)
                return response, usage

            return response

        except Exception as e:
            error_msg = f"Error calling {self.provider_name} API: {str(e)}"
            self.logger.error(error_msg)
            if return_usage:
                return error_msg, {}
            return error_msg


class ProviderFactory:
    """Factory to create appropriate provider instances"""

    _providers = {
        "xai": XAIProvider,
    }

    @classmethod
    def get_provider(cls, provider_name: str) -> XAIProvider:
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
    """Handle streaming text completion"""
    provider_name = get_setting("LLM_PROVIDER", "xai").lower()

    if provider_name != "xai":
        logger.warning(f"Streaming not supported for {provider_name}, using regular completion")
        result = text_completion_ability(prompt, role, return_usage=False)
        print(result)
        return result

    # XAI streaming implementation would go here
    logger.warning("XAI streaming not implemented yet")
    return text_completion_ability(prompt, role, return_usage=False)
