"""
FastAPI Dependencies - Dependency injection for routes
"""

from typing import Generator

from fastapi import Depends

from api.core.context import AppContext, get_context


async def get_app_context() -> AppContext:
    """
    Dependency that provides the application context.
    Use this in route handlers to access all services.

    Example:
        @router.get("/campaigns")
        async def list_campaigns(ctx: AppContext = Depends(get_app_context)):
            ctx.logger.info("Listing campaigns")
            ...
    """
    return get_context()
