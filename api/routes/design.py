"""
Email Design Generation Endpoint
Multi-agent system that creates diverse email designs from brand intelligence
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool

from api.core.context import AppContext
from api.routes.deps import get_app_context
from api.schemas.requests import EmailDesignRequest
from api.schemas.responses import EmailDesignResponse, ErrorResponse

router = APIRouter(tags=["Design"])


@router.post(
    "/email-design",
    response_model=EmailDesignResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input"},
        503: {"model": ErrorResponse, "description": "Design generation failed"},
    },
    summary="Generate email designs from brand intelligence",
    description="""
    Spawns multiple design agents with different personas to create
    diverse email design options:

    - **MINIMALIST**: Clean, whitespace-focused, typography-driven
    - **BOLD**: Strong colors, large imagery, impactful CTAs
    - **ELEGANT**: Sophisticated, luxury feel, refined details

    Each design includes:
    - Subject line and preview text
    - Headline and body copy
    - CTA button
    - Color scheme and typography
    - Full HTML template
    - Design rationale
    """,
)
async def generate_email_designs(
    request: EmailDesignRequest,
    ctx: AppContext = Depends(get_app_context),
) -> EmailDesignResponse:
    """
    Generate multiple email design variations using AI agents.

    Each agent has a unique design persona (minimalist, bold, elegant)
    and produces a distinct design based on the brand intelligence.
    """
    ctx.logger.info(
        f"Generating {request.num_designs} email designs. "
        f"Goal: {request.campaign_goal[:50]}..."
    )

    try:
        # Run the email design ability in a thread pool
        result_json = await run_in_threadpool(
            ctx.email_design,
            json.dumps(request.brand_intelligence),
            request.campaign_goal,
            request.num_designs,
            request.parallel,
        )

        # Parse the result
        result = json.loads(result_json)

        # Check for errors
        if not result.get("success", False):
            error_msg = result.get("error", "Design generation failed")
            ctx.logger.error(f"Email design failed: {error_msg}")
            raise HTTPException(status_code=503, detail=error_msg)

        ctx.logger.info(f"Generated {result.get('num_designs', 0)} email designs")

        return EmailDesignResponse(
            success=True,
            num_designs=result.get("num_designs", 0),
            campaign_goal=request.campaign_goal,
            designs=result.get("designs", []),
            metadata=result.get("metadata", {}),
        )

    except json.JSONDecodeError as e:
        ctx.logger.error(f"Failed to parse design result: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse design result")

    except HTTPException:
        raise

    except Exception as e:
        ctx.logger.error(f"Email design error: {e}", exc_info=True)
        raise HTTPException(
            status_code=503, detail=f"Design generation failed: {str(e)}"
        )
