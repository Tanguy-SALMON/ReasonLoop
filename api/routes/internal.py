"""
Internal API Routes - Secured endpoints for service-to-service communication

These endpoints are designed for the sidecar microservice pattern where
be-campaign (main backend) communicates with ReasonLoop (AI agent service).

All endpoints require the X-Internal-Secret header for authentication.
"""

import asyncio
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, HttpUrl

from api.dependencies import validate_url_security, verify_internal_secret

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/internal",
    tags=["Internal"],
    dependencies=[Depends(verify_internal_secret)],
    responses={
        403: {"description": "Access denied - invalid or missing X-Internal-Secret"},
        408: {"description": "Request timeout - analysis took too long"},
    },
)


# =============================================================================
# Constants
# =============================================================================

ANALYSIS_TIMEOUT_SECONDS = 45  # Hard limit for analysis operations


# =============================================================================
# Request/Response Models
# =============================================================================


class AnalysisStatus(str, Enum):
    """Status of an analysis operation"""

    SUCCESS = "success"
    CACHED = "cached"
    ERROR = "error"
    TIMEOUT = "timeout"


class AnalysisRequest(BaseModel):
    """Request payload for website analysis"""

    url: HttpUrl = Field(
        ...,
        description="The website URL to analyze. Must be a public, accessible URL.",
        examples=["https://www.shiseido.com/us/en/"],
    )
    force_refresh: bool = Field(
        default=False,
        description="If True, bypass cache and perform fresh analysis. "
        "If False, return cached data if available.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "url": "https://www.shiseido.com/us/en/",
                    "force_refresh": False,
                }
            ]
        }
    }


class AnalysisResponse(BaseModel):
    """Response payload from website analysis"""

    status: AnalysisStatus = Field(
        ...,
        description="Status of the analysis operation",
    )
    url: str = Field(
        ...,
        description="The analyzed URL",
    )
    analysis_date: str = Field(
        ...,
        description="ISO timestamp of when the analysis was performed",
    )
    cached: bool = Field(
        default=False,
        description="Whether this response was served from cache",
    )

    # Brand Intelligence Data
    brand_identity: dict[str, Any] = Field(
        default_factory=dict,
        description="Brand name, logo, colors, fonts, tagline",
    )
    brand_voice: dict[str, Any] = Field(
        default_factory=dict,
        description="Brand tone, CTA patterns, emoji usage",
    )
    products: dict[str, Any] = Field(
        default_factory=dict,
        description="Product categories, featured items, pricing",
    )
    value_propositions: dict[str, Any] = Field(
        default_factory=dict,
        description="USPs, guarantees, quality claims",
    )
    promotions: dict[str, Any] = Field(
        default_factory=dict,
        description="Current offers, discounts, newsletter incentives",
    )
    audience: dict[str, Any] = Field(
        default_factory=dict,
        description="Target demographic, pain points, testimonials",
    )
    technical: dict[str, Any] = Field(
        default_factory=dict,
        description="Platform, currency, blog info",
    )
    seo: dict[str, Any] = Field(
        default_factory=dict,
        description="SEO title, meta description, keywords",
    )
    trust_signals: dict[str, Any] = Field(
        default_factory=dict,
        description="Payment methods, security badges, social media",
    )
    email_recommendations: dict[str, Any] = Field(
        default_factory=dict,
        description="Recommended templates, subject line style, content suggestions",
    )

    # Metadata
    error_message: str | None = Field(
        default=None,
        description="Error details if status is 'error' or 'timeout'",
    )
    processing_time_ms: int | None = Field(
        default=None,
        description="Time taken to process the request in milliseconds",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "success",
                    "url": "https://www.shiseido.com/us/en/",
                    "analysis_date": "2026-01-24T16:30:00Z",
                    "cached": False,
                    "brand_identity": {
                        "name": "Shiseido",
                        "tagline": "Since 1872",
                        "colors": ["#000000", "#C41230"],
                    },
                    "brand_voice": {
                        "tone": ["luxury", "sophisticated"],
                        "emoji_usage": False,
                    },
                    "processing_time_ms": 12500,
                }
            ]
        }
    }


# =============================================================================
# Simple In-Memory Cache (for demo - use Redis in production)
# =============================================================================

_analysis_cache: dict[str, tuple[datetime, dict]] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour


def get_cached_analysis(url: str) -> dict | None:
    """Retrieve cached analysis if still valid"""
    if url not in _analysis_cache:
        return None

    cached_time, data = _analysis_cache[url]
    age_seconds = (datetime.now() - cached_time).total_seconds()

    if age_seconds > CACHE_TTL_SECONDS:
        del _analysis_cache[url]
        return None

    logger.info(f"Cache hit for {url} (age: {age_seconds:.0f}s)")
    return data


