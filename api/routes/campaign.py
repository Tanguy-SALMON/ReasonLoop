"""
Full Campaign Pipeline Endpoint
Chains website intelligence extraction with email design generation
"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool

from api.core.context import AppContext
from api.routes.deps import get_app_context
from api.schemas.requests import FullCampaignRequest
from api.schemas.responses import ErrorResponse, FullCampaignResponse

router = APIRouter(tags=["Campaign"])


@router.post(
    "/campaign/full",
    response_model=FullCampaignResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input"},
        503: {"model": ErrorResponse, "description": "Pipeline failed"},
    },
    summary="Full campaign generation pipeline",
    description="""
    Complete end-to-end campaign generation:

    **Step 1: Website Intelligence**
    - Scrapes the target website
    - Extracts brand identity, colors, fonts, tone
    - Identifies products, pricing, promotions
    - Captures audience insights

    **Step 2: Email Design Generation**
    - Uses brand intelligence to inform designs
    - Spawns 3 design agents (minimalist, bold, elegant)
    - Each creates a unique email design
    - Returns production-ready HTML templates

    This is the one-stop endpoint for generating email campaigns
    from just a website URL.
    """,
)
async def generate_full_campaign(
    request: FullCampaignRequest,
    ctx: AppContext = Depends(get_app_context),
) -> FullCampaignResponse:
    """
    Generate a complete email campaign from a website URL.

    This endpoint chains:
    1. Website intelligence extraction
    2. Email design generation with multiple personas

    Returns both the brand intelligence and the generated designs.
    """
    ctx.logger.info(f"Starting full campaign pipeline for: {request.website_url}")

    try:
        # Step 1: Extract website intelligence
        ctx.logger.info("Step 1: Extracting website intelligence...")

        intelligence_json = await run_in_threadpool(
            ctx.website_intelligence, str(request.website_url)
        )
        intelligence = json.loads(intelligence_json)

        if "error" in intelligence:
            ctx.logger.error(f"Website analysis failed: {intelligence['error']}")
            raise HTTPException(
                status_code=503,
                detail=f"Website analysis failed: {intelligence['error']}",
            )

        ctx.logger.info("Website intelligence extracted successfully")

        # Step 2: Generate email designs using the intelligence
        ctx.logger.info("Step 2: Generating email designs...")

        designs_json = await run_in_threadpool(
            ctx.email_design,
            intelligence_json,  # Pass the raw JSON
            request.campaign_goal,
            request.num_designs,
            True,  # parallel
        )
        designs = json.loads(designs_json)

        if not designs.get("success", False):
            ctx.logger.error(f"Design generation failed: {designs.get('error')}")
            raise HTTPException(
                status_code=503,
                detail=f"Design generation failed: {designs.get('error')}",
            )

        ctx.logger.info(
            f"Full campaign pipeline completed. "
            f"Generated {designs.get('num_designs', 0)} designs"
        )

        return FullCampaignResponse(
            success=True,
            website_url=str(request.website_url),
            campaign_goal=request.campaign_goal,
            intelligence=intelligence,
            designs=designs,
            generated_at=datetime.now().isoformat(),
        )

    except json.JSONDecodeError as e:
        ctx.logger.error(f"Failed to parse pipeline result: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse pipeline result")

    except HTTPException:
        raise

    except Exception as e:
        ctx.logger.error(f"Campaign pipeline error: {e}", exc_info=True)
        raise HTTPException(
            status_code=503, detail=f"Campaign generation failed: {str(e)}"
        )
