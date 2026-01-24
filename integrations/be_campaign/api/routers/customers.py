"""
Customer API Router - Endpoints for customer management with AI enrichment

This router provides endpoints for be-campaign to manage customers and
trigger AI enrichment via ReasonLoop.

The /enrich endpoint uses FastAPI's BackgroundTasks to process the
AI analysis asynchronously, returning immediately with a 202 Accepted.

Usage:
    from api.routers.customers import router
    app.include_router(router, prefix="/api/v1/customers", tags=["Customers"])
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ...services.customer_ai_service import enrich_customer_background

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Customers"])


# =============================================================================
# Request/Response Models
# =============================================================================


class EnrichmentStatus(str, Enum):
    """Status of an enrichment request"""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_WEBSITE = "no_website"


class EnrichRequest(BaseModel):
    """Optional parameters for enrichment request"""

    force_refresh: bool = Field(
        default=False,
        description="Bypass cache and perform fresh analysis",
    )

    model_config = {"json_schema_extra": {"examples": [{"force_refresh": False}]}}


class EnrichResponse(BaseModel):
    """Response from enrichment trigger"""

    status: EnrichmentStatus = Field(
        ...,
        description="Status of the enrichment request",
    )
    customer_id: str = Field(
        ...,
        description="ID of the customer being enriched",
    )
    message: str = Field(
        ...,
        description="Human-readable status message",
    )
    queued_at: str = Field(
        ...,
        description="ISO timestamp when request was queued",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "queued",
                    "customer_id": "cust_123",
                    "message": "Enrichment task queued for processing",
                    "queued_at": "2026-01-24T16:30:00Z",
                }
            ]
        }
    }


class CustomerResponse(BaseModel):
    """Customer data response"""

    id: str
    name: str
    email: str | None = None
    website: str | None = None

    # AI enrichment fields
    brand_tone: str | None = None
    ai_keywords: list[str] = []
    ai_categories: list[str] = []
    brand_colors: list[str] = []
    pricing_tier: str | None = None
    ai_enrichment_status: str = "pending"
    ai_enriched_at: str | None = None


class CustomerListResponse(BaseModel):
    """List of customers"""

    customers: list[CustomerResponse]
    total: int
    page: int = 1
    page_size: int = 20


# =============================================================================
# Mock Database (replace with real DB in production)
# =============================================================================


# In-memory mock database for demonstration
_mock_customers: dict[str, dict] = {
    "cust_001": {
        "id": "cust_001",
        "name": "Shiseido US",
        "email": "contact@shiseido.com",
        "website": "https://www.shiseido.com/us/en/",
        "brand_tone": None,
        "ai_keywords": [],
        "ai_enrichment_status": "pending",
    },
    "cust_002": {
        "id": "cust_002",
        "name": "COS Thailand",
        "email": "contact@cos.com",
        "website": "https://th.cos.com",
        "brand_tone": None,
        "ai_keywords": [],
        "ai_enrichment_status": "pending",
    },
}


def get_mock_customer(customer_id: str) -> dict | None:
    """Get customer from mock database"""
    return _mock_customers.get(customer_id)


def update_mock_customer(customer_id: str, data: dict) -> None:
    """Update customer in mock database"""
    if customer_id in _mock_customers:
        _mock_customers[customer_id].update(data)


# =============================================================================
# Dependency Injection (replace with real DB session)
# =============================================================================


class MockDBSession:
    """Mock database session for demonstration"""

    def query(self, model: type) -> "MockQuery":
        return MockQuery()

    def commit(self) -> None:
        pass

    def refresh(self, instance: Any) -> None:
        pass


class MockQuery:
    """Mock query builder"""

    def __init__(self):
        self._filters = []

    def filter(self, *args) -> "MockQuery":
        return self

    def first(self) -> dict | None:
        return None

    def get(self, id: str) -> dict | None:
        return get_mock_customer(id)


async def get_db() -> MockDBSession:
    """
    Database session dependency.

    Replace this with your actual database session factory:

        from sqlalchemy.orm import Session
        from database import SessionLocal

        def get_db():
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()
    """
    return MockDBSession()


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "",
    response_model=CustomerListResponse,
    summary="List all customers",
)
async def list_customers(
    page: int = 1,
    page_size: int = 20,
    db: MockDBSession = Depends(get_db),
) -> CustomerListResponse:
    """
    List all customers with pagination.
    """
    customers = [CustomerResponse(**data) for data in _mock_customers.values()]

    return CustomerListResponse(
        customers=customers,
        total=len(customers),
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Get customer by ID",
)
async def get_customer(
    customer_id: str,
    db: MockDBSession = Depends(get_db),
) -> CustomerResponse:
    """
    Get a single customer by ID.
    """
    customer = get_mock_customer(customer_id)

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found",
        )

    return CustomerResponse(**customer)


@router.post(
    "/{customer_id}/enrich",
    response_model=EnrichResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger AI enrichment for customer",
    description="""
    Triggers an asynchronous AI enrichment process for the customer.

    This endpoint:
    1. Validates the customer exists and has a website
    2. Queues a background task to call ReasonLoop
    3. Returns immediately with 202 Accepted

    The enrichment process will:
    - Analyze the customer's website using ReasonLoop
    - Extract brand intelligence (tone, colors, keywords)
    - Update the customer record with AI-enriched fields

    Check the customer's `ai_enrichment_status` field to monitor progress:
    - `queued`: Waiting to be processed
    - `processing`: Analysis in progress
    - `completed`: Successfully enriched
    - `failed`: Enrichment failed (see `ai_enrichment_error`)

    **Note**: Analysis typically takes 10-45 seconds.
    """,
)
async def enrich_customer(
    customer_id: str,
    request: EnrichRequest | None = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: MockDBSession = Depends(get_db),
) -> EnrichResponse:
    """
    Trigger AI enrichment for a customer.

    This endpoint queues a background task and returns immediately.
    """
    logger.info(f"[ENRICH] Received request for customer {customer_id}")

    # Get customer
    customer = get_mock_customer(customer_id)

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found",
        )

    # Check for website
    website = customer.get("website")
    if not website:
        logger.warning(f"[ENRICH] No website configured for customer {customer_id}")
        return EnrichResponse(
            status=EnrichmentStatus.NO_WEBSITE,
            customer_id=customer_id,
            message="Customer has no website configured. Cannot perform AI enrichment.",
            queued_at=datetime.now().isoformat(),
        )

    # Check if already processing
    current_status = customer.get("ai_enrichment_status")
    if current_status == "processing":
        return EnrichResponse(
            status=EnrichmentStatus.PROCESSING,
            customer_id=customer_id,
            message="Enrichment already in progress. Please wait.",
            queued_at=datetime.now().isoformat(),
        )

    # Update status to queued
    update_mock_customer(customer_id, {"ai_enrichment_status": "queued"})

    # Queue background task
    force_refresh = request.force_refresh if request else False

    background_tasks.add_task(
        enrich_customer_background,
        customer_id=customer_id,
        website=website,
        db=db,
        force_refresh=force_refresh,
    )

    logger.info(f"[ENRICH] Queued enrichment task for customer {customer_id}")

    return EnrichResponse(
        status=EnrichmentStatus.QUEUED,
        customer_id=customer_id,
        message="Enrichment task queued for processing. "
        "Check customer status in ~30 seconds.",
        queued_at=datetime.now().isoformat(),
    )


@router.get(
    "/{customer_id}/enrichment-status",
    summary="Check enrichment status",
)
async def get_enrichment_status(
    customer_id: str,
    db: MockDBSession = Depends(get_db),
) -> dict:
    """
    Check the current enrichment status for a customer.

    Returns the AI enrichment fields including status, error (if any),
    and timestamp of last enrichment.
    """
    customer = get_mock_customer(customer_id)

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found",
        )

    return {
        "customer_id": customer_id,
        "status": customer.get("ai_enrichment_status", "pending"),
        "enriched_at": customer.get("ai_enriched_at"),
        "error": customer.get("ai_enrichment_error"),
        "brand_tone": customer.get("brand_tone"),
        "ai_keywords": customer.get("ai_keywords", []),
    }
