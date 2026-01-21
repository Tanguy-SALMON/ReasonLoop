"""
API Configuration - Single source of truth for all settings
"""

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class APIConfig:
    """API Configuration loaded from environment"""

    # Server
    host: str
    port: int
    debug: bool
    cors_origins: list[str]

    # API
    api_title: str
    api_version: str
    api_prefix: str

    @classmethod
    def from_env(cls) -> "APIConfig":
        """Load configuration from environment variables"""
        cors_origins = os.getenv("API_CORS_ORIGINS", "*")

        return cls(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8000")),
            debug=os.getenv("API_DEBUG", "false").lower() == "true",
            cors_origins=cors_origins.split(",") if cors_origins != "*" else ["*"],
            api_title="ReasonLoop Campaign API",
            api_version="1.0.0",
            api_prefix="/api/v1",
        )


@lru_cache()
def get_config() -> APIConfig:
    """Get cached configuration instance"""
    return APIConfig.from_env()
