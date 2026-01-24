"""
AI Agent Adapter - HTTP client for ReasonLoop Intelligence Service

This adapter handles all communication between be-campaign and the ReasonLoop
microservice. It implements proper error handling, timeouts, and retry logic
for production reliability.

Usage:
    adapter = AIAgentAdapter()

    # Synchronous context (FastAPI BackgroundTasks)
    result = await adapter.get_website_intelligence("https://example.com")

    # With custom configuration
    adapter = AIAgentAdapter(
        base_url="http://reasonloop:8001",
        secret_key="my-secret",
        timeout=90.0
    )
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class AIAgentConfig:
    """Configuration for the AI Agent Adapter"""

    base_url: str = field(
        default_factory=lambda: os.getenv("REASONLOOP_URL", "http://localhost:8001")
    )
    secret_key: str = field(
        default_factory=lambda: os.getenv("INTERNAL_SERVICE_SECRET", "")
    )
    timeout: float = 60.0  # 60 seconds (longer than ReasonLoop's 45s internal timeout)
    max_retries: int = 2
    retry_delay: float = 1.0


class AIAgentAdapter:
    """
    HTTP adapter for communicating with ReasonLoop Intelligence Service.

    This adapter provides a clean interface for be-campaign to request
    website analysis from ReasonLoop without coupling to implementation details.

    Features:
    - Async HTTP client with configurable timeout
    - Automatic retry on transient failures
    - Proper error handling (never raises to caller)
    - Structured logging for debugging
    - Header-based authentication (X-Internal-Secret)

    Thread Safety:
    - Each call creates a new httpx.AsyncClient
    - Safe to use from multiple coroutines

    Error Handling:
    - Returns None on any failure
    - Logs detailed error information
    - Caller should handle None gracefully
    """

    def __init__(
        self,
        base_url: str | None = None,
        secret_key: str | None = None,
        timeout: float | None = None,
        config: AIAgentConfig | None = None,
    ):
        """
        Initialize the adapter with optional configuration.

        Args:
            base_url: ReasonLoop API base URL (default: from env REASONLOOP_URL)
            secret_key: Internal service secret (default: from env INTERNAL_SERVICE_SECRET)
            timeout: Request timeout in seconds (default: 60.0)
            config: Full configuration object (overrides other params)
        """
        if config:
            self._config = config
        else:
            self._config = AIAgentConfig()
            if base_url:
                self._config.base_url = base_url
            if secret_key:
                self._config.secret_key = secret_key
            if timeout:
                self._config.timeout = timeout

        self._validate_config()

    def _validate_config(self) -> None:
        """Validate configuration and log warnings"""
        if not self._config.secret_key:
            logger.warning(
                "INTERNAL_SERVICE_SECRET not configured. "
                "ReasonLoop requests will fail with 403."
            )

        if not self._config.base_url:
            logger.warning(
                "REASONLOOP_URL not configured. Using default: http://localhost:8001"
            )

    @property
    def analyze_endpoint(self) -> str:
        """Full URL for the analyze endpoint"""
        return f"{self._config.base_url.rstrip('/')}/api/v1/internal/v1/analyze"

    @property
    def health_endpoint(self) -> str:
        """Full URL for the internal health endpoint"""
        return f"{self._config.base_url.rstrip('/')}/api/v1/internal/v1/health"

    def _get_headers(self) -> dict[str, str]:
        """Build request headers including authentication"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Internal-Secret": self._config.secret_key,
            "User-Agent": "be-campaign/1.0",
        }

    async def health_check(self) -> bool:
        """
        Check if ReasonLoop service is healthy and reachable.

        Returns:
            True if service is healthy, False otherwise.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    self.health_endpoint,
                    headers=self._get_headers(),
                )
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False

    async def get_website_intelligence(
        self,
        url: str,
        force_refresh: bool = False,
    ) -> dict[str, Any] | None:
        """
        Request website intelligence analysis from ReasonLoop.

        This method calls the ReasonLoop /api/v1/internal/v1/analyze endpoint
        to extract brand intelligence from a website.

        Args:
            url: The website URL to analyze (must be public, not localhost)
            force_refresh: If True, bypass cache and perform fresh analysis

        Returns:
            Dict containing the analysis result with keys:
            - status: "success", "cached", "error", or "timeout"
            - brand_identity: Brand name, colors, fonts, logo
            - brand_voice: Tone, CTA patterns
            - products: Categories, pricing
            - (and more...)

            Returns None if:
            - ReasonLoop is unreachable
            - Authentication fails
            - Request times out
            - Any other error occurs

        Example:
            result = await adapter.get_website_intelligence("https://shiseido.com")
            if result:
                brand_name = result.get("brand_identity", {}).get("name")
                brand_tone = result.get("brand_voice", {}).get("tone", [])
        """
        request_payload = {
            "url": url,
            "force_refresh": force_refresh,
        }

        logger.info(f"[AI-ADAPTER] Requesting analysis for: {url}")

        for attempt in range(self._config.max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(self._config.timeout)
                ) as client:
                    response = await client.post(
                        self.analyze_endpoint,
                        json=request_payload,
                        headers=self._get_headers(),
                    )

                    # Handle different response codes
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(
                            f"[AI-ADAPTER] Analysis successful for {url} "
                            f"(status={data.get('status')}, cached={data.get('cached')})"
                        )
                        return data

                    elif response.status_code == 403:
                        logger.error(
                            "[AI-ADAPTER] Authentication failed - check INTERNAL_SERVICE_SECRET"
                        )
                        return None  # Don't retry auth failures

                    elif response.status_code == 400:
                        error_detail = response.json().get("detail", "Bad request")
                        logger.warning(f"[AI-ADAPTER] Bad request: {error_detail}")
                        return None  # Don't retry validation errors

                    elif response.status_code == 408:
                        logger.warning(f"[AI-ADAPTER] Analysis timed out for {url}")
                        return None  # ReasonLoop already timed out, don't retry

                    elif response.status_code >= 500:
                        logger.warning(
                            f"[AI-ADAPTER] Server error {response.status_code} "
                            f"(attempt {attempt + 1}/{self._config.max_retries + 1})"
                        )
                        if attempt < self._config.max_retries:
                            import asyncio

                            await asyncio.sleep(self._config.retry_delay)
                            continue
                        return None

                    else:
                        logger.error(
                            f"[AI-ADAPTER] Unexpected status {response.status_code}: "
                            f"{response.text[:200]}"
                        )
                        return None

            except httpx.TimeoutException:
                logger.warning(
                    f"[AI-ADAPTER] Request timeout after {self._config.timeout}s "
                    f"(attempt {attempt + 1}/{self._config.max_retries + 1})"
                )
                if attempt < self._config.max_retries:
                    import asyncio

                    await asyncio.sleep(self._config.retry_delay)
                    continue
                return None

            except httpx.ConnectError as e:
                logger.error(
                    f"[AI-ADAPTER] Connection failed to {self._config.base_url}: {e}"
                )
                return None  # Don't retry connection errors

            except httpx.RequestError as e:
                logger.error(f"[AI-ADAPTER] Request error: {e}")
                if attempt < self._config.max_retries:
                    import asyncio

                    await asyncio.sleep(self._config.retry_delay)
                    continue
                return None

            except Exception as e:
                logger.error(f"[AI-ADAPTER] Unexpected error: {e}", exc_info=True)
                return None

        return None

    async def close(self) -> None:
        """
        Cleanup resources (placeholder for future connection pooling).

        Currently a no-op as we create a new client per request.
        """
        pass


# Convenience function for simple usage
async def get_website_intelligence(
    url: str,
    force_refresh: bool = False,
) -> dict[str, Any] | None:
    """
    Convenience function for one-off analysis requests.

    Usage:
        from adapters.ai_agent_adapter import get_website_intelligence

        result = await get_website_intelligence("https://example.com")
    """
    adapter = AIAgentAdapter()
    return await adapter.get_website_intelligence(url, force_refresh)
