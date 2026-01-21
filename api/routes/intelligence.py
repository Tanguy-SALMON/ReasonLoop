"""
Website Intelligence Endpoint
Extracts brand data from customer websites for email campaign generation
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool

from api.core.context import AppContext
from api.core.errors import ServiceError
from api.routes.deps import get_app_context
from api.schemas.requests import WebsiteIntelligenceRequest
from api.schemas.responses import ErrorResponse, WebsiteIntelligenceResponse

router = APIRouter(tags=["Intelligence"])


@router.post(
    "/website-intelligence",
    response_model=WebsiteIntelligenceResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid URL"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
    summary="Analyze website for email campaign intelligence",
    description="""
    Extracts comprehensive brand intelligence from a website including:
    - Brand identity (name, logo, colors, fonts)
    - Brand voice and tone
    - Product catalog and pricing
    - Value propositions and USPs
    - Current promotions
    - Audience insights
    - Technical platform info
    - SEO metadata
    - Trust signals

    Use this data to generate personalized email campaigns.
    """,
)
async def analyze_website(
    request: WebsiteIntelligenceRequest,
    ctx: AppContext = Depends(get_app_context),
) -> WebsiteIntelligenceResponse:
    """
    Extract brand intelligence from a website.

    This endpoint scrapes the target website and extracts all information
    needed to create on-brand email campaigns.
    """
    ctx.logger.info(f"Analyzing website: {request.url}")

    try:
        # Run the ability in a thread pool (it's synchronous)
        result_json = await run_in_threadpool(
            ctx.website_intelligence, str(request.url)
        )

        # Parse the result
        result = json.loads(result_json)

        # Check for errors from the ability
        if "error" in result:
            ctx.logger.error(f"Website analysis failed: {result['error']}")
            raise HTTPException(status_code=503, detail=result["error"])

        ctx.logger.info(f"Website analysis completed for: {request.url}")

        return WebsiteIntelligenceResponse(
            success=True,
            website_url=str(request.url),
            analysis_date=result.get("analysis_date", ""),
            brand_identity=result.get("brand_identity", {}),
            brand_voice=result.get("brand_voice", {}),
            products=result.get("products", {}),
            value_propositions=result.get("value_propositions", {}),
            promotions=result.get("promotions", {}),
            audience=result.get("audience", {}),
            technical=result.get("technical", {}),
            seo=result.get("seo", {}),
            trust_signals=result.get("trust_signals", {}),
            email_campaign_recommendations=result.get(
                "email_campaign_recommendations", {}
            ),
        )

    except json.JSONDecodeError as e:
        ctx.logger.error(f"Failed to parse intelligence result: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse analysis result")

    except HTTPException:
        raise

    except Exception as e:
        ctx.logger.error(f"Website analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Analysis failed: {str(e)}")
