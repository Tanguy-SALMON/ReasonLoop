"""
Customer AI Service - Business logic for AI-powered customer enrichment

This service orchestrates the process of enriching customer data with
brand intelligence from ReasonLoop. It's designed to run as a background
task to avoid blocking the main API thread.

Architecture:
    API Endpoint -> BackgroundTask -> CustomerAIService -> AIAgentAdapter -> ReasonLoop

Usage:
    # In a FastAPI background task
    from services.customer_ai_service import enrich_customer_background

    @router.post("/{id}/enrich")
    async def enrich(id: str, background_tasks: BackgroundTasks, db: Session):
        customer = db.query(Customer).get(id)
        background_tasks.add_task(
            enrich_customer_background,
            customer_id=id,
            website=customer.website,
            db=db
        )
        return {"status": "queued"}
"""

import logging
from datetime import datetime
from typing import Any, Protocol

from ..adapters.ai_agent_adapter import AIAgentAdapter
from ..models.customer import Customer

logger = logging.getLogger(__name__)


# =============================================================================
# Database Protocol (for dependency injection)
# =============================================================================


class DatabaseSession(Protocol):
    """
    Protocol for database session operations.

    This allows the service to work with any ORM (SQLAlchemy, SQLModel, etc.)
    as long as it implements these methods.
    """

    def query(self, model: type) -> Any:
        """Query a model"""
        ...

    def commit(self) -> None:
        """Commit the current transaction"""
        ...

    def refresh(self, instance: Any) -> None:
        """Refresh an instance from the database"""
        ...


# =============================================================================
# Service Class
# =============================================================================


class CustomerAIService:
    """
    Service for AI-powered customer enrichment.

    This service handles:
    1. Fetching customer from database
    2. Calling ReasonLoop for website analysis
    3. Mapping intelligence data to customer fields
    4. Persisting enriched data back to database
    5. Error handling and status tracking

    Example:
        service = CustomerAIService(db_session, adapter)
        success = await service.enrich_customer("cust_123")
    """

    def __init__(
        self,
        db: DatabaseSession | None = None,
        adapter: AIAgentAdapter | None = None,
    ):
        """
        Initialize the service.

        Args:
            db: Database session for persistence (optional for testing)
            adapter: AI agent adapter (creates default if not provided)
        """
        self._db = db
        self._adapter = adapter or AIAgentAdapter()

    async def enrich_customer(
        self,
        customer_id: str,
        website: str | None = None,
        force_refresh: bool = False,
    ) -> bool:
        """
        Enrich a customer with AI-extracted website intelligence.

        Args:
            customer_id: The customer ID to enrich
            website: Website URL (if not provided, fetched from customer record)
            force_refresh: Bypass ReasonLoop cache

        Returns:
            True if enrichment succeeded, False otherwise
        """
        logger.info(f"[AI-SERVICE] Starting enrichment for customer {customer_id}")

        # Get customer from database
        customer = self._get_customer(customer_id)
        if not customer:
            logger.error(f"[AI-SERVICE] Customer {customer_id} not found")
            return False

        # Determine website URL
        target_url = website or customer.website
        if not target_url:
            logger.warning(f"[AI-SERVICE] No website URL for customer {customer_id}")
            self._mark_failed(customer, "No website URL configured")
            return False

        # Mark as processing
        customer.mark_enrichment_processing()
        self._commit()

        # Call ReasonLoop
        logger.info(f"[AI-SERVICE] Analyzing website: {target_url}")
        intelligence = await self._adapter.get_website_intelligence(
            url=target_url,
            force_refresh=force_refresh,
        )

        # Handle failure
        if intelligence is None:
            logger.error(f"[AI-SERVICE] Analysis failed for {target_url}")
            self._mark_failed(customer, "ReasonLoop analysis failed or unreachable")
            return False

        # Check for error status in response
        status = intelligence.get("status", "unknown")
        if status in ("error", "timeout"):
            error_msg = intelligence.get("error_message", "Unknown error")
            logger.error(f"[AI-SERVICE] Analysis returned error: {error_msg}")
            self._mark_failed(customer, error_msg)
            return False

        # Apply enrichment
        try:
            customer.apply_ai_enrichment(intelligence)
            self._commit()
            logger.info(
                f"[AI-SERVICE] Successfully enriched customer {customer_id} "
                f"(brand_tone={customer.brand_tone}, categories={len(customer.ai_categories)})"
            )
            return True

        except Exception as e:
            logger.error(f"[AI-SERVICE] Failed to apply enrichment: {e}", exc_info=True)
            self._mark_failed(customer, f"Failed to apply enrichment: {str(e)}")
            return False

    def _get_customer(self, customer_id: str) -> Customer | None:
        """
        Fetch customer from database.

        Override this method for your specific ORM.
        """
        if self._db is None:
            logger.warning("[AI-SERVICE] No database session - using mock customer")
            return Customer(id=customer_id, name="Mock Customer")

        try:
            return self._db.query(Customer).filter(Customer.id == customer_id).first()
        except Exception as e:
            logger.error(f"[AI-SERVICE] Database error: {e}")
            return None

    def _mark_failed(self, customer: Customer, error: str) -> None:
        """Mark customer enrichment as failed and persist"""
        customer.mark_enrichment_failed(error)
        self._commit()

    def _commit(self) -> None:
        """Commit database changes"""
        if self._db is not None:
            try:
                self._db.commit()
            except Exception as e:
                logger.error(f"[AI-SERVICE] Commit failed: {e}")


