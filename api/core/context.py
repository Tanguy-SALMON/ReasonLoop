"""
Application Context Pattern - All dependencies in one place
"""

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from api.core.config import APIConfig, get_config


@dataclass
class AppContext:
    """
    Application context containing all dependencies.
    Passed to route handlers for easy testing and clear dependency management.
    """

    config: APIConfig
    logger: logging.Logger

    # Ability executors (lazy-loaded)
    _website_intelligence: Optional[Callable] = None
    _email_design: Optional[Callable] = None

    @property
    def website_intelligence(self) -> Callable:
        """Get website intelligence ability"""
        if self._website_intelligence is None:
            from abilities.website_intelligence import website_intelligence_ability

            self._website_intelligence = website_intelligence_ability
        return self._website_intelligence

    @property
    def email_design(self) -> Callable:
        """Get email design ability"""
        if self._email_design is None:
            from abilities.email_design_agent import email_design_ability

            self._email_design = email_design_ability
        return self._email_design


def create_context() -> AppContext:
    """Factory function to create application context"""
    logger = logging.getLogger("api")

    return AppContext(
        config=get_config(),
        logger=logger,
    )


# Singleton context for dependency injection
_context: Optional[AppContext] = None


def get_context() -> AppContext:
    """Get or create application context (for FastAPI dependency)"""
    global _context
    if _context is None:
        _context = create_context()
    return _context
