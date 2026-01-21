"""
Response schemas - Pydantic models for API output
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """Base response with success flag"""

    success: bool = True


class ErrorResponse(BaseModel):
    """Error response"""

    success: bool = False
    error: str
    status_code: int = 500


class HealthResponse(BaseModel):
    """Health check response"""

    status: str = "healthy"
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)
    abilities: List[str] = []


class AbilitiesResponse(BaseModel):
    """List of available abilities"""

    success: bool = True
    abilities: List[str]
    count: int


class WebsiteIntelligenceResponse(BaseModel):
    """Website intelligence extraction response"""

    success: bool = True
    website_url: str
    analysis_date: str
    brand_identity: Dict[str, Any] = {}
    brand_voice: Dict[str, Any] = {}
    products: Dict[str, Any] = {}
    value_propositions: Dict[str, Any] = {}
    promotions: Dict[str, Any] = {}
    audience: Dict[str, Any] = {}
    technical: Dict[str, Any] = {}
    seo: Dict[str, Any] = {}
    trust_signals: Dict[str, Any] = {}
    email_campaign_recommendations: Dict[str, Any] = {}


class EmailDesignSchema(BaseModel):
    """Single email design"""

    design_id: str
    persona: str
    subject_line: str
    preview_text: str
    headline: str
    body_copy: str
    cta_text: str
    cta_url: str
    color_scheme: Dict[str, str]
    typography: Dict[str, str]
    layout: str
    html_template: str
    design_rationale: str
    target_audience: str
    estimated_engagement: str
    created_at: str


class EmailDesignResponse(BaseModel):
    """Email design generation response"""

    success: bool = True
    num_designs: int
    campaign_goal: str
    designs: List[EmailDesignSchema]
    metadata: Dict[str, Any] = {}


class FullCampaignResponse(BaseModel):
    """Full campaign pipeline response"""

    success: bool = True
    website_url: str
    campaign_goal: str
    intelligence: Dict[str, Any]
    designs: Dict[str, Any]
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