# =============================================================================
# Standalone Background Task Function
# =============================================================================


async def enrich_customer_background(
    customer_id: str,
    website: str,
    db: Any = None,
    force_refresh: bool = False,
) -> None:
    """
    Background task function for customer enrichment.

    This function is designed to be called from FastAPI's BackgroundTasks.
    It creates its own service instance and handles all errors internally.

    Args:
        customer_id: The customer ID to enrich
        website: The website URL to analyze
        db: Database session (optional, for persistence)
        force_refresh: Bypass cache

    Usage in FastAPI:
        @router.post("/{id}/enrich")
        async def trigger_enrich(
            id: str,
            background_tasks: BackgroundTasks,
            db: Session = Depends(get_db)
        ):
            customer = db.query(Customer).get(id)
            background_tasks.add_task(
                enrich_customer_background,
                customer_id=id,
                website=customer.website,
                db=db,
            )
            return {"status": "queued", "customer_id": id}
    """
    logger.info(f"[BACKGROUND] Starting enrichment task for customer {customer_id}")

    try:
        service = CustomerAIService(db=db)
        success = await service.enrich_customer(
            customer_id=customer_id,
            website=website,
            force_refresh=force_refresh,
        )

        if success:
            logger.info(f"[BACKGROUND] Enrichment completed for customer {customer_id}")
        else:
            logger.warning(f"[BACKGROUND] Enrichment failed for customer {customer_id}")

    except Exception as e:
        logger.error(
            f"[BACKGROUND] Unexpected error in enrichment task: {e}", exc_info=True
        )


# =============================================================================
# Batch Enrichment (for scheduled jobs)
# =============================================================================


async def enrich_pending_customers(
    db: Any,
    limit: int = 10,
    force_refresh: bool = False,
) -> dict[str, int]:
    """
    Batch enrich all pending customers.

    This function is designed for scheduled jobs (cron, Celery, etc.)
    that periodically enrich new customers.

    Args:
        db: Database session
        limit: Maximum number of customers to process
        force_refresh: Bypass cache

    Returns:
        Dict with counts: {"processed": N, "success": M, "failed": K}

    Usage:
        # In a scheduled job
        from services.customer_ai_service import enrich_pending_customers

        async def daily_enrichment_job():
            db = get_db_session()
            result = await enrich_pending_customers(db, limit=100)
            print(f"Enriched {result['success']}/{result['processed']} customers")
    """
    logger.info(f"[BATCH] Starting batch enrichment (limit={limit})")

    # Query pending customers
    # This would be: db.query(Customer).filter(Customer.ai_enrichment_status == "pending").limit(limit)
    # For now, we'll just log

    stats = {"processed": 0, "success": 0, "failed": 0}

    # In a real implementation:
    # pending = db.query(Customer).filter(
    #     Customer.ai_enrichment_status == "pending",
    #     Customer.website.isnot(None)
    # ).limit(limit).all()
    #
    # for customer in pending:
    #     stats["processed"] += 1
    #     service = CustomerAIService(db=db)
    #     if await service.enrich_customer(customer.id, force_refresh=force_refresh):
    #         stats["success"] += 1
    #     else:
    #         stats["failed"] += 1

    logger.info(f"[BATCH] Completed: {stats}")
    return stats
