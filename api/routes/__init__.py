"""
API Routes

Public routes:
- health: Health check endpoints
- intelligence: Website intelligence analysis
- design: Email design generation
- campaign: Full campaign pipeline

Internal routes (require X-Internal-Secret):
- internal: Service-to-service communication endpoints
"""

from api.routes import campaign, design, health, intelligence, internal

__all__ = ["health", "intelligence", "design", "campaign", "internal"]
