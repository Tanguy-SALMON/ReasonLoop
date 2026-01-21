"""
Health and utility endpoints
"""

from datetime import datetime

from fastapi import APIRouter, Depends

from api.core.context import AppContext
from api.routes.deps import get_app_context
from api.schemas.responses import AbilitiesResponse, HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(ctx: AppContext = Depends(get_app_context)) -> HealthResponse:
    """
    Health check endpoint.
    Returns API status, version, and available abilities.
    """
    # Import abilities to get the list
    from abilities.ability_registry import list_abilities

    abilities = list(list_abilities().keys())

    return HealthResponse(
        status="healthy",
        version=ctx.config.api_version,
        timestamp=datetime.now(),
        abilities=abilities,
    )


@router.get("/abilities", response_model=AbilitiesResponse)
async def list_available_abilities(
    ctx: AppContext = Depends(get_app_context),
) -> AbilitiesResponse:
    """
    List all available abilities that can be used via the API.
    """
    from abilities.ability_registry import list_abilities

    abilities = list(list_abilities().keys())

    return AbilitiesResponse(
        success=True,
        abilities=abilities,
        count=len(abilities),
    )
