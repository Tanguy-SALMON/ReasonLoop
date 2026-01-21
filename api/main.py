"""
ReasonLoop Campaign API - FastAPI Application Entry Point

This API exposes the website intelligence and email design agents
as RESTful endpoints for automated email campaign generation.
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.core.config import get_config
from api.core.errors import APIError, api_error_handler
from api.routes import campaign, design, health, intelligence

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Startup: Load abilities, initialize services
    Shutdown: Cleanup resources
    """
    # Startup
    logger.info("Starting ReasonLoop Campaign API...")

    # Import abilities to trigger registration
    try:
        import abilities  # noqa: F401
        from abilities.ability_registry import list_abilities

        available = list(list_abilities().keys())
        logger.info(f"Loaded {len(available)} abilities: {available}")
    except Exception as e:
        logger.error(f"Failed to load abilities: {e}")

    logger.info("API startup complete")

    yield

    # Shutdown
    logger.info("Shutting down ReasonLoop Campaign API...")


def create_app() -> FastAPI:
    """
    Factory function to create the FastAPI application.
    This pattern allows for easy testing and configuration.
    """
    config = get_config()

    app = FastAPI(
        title=config.api_title,
        version=config.api_version,
        description="""
## ReasonLoop Campaign API

AI-powered email campaign generation service.

### Features

- **Website Intelligence**: Extract brand data from any website
- **Email Design Generation**: Create multiple email designs with AI agents
- **Full Pipeline**: One-click campaign generation from URL to HTML

### Workflow

1. **Analyze**: POST `/api/v1/website-intelligence` with a website URL
2. **Design**: POST `/api/v1/email-design` with brand intelligence
3. **Or use**: POST `/api/v1/campaign/full` for the complete pipeline

### Design Personas

The email design endpoint spawns multiple AI agents:
- **Minimalist**: Clean, whitespace-focused
- **Bold**: Strong colors, impactful CTAs
- **Elegant**: Sophisticated, luxury feel
        """,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register exception handlers
    app.add_exception_handler(APIError, api_error_handler)

    # Include routers
    app.include_router(health.router, prefix=config.api_prefix)
    app.include_router(intelligence.router, prefix=config.api_prefix)
    app.include_router(design.router, prefix=config.api_prefix)
    app.include_router(campaign.router, prefix=config.api_prefix)

    # Root endpoint
    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "name": config.api_title,
            "version": config.api_version,
            "docs": "/docs",
            "health": f"{config.api_prefix}/health",
        }

    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    config = get_config()

    uvicorn.run(
        "api.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
    )
