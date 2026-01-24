"""
Customer Model with AI-enriched fields

This model extends the base customer with fields populated by ReasonLoop analysis.
These fields enable personalized email campaign generation based on brand intelligence.

Usage:
    # SQLAlchemy ORM example
    from models.customer import Customer

    customer = Customer(
        id="cust_123",
        name="Acme Corp",
        website="https://acme.com",
    )

    # After AI enrichment
    customer.brand_tone = "professional, innovative"
    customer.ai_keywords = ["technology", "solutions", "enterprise"]
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CustomerAIFields:
    """
    AI-enriched fields extracted from website analysis.

    These fields are populated by the customer_ai_service after
    calling ReasonLoop's intelligence endpoint.
    """

    # Brand Voice & Tone
    brand_tone: str | None = None
    """Comma-separated brand tones (e.g., "luxury, sophisticated, professional")"""

    brand_voice_characteristics: str | None = None
    """Description of brand voice (e.g., "Uses emojis, casual tone")"""

    # Keywords & SEO
    ai_keywords: list[str] = field(default_factory=list)
    """Primary keywords extracted from website SEO"""

    ai_categories: list[str] = field(default_factory=list)
    """Product categories from website"""

    # Visual Identity
    brand_colors: list[str] = field(default_factory=list)
    """Brand colors as hex codes (e.g., ["#000000", "#C41230"])"""

    brand_fonts: list[str] = field(default_factory=list)
    """Brand fonts (e.g., ["Noto Sans", "Bodoni"])"""

    brand_logo_url: str | None = None
    """URL to brand logo"""

    # Business Intelligence
    pricing_tier: str | None = None
    """Detected pricing tier: budget, mid-range, premium, luxury"""

    platform: str | None = None
    """E-commerce platform: Shopify, Magento, WooCommerce, etc."""

    currency: str = "USD"
    """Primary currency"""

    # Recommendations
    email_subject_style: str | None = None
    """Recommended subject line style for email campaigns"""

    recommended_templates: list[str] = field(default_factory=list)
    """Recommended email template types: welcome, promotional, etc."""

    content_suggestions: list[str] = field(default_factory=list)
    """Content suggestions for email campaigns"""

    # Metadata
    ai_enriched_at: datetime | None = None
    """Timestamp when AI enrichment was performed"""

    ai_enrichment_status: str = "pending"
    """Status: pending, processing, completed, failed"""

    ai_enrichment_error: str | None = None
    """Error message if enrichment failed"""

    raw_intelligence: dict[str, Any] = field(default_factory=dict)
    """Full raw response from ReasonLoop (for debugging/extension)"""


@dataclass
class Customer:
    """
    Customer model with AI enrichment support.

    In a real application, this would be a SQLAlchemy/SQLModel ORM class.
    This dataclass serves as a reference implementation.

    Database Schema (MySQL/PostgreSQL):

        CREATE TABLE customers (
            id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            website VARCHAR(500),

            -- AI-enriched fields
            brand_tone VARCHAR(500),
            brand_voice_characteristics TEXT,
            ai_keywords JSON,
            ai_categories JSON,
            brand_colors JSON,
            brand_fonts JSON,
            brand_logo_url VARCHAR(1000),
            pricing_tier VARCHAR(50),
            platform VARCHAR(100),
            currency VARCHAR(10) DEFAULT 'USD',
            email_subject_style TEXT,
            recommended_templates JSON,
            content_suggestions JSON,
            ai_enriched_at TIMESTAMP,
            ai_enrichment_status VARCHAR(50) DEFAULT 'pending',
            ai_enrichment_error TEXT,
            raw_intelligence JSON,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        );
    """

    # Core fields
    id: str
    name: str
    email: str | None = None
    website: str | None = None

    # AI-enriched fields (flattened for ORM compatibility)
    brand_tone: str | None = None
    brand_voice_characteristics: str | None = None
    ai_keywords: list[str] = field(default_factory=list)
    ai_categories: list[str] = field(default_factory=list)
    brand_colors: list[str] = field(default_factory=list)
    brand_fonts: list[str] = field(default_factory=list)
    brand_logo_url: str | None = None
    pricing_tier: str | None = None
    platform: str | None = None
    currency: str = "USD"
    email_subject_style: str | None = None
    recommended_templates: list[str] = field(default_factory=list)
    content_suggestions: list[str] = field(default_factory=list)
    ai_enriched_at: datetime | None = None
    ai_enrichment_status: str = "pending"
    ai_enrichment_error: str | None = None
    raw_intelligence: dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def apply_ai_enrichment(self, intelligence: dict[str, Any]) -> None:
        """
        Apply AI intelligence data to customer fields.

        Args:
            intelligence: Response from ReasonLoop /api/v1/internal/v1/analyze
        """
        # Brand Identity
        brand_identity = intelligence.get("brand_identity", {})
        self.brand_logo_url = brand_identity.get("logo_url")
        self.brand_colors = brand_identity.get("colors", [])
        self.brand_fonts = brand_identity.get("fonts", [])

        # Brand Voice
        brand_voice = intelligence.get("brand_voice", {})
        tones = brand_voice.get("tone", [])
        self.brand_tone = ", ".join(tones) if tones else None
        self.brand_voice_characteristics = brand_voice.get("characteristics")

        # Products
        products = intelligence.get("products", {})
        self.ai_categories = products.get("categories", [])
        self.pricing_tier = products.get("pricing_tier")

        # Technical
        technical = intelligence.get("technical", {})
        self.platform = technical.get("platform")
        self.currency = technical.get("currency", "USD")

        # SEO Keywords
        seo = intelligence.get("seo", {})
        self.ai_keywords = seo.get("primary_keywords", [])

        # Email Recommendations
        recommendations = intelligence.get("email_recommendations", {})
        self.email_subject_style = recommendations.get("subject_line_style")
        self.recommended_templates = recommendations.get("recommended_templates", [])
        self.content_suggestions = recommendations.get("content_suggestions", [])

        # Metadata
        self.ai_enriched_at = datetime.now()
        self.ai_enrichment_status = "completed"
        self.ai_enrichment_error = None
        self.raw_intelligence = intelligence
        self.updated_at = datetime.now()

    def mark_enrichment_failed(self, error: str) -> None:
        """Mark enrichment as failed with error message"""
        self.ai_enrichment_status = "failed"
        self.ai_enrichment_error = error
        self.ai_enriched_at = datetime.now()
        self.updated_at = datetime.now()

    def mark_enrichment_processing(self) -> None:
        """Mark enrichment as in progress"""
        self.ai_enrichment_status = "processing"
        self.updated_at = datetime.now()

    @property
    def is_enriched(self) -> bool:
        """Check if customer has been AI-enriched"""
        return self.ai_enrichment_status == "completed"

    @property
    def needs_enrichment(self) -> bool:
        """Check if customer needs AI enrichment"""
        return self.website is not None and self.ai_enrichment_status in (
            "pending",
            "failed",
        )