def set_cached_analysis(url: str, data: dict) -> None:
    """Store analysis result in cache"""
    _analysis_cache[url] = (datetime.now(), data)
    logger.info(f"Cached analysis for {url}")


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/v1/analyze",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze website for brand intelligence",
    description="""
    Performs comprehensive website analysis to extract brand intelligence data.

    **Security**: Requires X-Internal-Secret header.

    **Timeout**: Operations are limited to 45 seconds. If analysis takes longer,
    a 408 Request Timeout is returned.

    **Caching**: Results are cached for 1 hour. Use `force_refresh=true` to bypass cache.

    **SSRF Protection**: Localhost and private IPs are rejected.
    """,
)
async def analyze_website(request: AnalysisRequest) -> AnalysisResponse:
    """
    Analyze a website and extract brand intelligence for email campaign generation.

    This endpoint is designed for internal service-to-service communication.
    The main backend (be-campaign) calls this to enrich customer data.
    """
    import time

    start_time = time.time()

    url_str = str(request.url)
    logger.info(
        f"[ANALYZE] Request received for: {url_str} (force_refresh={request.force_refresh})"
    )

    # Security: Validate URL is not internal/private
    validate_url_security(url_str)

    # Check cache if not forcing refresh
    if not request.force_refresh:
        cached = get_cached_analysis(url_str)
        if cached:
            processing_time = int((time.time() - start_time) * 1000)
            return AnalysisResponse(
                status=AnalysisStatus.CACHED,
                url=url_str,
                analysis_date=cached.get("analysis_date", datetime.now().isoformat()),
                cached=True,
                brand_identity=cached.get("brand_identity", {}),
                brand_voice=cached.get("brand_voice", {}),
                products=cached.get("products", {}),
                value_propositions=cached.get("value_propositions", {}),
                promotions=cached.get("promotions", {}),
                audience=cached.get("audience", {}),
                technical=cached.get("technical", {}),
                seo=cached.get("seo", {}),
                trust_signals=cached.get("trust_signals", {}),
                email_recommendations=cached.get("email_campaign_recommendations", {}),
                processing_time_ms=processing_time,
            )

    # Perform fresh analysis with timeout
    try:
        result = await asyncio.wait_for(
            _run_website_intelligence(url_str),
            timeout=ANALYSIS_TIMEOUT_SECONDS,
        )

        processing_time = int((time.time() - start_time) * 1000)

        # Check for errors in the result
        if "error" in result:
            logger.error(f"[ANALYZE] Analysis failed for {url_str}: {result['error']}")
            return AnalysisResponse(
                status=AnalysisStatus.ERROR,
                url=url_str,
                analysis_date=datetime.now().isoformat(),
                cached=False,
                error_message=result["error"],
                processing_time_ms=processing_time,
            )

        # Cache the successful result
        set_cached_analysis(url_str, result)

        logger.info(f"[ANALYZE] Success for {url_str} in {processing_time}ms")

        return AnalysisResponse(
            status=AnalysisStatus.SUCCESS,
            url=url_str,
            analysis_date=result.get("analysis_date", datetime.now().isoformat()),
            cached=False,
            brand_identity=result.get("brand_identity", {}),
            brand_voice=result.get("brand_voice", {}),
            products=result.get("products", {}),
            value_propositions=result.get("value_propositions", {}),
            promotions=result.get("promotions", {}),
            audience=result.get("audience", {}),
            technical=result.get("technical", {}),
            seo=result.get("seo", {}),
            trust_signals=result.get("trust_signals", {}),
            email_recommendations=result.get("email_campaign_recommendations", {}),
            processing_time_ms=processing_time,
        )

    except asyncio.TimeoutError:
        processing_time = int((time.time() - start_time) * 1000)
        logger.error(
            f"[ANALYZE] Timeout after {ANALYSIS_TIMEOUT_SECONDS}s for {url_str}"
        )
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=f"Analysis timed out after {ANALYSIS_TIMEOUT_SECONDS} seconds. "
            f"The website may be slow or complex. Try again later.",
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except Exception as e:
        processing_time = int((time.time() - start_time) * 1000)
        logger.error(f"[ANALYZE] Unexpected error for {url_str}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Analysis service error: {str(e)}",
        )


@router.get(
    "/v1/health",
    summary="Internal health check",
    description="Health check endpoint for service discovery and load balancers.",
)
async def internal_health() -> dict:
    """Internal health check - verifies the service is running and auth is working"""
    return {
        "status": "healthy",
        "service": "reasonloop-intelligence",
        "version": "0.3.0",
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# Helper Functions
# =============================================================================


async def _run_website_intelligence(url: str) -> dict:
    """
    Execute the website intelligence ability in a thread pool.

    The website_intelligence_ability is synchronous (uses requests/BeautifulSoup),
    so we run it in a thread pool to not block the async event loop.
    """
    from abilities.website_intelligence import website_intelligence_ability

    # Run synchronous ability in thread pool
    result_json = await run_in_threadpool(website_intelligence_ability, url)

    # Parse JSON result
    try:
        return json.loads(result_json)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse intelligence result: {e}")
        return {"error": f"Failed to parse analysis result: {e}"}
